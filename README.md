# Bot Features

-   **Chat Management**
    -   New users are accepted automatically.
    -   Upon joining, they receive a welcome message with a link to the group rules.
-   **Response Generation**
    -   In group chats, if someone types “alo”, the bot will reply (no more than once every 60 seconds).
    -   In private messages, you can chat with the bot without any trigger words.
-   **Link Checking**
    -   The bot automatically scans all links using Google Safe Browsing API.
    -   Safe links get a ⚡️ reaction, unsafe links get a 🤬 reaction.
    -   Links to YouTube Music will show a special "complaint" button.
-   **Weather**
    -   The `/weather` command provides a forecast for Kyiv.
-   **Support**
    -   The `/support` command connects you directly with the admin in a private chat.
-   **Translator**
    -   The `/translate` command allows you to translate text.

# Можливості бота

-   **Керування чатом**
    -   Нові користувачі приймаються автоматично.
    -   Приєднавшись, вони отримують вітальне повідомлення з посиланням на правила.
-   **Генерація відповідей**
    -   У груповому чаті, якщо написати «ало», бот відповість на запитання (не частіше ніж раз на 60 секунд).
    -   У приватних повідомленнях можна спілкуватися без тригерів.
-   **Перевірка посилань**
    -   Бот автоматично перевіряє всі посилання через Google Safe Browsing API.
    -   Безпечні посилання отримують реакцію ⚡️, а небезпечні — 🤬.
    -   Посилання на YouTube Music викликають спеціальну кнопку для скарги.
-   **Погода**
    -   Команда `/weather` надішле прогноз погоди для Києва.
-   **Підтримка**
    -   Команда `/support` допоможе швидко зв’язатися з адміністратором у приватному чаті.
-   **Перекладач**
    -   Команда `/translate` дозволяє перекладати текст.

## Налаштування та запуск

1.  Клонуйте цей репозиторій.
2.  Створіть файл `.env` у кореневій директорії проєкту та додайте до нього наступні змінні:
TELEGRAM_BOT_TOKEN="ВАШ_ТОКЕН_БОТА"
GOOGLE_SAFE_BROWSING_API_KEY="ВАШ_КЛЮЧ_SAFE_BROWSING"
OPENWEATHERMAP_API_KEY="ВАШ_КЛЮЧ_OPENWEATHERMAP"
GEMINI_API_KEY="ВАШ_КЛЮЧ_GEMINI"
SUPPORT_ID="ВАШ_ТЕЛЕГРАМ_ID_ДЛЯ_ПІДТРИМКИ"
3.  Встановіть необхідні залежності:
    `pip install -r requirements.txt`
4.  Запустіть бота:
    `python3 main.py`

