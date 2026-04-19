"""
Voxa Client Configuration
"""

SERVER_URL = "https://voxa-server-1xhr.onrender.com"
CHAT_ENDPOINT = "/chat"

# Настройки распознавания
RECOGNITION_ENGINE = "google"
ENERGY_THRESHOLD = 4000
PAUSE_THRESHOLD = 0.8

# Настройки активации по имени
WAKE_WORD_ENABLED = True
WAKE_WORDS = ["вокс", "воха", "вокса", "привет вокс", "окей вокс"]
WAKE_SENSITIVITY = 0.6

# Команды
EXIT_COMMANDS = ["выход", "пока", "завершить работу", "выйти", "стоп"]
REPEAT_COMMANDS = ["повтори", "повтори последнее", "еще раз"]
CLEAR_CHAT_COMMANDS = ["очисти чат", "забудь всё", "новый диалог", "очистить чат"]