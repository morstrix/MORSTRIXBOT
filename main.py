# main.py

import os
import asyncio
import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ChatJoinRequestHandler, CallbackQueryHandler, JobQueue,
    ConversationHandler
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from dotenv import load_dotenv
from aiohttp import web

# === Імпорти модулів ===
from ai import handle_gemini_message_group, handle_gemini_message_private
from handlers import (
    handle_new_members, handle_join_request, handle_callback_query,
    font_start, font_get_text, font_cancel,
    handle_web_app_data,
)
from safe import check_links

# ========================================
# ЛОГУВАННЯ
# ========================================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========================================
# КОНФІГУРАЦІЯ
# ========================================
if os.getenv("RENDER") != "true":
    load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не знайдено!")

# ========================================
# КОМАНДА /start (без Web App кнопки)
# ========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("ПРАВИЛА", callback_data="show_rules")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "ᴡᴇʟᴄᴏᴍᴇ \n\n"
        "➞ ᴀʙᴛᴏпᴘийᴏᴍ зᴀяʙᴏᴋ\n"
        "➞ пᴇᴘᴇʙіᴘᴋᴀ пᴏᴄиʌᴀнь\n"
        "➞ /font - ᴛᴇᴋᴄᴛ ᴄᴛᴀйʌᴇᴘ\n\n"
        "➞ ШІ — дʌя чʌᴇніʙ ᴋʌубу (ᴀʌᴏ)\n"
        "➞ DRAFTZ — у меню (Main App)",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

# ========================================
# РЕЄСТРАЦІЯ ОБРОБНИКІВ
# ========================================
def setup_handlers(application: Application):
    application.add_handler(CommandHandler("start", start_command))

    # FONT
    font_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("font", font_start)],
        states={0: [MessageHandler(filters.TEXT & ~filters.COMMAND, font_get_text)]},
        fallbacks=[CommandHandler("cancel", font_cancel)],
        allow_reentry=True
    )
    application.add_handler(font_conv_handler)

    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))

    # КРИТИЧНО: Прийом даних з Mini App (Main App)
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    # Gemini AI
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_gemini_message_private))
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)ало') & filters.ChatType.GROUPS,
        handle_gemini_message_group
    ))

    # Safe Links
    link_filters = filters.Entity("url") | filters.Entity("text_link")
    application.add_handler(MessageHandler(link_filters & filters.ChatType.GROUPS, check_links))

# ========================================
# WEBHOOK SERVER
# ========================================
async def start_webhook_server(application: Application):
    app = web.Application()

    webhook_path = f'/webhook_{TELEGRAM_BOT_TOKEN}'
    async def telegram_webhook(request):
        try:
            data = await request.json()
            update = Update.de_json(data, application.bot)
            await application.update_queue.put(update)
            return web.Response(text="OK", status=200)
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return web.Response(text="Error", status=500)

    app.router.add_post(webhook_path, telegram_webhook)

    async def health(request):
        return web.Response(text="MORSTRIX BOT IS ALIVE", status=200)
    app.router.add_get('/', health)
    app.router.add_get('/health', health)

    app['bot_app'] = application

    await application.initialize()
    setup_handlers(application)

    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}{webhook_path}"
    logger.info(f"Встановлюю вебхук: {webhook_url}")
    try:
        await application.bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        logger.info("Вебхук встановлено!")
    except Exception as e:
        logger.error(f"Помилка вебхука: {e}")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Сервер запущено: 0.0.0.0:{PORT}")

    await application.start()
    await asyncio.Future()

# ========================================
# ЗАПУСК
# ========================================
application = Application.builder().token(TELEGRAM_BOT_TOKEN).job_queue(JobQueue()).build()

def main():
    if os.getenv("RENDER") == "true":
        logger.info("=== RENDER: WEBHOOK MODE ===")
        asyncio.run(start_webhook_server(application))
    else:
        logger.info("=== LOCAL: POLLING MODE ===")
        setup_handlers(application)
        application.run_polling()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Критична помилка: {e}", exc_info=True)