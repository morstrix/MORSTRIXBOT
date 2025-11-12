# main.py — ГІБРИД: webhook + polling ТІЛЬКИ для chat_join_request

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

# === Імпорти ===
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
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========================================
# КОНФІГУРАЦІЯ
# ========================================
if os.getenv("RENDER") != "true":
    load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))

# ========================================
# /start
# ========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("ПРАВИЛА", callback_data="show_rules")]]
    await update.message.reply_text(
        "ᴡᴇʟᴄᴏᴍᴇ \n\n"
        "➞ ᴀʙᴛᴏᴘᴘийᴏᴍ зᴀяʙᴏᴋ\n"
        "➞ пᴇᴘᴇʙіᴘᴋᴀ пᴏᴄиʌᴀнь\n"
        "➞ /font - ᴛᴇᴋᴄᴛ ᴄᴛᴀйʌᴇᴘ\n\n"
        "➞ ШІ — дʌя чʌᴇніʙ ᴋʌубу (ᴀʌᴏ)\n"
        "➞ ᴘᴀɪɴᴛ ᴀᴘᴘ (ᴘʀᴏᴛᴏᴛʏᴘᴇ)",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.MARKDOWN
    )

# ========================================
# ОСНОВНІ ОБРОБНИКИ (для webhook)
# ========================================
def setup_main_handlers(app: Application):
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("font", font_start)],
        states={0: [MessageHandler(filters.TEXT & ~filters.COMMAND, font_get_text)]},
        fallbacks=[CommandHandler("cancel", font_cancel)],
        allow_reentry=True
    ))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_gemini_message_private))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)ало') & filters.ChatType.GROUPS,
        handle_gemini_message_group
    ))
    link_filters = filters.Entity("url") | filters.Entity("text_link")
    app.add_handler(MessageHandler(link_filters & filters.ChatType.GROUPS, check_links))

# ========================================
# ОКРЕМИЙ POLLING ДЛЯ chat_join_request
# ========================================
async def run_join_request_polling():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    
    logger.info("=== POLLING ДЛЯ chat_join_request ЗАПУЩЕНО ===")
    await app.run_polling(
        allowed_updates=["chat_join_request"],
        drop_pending_updates=True
    )

# ========================================
# WEBHOOK SERVER
# ========================================
async def start_webhook():
    app = Application.builder().token(TOKEN).job_queue(JobQueue()).build()
    setup_main_handlers(app)
    
    await app.initialize()
    await app.start()

    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}/webhook_{TOKEN}"
    await app.bot.set_webhook(
        url=webhook_url,
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query", "my_chat_member", "web_app_data"]
    )
    logger.info(f"Webhook встановлено: {webhook_url}")

    # Запускаємо aiohttp сервер
    web_app = web.Application()
    web_app.router.add_post(f'/webhook_{TOKEN}', lambda req: app.update_queue.put(Update.de_json(req.json(), app.bot)))
    web_app.router.add_get('/', lambda req: web.Response(text="OK"))
    web_app.router.add_get('/health', lambda req: web.Response(text="OK"))

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info("Webhook сервер запущено")

    # Запускаємо polling для join request
    asyncio.create_task(run_join_request_polling())

    await asyncio.Event().wait()  # Тримаємо процес живим

# ========================================
# ЗАПУСК
# ========================================
def main():
    if os.getenv("RENDER") == "true":
        logger.info("=== RENDER: ГІБРИДНИЙ РЕЖИМ (webhook + polling) ===")
        asyncio.run(start_webhook())
    else:
        logger.info("=== LOCAL: POLLING ===")
        app = Application.builder().token(TOKEN).build()
        setup_main_handlers(app)
        app.add_handler(ChatJoinRequestHandler(handle_join_request))
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()