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
from telegram.constants import ParseMode, UpdateType
from dotenv import load_dotenv
from aiohttp import web

# === Імпорт модулів бота ===
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
    raise ValueError("TELEGRAM_BOT_TOKEN не знайдено! Додай у .env або Render Env Vars.")

# ========================================
# КОМАНДИ
# ========================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ᴡᴇʟᴄᴏᴍᴇ \n\n"
        "фунᴋціᴏнᴀʌ:\n"
        "➞ ᴀʙᴛᴏпᴘийᴏᴍ зᴀяʙᴏᴋ\n"
        "➞ пᴇᴘᴇʙіᴘᴋᴀ пᴏᴄиʌᴀнь\n"
        "➞ /font - ᴛᴇᴋᴄᴛ ᴄᴛᴀйʌᴇᴘ \n\n"
        "➞ ШІ — дʌя чʌᴇніʙ ᴋʌубу.\n"
        "ᴛᴘигᴇᴘ ᴀʌᴏ у гᴘупі.\n\n"
        "➞ ʜᴇʟᴘᴇʀ: ɴᴏᴛᴇ/ᴀʀᴛ/ᴘᴜꜱʜ",
        parse_mode=ParseMode.MARKDOWN
    )

async def drafts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Відкриває DRAFTZ через GitHub Pages (стабільно, швидко, без Render)."""
    web_app_url = "https://morstrix.github.io/MORSTRIXBOT/drafts.html"
    logger.info(f"Відкриваю DRAFTZ: {web_app_url}")

    keyboard = [[InlineKeyboardButton("ВІДКРИТИ DRAFTZ", web_app={"url": web_app_url})]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "**MORSTRIX DRAFTZ**\n"
        "Каталоги • Замітки • Нагадування • Піксельний арт\n"
        "Зберігання: LocalStorage (у браузері)",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )

# ========================================
# РЕЄСТРАЦІЯ ОБРОБНИКІВ
# ========================================
def setup_handlers(application: Application):
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("drafts", drafts_command))

    # FONT CONVERSATION
    font_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("font", font_start)],
        states={
            0: [MessageHandler(filters.TEXT & ~filters.COMMAND, font_get_text)],
        },
        fallbacks=[CommandHandler("cancel", font_cancel)],
        allow_reentry=True
    )
    application.add_handler(font_conv_handler)

    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
    application.add_handler(ChatJoinRequestHandler(handle_join_request))
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
# WEBHOOK SERVER (тільки для Telegram)
# ========================================
async def start_webhook_server(application: Application):
    app = web.Application()

    # Webhook endpoint
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

    # Health check
    async def health(request):
        return web.Response(text="MORSTRIX BOT IS ALIVE", status=200)
    app.router.add_get('/', health)
    app.router.add_get('/health', health)

    # Додаємо application
    app['bot_app'] = application

    # Ініціалізація
    await application.initialize()
    setup_handlers(application)

    # Встановлюємо вебхук
    if os.getenv("RENDER") == "true":
        render_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME')}"
        webhook_url = f"{render_url}{webhook_path}"
    else:
        webhook_url = f"https://example.com{webhook_path}"  # для локального тесту

    logger.info(f"Встановлюю вебхук: {webhook_url}")
    try:
        await application.bot.set_webhook(
            url=webhook_url,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        logger.info("Вебхук успішно встановлено!")
    except Exception as e:
        logger.error(f"Не вдалося встановити вебхук: {e}")

    # Запуск сервера
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Webhook сервер запущено на 0.0.0.0:{PORT}")

    # Запуск JobQueue
    await application.start()
    logger.info("Bot Application запущено.")

    # Тримаємо процес живим
    await asyncio.Future()

# ========================================
# ЗАПУСК
# ========================================
application = Application.builder().token(TELEGRAM_BOT_TOKEN).job_queue(JobQueue()).build()

def main():
    if os.getenv("RENDER") == "true":
        logger.info("=== ЗАПУСК НА RENDER (WEBHOOK) ===")
        asyncio.run(start_webhook_server(application))
    else:
        logger.info("=== ЗАПУСК У РЕЖИМІ POLLING ===")
        setup_handlers(application)
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Критична помилка: {e}", exc_info=True)