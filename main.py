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

# ✅ ФІКС: ІМПОРТУЄМО ОБИДВА ХЕНДЛЕРИ З AI
from ai import handle_gemini_message_group, handle_gemini_message_private
from handlers import (
    handle_new_members,
    handle_join_request,
    handle_callback_query,
    # ✅ ІМПОРТ ДЛЯ MINI APP
    open_drafts_webapp
)
from safe import check_links
from weather import weather_command
# ❌ ВИДАЛЕНО: from support import support_command, handle_private_message, handle_reply_button 
from translator import translate_text_command, handle_translation_text, TRANSLATE_STATE

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("https://morstrixbot-afjc.onrender.com/")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Логіка /start для саппорта видалена, залишаємо базову відповідь
    await update.message.reply_text("🖖")


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env файле.")
        return

    job_queue = JobQueue()
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).job_queue(job_queue).build()
    
    # Обробники для команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("weather", weather_command))
    # ✅ ДОДАНО: ОБРОБНИК ДЛЯ MINI APP
    application.add_handler(CommandHandler("drafts", open_drafts_webapp, filters.ChatType.PRIVATE))
    # ❌ ВИДАЛЕНО: application.add_handler(CommandHandler("support", support_command)) 

    # Обробник кнопок InlineKeyboard (для правил)
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Обробник перекладу (ConversationHandler)
    translate_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("translate", translate_text_command)],
        states={
            TRANSLATE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translation_text)]
        },
        fallbacks=[]
    )
    application.add_handler(translate_conv_handler)
    
    # Обробники для вступу в групу
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))

    # ✅ ВИПРАВЛЕНО: ОБРОБНИК ДЛЯ ОСОБИСТИХ ПОВІДОМЛЕНЬ ТЕПЕР ВИКОРИСТОВУЄ handle_gemini_message_private
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.ALL) & filters.ChatType.PRIVATE & ~filters.COMMAND,
        handle_gemini_message_private
    ))
    # ❌ ВИДАЛЕНО: Обробники для саппорта були тут

    # Обробник посилань
    link_filters = filters.Entity("url") | filters.Entity("text_link")
    application.add_handler(MessageHandler(link_filters & filters.ChatType.GROUPS, check_links))

    # Обробник тригера "ало" в групі (залишається)
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)ало') & filters.ChatType.GROUPS,
        handle_gemini_message_group
    ))
    
    if os.getenv("RENDER") == "true":
        print("Запуск бота в режимі вебхуків для Render.")
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=f"{RENDER_EXTERNAL_URL}{TELEGRAM_BOT_TOKEN}",
            max_connections=50
        )
    else:
        print("Запуск бота в режимі поллінгу.")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()