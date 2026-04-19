#!/usr/bin/env python3
"""
Voxa Client - Локальный клиент для голосового ассистента Voxa

Этот скрипт:
- Слушает микрофон и распознаёт речь пользователя в текст
- Отправляет текст на сервер Voxa (HTTP POST запрос к эндпоинту /chat)
- Принимает ответ от сервера и озвучивает его с помощью синтеза речи
- Поддерживает локальные команды (выход, повтори) и корректно обрабатывает серверные команды
"""

import sys
import uuid
import json
import time
from typing import Optional

import speech_recognition as sr
import pyttsx3
import requests

from config import (
    SERVER_URL,
    CHAT_ENDPOINT,
    RECOGNITION_ENGINE,
    ENERGY_THRESHOLD,
    PAUSE_THRESHOLD,
    TTS_RATE,
    TTS_VOLUME,
    EXIT_COMMANDS,
    REPEAT_COMMANDS,
    CLEAR_CHAT_COMMANDS,
)


class VoxaClient:
    """Основной класс клиента Voxa"""

    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.last_response: Optional[str] = None
        self.recognizer = sr.Recognizer()
        self.microphone: Optional[sr.Microphone] = None
        self.engine: Optional[pyttsx3.Engine] = None
        
        # Настройка распознавателя
        self.recognizer.energy_threshold = ENERGY_THRESHOLD
        self.recognizer.pause_threshold = PAUSE_THRESHOLD

    def setup_microphone(self) -> bool:
        """Проверка и настройка микрофона"""
        try:
            self.microphone = sr.Microphone()
            # Калибровка фонового шума
            print("🎤 Калибровка микрофона (подождите 1 секунду)...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Микрофон готов к работе")
            return True
        except Exception as e:
            print(f"❌ Ошибка при инициализации микрофона: {e}")
            return False

    def setup_tts(self) -> bool:
        """Настройка синтеза речи"""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', TTS_RATE)
            self.engine.setProperty('volume', TTS_VOLUME)
            
            # Попытка выбрать русский голос
            voices = self.engine.getProperty('voices')
            for voice in voices:
                if 'ru' in voice.languages or 'Russian' in voice.name:
                    self.engine.setProperty('voice', voice.id)
                    break
            
            print("✅ Синтез речи настроен")
            return True
        except Exception as e:
            print(f"❌ Ошибка при инициализации синтеза речи: {e}")
            return False

    def listen(self) -> Optional[str]:
        """Прослушивание микрофона и распознавание речи"""
        if not self.microphone:
            print("❌ Микрофон не инициализирован")
            return None

        try:
            with self.microphone as source:
                print("🎤 Говорите...")
                audio = self.recognizer.listen(source, timeout=10)
            
            print("⏳ Распознавание...")
            
            # Использование Google Web Speech API
            text = self.recognizer.recognize_google(audio, language="ru-RU")
            return text.strip()
            
        except sr.WaitTimeoutError:
            print("⏱️ Время ожидания истекло. Попробуйте снова.")
            return None
        except sr.UnknownValueError:
            print("❓ Не удалось распознать речь. Попробуйте повторить.")
            return None
        except sr.RequestError as e:
            print(f"❌ Ошибка сервиса распознавания: {e}")
            return None
        except Exception as e:
            print(f"❌ Ошибка при прослушивании: {e}")
            return None

    def speak(self, text: str) -> None:
        """Озвучивание текста"""
        if not text:
            return
            
        print(f"Voxa: {text}")
        
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"⚠️ Ошибка синтеза речи: {e}")

    def send_to_server(self, text: str) -> Optional[str]:
        """Отправка текста на сервер и получение ответа"""
        url = f"{SERVER_URL}{CHAT_ENDPOINT}"
        
        payload = {
            "text": text,
            "session_id": self.session_id
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            return data.get("response", "Нет ответа от сервера")
            
        except requests.exceptions.ConnectionError:
            print("❌ Сервер Voxa не отвечает. Проверьте подключение.")
            return None
        except requests.exceptions.Timeout:
            print("❌ Превышено время ожидания ответа от сервера.")
            return None
        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP ошибка: {e}")
            return None
        except json.JSONDecodeError:
            print("❌ Ошибка при парсинге ответа сервера.")
            return None
        except Exception as e:
            print(f"❌ Неожиданная ошибка: {e}")
            return None

    def is_exit_command(self, text: str) -> bool:
        """Проверка команды выхода"""
        text_lower = text.lower()
        return any(cmd in text_lower for cmd in EXIT_COMMANDS)

    def is_repeat_command(self, text: str) -> bool:
        """Проверка команды повтора"""
        text_lower = text.lower()
        return any(cmd in text_lower for cmd in REPEAT_COMMANDS)

    def process_command(self, text: str) -> bool:
        """
        Обработка локальных команд.
        Возвращает True, если команда была обработана локально.
        """
        # Команда выхода
        if self.is_exit_command(text):
            self.speak("👋 До свидания!")
            return True
        
        # Команда повтора
        if self.is_repeat_command(text):
            if self.last_response:
                print(f"[Повтор] {self.last_response}")
                self.speak(self.last_response)
            else:
                self.speak("Нечего повторять. Задайте вопрос сначала.")
            return True
        
        return False

    def run(self) -> None:
        """Основной цикл работы клиента"""
        print("=" * 50)
        print("🎙️  Voxa Client запущен")
        print(f"🔗 Сервер: {SERVER_URL}")
        print(f"🆔 Session ID: {self.session_id}")
        print("=" * 50)
        
        # Инициализация
        if not self.setup_microphone():
            print("❌ Не удалось инициализировать микрофон. Выход.")
            return
        
        if not self.setup_tts():
            print("❌ Не удалось инициализировать синтез речи. Выход.")
            return
        
        self.speak("Voxa готова к работе. Говорите!")
        
        try:
            while True:
                # Прослушивание
                text = self.listen()
                
                if not text:
                    continue
                
                print(f"Вы: {text}")
                
                # Обработка локальных команд
                if self.process_command(text):
                    # Если это была команда выхода
                    if self.is_exit_command(text):
                        break
                    continue
                
                # Отправка на сервер
                response = self.send_to_server(text)
                
                if response:
                    self.last_response = response
                    self.speak(response)
                else:
                    self.speak("Извините, возникла проблема с соединением.")
                    
        except KeyboardInterrupt:
            print("\n\n👋 Работа завершена пользователем")
        finally:
            self.speak("До свидания!")


def main():
    """Точка входа"""
    client = VoxaClient()
    client.run()


if __name__ == "__main__":
    main()
