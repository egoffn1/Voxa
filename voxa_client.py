#!/usr/bin/env python3
"""
Voxa Client v3.0 - Работает с обновленным сервером (бинарный MP3 ответ)
Использует ffplay или mpv для воспроизведения аудио от сервера.
НЕ использует локальные библиотеки синтеза речи (pyttsx3, torch, silero, simpleaudio).

Для работы аудио на Linux (Bazzite/Fedora) установите ffmpeg:
    sudo dnf install -y ffmpeg
"""

import sys
import uuid
import json
import time
import os
import tempfile
import subprocess
from typing import Optional

import speech_recognition as sr
import requests

from config import (
    SERVER_URL,
    CHAT_ENDPOINT,
    ENERGY_THRESHOLD,
    PAUSE_THRESHOLD,
    WAKE_WORD_ENABLED,
    WAKE_WORDS,
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

    def _play_audio_file(self, file_path: str) -> bool:
        """
        Воспроизводит аудиофайл через ffplay (ffmpeg) или mpv.
        Возвращает True если воспроизведение успешно, False иначе.
        """
        # Пробуем ffplay (из пакета ffmpeg)
        try:
            result = subprocess.run(
                ["ffplay", "-nodisp", "-autoexit", file_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60
            )
            return True
        except FileNotFoundError:
            pass  # ffplay не найден, пробуем mpv
        except subprocess.TimeoutExpired:
            print("⚠️ Превышено время ожидания воспроизведения")
            return False
        except Exception as e:
            print(f"⚠️ Ошибка ffplay: {e}")
        
        # Пробуем mpv
        try:
            result = subprocess.run(
                ["mpv", "--no-video", file_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60
            )
            return True
        except FileNotFoundError:
            print("❌ Не найден ffplay или mpv. Установите ffmpeg:")
            print("   sudo dnf install -y ffmpeg")
            return False
        except subprocess.TimeoutExpired:
            print("⚠️ Превышено время ожидания воспроизведения")
            return False
        except Exception as e:
            print(f"⚠️ Ошибка mpv: {e}")
            return False

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

    def send_to_server(self, text: str) -> bool:
        """
        Отправка запроса на сервер и воспроизведение аудио-ответа.
        Сервер возвращает бинарный MP3 файл.
        """
        url = f"{SERVER_URL}{CHAT_ENDPOINT}"
        payload = {"message": text, "session_id": self.session_id}
        
        temp_file = None
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 400:
                print(f"⚠️ Ошибка сервера: {response.text}")
                return False
            
            response.raise_for_status()
            
            # Проверяем тип контента (audio/mpeg или application/octet-stream)
            content_type = response.headers.get("Content-Type", "")
            if not (content_type.startswith("audio/") or 
                    content_type.startswith("application/octet-stream")):
                print(f"⚠️ Неожиданный тип ответа: {content_type}")
                return False
            
            # Сохраняем во временный файл
            temp_fd, temp_file = tempfile.mkstemp(suffix=".mp3")
            try:
                with os.fdopen(temp_fd, 'wb') as f:
                    f.write(response.content)
                
                print("🔊 Воспроизведение ответа...")
                if self._play_audio_file(temp_file):
                    return True
                else:
                    return False
            finally:
                # Удаляем временный файл после воспроизведения
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        print(f"⚠️ Не удалось удалить временный файл: {e}")
                        
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Ошибка подключения к серверу: {e}")
            return False
        except requests.exceptions.Timeout:
            print("❌ Превышено время ожидания ответа от сервера")
            return False
        except Exception as e:
            print(f"❌ Ошибка при отправке запроса: {e}")
            return False
        finally:
            # Дополнительная страховка удаления файла
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

    def is_exit_command(self, text: str) -> bool:
        return any(cmd in text.lower() for cmd in EXIT_COMMANDS)

    def run(self):
        print("=" * 50)
        print("🚀 Voxa Client v3.0 (Server Audio Response)")
        print(f"🔗 Сервер: {SERVER_URL}")
        print("=" * 50)
        print("💡 Для воспроизведения аудио требуется ffmpeg или mpv")
        print("   Установка: sudo dnf install -y ffmpeg")
        print("=" * 50)

        if not self.setup_microphone():
            return

        print("✅ Система запущена. Я слушаю.")
        
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
                    print("👋 До свидания!")
                    break
                
                if not self.send_to_server(text):
                    print("⚠️ Ошибка связи с сервером.")

        except KeyboardInterrupt:
            print("\n👋 Выключение...")


if __name__ == "__main__":
    client = VoxaClient()
    client.run()