"""
Модуль конфигурации Telegram Tracker Bot.
Загружает переменные окружения (.env).
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token от @BotFather (например: 123456789:ABCdefGhI...)
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Данные приложения Telegram API с my.telegram.org (App api_id & api_hash)
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "").strip()

# StringSession пользователя для MTProto (генерируется через generate_session.py)
SESSION_STRING = os.getenv("SESSION_STRING", "").strip()

# Путь к файлу сохранения данных целей
DATA_FILE = os.getenv("DATA_FILE", "targets.json")

# Проверка обязательных переменных
if not BOT_TOKEN:
    print("[ПРЕДУПРЕЖДЕНИЕ] BOT_TOKEN не установлен в .env!")
if not API_ID or not API_HASH:
    print("[ПРЕДУПРЕЖДЕНИЕ] API_ID или API_HASH не установлены в .env! Получите их на my.telegram.org")
