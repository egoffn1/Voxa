# Voxa Client - Локальный голосовой клиент

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Локальный клиент для голосового ассистента **Voxa**, который позволяет взаимодействовать с сервером через микрофон и динамики вашего компьютера.

## 🎯 Возможности

- 🎤 **Распознавание речи** - преобразование голоса в текст через Google Web Speech API
- 🔊 **Синтез речи** - озвучивание ответов ассистента через pyttsx3 (офлайн)
- 💬 **Интерактивный диалог** - бесконечный цикл общения с сервером
- ⚡ **Локальные команды**:
  - `"выход"`, `"пока"`, `"завершить работу"` - завершение работы клиента
  - `"повтори"`, `"еще раз"` - повтор последнего ответа без запроса к серверу
  - `"очисти чат"`, `"забудь всё"` - очистка истории диалога (отправляется на сервер)
- 🛡️ **Обработка ошибок** - корректная обработка сетевых сбоев и ошибок распознавания

## 📋 Требования

- Python 3.10 или выше
- Микрофон
- Интернет-соединение (для распознавания речи через Google API)
- Доступ к серверу Voxa

### Системные зависимости для работы с аудио

Для работы микрофона требуется один из следующих вариантов:

#### Вариант 1: PyAudio (классический, требует PortAudio)

**Linux (Fedora/Bazzite):**
```bash
# Для Bazzite (Fedora Atomic) требуется rpm-ostree
rpm-ostree install portaudio-devel python3-pyaudio
# После установки перезагрузите систему:
systemctl reboot
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

**macOS:**
```bash
brew install portaudio
pip install pyaudio
```

**Windows:**
```bash
pip install pipwin
pipwin install pyaudio
```

#### Вариант 2: sounddevice (рекомендуется для Linux)

Более простой вариант для Linux, не требует системных зависимостей:

```bash
pip install sounddevice numpy
```

**Примечание для Bazzite/Fedora Atomic:** Если у вас возникают проблемы с установкой PyAudio, используйте sounddevice — он проще в установке и работает без системных библиотек.

## 🚀 Установка

### 1. Клонирование репозитория

```bash
git clone https://github.com/egoffn1/Voxa.git
cd Voxa
```

### 2. Создание виртуального окружения

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей

#### Общие зависимости

```bash
pip install -r requirements.txt
```

Этот файл уже содержит все необходимые зависимости, включая `sounddevice` для альтернативного метода работы с микрофоном.

#### Если используете PyAudio (опционально)

Если вы хотите использовать классический метод через PyAudio вместо sounddevice:

**Windows:**
```bash
pip install pipwin
pipwin install pyaudio
```

Или скачайте готовый wheel файл с [Gohlke's site](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio):
```bash
pip install PyAudio‑0.2.14‑cp310‑cp310‑win_amd64.whl
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install portaudio19-dev python3-pyaudio
pip install pyaudio
```

**macOS:**
```bash
brew install portaudio
pip install pyaudio
```

**Linux (Fedora/Bazzite):**
```bash
# Для Bazzite требуется rpm-ostree
rpm-ostree install portaudio-devel python3-pyaudio
# После установки перезагрузите систему:
systemctl reboot
pip install pyaudio
```

> **💡 Совет для Bazzite/Fedora Atomic:** Рекомендуется использовать `sounddevice` вместо PyAudio, так как он не требует системных зависимостей и проще в установке. Просто выполните `pip install -r requirements.txt` — sounddevice уже включён в зависимости.

## ⚙️ Настройка

### Конфигурация сервера

Откройте файл `config.py` и укажите URL вашего сервера Voxa:

```python
SERVER_URL = "http://localhost:5000"  # Замените на ваш адрес
```

Если сервер развернут в интернете, используйте полный URL:
```python
SERVER_URL = "https://voxa-server.example.com"
```

### Дополнительные настройки

В `config.py` можно настроить:

```python
# Распознавание речи
ENERGY_THRESHOLD = 4000  # Порог чувствительности микрофона
PAUSE_THRESHOLD = 0.8    # Пауза для определения конца фразы (сек)

# Синтез речи
TTS_RATE = 150           # Скорость речи (слова в минуту)
TTS_VOLUME = 1.0         # Громкость (0.0 - 1.0)

