#!/usr/bin/env python3
"""
Voxa Client - Локальный клиент для голосового ассистента Voxa

Этот скрипт:
- Слушает микрофон и распознаёт речь пользователя в текст
- Отправляет текст на сервер Voxa (HTTP POST запрос к эндпоинту /chat)
- Принимает ответ от сервера и озвучивает его с помощью синтеза речи
- Поддерживает локальные команды (выход, повтори) и корректно обрабатывает серверные команды
- Работает в текстовом режиме, если аудио-библиотеки недоступны

Поддерживаемые аудио-бэкенды:
- PyAudio (требуется системная библиотека PortAudio)
- sounddevice (альтернатива для Linux, требует PortAudio)
- Текстовый режим (работает везде)
"""

import sys
import uuid
import json
import time
from typing import Optional

# Импорт requests (обязательная зависимость)
try:
    import requests
except ImportError:
    print("❌ Ошибка: не установлен модуль 'requests'. Выполните: pip install requests")
    sys.exit(1)

# Попытка импорта speech_recognition
speech_recognition_available = False
sr = None
try:
    import speech_recognition as sr
    speech_recognition_available = True
except ImportError:
    print("⚠️ Модуль 'speech_recognition' не установлен. Будет доступен только текстовый режим.")
    print("   Для установки: pip install SpeechRecognition")

# Попытка импорта pyttsx3
pyttsx3_available = False
pyttsx3 = None
try:
    import pyttsx3
    pyttsx3_available = True
except ImportError:
    print("⚠️ Модуль 'pyttsx3' не установлен. Ответы будут только в тексте.")
    print("   Для установки: pip install pyttsx3")

# Попытка импорта sounddevice и numpy (для альтернативного метода записи)
sounddevice_available = False
sd = None
np = None
try:
    import sounddevice as sd
    import numpy as np
    sounddevice_available = True
except ImportError:
    pass
