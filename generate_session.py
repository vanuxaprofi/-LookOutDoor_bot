"""
Скрипт для получения SESSION_STRING.
Запустите локально один раз: python generate_session.py
Полученную строку вставьте в переменные окружения Render как SESSION_STRING.
Это избавит вас от необходимости вводить код подтверждения на сервере Render!
"""

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

print("=" * 60)
print("ГЕНЕРАТОР TELEGRAM STRING SESSION ДЛЯ RENDER / GITHUB")
print("=" * 60)

api_id = input("Введите ваш API_ID (с сайта my.telegram.org): ").strip()
api_hash = input("Введите ваш API_HASH (с сайта my.telegram.org): ").strip()

with TelegramClient(StringSession(), int(api_id), api_hash) as client:
    session_str = client.session.save()
    print("\n" + "=" * 60)
    print("ВАША СЕССИЯ УСПЕШНО СОЗДАНА! (СКОПИРУЙТЕ СТРОКУ НИЖЕ):")
    print("=" * 60)
    print(session_str)
    print("=" * 60)
    print("Добавьте эту строку в .env или в Environment Variables на Render под именем:")
    print("SESSION_STRING")
    print("=" * 60)
