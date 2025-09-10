Bot Features
• Chat Management
New users are accepted automatically.
Upon joining, they receive a welcome message with a link to the group rules.
• Response Generation
In group chats, if someone types “alo”, the bot will reply (no more than once every 60 seconds).
In private messages, you can chat with the bot without any trigger words.
• Link Checking
The bot automatically scans all links using Google Safe Browsing API.
Unsafe links are deleted, and the user receives a warning.
• Weather
The /weather command provides a forecast.
Every day at 8:00 AM, the bot posts the morning, afternoon, and evening forecast in the group chat.
Weather messages are automatically deleted after 4 hours.
• Support
The /support command connects you directly with the admin in a private chat.
• Translate

Можливості бота
• Керування чатом
Нові користувачі приймаються автоматично.
Приєднавшись, вони отримують вітальне повідомлення з посиланням на правила.
• Генерація відповідей
У груповому чаті, якщо написати «ало», бот відповість на запитання (не частіше ніж раз на 60 секунд).
У приватних повідомленнях можна спілкуватися без тригерів.
• Перевірка посилань
Бот автоматично перевіряє всі посилання через Google Safe Browsing API.
Небезпечні лінки видаляються, а користувач отримує попередження.
• Погода
Команда /weather надішле прогноз.
Щодня о 8:00 бот публікує прогноз на ранок, день та вечір у груповому чаті.
Повідомлення автоматично видаляється через 4 години.
• Підтримка
Команда /support допоможе швидко зв’язатися з адміністратором у приватному чаті.
• Перекладач

## Налаштування та запуск

1.  Клонуйте цей репозиторій.
2.  Створіть файл .env у кореневій директорії проєкту та додайте до нього наступні змінні:

TELEGRAM_BOT_TOKEN="ВАШ_ТОКЕН_БОТА"
GOOGLE_SAFE_BROWSING_API_KEY="ВАШ_КЛЮЧ_SAFE_BROWSING"
OPENWEATHERMAP_API_KEY="ВАШ_КЛЮЧ_OPENWEATHERMAP"
GEMINI_API_KEY="ВАШ_КЛЮЧ_GEMINI"
TELEGRAM_CHAT_ID="ІДЕНТИФІКАТОР_ГРУПОВОГО_ЧАТУ"
MESSAGE_THREAD_ID="ІДЕНТИФІКАТОР_ТРЕДУ"
ADMIN_ID="ІДЕНТИФІКАТОР_АДМІНА"

Встановіть необхідні залежності:
pip install -r requirements.txt

Запустіть бота:
python3 main.py