except OSError as e:
    # PortAudio библиотека не найдена
    if "PortAudio" in str(e):
        print(f"⚠️ sounddevice установлен, но библиотека PortAudio не найдена: {e}")
        print("   Для Bazzite/Fedora: sudo rpm-ostree install portaudio")
        print("   После установки перезагрузите систему: systemctl reboot")
        sounddevice_available = False
    else:
        raise

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
        self.recognizer = sr.Recognizer() if sr else None
        self.microphone = None
        self.engine = None
        
        # Настройка распознавателя (если доступен)
        if self.recognizer:
            self.recognizer.energy_threshold = ENERGY_THRESHOLD
            self.recognizer.pause_threshold = PAUSE_THRESHOLD

    def setup_microphone(self) -> bool:
        """Проверка и настройка микрофона"""
        if not speech_recognition_available:
            print("⚠️ Распознавание речи недоступно. Будет использоваться текстовый режим.")
            return False
        
        # Попытка использовать стандартный Microphone (PyAudio)
        try:
            self.microphone = sr.Microphone()  # type: ignore
            # Калибровка фонового шума
            print("🎤 Калибровка микрофона (подождите 1 секунду)...")
            with self.microphone as source:  # type: ignore
                self.recognizer.adjust_for_ambient_noise(source, duration=1)  # type: ignore
            print("✅ Микрофон готов к работе (PyAudio)")
            return True
        except Exception as e:
            print(f"⚠️ Ошибка при инициализации PyAudio: {e}")
            
            # Если PyAudio не работает, пробуем sounddevice
            if sounddevice_available:
                print("🔄 sounddevice доступен, но требует PortAudio для работы с микрофоном.")
                print("   Для полноценной работы установите PortAudio:")
                print("   sudo rpm-ostree install portaudio && systemctl reboot")
                return False
            else:
                print("❌ Ни PyAudio, ни sounddevice не доступны.")
                print("   Установите один из вариантов:")
                print("   - PyAudio: sudo rpm-ostree install portaudio-devel python3-pyaudio (Bazzite/Fedora)")
                print("   - sounddevice: pip install sounddevice numpy (но всё равно нужен PortAudio)")
                return False

    def setup_tts(self) -> bool:
        """Настройка синтеза речи"""
        if not pyttsx3_available:
            print("⚠️ Синтез речи недоступен. Ответы будут выводиться только текстом.")
            return False
            
        try:
            self.engine = pyttsx3.init()  # type: ignore
            self.engine.setProperty('rate', TTS_RATE)  # type: ignore
            self.engine.setProperty('volume', TTS_VOLUME)  # type: ignore
            
            # Попытка выбрать русский голос
            voices = self.engine.getProperty('voices')  # type: ignore
            for voice in voices:
                if 'ru' in voice.languages or 'Russian' in voice.name:
                    self.engine.setProperty('voice', voice.id)  # type: ignore
                    break
            
            print("✅ Синтез речи настроен")
            return True
        except Exception as e:
            print(f"❌ Ошибка при инициализации синтеза речи: {e}")
            return False

    def listen(self) -> Optional[str]:
        """
        Прослушивание микрофона и распознавание речи.
        
        Если аудио-библиотеки недоступны, запрашивает текст вручную.
        """
        # Если микрофон не настроен, используем текстовый ввод
        if self.microphone is None or not speech_recognition_available:
            try:
                text = input("📝 Введите текст (или 'выход'): ").strip()
                return text if text else None
            except EOFError:
                return None
            except KeyboardInterrupt:
                raise
        
        # Метод 1: Используем стандартный Microphone (PyAudio)
        try:
            with self.microphone as source:  # type: ignore
                print("🎤 Говорите...")
                audio = self.recognizer.listen(source, timeout=10)  # type: ignore
            
            return self._recognize_audio(audio)
            
        except sr.WaitTimeoutError:  # type: ignore
            print("⏱️ Время ожидания истекло. Попробуйте снова.")
            return None
        except Exception as e:
            print(f"⚠️ Ошибка при прослушивании: {e}")
            # Возвращаемся к текстовому вводу
            try:
                text = input("📝 Введите текст (или 'выход'): ").strip()
                return text if text else None
            except (EOFError, KeyboardInterrupt):
                return None

    def _listen_with_sounddevice(self) -> Optional[str]:
        """
        Альтернативный метод прослушивания через sounddevice.
        Требует установленную библиотеку PortAudio.
        """
        if not sounddevice_available:
            print("❌ sounddevice недоступен.")
            return None
        
        print("🎤 Говорите (режим sounddevice)...")
        
        try:
            # Параметры записи
            sample_rate = 16000  # Частота дискретизации для Google Speech API
            duration = 5  # Максимальная длительность записи (секунды)
            
            # Запись аудио с микрофона
            audio_data = sd.rec(  # type: ignore
                int(sample_rate * duration),
                samplerate=sample_rate,
                channels=1,
                dtype=np.int16  # type: ignore
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
                    rms = np.sqrt(np.mean(recent_audio ** 2))  # type: ignore
                    
                    if rms > silence_threshold:
                        last_speech_time = time.time()
                    elif time.time() - last_speech_time > silence_duration:
                        break  # Тишина более silence_duration секунд
                
                time.sleep(0.1)
            
            sd.stop()  # type: ignore
            
            # Преобразуем в формат для speech_recognition
            audio_bytes = audio_data.tobytes()
            audio = sr.AudioData(audio_bytes, sample_rate, 2)  # 2 bytes per sample (int16)  # type: ignore
            
            return self._recognize_audio(audio)
            
        except Exception as e:
            print(f"❌ Ошибка при прослушивании (sounddevice): {e}")
            return None

    def _recognize_audio(self, audio) -> Optional[str]:  # type: ignore
        """
        Распознавание аудио с использованием Google Web Speech API.
        """
        if not speech_recognition_available or not self.recognizer:
            return None
            
        print("⏳ Распознавание...")
        
        try:
            # Использование Google Web Speech API
            text = self.recognizer.recognize_google(audio, language="ru-RU")  # type: ignore
            return text.strip()
            
        except sr.UnknownValueError:  # type: ignore
            print("❓ Не удалось распознать речь. Попробуйте повторить.")
            return None
        except sr.RequestError as e:  # type: ignore
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
                self.engine.say(text)  # type: ignore
                self.engine.runAndWait()  # type: ignore
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
        print("🎙️ Voxa Client запущен")
        print(f"🔗 Сервер: {SERVER_URL}")
        print(f"🆔 Session ID: {self.session_id}")
        
        # Информируем о доступных режимах
        if not speech_recognition_available:
            print("⚠️ Режим: ТОЛЬКО ТЕКСТОВЫЙ (установите SpeechRecognition для голоса)")
        elif self.setup_microphone():
            print("🎤 Режим: ГОЛОСОВОЙ (PyAudio)")
        else:
            print("⌨️ Режим: ТЕКСТОВЫЙ (микрофон недоступен)")
            
        if not pyttsx3_available:
            print("📝 Ответы: ТОЛЬКО ТЕКСТ (установите pyttsx3 для озвучки)")
        else:
            print("🔊 Ответы: С ОЗВУЧКОЙ")
            
        print("=" * 50)
        
        # Инициализация TTS
        self.setup_tts()
        
        if pyttsx3_available:
            self.speak("Voxa готова к работе. Говорите!")
        else:
            print("\nVoxa готова к работе. Введите текст или 'выход'.\n")
        
        try:
            while True:
                # Прослушивание или ввод текста
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
            if pyttsx3_available:
                self.speak("До свидания!")
            else:
                print("\n👋 До свидания!")


def main():
    """Точка входа"""
    client = VoxaClient()
    client.run()


if __name__ == "__main__":
    main()
