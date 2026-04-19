#!/usr/bin/env python3
"""
Voxa Client - Локальный клиент для голосового ассистента Voxa

Этот скрипт:
- Слушает микрофон и распознаёт речь пользователя в текст
- Отправляет текст на сервер Voxa (HTTP POST запрос к эндпоинту /chat)
- Принимает ответ от сервера и озвучивает его с помощью синтеза речи
- Поддерживает локальные команды (выход, повтори) и корректно обрабатывает серверные команды

Поддерживаемые аудио-бэкенды:
- PyAudio (требуется системная библиотека PortAudio)
- sounddevice (альтернатива для Linux, проще в установке)
"""

import sys
import uuid
import json
import time
from typing import Optional

import speech_recognition as sr
import pyttsx3
import requests

# Попытка импорта sounddevice для альтернативного метода прослушивания
try:
    import sounddevice as sd
    import numpy as np
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

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
        # Попытка использовать стандартный Microphone (PyAudio)
        try:
            self.microphone = sr.Microphone()
            # Калибровка фонового шума
            print("🎤 Калибровка микрофона (подождите 1 секунду)...")
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Микрофон готов к работе (PyAudio)")
            return True
        except Exception as e:
            print(f"⚠️ Ошибка при инициализации PyAudio: {e}")
            
            # Если PyAudio не работает, пробуем sounddevice
            if SOUNDDEVICE_AVAILABLE:
                print("🔄 Пробуем альтернативный метод через sounddevice...")
                # sounddevice не требует специальной инициализации для speech_recognition
                # Мы будем использовать его в методе listen()
                print("✅ sounddevice доступен. Будет использоваться альтернативный метод прослушивания.")
                return True
            else:
                print("❌ Ни PyAudio, ни sounddevice не доступны.")
                print("   Установите один из вариантов:")
                print("   - PyAudio: rpm-ostree install portaudio-devel python3-pyaudio (Bazzite/Fedora)")
                print("   - sounddevice: pip install sounddevice numpy")
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
        """
        Прослушивание микрофона и распознавание речи.
        
        Поддерживает два метода:
        1. Стандартный через PyAudio (sr.Microphone)
        2. Альтернативный через sounddevice (для Linux без PyAudio)
        """
        # Метод 1: Используем стандартный Microphone (PyAudio)
        if self.microphone is not None:
            try:
                with self.microphone as source:
                    print("🎤 Говорите...")
                    audio = self.recognizer.listen(source, timeout=10)
                
                return self._recognize_audio(audio)
                
            except sr.WaitTimeoutError:
                print("⏱️ Время ожидания истекло. Попробуйте снова.")
                return None
            except Exception as e:
                print(f"⚠️ Ошибка при прослушивании (PyAudio): {e}")
                # Если есть sounddevice, пробуем альтернативный метод
                if SOUNDDEVICE_AVAILABLE:
                    print("🔄 Переключаемся на sounddevice...")
                    return self._listen_with_sounddevice()
                return None
        
        # Метод 2: Используем sounddevice (если PyAudio недоступен)
        elif SOUNDDEVICE_AVAILABLE:
            return self._listen_with_sounddevice()
        
        else:
            print("❌ Микрофон не инициализирован и нет доступных аудио-бэкендов.")
            return None

    def _listen_with_sounddevice(self) -> Optional[str]:
        """
        Альтернативный метод прослушивания через sounddevice.
        
        Записывает аудио с микрофона используя sounddevice и numpy,
        затем передаёт в speech_recognition для распознавания.
        """
        if not SOUNDDEVICE_AVAILABLE:
            print("❌ sounddevice недоступен.")
            return None
        
        print("🎤 Говорите (режим sounddevice)...")
        
        try:
            # Параметры записи
            sample_rate = 16000  # Частота дискретизации для Google Speech API
            duration = 5  # Максимальная длительность записи (секунды)
            
            # Запись аудио с микрофона
            audio_data = sd.rec(
                int(sample_rate * duration),
                samplerate=sample_rate,
                channels=1,
                dtype=np.int16
            )
            
            # Ждём завершения записи или прерывания по тишине
            start_time = time.time()
            silence_threshold = 500  # Порог тишины
            silence_duration = 0.8   # Длительность тишины для окончания записи
            
            last_speech_time = start_time
            
            while True:
                if time.time() - start_time > duration:
                    break  # Превышена максимальная длительность
                
                # Проверяем уровень громкости для обнаружения конца речи
                if len(audio_data) > int(sample_rate * 0.1):
                    # Получаем последние 0.1 секунды записи
                    recent_audio = audio_data[-int(sample_rate * 0.1):]
                    rms = np.sqrt(np.mean(recent_audio ** 2))
                    
                    if rms > silence_threshold:
                        last_speech_time = time.time()
                    elif time.time() - last_speech_time > silence_duration:
                        break  # Тишина более silence_duration секунд
                
                time.sleep(0.1)
            
            sd.stop()
            
            # Преобразуем в формат для speech_recognition
            audio_bytes = audio_data.tobytes()
            audio = sr.AudioData(audio_bytes, sample_rate, 2)  # 2 bytes per sample (int16)
            
            return self._recognize_audio(audio)
            
        except Exception as e:
            print(f"❌ Ошибка при прослушивании (sounddevice): {e}")
            return None

    def _recognize_audio(self, audio: sr.AudioData) -> Optional[str]:
        """
        Распознавание аудио с использованием Google Web Speech API.
        """
        print("⏳ Распознавание...")
        
        try:
            # Использование Google Web Speech API
            text = self.recognizer.recognize_google(audio, language="ru-RU")
            return text.strip()
            
        except sr.UnknownValueError:
            print("❓ Не удалось распознать речь. Попробуйте повторить.")
            return None
        except sr.RequestError as e:
            print(f"❌ Ошибка сервиса распознавания: {e}")
            return None
        except Exception as e:
            print(f"❌ Ошибка при распознавании: {e}")
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
