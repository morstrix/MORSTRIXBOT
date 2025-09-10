import os
import pytz
import datetime
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ChatJoinRequestHandler,
    CallbackQueryHandler,
    JobQueue,
    ConversationHandler
)
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv

from ai import handle_gemini_message_group, handle_gemini_message_private
from handlers import handle_new_members, handle_join_request, handle_callback_query
from safe import check_links
from weather import weather_command, post_weather_job
from support import support_command, handle_private_message, handle_reply_button
from translator import translate_text_command, handle_translation_text, auto_translate_en_to_ua, TRANSLATE_STATE

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
MESSAGE_THREAD_ID = os.getenv("MESSAGE_THREAD_ID")
ADMIN_ID = os.getenv("ADMIN_ID")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args and context.args[0] == 'support':
        context.user_data['state'] = 'support'
        await update.message.reply_text("катай меседж")

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Ошибка: TELEGRAM_BOT_TOKEN не найден в .env файле.")
        return

    kyiv_tz = pytz.timezone('Europe/Kyiv')

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    job_queue: JobQueue = application.job_queue

    # Обробники команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(CommandHandler("support", support_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Обробник для перекладу
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("translate", translate_text_command)],
        states={
            TRANSLATE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_translation_text)],
        },
        fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)]
    )
    application.add_handler(conv_handler)

    # Обробники для вступу в групу
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))

    # Обробники для особистих повідомлень
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.Document.ALL) & filters.ChatType.PRIVATE & ~filters.COMMAND,
        handle_private_message
    ))

    link_filters = filters.Entity("url") | filters.Entity("text_link")
    application.add_handler(MessageHandler(link_filters & filters.ChatType.GROUPS, check_links))

    # Обробники для групових чатів
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.GROUPS & ~filters.COMMAND,
        auto_translate_en_to_ua
    ))

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)ало') & filters.ChatType.GROUPS,
        handle_gemini_message_group
    ))

    if TELEGRAM_CHAT_ID and MESSAGE_THREAD_ID:
        job_queue.run_daily(
            post_weather_job,
            time=datetime.time(hour=8, minute=0, second=0, tzinfo=kyiv_tz),
            job_kwargs={'misfire_grace_time': 60},
            data={'chat_id': TELEGRAM_CHAT_ID, 'message_thread_id': int(MESSAGE_THREAD_ID)},
            name="daily_weather_forecast"
        )
        print("Ежедневное задание для прогноза погоды запланировано на 08:00 по Киеву.")
    else:
        print("Ошибка: TELEGRAM_CHAT_ID или MESSAGE_THREAD_ID не найден. Ежедневное расписание погоды будет отключено.")

    # Выбираем режим запуска в зависимости от окружения
    if os.getenv("RENDER") == "true":
        print("Запуск бота в режиме вебхуков для Render.")
        
        # ПРАВИЛЬНОЕ использование вебхуков
        application.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            url_path="webhook",  # ФИКСИРОВАННЫЙ путь
            webhook_url=f"{RENDER_EXTERNAL_URL}/webhook",  # Без токена в URL
            secret_token='WEBHOOK_SECRET'  # Опционально для безопасности
        )
    else:
        print("Запуск бота в режиме long-polling для локального тестирования.")
        application.run_polling()

if __name__ == '__main__':
    main()