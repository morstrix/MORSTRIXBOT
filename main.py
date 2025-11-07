# main.py

import os
import asyncio
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ChatJoinRequestHandler, CallbackQueryHandler, JobQueue,
    ConversationHandler 
)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup # ✅ ДОДАНО: Inline-кнопки
from telegram.ext import ContextTypes
# ✅ ВИПРАВЛЕНО ІМПОРТ: UpdateType повинен бути тут
from telegram.constants import ParseMode, UpdateType 
from dotenv import load_dotenv
from aiohttp import web 

# Импорты ваших модулей
from ai import handle_gemini_message_group, handle_gemini_message_private
from handlers import (
    handle_new_members, handle_join_request, handle_callback_query,
    font_start, font_get_text, font_cancel,
    handle_web_app_data, # ✅ ВІДНОВЛЕНО
)
from safe import check_links 

# ----------------------------------------------------
# 🛡️ КОНФИГУРАЦИЯ
# ----------------------------------------------------

if os.getenv("RENDER") != "true":
    load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
PORT = int(os.environ.get("PORT", 8080))

# ----------------------------------------------------
#          Инициализация Telegram Application
# ----------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ᴡᴇʟᴄᴏᴍᴇ \n\n"
        "фунᴋціᴏнᴀʌ:\n"
        "➞ ᴀʙᴛᴏпᴘийᴏᴍ зᴀяʙᴏᴋ\n"
        "➞ пᴇᴘᴇʙіᴘᴋᴀ пᴏᴄиʌᴀнь\n"
        "➞ /font - ᴛᴇᴋᴄᴛ ᴄᴛᴀйʌᴇᴘ \n\n"
        "➞ ШІ — дʌя чʌᴇніʙ ᴋʌубу.\n"
        "ᴛᴘигᴇᴘ ᴀʌᴏ у гᴘупі.\n\n"
        "➞ ʜᴇʟᴘᴇʀ: ɴᴏᴛᴇ/ᴀʀᴛ/ᴘᴜꜱʜ", # Або можна повернути стару версію тексту, дивлячись на те, яку ви обрали.
        parse_mode=ParseMode.MARKDOWN
    )

job_queue = JobQueue()
application = Application.builder().token(TELEGRAM_BOT_TOKEN).job_queue(job_queue).build()

# 🆕 СТАНИ ДЛЯ FONT_HANDLER
FONT_START, FONT_GET_TEXT = range(2)

# ----------------------------------------------------
#               ФУНКЦІЯ ДЛЯ /drafts (ВІДНОВЛЕНО)
# ----------------------------------------------------

async def drafts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Відкриває Web App з чернетками (drafts)."""
    
    web_app_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/drafts.html" if RENDER_EXTERNAL_URL else "https://example.com/drafts.html"
    
    keyboard = [[InlineKeyboardButton("📝 ВІДКРИТИ DRAFTZ", web_app={"url": web_app_url})]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📝 **MORSTRIX DRAFTZ** \nСтворюй каталоги, нотатки, нагадування та піксельний арт.",
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN
    )


# ====================================================
#              РЕЄСТРАЦІЯ ОБРОБНИКІВ
# ====================================================

application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("drafts", drafts_command)) # ✅ ВІДНОВЛЕНО /drafts

# 💥 FONT CONVERSATION HANDLER 💥
font_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("font", font_start)],
    states={
        FONT_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, font_get_text)],
        FONT_GET_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, font_get_text)], 
    },
    fallbacks=[CommandHandler("cancel", font_cancel)],
    allow_reentry=True
)

application.add_handler(font_conv_handler)


application.add_handler(CallbackQueryHandler(handle_callback_query)) 
application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
application.add_handler(ChatJoinRequestHandler(handle_join_request))

# ✅ ФІКС: Використовуємо коректну константу filters.StatusUpdate.WEB_APP_DATA
application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data)) 

# Обработчики Gemini (ІІ з перевіркою)
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_gemini_message_private))
application.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)ало') & filters.ChatType.GROUPS,
    handle_gemini_message_group
))

# ✅ Обробник для перевірки посилань (автоматичний)
link_filters = filters.Entity("url") | filters.Entity("text_link")
application.add_handler(MessageHandler(link_filters & filters.ChatType.GROUPS, check_links))


# ----------------------------------------------------
#           💥 Webhook Server (aiohttp) 💥
# ----------------------------------------------------

async def start_webhook_server(application: Application):
    """Настраивает и запускает aiohttp сервер для Webhook."""
    
    # 1. Настройка aiohttp
    app = web.Application()

    # ✅ ВІДНОВЛЕНО: Додаємо статику для доступу до drafts.html
    app.router.add_static('/', path='./', name='static_files', follow_symlinks=True) 

    # 2. Добавляем Webhook Telegram
    webhook_path = f'/{TELEGRAM_BOT_TOKEN}'
    
    async def handle_telegram_webhook(request):
        """Обрабатывает запросы Webhook от Telegram."""
        bot_app = request.app['bot_app']
        
        if request.content_length > 10**6: 
            print("Запрос слишком большой, игнорируется.")
            return web.Response(text="request too large", status=413)
            
        try:
            data = await request.json()
        except Exception as e:
            print(f"Ошибка получения JSON: {e}")
            return web.Response(text="bad request", status=400)
            
        await bot_app.update_queue.put(Update.de_json(data=data, bot=bot_app.bot))
        return web.Response(text="ok", status=200)

    app.router.add_post(webhook_path, handle_telegram_webhook)

    # 3. Добавляем простой health check
    async def handle_health_check(request):
        return web.Response(text="Bot is running!", status=200)
    app.router.add_get('/', handle_health_check)
    
    # Добавляем объект Application и Bot в контекст aiohttp
    app['bot_app'] = application
    
    # 4. Ініціалізація додатка
    await application.initialize()
    
    # 5. Установка Webhook
    if RENDER_EXTERNAL_URL:
        base_url = RENDER_EXTERNAL_URL.rstrip('/')
        full_webhook_url = f"{base_url}{webhook_path}"
        
        print(f"Установка вебхука на: {full_webhook_url}")
        await application.bot.set_webhook(
            url=full_webhook_url,
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        print("Вебхук успешно установлен.")
    
    # 6. Запуск сервера
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    print(f"Запуск aiohttp Webhook Server на порту {PORT}")
    await site.start()
    
    # Запуск додатка (включає JobQueue)
    await application.start()
    
    # Бесконечный цикл, щоб тримати процес активним
    await asyncio.Future() 

# ----------------------------------------------------\
#                      Запуск
# ----------------------------------------------------\

def main():
    if os.getenv("RENDER") == "true":
        print("Запуск в режиме Webhook (Render)...")
        # Запускаем асинхронный сервер
        asyncio.run(start_webhook_server(application))
    else:
        print("Запуск бота в режиме опроса (Polling).")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Сталася фатальна помилка при запуску: {e}")