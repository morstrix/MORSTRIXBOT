# main.py

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
# ОНОВЛЕНО: Додано send_file
from flask import Flask, request, render_template, send_file 

# Імпорти ваших модулів
from ai import handle_gemini_message_group, handle_gemini_message_private
from handlers import (
    handle_new_members, handle_join_request, handle_callback_query,
    open_drafts_webapp, handle_webapp_data, 
    font_start_command, font_receive_text, font_cancel, FONT_STATE # ОНОВЛЕНО: Додано функції для ConversationHandler та стан
)
# Видалено імпорти: from weather import weather_command, from translator import ...

# ----------------------------------------------------
# 🛡️ КОНФІГУРАЦІЯ
# ----------------------------------------------------

if os.getenv("RENDER") != "true":
    load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 8080))
# Встановлюємо Flask-додаток
app = Flask(__name__, template_folder='.') # Змінив назад на '.' для відповідності вашій структурі

# ----------------------------------------------------
#          Ініціалізація Telegram Application
# ----------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущено та готовий до роботи.")

# Ініціалізація об'єкта application
# Використовуємо .build() без явного JobQueue, оскільки JobQueue ініціалізується всередині Application.builder()
# але залишаємо логіку, що була у вашому файлі:
job_queue = JobQueue()
application = Application.builder().token(TELEGRAM_BOT_TOKEN).job_queue(job_queue).build()


# Реєстрація Обробників
application.add_handler(CommandHandler("start", start_command))
# Видалено: application.add_handler(CommandHandler("weather", weather_command, filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
application.add_handler(CommandHandler("drafts", open_drafts_webapp, filters.ChatType.PRIVATE))

# ОНОВЛЕНО: Додано ConversationHandler для команди /font
font_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('font', font_start_command)],
    states={
        FONT_STATE: [
            # Очікуємо будь-якого текстового повідомлення від користувача, яке не є командою
            MessageHandler(filters.TEXT & ~filters.COMMAND, font_receive_text)
        ],
    },
    fallbacks=[
        CommandHandler('cancel', font_cancel), # Можливість скасувати розмову
        # Якщо прийде інша команда, розмова також завершиться
        MessageHandler(filters.COMMAND, font_cancel) 
    ],
    # Обмежуємо роботу приватними чатами та групами
    per_user=True, # Розмова індивідуальна для кожного користувача
    per_chat=False,
)

application.add_handler(font_conv_handler) # Додаємо обробник розмови

application.add_handler(CallbackQueryHandler(handle_callback_query)) # Виправлено: обробляє всі callback, не тільки 'show_rules'

# Видалено: translate_conv_handler

application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
application.add_handler(ChatJoinRequestHandler(handle_join_request))

# === Обробка WebApp Data
application.add_handler(MessageHandler(
    filters.StatusUpdate.WEB_APP_DATA,
    handle_webapp_data
))

# Обробники Gemini та посилань...
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_gemini_message_private))

# Обробник Gemini в групі
application.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)ало') & filters.ChatType.GROUPS,
    handle_gemini_message_group
))
# Обробник посилань залишаємо закоментованим, як було, оскільки 'check_links' не імпортовано
# link_filters = filters.Entity("url") | filters.Entity("text_link")
# application.add_handler(MessageHandler(link_filters & filters.ChatType.GROUPS, check_links))


# ----------------------------------------------------
#           💥 Обробники Flask (Web App) 💥
# ----------------------------------------------------

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
async def telegram_webhook():
    """Обробляє запити Webhook від Telegram."""
    if request.content_length > 10**6: # Обмеження розміру запиту (наприклад, 1MB)
        print("Запит занадто великий, ігнорується.")
        return "request too large", 413
        
    try:
        data = request.get_json(force=True)
    except Exception as e:
        print(f"Помилка отримання JSON: {e}")
        return "bad request", 400
        
    await application.update_queue.put(Update.de_json(data=data, bot=application.bot))
    return "ok", 200

@app.route('/drafts')
def webapp_drafts():
    """Обслуговує HTML-файл для Web App, гарантуючи коректний MIME-тип."""
    # ВИПРАВЛЕНО: Використовуємо send_file для гарантованої віддачі з Content-Type: text/html
    return send_file('drafts.html', mimetype='text/html') 

@app.route('/')
def index():
    """Проста сторінка, щоб перевірити, чи працює Flask."""
    return "Flask server is running."

# ----------------------------------------------------
#                      Запуск
# ----------------------------------------------------

async def setup_webhook():
    """Встановлює вебхук."""
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
            asyncio.run(setup_webhook())
        except Exception as e:
            print(f"Помилка під час асинхронного запуску setup_webhook: {e}")
            
        print(f"Запуск Flask Web App на порту {PORT}")
        # Запускаємо Flask на тому ж порту, що і Webhook
        app.run(host="0.0.0.0", port=PORT, debug=False)

    else:
        print("Запуск бота в режимі опитування (Polling).")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Сталася фатальна помилка при запуску: {e}")