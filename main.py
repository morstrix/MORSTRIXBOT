# main.py — POLLING (головний) + HTTP-сервер (фон)

import os
import asyncio
import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ChatJoinRequestHandler, CallbackQueryHandler,
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

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.environ.get("PORT", 8080))

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не знайдено!")

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
# РЕЄСТРАЦІЯ ОБРОБНИКІВ
# ========================================
def setup_handlers(app: Application):
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("font", font_start)],
        states={0: [MessageHandler(filters.TEXT & ~filters.COMMAND, font_get_text)]},
        fallbacks=[CommandHandler("cancel", font_cancel)],
        allow_reentry=True
    ))
    app.add_handler(CallbackQueryHandler(handle_callback_query))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_gemini_message_private))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)ало') & filters.ChatType.GROUPS,
        handle_gemini_message_group
    ))
    link_filters = filters.Entity("url") | filters.Entity("text_link")
    app.add_handler(MessageHandler(link_filters & filters.ChatType.GROUPS, check_links))

# ========================================
# HTTP-сервер (для Render)
# ========================================
async def health_check(request):
    return web.Response(text="MORSTRIX BOT IS ALIVE", status=200)

async def start_http_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"HTTP-сервер запущено на порту {PORT}")

# ========================================
# ЗАПУСК
# ========================================
def main():
    if os.getenv("RENDER") == "true":
        logger.info("=== RENDER: POLLING + HTTP HEALTH CHECK ===")
        
        # Запускаємо HTTP-сервер у фоні
        loop = asyncio.get_event_loop()
        loop.create_task(start_http_server())
        
        # Запускаємо polling у головному потоці
        app = Application.builder().token(TOKEN).build()
        setup_handlers(app)
        
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=[
                "message", "callback_query", "chat_join_request",
                "my_chat_member", "chat_member", "web_app_data"
            ]
        )
    else:
        logger.info("=== LOCAL: POLLING ===")
        app = Application.builder().token(TOKEN).build()
        setup_handlers(app)
        app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()