# Локальные команды
EXIT_COMMANDS = ["выход", "пока", "завершить работу"]
REPEAT_COMMANDS = ["повтори", "еще раз"]
```

## 🎮 Использование

### Запуск клиента

```bash
python voxa_client.py
```

### Пример сеанса связи

```
==================================================
🎙️  Voxa Client запущен
🔗 Сервер: http://localhost:5000
🆔 Session ID: 550e8400-e29b-41d4-a716-446655440000
==================================================
🎤 Калибровка микрофона (подождите 1 секунду)...
✅ Микрофон готов к работе
✅ Синтез речи настроен
Voxa: Voxa готова к работе. Говорите!

🎤 Говорите...
Вы: Привет, как дела?
⏳ Распознавание...
Voxa: Привет! У меня всё отлично, я готов помогать.

🎤 Говорите...
Вы: Очисти чат
⏳ Распознавание...
Voxa: История диалога очищена.

🎤 Говорите...
Вы: Повтори
Voxa: История диалога очищена.

🎤 Говорите...
Вы: Выход
Voxa: 👋 До свидания!
Voxa: До свидания!
```

## 📁 Структура проекта

```
Voxa/
├── voxa_client.py      # Основной скрипт клиента
├── config.py           # Файл конфигурации
├── requirements.txt    # Зависимости Python
├── README.md          # Документация
├── .gitignore         # Исключения для Git
└── app.py             # Серверная часть (Voxa Server)
```

## 🔧 Решение проблем

### Микрофон не работает / Ошибка импорта PyAudio

**Для Bazzite/Fedora Atomic:**

У вас есть два варианта:

#### Вариант A: Использовать sounddevice (рекомендуется)

1. Убедитесь, что установлен `sounddevice`:
   ```bash
   pip install sounddevice numpy
   ```

2. Запустите клиента — он автоматически использует sounddevice если PyAudio недоступен.

#### Вариант B: Установить PyAudio через rpm-ostree

1. Выполните команду для установки системных зависимостей:
   ```bash
   sudo rpm-ostree install portaudio-devel python3-pyaudio
   ```
   
   > **Важно:** На Bazzite (Fedora Atomic) команда `rpm-ostree` требует прав root. Возможно, вам потребуется ввести пароль администратора или запустить терминал в режиме разработчика.

2. После успешной установки перезагрузите систему:
   ```bash
   systemctl reboot
   ```

3. После перезагрузки установите Python-пакет:
   ```bash
   pip install pyaudio
   ```

4. Проверьте работу клиента:
   ```bash
   python voxa_client.py
   ```

### Ошибка распознавания речи

- Убедитесь в наличии интернет-соединения (требуется для Google Speech API)
- Попробуйте говорить громче и четче
- Отрегулируйте `ENERGY_THRESHOLD` в `config.py`

### Сервер не отвечает

- Проверьте, запущен ли сервер Voxa
- Убедитесь, что URL сервера в `config.py` указан правильно
- Проверьте брандмауэр и сетевые настройки

### Проблемы с синтезом речи

- Убедитесь, что установлены все зависимости
- Проверьте наличие русских голосов в системе:
  ```python
  import pyttsx3
  engine = pyttsx3.init()
  voices = engine.getProperty('voices')
  for voice in voices:
      print(voice.name, voice.languages)
  ```

## 🌐 Альтернативные движки распознавания

В будущем планируется поддержка офлайн-распознавания через:

- **Vosk** - легковесный офлайн-движок
- **Whisper** - точная модель от OpenAI

Для включения альтернативного движка измените в `config.py`:
```python
RECOGNITION_ENGINE = "vosk"  # или "whisper"
```

## 📝 Лицензия

MIT License - см. файл LICENSE для деталей.

## 🔗 Ссылки

- [Сервер Voxa](https://github.com/egoffn1/Voxa_Server)
- [Клиент Voxa](https://github.com/egoffn1/Voxa)
- [SpeechRecognition Documentation](https://pypi.org/project/SpeechRecognition/)
- [pyttsx3 Documentation](https://pyttsx3.readthedocs.io/)

## 👨‍💻 Автор

Разработано командой Voxa.

---

**Приятного общения с Voxa! 🎉**
