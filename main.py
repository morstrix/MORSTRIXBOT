# main.py (ПОВНИЙ КОД З FLASK)

import os
import json
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
app = Flask(__name__, template_folder='templates') # Вказуємо папку для HTML

# ----------------------------------------------------
#          Ініціалізація Telegram Application
# ----------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущено та готовий до роботи.")

# Ініціалізація об'єкта application
job_queue = JobQueue()
application = Application.builder().token(TELEGRAM_BOT_TOKEN).job_queue(job_queue).build()

# Реєстрація Обробників
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("weather", weather_command, filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
application.add_handler(CommandHandler("drafts", open_drafts_webapp, filters.ChatType.PRIVATE))

application.add_handler(CallbackQueryHandler(handle_callback_query, pattern="show_rules"))

translate_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("translate", translate_text_command, filters.ChatType.GROUPS)],
    states={TRANSLATE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translation_text)]},
    fallbacks=[]
)
application.add_handler(translate_conv_handler)

application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
application.add_handler(ChatJoinRequestHandler(handle_join_request))

# Обробник Web App Data (дані, які надсилає ваш drafts.html)
application.add_handler(MessageHandler(
    filters.TEXT & filters.FROM_WEBAPP,
    handle_webapp_data
))

# Обробники Gemini та посилань...
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_gemini_message_private))
link_filters = filters.Entity("url") | filters.Entity("text_link")
application.add_handler(MessageHandler(link_filters & filters.ChatType.GROUPS, check_links))
application.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)ало') & filters.ChatType.GROUPS,
    handle_gemini_message_group
))


# ----------------------------------------------------
#           💥 Обробники Flask (Web App) 💥
# ----------------------------------------------------

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
async def telegram_webhook():
    """Обробляє запити Webhook від Telegram."""
    await application.update_queue.put(Update.de_json(data=request.get_json(force=True), bot=application.bot))
    return "ok"

@app.route('/drafts')
def webapp_drafts():
    """Обслуговує HTML-файл для Web App (виправлення 404)."""
    # Flask шукає drafts.html у папці 'templates'
    return render_template('drafts.html') 

# ----------------------------------------------------
#                      Запуск
# ----------------------------------------------------

def main():
    if os.getenv("RENDER") == "true":
        # Налаштування Webhook
        base_url = RENDER_EXTERNAL_URL.rstrip('/') if RENDER_EXTERNAL_URL else ""
        full_webhook_url = f"{base_url}/{TELEGRAM_BOT_TOKEN}"
        
        # Встановлюємо Webhook у Telegram
        application.run_polling(drop_pending_updates=True) # Потрібно викликати хоча б раз для синхронізації
        application.set_webhook(url=full_webhook_url, allowed_updates=Update.ALL_TYPES)
        
        print(f"Flask Web App та Telegram Webhook запущені на порту {PORT}")
        # Запускаємо Flask на тому ж порту, що і Webhook
        # application.run_webhook не використовуємо
        app.run(host="0.0.0.0", port=PORT, debug=False)

    else:
        print("Запуск бота в режимі опитування (Polling).")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Запускаємо Application.run_polling() перед application.set_webhook()
    # Це гарантує, що всі хендлери і JobQueue ініціалізовані.
    try:
        main()
    except Exception as e:
        print(f"Сталася помилка при запуску: {e}")