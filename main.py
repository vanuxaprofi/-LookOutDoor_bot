"""
Telegram Online/Offline Tracker Bot
Построен на библиотеке Telethon (MTProto).
Отслеживает появление и выход пользователей в сети с минимальной задержкой.
Полностью отвечает требованиям кнопок (только ReplyKeyboardMarkup, без inline кнопок).
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
import aiohttp
from aiohttp import web
from telethon import TelegramClient, events, types
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import UserStatusOnline, UserStatusOffline, UserStatusRecently

import config
from storage import Storage

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("TGTracker")

# Инициализация хранилища целей
storage = Storage(config.DATA_FILE)

# Инициализация клиента Telethon
# Для отслеживания статуса онлайна Telegram требует сессию пользователя (MTProto).
# Бот запускается через сессию пользователя с поддержкой режима бота или dual-client.
if config.SESSION_STRING:
    from telethon.sessions import StringSession
    user_client = TelegramClient(
        StringSession(config.SESSION_STRING),
        config.API_ID,
        config.API_HASH
    )
else:
    user_client = TelegramClient(
        "tracker_session",
        config.API_ID,
        config.API_HASH
    )

bot_client = TelegramClient(
    "bot_session",
    config.API_ID,
    config.API_HASH
).start(bot_token=config.BOT_TOKEN)

# Состояния пользователей (FSM в памяти)
user_states = {}  # chat_id -> "WAITING_USERNAME" | None
target_last_status = {}  # user_id -> {"status": "online"|"offline", "time": datetime}

# ==================== КЛАВИАТУРЫ (REPLY KEYBOARDS) ====================

def get_main_keyboard():
    """Кнопки при /start и возврате назад"""
    return [
        [types.KeyboardButton("➕ ДОБАВИТЬ")],
        [types.KeyboardButton("👤 ЦЕЛИ")],
        [types.KeyboardButton("➖ ИСКЛЮЧИТЬ")]
    ]

def get_add_keyboard():
    """Кнопки после нажатия «➕ ДОБАВИТЬ»"""
    return [
        [types.KeyboardButton("✔️ ДОБАВИТЬ")],
        [types.KeyboardButton("✖️ НАЗАД")]
    ]

def get_back_only_keyboard():
    """Кнопка только назад во время ввода юзернейма"""
    return [
        [types.KeyboardButton("✖️ НАЗАД")]
    ]

def get_goals_keyboard():
    """Кнопки при просмотре «👤 ЦЕЛИ»"""
    return [
        [types.KeyboardButton("➕ ДОБАВИТЬ")],
        [types.KeyboardButton("➖ ИСКЛЮЧИТЬ")],
        [types.KeyboardButton("✖️ НАЗАД")]
    ]

def get_exclude_keyboard(targets: list):
    """Динамические кнопки для исключения целей"""
    keyboard = [[types.KeyboardButton("✖️ НАЗАД")]]
    for t in targets:
        title = f"@{t['username']} ({t.get('nickname', 'Цель')})"
        keyboard.append([types.KeyboardButton(title)])
    return keyboard

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

async def resolve_target_info(username_clean: str):
    """
    Получает информацию о пользователе через MTProto:
    - Проверка существования
    - Фото профиля (скачивание во временный файл)
    - Username, Никнейм, О себе (Bio)
    """
    try:
        entity = await user_client.get_entity(username_clean)
        if not isinstance(entity, types.User):
            return None

        # Получаем полный профиль с описанием (Bio)
        full = await user_client(GetFullUserRequest(entity.id))
        bio = full.about if full.about else "Не указано"
        
        first_name = entity.first_name or ""
        last_name = entity.last_name or ""
        nickname = f"{first_name} {last_name}".strip() or "Без имени"

        # Скачиваем фото профиля
        photo_path = None
        try:
            os.makedirs("downloads", exist_ok=True)
            photo_path = await user_client.download_profile_photo(
                entity,
                file=f"downloads/{entity.id}.jpg"
            )
        except Exception as e:
            logger.warning(f"Не удалось загрузить аватар {username_clean}: {e}")

        status_str = "offline"
        if isinstance(entity.status, UserStatusOnline):
            status_str = "online"

        return {
            "id": entity.id,
            "username": entity.username or username_clean,
            "nickname": nickname,
            "bio": bio,
            "photo_path": photo_path,
            "status": status_str
        }
    except Exception as e:
        logger.error(f"Ошибка поиска пользователя {username_clean}: {e}")
        return None

# ==================== ОБРАБОТЧИКИ КОМАНД И КНОПОК БОТА ====================

@bot_client.on(events.NewMessage(pattern="/start"))
async def handle_start(event):
    chat_id = event.chat_id
    user_states[chat_id] = None
    welcome_text = (
        "👋 **Добро пожаловать в систему мониторинга онлайна!**\n\n"
        "Бот отслеживает время захода и выхода выбранных людей в Telegram "
        "с минимальными интервалами и сразу присылает уведомление.\n\n"
        "Выберите действие ниже:"
    )
    await event.respond(welcome_text, buttons=get_main_keyboard())

@bot_client.on(events.NewMessage)
async def handle_messages(event):
    text = event.raw_text.strip()
    chat_id = event.chat_id

    # Игнорируем команды типа /start здесь
    if text.startswith("/"):
        return

    current_state = user_states.get(chat_id)

    # 1. Кнопка «✖️ НАЗАД»
    if text == "✖️ НАЗАД":
        user_states[chat_id] = None
        await event.respond("Вы зашли обратно внутрь", buttons=get_main_keyboard())
        return

    # 2. Кнопка «➕ ДОБАВИТЬ» в главном меню или в меню целей
    if text == "➕ ДОБАВИТЬ":
        user_states[chat_id] = None
        await event.respond(
            "Нажмите «✔️ ДОБАВИТЬ» для ввода юзернейма или вернитесь назад:",
            buttons=get_add_keyboard()
        )
        return

    # 3. Кнопка «✔️ ДОБАВИТЬ»
    if text == "✔️ ДОБАВИТЬ":
        user_states[chat_id] = "WAITING_USERNAME"
        await event.respond(
            "Введите username цели (например, @durov или durov):",
            buttons=get_back_only_keyboard()
        )
        return

    # 4. Если пользователь находится в режиме ожидания ввода username
    if current_state == "WAITING_USERNAME":
        username_input = text.replace("@", "").strip()
        await event.respond("🔍 Проверяю цель в Telegram...")

        target_info = await resolve_target_info(username_input)
        if not target_info:
            await event.respond(
                "❌ Цель не найдена попробуйте еще раз",
                buttons=get_back_only_keyboard()
            )
            return

        # Добавляем в хранилище
        storage.add_target(
            chat_id=chat_id,
            user_id=target_info["id"],
            username=target_info["username"],
            nickname=target_info["nickname"],
            bio=target_info["bio"]
        )

        # Сохраняем текущий статус
        target_last_status[target_info["id"]] = {
            "status": target_info["status"],
            "last_seen": datetime.now(timezone.utc)
        }

        user_states[chat_id] = None

        card_text = (
            f"👤 **Юз:** @{target_info['username']}\n"
            f"🏷 **Никнейм:** {target_info['nickname']}\n"
            f"📝 **О себе:** {target_info['bio']}\n\n"
            f"☑️ **ЦЕЛЬ ПОДКЛЮЧЕНА**"
        )

        if target_info["photo_path"] and os.path.exists(target_info["photo_path"]):
            await bot_client.send_file(
                chat_id,
                target_info["photo_path"],
                caption=card_text,
                buttons=get_main_keyboard()
            )
            # Удаляем локальный файл после отправки
            try:
                os.remove(target_info["photo_path"])
            except:
                pass
        else:
            await event.respond(card_text, buttons=get_main_keyboard())
        return

    # 5. Кнопка «👤 ЦЕЛИ»
    if text == "👤 ЦЕЛИ":
        user_states[chat_id] = None
        targets = storage.get_targets(chat_id)
        if not targets:
            await event.respond(
                "У вас пока нет отслеживаемых целей.\nНажмите «➕ ДОБАВИТЬ», чтобы начать.",
                buttons=get_goals_keyboard()
            )
            return

        lines = ["📋 **Цели на данный момент:**"]
        for idx, t in enumerate(targets, 1):
            st = target_last_status.get(t["user_id"], {}).get("status", "unknown")
            st_icon = "🟢 В сети" if st == "online" else "⚪ Не в сети"
            lines.append(f"{idx}. @{t['username']} ({t.get('nickname', 'Цель')}) — {st_icon}")

        response_text = "\n".join(lines)
        await event.respond(response_text, buttons=get_goals_keyboard())
        return

    # 6. Кнопка «➖ ИСКЛЮЧИТЬ»
    if text == "➖ ИСКЛЮЧИТЬ":
        user_states[chat_id] = "EXCLUDING"
        targets = storage.get_targets(chat_id)
        if not targets:
            user_states[chat_id] = None
            await event.respond(
                "Список целей пуст, некого исключать.",
                buttons=get_main_keyboard()
            )
            return

        await event.respond(
            "Кого хотите исключить? Выберите цель на клавиатуре:",
            buttons=get_exclude_keyboard(targets)
        )
        return

    # 7. Обработка нажатия на конкретную цель для исключения
    if current_state == "EXCLUDING" or text.startswith("@"):
        targets = storage.get_targets(chat_id)
        # Ищем цель по строке кнопки "@username (Ник)"
        matched_target = None
        for t in targets:
            prefix = f"@{t['username']}"
            if text.startswith(prefix) or text == t['username']:
                matched_target = t
                break

        if matched_target:
            storage.remove_target(chat_id, matched_target["user_id"])
            user_states[chat_id] = None

            card_text = (
                f"👤 **Юз:** @{matched_target['username']}\n"
                f"🏷 **Никнейм:** {matched_target.get('nickname', 'Без имени')}\n"
                f"📝 **О себе:** {matched_target.get('bio', 'Не указано')}\n\n"
                f"🔓 **Цель свободна**\n"
                f"Отчёты о входе и выходе больше не будут приходить."
            )
            await event.respond(card_text, buttons=get_main_keyboard())
            return

# ==================== МОНИТОРИНГ СТАТУСОВ ON-LINE / OFF-LINE ====================

@user_client.on(events.Raw(types.UpdateUserStatus))
async def handle_user_status_update(event):
    """
    Слушает события изменения статуса в MTProto в реальном времени.
    Срабатывает мгновенно (задержка < 1 сек), когда пользователь заходит или выходит.
    """
    user_id = event.user_id
    status = event.status

    # Проверяем, отслеживаем ли мы этого пользователя
    subscribed_chats = storage.get_subscribers_for_target(user_id)
    if not subscribed_chats:
        return

    target_data = storage.get_target_by_id(user_id)
    username = target_data["username"] if target_data else f"id{user_id}"
    nickname = target_data.get("nickname", "Цель") if target_data else ""

    now = datetime.now(timezone.utc)
    prev = target_last_status.get(user_id, {})
    prev_status = prev.get("status")

    if isinstance(status, UserStatusOnline):
        # Пользователь зашел в сеть
        if prev_status != "online":
            target_last_status[user_id] = {"status": "online", "last_seen": now}
            alert_text = (
                f"🟢 **@{username} ({nickname}) ЗАШЕЛ В СЕТЬ!**\n"
                f"⏰ Время: {now.strftime('%H:%M:%S UTC')}"
            )
            for cid in subscribed_chats:
                try:
                    await bot_client.send_message(cid, alert_text)
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления в {cid}: {e}")

    elif isinstance(status, (UserStatusOffline, UserStatusRecently)):
        # Пользователь вышел из сети
        if prev_status == "online":
            target_last_status[user_id] = {"status": "offline", "last_seen": now}
            online_duration_str = ""
            if "last_seen" in prev:
                duration_secs = int((now - prev["last_seen"]).total_seconds())
                mins, secs = divmod(duration_secs, 60)
                hours, mins = divmod(mins, 60)
                if hours > 0:
                    online_duration_str = f"\n⏱ Был в сети: {hours} ч {mins} мин {secs} сек"
                else:
                    online_duration_str = f"\n⏱ Был в сети: {mins} мин {secs} сек"

            alert_text = (
                f"⚪ **@{username} ({nickname}) ВЫШЕЛ ИЗ СЕТИ**\n"
                f"⏰ Время выхода: {now.strftime('%H:%M:%S UTC')}"
                f"{online_duration_str}"
            )
            for cid in subscribed_chats:
                try:
                    await bot_client.send_message(cid, alert_text)
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления в {cid}: {e}")

async def polling_fallback_loop():
    """
    Резервный цикл проверки с минимальным интервалом (каждые 3-5 секунд).
    Гарантирует фиксацию изменения статуса, даже если сырое событие было пропущено сетью.
    """
    while True:
        try:
            all_target_ids = storage.get_all_tracked_user_ids()
            if all_target_ids:
                users = await user_client.get_entity(list(all_target_ids))
                if not isinstance(users, list):
                    users = [users]

                now = datetime.now(timezone.utc)
                for u in users:
                    subscribers = storage.get_subscribers_for_target(u.id)
                    if not subscribers:
                        continue

                    prev = target_last_status.get(u.id, {})
                    prev_status = prev.get("status")
                    is_online = isinstance(u.status, UserStatusOnline)

                    if is_online and prev_status != "online":
                        target_last_status[u.id] = {"status": "online", "last_seen": now}
                        uname = u.username or f"id{u.id}"
                        nname = f"{u.first_name or ''} {u.last_name or ''}".strip()
                        alert = f"🟢 **@{uname} ({nname}) ЗАШЕЛ В СЕТЬ!**\n⏰ {now.strftime('%H:%M:%S UTC')}"
                        for cid in subscribers:
                            await bot_client.send_message(cid, alert)

                    elif not is_online and prev_status == "online":
                        target_last_status[u.id] = {"status": "offline", "last_seen": now}
                        uname = u.username or f"id{u.id}"
                        nname = f"{u.first_name or ''} {u.last_name or ''}".strip()
                        alert = f"⚪ **@{uname} ({nname}) ВЫШЕЛ ИЗ СЕТИ**\n⏰ {now.strftime('%H:%M:%S UTC')}"
                        for cid in subscribers:
                            await bot_client.send_message(cid, alert)

        except Exception as e:
            logger.debug(f"Фоновый опрос: {e}")

        await asyncio.sleep(4)  # Минимальный безопасный интервал от flood-wait

# ==================== HEALTHCHECK HTTP SERVER (ДЛЯ RENDER) ====================

async def healthcheck_handler(request):
    """Render Web Service требует отвечать 200 OK на HTTP запросы для поддержания работы"""
    return web.Response(text="Telegram Tracker Bot is running healthy 🚀", status=200)

async def start_web_server():
    port = int(os.environ.get("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", healthcheck_handler)
    app.router.add_get("/health", healthcheck_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Healthcheck сервер запущен на порту {port}")

# ==================== ТОЧКА ВХОДА ====================

async def main():
    logger.info("Запуск Telegram Tracker Bot...")
    
    # 1. Запуск MTProto User Client
    await user_client.start()
    logger.info("MTProto User Client авторизован и запущен")

    # 2. Запуск Bot Client
    logger.info("Bot Client авторизован и слушает команды")

    # 3. Запуск веб-сервера для Render
    await start_web_server()

    # 4. Запуск резервного цикла отслеживания
    asyncio.create_task(polling_fallback_loop())

    logger.info("Бот готов к работе!")
    
    # Держим бота запущенным
    await asyncio.gather(
        bot_client.run_until_disconnected(),
        user_client.run_until_disconnected()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
