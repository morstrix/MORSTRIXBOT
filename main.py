# main.py — WEBHOOK версия

import os
import logging
import hashlib
import hmac
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ChatJoinRequestHandler, CallbackQueryHandler,
    ConversationHandler
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from aiohttp import web
import ssl
import certifi

# === Импорты ===
from ai import handle_gemini_message_group, handle_gemini_message_private
from handlers import (
    handle_new_members, handle_join_request, handle_callback_query,
    font_start, font_get_text, font_cancel,
    handle_web_app_data,
)
from safe import check_links

# ========================================
# КОНФИГУРАЦИЯ
# ========================================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")  # Секретный токен для верификации
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # Ваш домен на Render
PORT = int(os.environ.get("PORT", 8080))

if not all([TOKEN, WEBHOOK_HOST]):
    raise ValueError("Не все переменные окружения установлены!")

# ========================================
# ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ
# ========================================
application = Application.builder().token(TOKEN).build()

# ========================================
# ОБРАБОТЧИКИ (как были)
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
# WEBHOOK ЭНДПОИНТЫ
# ========================================
async def handle_webhook(request):
    """Основной обработчик вебхука"""
    # Верификация секретного токена (опционально, но рекомендуется)
    if WEBHOOK_SECRET:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if not hmac.compare_digest(secret_header or "", WEBHOOK_SECRET):
            return web.Response(status=403, text="Forbidden")
    
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.update_queue.put(update)
        return web.Response(text="OK")
    except Exception as e:
        logging.error(f"Ошибка обработки вебхука: {e}")
        return web.Response(status=500, text="Internal Server Error")

async def health_check(request):
    """Health check для Render"""
    return web.Response(text="MORSTRIX BOT IS ALIVE", status=200)

async def setup_webhook():
    """Установка вебхука"""
    webhook_url = f"{WEBHOOK_HOST}/webhook"
    
    # Установка секретного токена для вебхука
    await application.bot.set_webhook(
        url=webhook_url,
        secret_token=WEBHOOK_SECRET,
        allowed_updates=[
            "message", "callback_query", "chat_join_request",
            "my_chat_member", "chat_member", "web_app_data"
        ]
    )
    
    logging.info(f"Webhook установлен на {webhook_url}")

# ========================================
# ЗАПУСК
# ========================================
async def main():
    # Настройка обработчиков
    setup_handlers(application)
    
    # Инициализация приложения
    await application.initialize()
    
    # Установка вебхука
    await setup_webhook()
    
    # Создание aiohttp приложения
    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    # Запуск сервера
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    
    logging.info(f"Сервер запущен на порту {PORT}")
    
    # Бесконечный цикл
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен")