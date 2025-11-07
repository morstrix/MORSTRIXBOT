# main.py (ПОВНИЙ КОД З FLASK)

import os
import json
import asyncio # <--- НОВИЙ ІМПОРТ
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
from safe import check_links 
from weather import weather_command
from translator import translate_text_command, handle_translation_text, TRANSLATE_STATE

# ----------------------------------------------------
# 🛡️ КОНФІГУРАЦІЯ
# ----------------------------------------------------

if os.getenv("RENDER") != "true":
    load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 8080))
# Встановлюємо Flask-додаток
app = Flask(__name__, template_folder='.') # Змінено 'templates' на '.'

# ----------------------------------------------------
# 🤖 НАЛАШТУВАННЯ БОТА
# ----------------------------------------------------

# Ініціалізація Application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
job_queue: JobQueue = application.job_queue

# --- Хендлери ---

# 1. Початок роботи /drafts (Web App)
application.add_handler(CommandHandler("drafts", open_drafts_webapp, filters=filters.ChatType.PRIVATE))
# 2. Обробка даних з Web App
application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_webapp_data))

# 3. Обробка команди /weather
application.add_handler(CommandHandler("weather", weather_command))

# 4. Обробка команди /translate
translate_handler = ConversationHandler(
    entry_points=[CommandHandler("translate", translate_text_command)],
    states={
        TRANSLATE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translation_text)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)] # Додайте команду скасування, якщо потрібно
)
application.add_handler(translate_handler)

# 5. Обробка нових учасників
application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))

# 6. Обробка запитів на приєднання
application.add_handler(ChatJoinRequestHandler(handle_join_request))

# 7. Обробка натискань Inline кнопок (CallbackQueryHandler)
application.add_handler(CallbackQueryHandler(handle_callback_query))

# 8. Обробка повідомлень з посиланнями (Safe Browsing) - тільки в групах
application.add_handler(MessageHandler(
    filters.ChatType.GROUPS & (filters.Entity("url") | filters.Entity("text_link")), 
    check_links
))

# 9. Обробка повідомлень для Gemini (групові чати)
# Фільтр: повідомлення, що містять "ало" або згадку бота
gemini_group_filter = filters.ChatType.GROUPS & filters.TEXT & (
    filters.Regex(r'(?i)\bало\b') | 
    filters.Mention(application.bot.username)
)
application.add_handler(MessageHandler(gemini_group_filter, handle_gemini_message_group))

# 10. Обробка повідомлень для Gemini (приватні чати)
application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, handle_gemini_message_private))


# ----------------------------------------------------
# 🌐 FLASK & WEBHOOK (для Render)
# ----------------------------------------------------

@app.route(f"/{TELEGRAM_BOT_TOKEN}", methods=["POST"])
async def webhook_handler():
    """Обробляє вхідні оновлення від Telegram."""
    if request.method == "POST":
        # Отримуємо оновлення у вигляді JSON
        update_json = request.get_json(force=True)
        update = Update.de_json(update_json, application.bot)
        
        # Обробляємо оновлення асинхронно
        await application.process_update(update)
    return "ok"

@app.route("/drafts")
def serve_drafts_webapp():
    """Надає HTML-файл для Web App."""
    return render_template("drafts.html")

# Функція для налаштування вебхука
async def setup_webhook():
    """Встановлює вебхук при запуску на Render."""
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

def main():
    if os.getenv("RENDER") == "true":
        print("Запуск в режимі Webhook (Render)...")
        
        # Налаштовуємо та запускаємо вебхук асинхронно
        try:
            # ВИПРАВЛЕНО: Використовуємо asyncio.run() для запуску асинхронної setup_webhook
            # Також Application.initialize() викликаємо тут, щоб ініціалізувати JobQueue
            application.initialize()
            asyncio.run(setup_webhook())
        except Exception as e:
            print(f"Помилка під час асинхронного запуску setup_webhook: {e}")
            
        print(f"Запуск Flask Web App на порту {PORT}")
        # Запускаємо Flask на тому ж порту, що і Webhook
        app.run(host="0.0.0.0", port=PORT, debug=False)

    else:
        print("Запуск бота в режимі опитування...")
        application.run_polling(poll_interval=3)

if __name__ == "__main__":
    main()