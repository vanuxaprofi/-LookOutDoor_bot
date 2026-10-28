# 🚀 Telegram Online/Offline Tracker Bot (Python + Render + GitHub)

Телеграм бот для мгновенного отслеживания онлайна и оффлайна выбранных целей в Telegram с минимальными задержками (< 1-2 сек).

## 🌟 Возможности
- 🔘 **Только Keyboard-кнопки** (без инлайн кнопок):
  - Главное меню: `➕ ДОБАВИТЬ`, `👤 ЦЕЛИ`, `➖ ИСКЛЮЧИТЬ`
  - Меню добавления: `✔️ ДОБАВИТЬ`, `✖️ НАЗАД`
  - Проверка цели с фото профиля, никнеймом, юзернеймом и био
  - Динамическое удаление целей по нажатию на имя
- ⚡ **Мгновенные уведомления**:
  - `🟢 @username (Имя) ЗАШЕЛ В СЕТЬ!`
  - `⚪ @username (Имя) ВЫШЕЛ ИЗ СЕТИ (Был в сети: X мин Y сек)`
- ☁️ **Бесплатная работа 24/7 на Render**:
  - Встроенный lightweight HTTP healthcheck сервер на порту `$PORT`
  - Сохранение целей в файле `targets.json`

---

## 🛠️ Шаг 1: Получение данных Telegram

### 1. Токен бота (BOT_TOKEN)
1. Откройте в Telegram бота **@BotFather**.
2. Отправьте команду `/newbot`.
3. Укажите название и юзернейм (например, `MyTrackerBot`).
4. Скопируйте полученный **HTTP API Token**.

### 2. API_ID и API_HASH
Обычный Bot API Telegram **не может** видеть статус присутствия других пользователей из соображений конфиденциальности. Для этого используется Telegram MTProto Client API:
1. Перейдите на сайт [my.telegram.org](https://my.telegram.org).
2. Авторизуйтесь под своим аккаунтом Telegram.
3. Откройте раздел **API development tools**.
4. Создайте приложение (название любое, например `TrackerApp`).
5. Скопируйте **api_id** и **api_hash**.

### 3. Генерация SESSION_STRING
Чтобы бот работал на Render без постоянного запроса SMS-кода:
1. Запустите локально:
   ```bash
   python generate_session.py
   ```
2. Введите API_ID, API_HASH и номер телефона с кодом из Telegram.
3. Скопируйте сгенерированную длинную строку сессии.

---

## 📦 Шаг 2: Загрузка проекта на GitHub

1. Создайте новый репозиторий на [GitHub.com](https://github.com) (например, `tg-online-tracker`).
2. В папке с кодом выполните команды в терминале:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Telegram Tracker Bot"
   git branch -M main
   git remote add origin https://github.com/ВАШ_ЛОГИН/tg-online-tracker.git
   git push -u origin main
   ```

---

## 🌐 Шаг 3: Развертывание на Render.com (Бесплатно 24/7)

1. Зарегистрируйтесь на [Render.com](https://render.com).
2. Нажмите **New +** -> **Web Service** (или **Background Worker**).
3. Подключите ваш GitHub репозиторий `tg-online-tracker`.
4. Заполните параметры:
   - **Name**: `telegram-tracker-bot`
   - **Language**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Instance Type**: `Free`
5. Перейдите во вкладку **Environment Variables** и добавьте:
   - `BOT_TOKEN` = ваш токен от BotFather
   - `API_ID` = ваш api_id с my.telegram.org
   - `API_HASH` = ваш api_hash с my.telegram.org
   - `SESSION_STRING` = строка из generate_session.py
6. Нажмите **Deploy Web Service**!

Бот автоматически поднимется, начнет слушать команды и мониторить цели 24/7!
