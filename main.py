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

# Импорты ваших модулей (Модуль support УДАЛЕН)
from ai import handle_gemini_message_group, handle_gemini_message_private
from handlers import (
    handle_new_members,
    handle_join_request,
    handle_callback_query,
    open_drafts_webapp
)
from safe import check_links
from weather import weather_command
from translator import translate_text_command, handle_translation_text, TRANSLATE_STATE


# ----------------------------------------------------
# 🛡️ БЕЗОПАСНАЯ ЗАГРУЗКА ПЕРЕМЕННЫХ СРЕДЫ 🛡️
# ----------------------------------------------------

# Загружаем .env только локально. На Render переменные уже есть.
if os.getenv("RENDER") != "true":
    load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Упрощенная логика /start, так как support удален
    await update.message.reply_text("Бот запущен.")


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не найден. Проверьте настройки Render.")
        return

    job_queue = JobQueue()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).job_queue(job_queue).build()
    
    job_queue.initialize(application)
    
    # ----------------------------------------------------
    #          Регистрация Обработчиков (Handlers)
    # ----------------------------------------------------
    
    # Обробники команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("weather", weather_command, filters.ChatType.GROUPS | filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("drafts", open_drafts_webapp, filters.ChatType.PRIVATE))
    # Команда /support УДАЛЕНА
    
    # Обробник кнопок
    application.add_handler(CallbackQueryHandler(handle_callback_query, pattern="show_rules"))
    # handle_reply_button УДАЛЕН

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

    # Обробчики личных сообщений (осталась только логика Gemini)
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
    #            💥 ФИКС WEBHOOK (Render) 💥
    # ----------------------------------------------------

    if os.getenv("RENDER") == "true":
        
        # 1. Очищаем базовый URL от слэшей
        base_url = RENDER_EXTERNAL_URL.rstrip('/') if RENDER_EXTERNAL_URL else ""
        
        # 2. Создаем правильный Webhook URL
        full_webhook_url = f"{base_url}/{TELEGRAM_BOT_TOKEN}"
        
        # !!! КРИТИЧЕСКИ ВАЖНАЯ ДИАГНОСТИКА !!!
        print(f"WEBHOOK_URL (DEBUG): [{full_webhook_url}]") 
        print("Запуск бота в режиме вебхуков для Render.")
        # !!! КРИТИЧЕСКИ ВАЖНАЯ ДИАГНОСТИКА !!!

        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=full_webhook_url,
            max_connections=50
        )
    else:
        # Для локального запуска
        print("Запуск бота в режиме опроса (Polling).")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()