import os
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ChatJoinRequestHandler,
    CallbackQueryHandler,
    ConversationHandler,
    JobQueue
)
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv

# Імпорти ваших модулів
from ai import handle_gemini_message_group, handle_gemini_message_private
from handlers import (
    handle_new_members,
    handle_join_request,
    handle_callback_query,
    open_drafts_webapp # Переконайтеся, що ця функція є у handlers.py
)
from safe import check_links
from weather import weather_command
from support import support_command, handle_private_message, handle_reply_button
from translator import translate_text_command, handle_translation_text, TRANSLATE_STATE


# ----------------------------------------------------
# 🛡️ БЕЗПЕЧНЕ ЗАВАНТАЖЕННЯ ЗМІННИХ СЕРЕДОВИЩА 🛡️
# ----------------------------------------------------

# Завантажуємо .env тільки локально. На Render змінні вже є.
if os.getenv("RENDER") != "true":
    load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0] == 'support':
        context.user_data['state'] = 'support'
        await update.message.reply_text("катай меседж")


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не найден. Проверьте настройки Render.")
        return

    job_queue = JobQueue()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).job_queue(job_queue).build()
    
    job_queue.initialize(application)
    
    # ----------------------------------------------------
    #          Реєстрація Обробників (Handlers)
    # ----------------------------------------------------
    
    # Обробники команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("weather", weather_command, filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("support", support_command, filters.ChatType.GROUPS))
    application.add_handler(CommandHandler("drafts", open_drafts_webapp, filters.ChatType.PRIVATE))

    # Обробник кнопок
    application.add_handler(CallbackQueryHandler(handle_callback_query, pattern="show_rules"))
    application.add_handler(CallbackQueryHandler(handle_reply_button, pattern="^reply_to_"))

    # Обробник перекладача (ConversationHandler)
    translate_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("translate", translate_text_command, filters.ChatType.GROUPS)],
        states={
            TRANSLATE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translation_text)]
        },
        fallbacks=[]
    )
    application.add_handler(translate_conv_handler)
    
    # Обробники для вступу в групу
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))

    # Обробники для особистих повідомлень
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.ALL) & filters.ChatType.PRIVATE & ~filters.COMMAND,
        handle_private_message
    ))
    
    # Обробник особистих повідомлень для Gemini
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        handle_gemini_message_private
    ))

    # Обробник посилань
    link_filters = filters.Entity("url") | filters.Entity("text_link")
    application.add_handler(MessageHandler(link_filters & filters.ChatType.GROUPS, check_links))

    # Обробник тригера "ало" в групі
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)ало') & filters.ChatType.GROUPS,
        handle_gemini_message_group
    ))
    
    # ----------------------------------------------------
    #            💥 ФІКС WEBHOOK (Render) 💥
    # ----------------------------------------------------

    if os.getenv("RENDER") == "true":
        
        # 1. Очищуємо базовий URL від слішів
        # .rstrip('/') видаляє кінцевий сліш, якщо він є.
        base_url = RENDER_EXTERNAL_URL.rstrip('/') if RENDER_EXTERNAL_URL else ""
        
        # 2. Створюємо правильний Webhook URL
        full_webhook_url = f"{base_url}/{TELEGRAM_BOT_TOKEN}"
        
        # !!! ДІАГНОСТИЧНИЙ ВИВІД !!!
        print(f"WEBHOOK_URL (DEBUG): [{full_webhook_url}]") 
        print("Запуск бота в режимі вебхуків для Render.")
        # !!! ДІАГНОСТИЧНИЙ ВИВІД !!!

        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=full_webhook_url,
            max_connections=50
        )
    else:
        # Для локального запуску
        print("Запуск бота в режимі опитування (Polling).")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()