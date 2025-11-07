main.py
# main.py (ПОВНИЙ КОД З FLASK)

import os
import json
import asyncio
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ChatJoinRequestHandler, CallbackQueryHandler, ConversationHandler, JobQueue
)
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv
from flask import Flask, request, render_template

# Імпорти ваших модулів
from ai import handle_gemini_message_group, handle_gemini_message_private
from handlers import (
    handle_new_members, handle_join_request, handle_callback_query,
    open_drafts_webapp, handle_webapp_data # handle_webapp_data - нова функція
)
from weather import weather_command
from translator import translate_text_command, handle_translation_text, TRANSLATE_STATE
from safe import check_links # Додано імпорт обробника посилань

# ----------------------------------------------------
# 🛡️ КОНФІГУРАЦІЯ
# ----------------------------------------------------

if os.getenv("RENDER") != "true":
    load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 8080))
# Встановлюємо Flask-додаток
app = Flask(__name__, template_folder='templates') # Вказуємо папку для HTML

# ----------------------------------------------------
# 🤖 ТЕЛЕГРАМ-БОТ НАЛАШТУВАННЯ
# ----------------------------------------------------

if not TELEGRAM_BOT_TOKEN:
    print("Помилка: TELEGRAM_BOT_TOKEN не встановлено.")
    exit(1)

# Ініціалізація Application та JobQueue
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
job_queue = application.job_queue # Ініціалізація job_queue

# ----------------------------------------------------
# 🔗 ВЕБХУК ТА FLASK МАРШРУТИ
# ----------------------------------------------------

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
async def telegram_webhook():
    """Обробляє вхідні оновлення від Telegram."""
    if request.method == "POST":
        await application.process_update(
            Update.de_json(request.get_json(force=True), application.bot)
        )
    return "ok"

@app.route("/")
def index():
    """Сторінка-заглушка для перевірки статусу."""
    return "Bot is running! Webhook is ready."

@app.route("/drafts")
def drafts():
    """Відкриває Telegram WebApp"""
    return "This route is for demonstration or internal use."

# ----------------------------------------------------
# ⚙️ АСИНХРОННЕ НАЛАШТУВАННЯ
# ----------------------------------------------------

async def setup_webhook():
    """Встановлює вебхук для Telegram-бота."""
    if RENDER_EXTERNAL_URL and TELEGRAM_BOT_TOKEN:
        base_url = RENDER_EXTERNAL_URL.rstrip('/')
        full_webhook_url = f"{base_url}/{TELEGRAM_BOT_TOKEN}"
        
        print(f"Встановлення вебхука на: {full_webhook_url}")
        try:
            await application.bot.set_webhook(
                url=full_webhook_url,
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            print("Вебхук успішно встановлено.")
        except Exception as e:
            print(f"Помилка встановлення вебхука: {e}")
    else:
        print("RENDER_EXTERNAL_URL або TELEGRAM_BOT_TOKEN не встановлено. Вебхук не налаштовано.")


# ----------------------------------------------------
# 🚀 ДОДАВАННЯ ОБРОБНИКІВ
# ----------------------------------------------------

def add_handlers():
    """Додає всі обробники до бота."""
    # 1. Обробники повідомлень
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_gemini_message_private))
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & (filters.Regex('^ало|@') | filters.Mention(application.bot.username)), 
        handle_gemini_message_group
    ))
    application.add_handler(MessageHandler(
        filters.Entity('url') | filters.Entity('text_link'), check_links, block=False
    ))

    # 2. Обробники команд
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("drafts", open_drafts_webapp))

    # 3. Обробники Web App
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

    # 4. Обробники розмов (ConversationHandler)
    translate_handler = ConversationHandler(
        entry_points=[CommandHandler("translate", translate_text_command)],
        states={
            TRANSLATE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translation_text)]
        },
        fallbacks=[],
        conversation_timeout=60 * 5, # 5 хвилин
    )
    application.add_handler(translate_handler)

    # 5. Обробники вступу/виходу та запитів на вступ
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
    application.add_handler(CallbackQueryHandler(handle_callback_query))


# ----------------------------------------------------
# 🚀 ЗАПУСК БОТА
# ----------------------------------------------------

add_handlers() # Додаємо обробники

def main():
    """Точка входу для запуску бота."""
    if os.getenv("RENDER") == "true":
        print("Запуск в режимі Webhook (Render)...")
        
        # 💡 ВИПРАВЛЕННЯ ПОМИЛКИ: Замість нестабільного asyncio.run() ми безпечно виконуємо
        # асинхронну функцію налаштування вебхука, використовуючи нижньорівневий API asyncio.
        try:
            # 1. Спробуємо отримати поточний цикл подій.
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # 2. Якщо циклу немає (це нормально для основного потоку), створюємо новий.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            # 3. Безпечно виконуємо асинхронну функцію, уникаючи конфлікту вкладених циклів.
            loop.run_until_complete(setup_webhook())
        except Exception as e:
            # Обробка помилок під час виконання setup_webhook()
            print(f"Помилка під час асинхронного запуску setup_webhook: {e}")
            
        print(f"Запуск Flask Web App на порту {PORT}")
        # Запускаємо Flask на тому ж порту, що і Webhook
        app.run(host="0.0.0.0", port=PORT, debug=False)

    else:
        print("Запуск бота в режимі опитування...")
        # Використовуємо asyncio.run для запуску основного асинхронного циклу для опитування
        async def run_polling():
            # Пробуємо видалити вебхук перед запуском опитування
            try:
                await application.bot.delete_webhook()
            except Exception as e:
                print(f"Помилка видалення вебхука: {e}")

            await application.run_polling(poll_interval=1.0)
            
        try:
            # Використовуємо asyncio.run для запуску основного асинхронного циклу
            asyncio.run(run_polling())
        except KeyboardInterrupt:
            print("Бот зупинено користувачем.")

if __name__ == '__main__':
    main()