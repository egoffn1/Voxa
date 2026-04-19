#!/usr/bin/env python3
"""
Voxa Client v2.1 - Исправленная загрузка Silero и воспроизведение через torchaudio
"""

import sys
import uuid
import json
import time
import os
import glob
import threading
from typing import Optional

import speech_recognition as sr
import requests
import numpy as np

# Зависимости для Silero
try:
    import torch
    import torchaudio
    SILERO_AVAILABLE = True
except ImportError:
    SILERO_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

from config import (
    SERVER_URL,
    CHAT_ENDPOINT,
    ENERGY_THRESHOLD,
    PAUSE_THRESHOLD,
    WAKE_WORD_ENABLED,
    WAKE_WORDS,
    TTS_ENGINE,
    SILERO_SPEAKER,
    EXIT_COMMANDS,
    REPEAT_COMMANDS,
)

class VoxaClient:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.last_response: Optional[str] = None
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_active = False
        
        self.recognizer.energy_threshold = ENERGY_THRESHOLD
        self.recognizer.pause_threshold = PAUSE_THRESHOLD
        self.recognizer.dynamic_energy_threshold = True

        self.tts_model = None
        self.pyttsx_engine = None
        self._setup_tts()

    def _setup_tts(self):
        """Инициализация движка синтеза речи"""
        if TTS_ENGINE == "silero" and SILERO_AVAILABLE:
            print("🧠 Загрузка нейросетевого голоса (Silero)...")
            try:
                # Загрузка модели Silero через torch.hub
                self.tts_model, example_text = torch.hub.load(
                    repo_or_dir='snakers4/silero-models',
                    model='silero_tts',
                    language='ru',
                    speaker=SILERO_SPEAKER
                )
                print("✅ Нейро-голос готов")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки Silero: {e}. Используем pyttsx3.")
                self._init_pyttsx3()
        else:
            self._init_pyttsx3()

    def _init_pyttsx3(self):
        """Инициализация стандартного голоса"""
        if PYTTSX3_AVAILABLE:
            try:
                self.pyttsx_engine = pyttsx3.init()
                voices = self.pyttsx_engine.getProperty('voices')
                for voice in voices:
                    if 'ru' in str(voice.languages).lower():
                        self.pyttsx_engine.setProperty('voice', voice.id)
                        break
                print("✅ Стандартный голос готов")
            except Exception as e:
                print(f"❌ Ошибка pyttsx3: {e}")
        else:
            print("❌ Нет доступных движков синтеза речи!")

    def setup_microphone(self) -> bool:
        """Настройка микрофона"""
        try:
            self.microphone = sr.Microphone()
            print("🎤 Калибровка микрофона...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print("✅ Микрофон готов")
            return True
        except Exception as e:
            print(f"❌ Ошибка микрофона: {e}")
            return False

    def listen_for_wake_word(self) -> bool:
        """Слушает и ждет имя ассистента"""
        if not WAKE_WORD_ENABLED:
            return True

        print("💤 Ожидание имени 'Вокс'...")
        
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=1, phrase_time_limit=2.0)
            
            try:
                text = self.recognizer.recognize_google(audio, language="ru-RU").lower()
                print(f"👂 Услышано: '{text}'")
                
                for word in WAKE_WORDS:
                    if word in text:
                        print("✨ АКТИВАЦИЯ!")
                        return True
            except sr.UnknownValueError:
                pass
            except sr.RequestError:
                pass
                
        except sr.WaitTimeoutError:
            pass
        except Exception as e:
            print(f"⚠️ Ошибка ожидания: {e}")
            
        return False

    def listen(self) -> Optional[str]:
        """Прослушивание команды"""
        try:
            with self.microphone as source:
                print("🎤 Слушаю...")
                audio = self.recognizer.listen(source, timeout=10)
            
            print("⏳ Распознавание...")
            text = self.recognizer.recognize_google(audio, language="ru-RU")
            return text.strip()
            
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except Exception as e:
            print(f"❌ Ошибка записи: {e}")
            return None

    def speak(self, text: str) -> None:
        """Озвучивание текста"""
        if not text:
            return
            
        print(f"Voxa: {text}")
        
        if TTS_ENGINE == "silero" and self.tts_model:
            self._speak_silero(text)
        elif self.pyttsx_engine:
            self._speak_pyttsx3(text)

    def _speak_silero(self, text: str):
        """Генерация и воспроизведение голоса Silero через torchaudio"""
        try:
            # Генерация аудио
            audio = self.tts_model.apply_tts(
                text=text,
                speaker=SILERO_SPEAKER,
                sample_rate=48000
            )
            
            # Воспроизведение через torchaudio (не требует внешних файлов)
            torchaudio.play(audio, sample_rate=48000)
            
        except Exception as e:
            print(f"⚠️ Ошибка нейро-голоса: {e}")
            self._speak_pyttsx3(text)

    def _speak_pyttsx3(self, text: str):
        """Стандартное озвучивание"""
        try:
            self.pyttsx_engine.say(text)
            self.pyttsx_engine.runAndWait()
        except Exception as e:
            print(f"⚠️ Ошибка голоса: {e}")

    def send_to_server(self, text: str) -> Optional[str]:
        """Отправка запроса на сервер"""
        url = f"{SERVER_URL}{CHAT_ENDPOINT}"
        payload = {"message": text, "session_id": self.session_id}
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 400:
                print(f"⚠️ Ошибка сервера: {response.text}")
                return None
            response.raise_for_status()
            return response.json().get("response")
        except Exception as e:
            print(f"❌ Сетевая ошибка: {e}")
            return None

    def is_exit_command(self, text: str) -> bool:
        return any(cmd in text.lower() for cmd in EXIT_COMMANDS)

    def run(self):
        print("="*50)
        print("🚀 Voxa Client v2.1 (Silero Fixed)")
        print(f"🔗 Сервер: {SERVER_URL}")
        print("="*50)

        if not self.setup_microphone():
            return

        self.speak("Система запущена. Я слушаю.")
        
        try:
            while True:
                if WAKE_WORD_ENABLED:
                    if not self.listen_for_wake_word():
                        continue
                
                text = self.listen()
                if not text:
                    continue

                print(f"Вы: {text}")

                if self.is_exit_command(text):
                    self.speak("До свидания!")
                    break
                
                response = self.send_to_server(text)
                if response:
                    self.last_response = response
                    self.speak(response)
                else:
                    self.speak("Ошибка связи с сервером.")

        except KeyboardInterrupt:
            print("\n👋 Выключение...")

if __name__ == "__main__":
    client = VoxaClient()
    client.run()