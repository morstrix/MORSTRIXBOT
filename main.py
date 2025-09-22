import os
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ChatJoinRequestHandler,
    CallbackQueryHandler,
    ConversationHandler
)
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv

# CHANGE: Видалено непотрібні імпорти
from ai import handle_gemini_message_group, handle_gemini_message_private
from handlers import (
    handle_new_members,
    handle_join_request,
    handle_callback_query,
    start_complaint,
    receive_replacement_link,
    cancel_complaint,
    AWAITING_LINK
)
from safe import check_links
from weather import weather_command
from support import support_command, handle_private_message, handle_reply_button
from translator import translate_text_command, handle_translation_text, TRANSLATE_STATE

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0] == 'support':
        context.user_data['state'] = 'support'
        await update.message.reply_text("катай меседж")


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env файле.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Обробники команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("support", support_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query, pattern='^show_rules$'))
    application.add_handler(CallbackQueryHandler(handle_reply_button, pattern='^reply_to_'))

    # Обробник для перекладу
    translate_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("translate", translate_text_command)],
        states={
            TRANSLATE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translation_text)],
        },
        fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)]
    )
    application.add_handler(translate_conv_handler)

    # Обробник для скарг
    complaint_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_complaint, pattern='^start_complaint$')],
        states={
            AWAITING_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_replacement_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel_complaint)],
        conversation_timeout=300
    )
    application.add_handler(complaint_conv_handler)

    # Обробники для вступу в групу
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))

    # Обробники для особистих повідомлень
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.ALL) & filters.ChatType.PRIVATE & ~filters.COMMAND,
        handle_private_message
    ))

    # Обробник посилань
    link_filters = filters.Entity("url") | filters.Entity("text_link")
    application.add_handler(MessageHandler(link_filters & filters.ChatType.GROUPS, check_links))

    # Обробник тригера "ало" в групі
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)ало') & filters.ChatType.GROUPS,
        handle_gemini_message_group
    ))
    
    # FIX: Видалено планувальник завдань для погоди
    # FIX: Видалено обробник для авто-перекладу

    if os.getenv("RENDER") == "true":
        print("Запуск бота в режимі вебхуків для Render.")
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url=f"{RENDER_EXTERNAL_URL}/{TELEGRAM_BOT_TOKEN}"
        )
    else print("Запуск бота в режимі long-polling для локального тестування.")
        application.run_polling()

if __name__ == '__main__':
    main()