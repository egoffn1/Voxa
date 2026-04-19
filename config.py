"""
Voxa Client Configuration
"""

# Server URL - измените на адрес вашего сервера Voxa
SERVER_URL = "http://localhost:5000"

# Endpoints
CHAT_ENDPOINT = "/chat"

# Recognition settings
RECOGNITION_ENGINE = "google"  # 'google', 'vosk', или 'whisper'
ENERGY_THRESHOLD = 4000  # Порог энергии для обнаружения речи
PAUSE_THRESHOLD = 0.8  # Пауза для определения конца фразы (секунды)

# TTS settings
TTS_RATE = 150  # Скорость речи (слова в минуту)
TTS_VOLUME = 1.0  # Громкость (0.0 - 1.0)

# Local commands
EXIT_COMMANDS = ["выход", "пока", "завершить работу", "выйти", "стоп"]
REPEAT_COMMANDS = ["повтори", "повтори последнее", "еще раз"]
CLEAR_CHAT_COMMANDS = ["очисти чат", "забудь всё", "новый диалог", "очистить чат"]
