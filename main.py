# main.py

import os
import asyncio
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ChatJoinRequestHandler, CallbackQueryHandler, JobQueue
)
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv
from aiohttp import web # ✅ Используем aiohttp для асинхронного Webhook/Web App сервера

# Импорты ваших модулей
from ai import handle_gemini_message_group, handle_gemini_message_private
from handlers import (
    handle_new_members, handle_join_request, handle_callback_query,
    open_drafts_webapp, handle_webapp_data, font_command
)
# Вынесли функционал Web App в отдельный модуль
import webapp_server 

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
    await update.message.reply_text("Бот запущен и готов к работе.")

# Инициализация объекта application
job_queue = JobQueue()
application = Application.builder().token(TELEGRAM_BOT_TOKEN).job_queue(job_queue).build()


# Регистрация Обработчиков
application.add_handler(CommandHandler("start", start_command))
application.add_handler(CommandHandler("drafts", open_drafts_webapp, filters.ChatType.PRIVATE))
application.add_handler(CommandHandler("font", font_command, filters.ChatType.ALL)) # /font теперь команда, а не ConversationHandler

application.add_handler(CallbackQueryHandler(handle_callback_query)) 
application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_members))
application.add_handler(ChatJoinRequestHandler(handle_join_request))

# === Обработка WebApp Data
application.add_handler(MessageHandler(
    filters.StatusUpdate.WEB_APP_DATA,
    handle_webapp_data
))

# Обработчики Gemini 
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_gemini_message_private))
application.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND & filters.Regex(r'(?i)ало') & filters.ChatType.GROUPS,
    handle_gemini_message_group
))
# Если захотите добавить проверку ссылок:
# link_filters = filters.Entity("url") | filters.Entity("text_link")
# application.add_handler(MessageHandler(link_filters & filters.ChatType.GROUPS, check_links))


# ----------------------------------------------------
#           💥 Webhook и Web App Server (aiohttp) 💥
# ----------------------------------------------------

# Загружаем логику сервера Web App из webapp_server.py
async def start_webhook_server(application: Application):
    """Настраивает и запускает aiohttp сервер для Webhook и Web App."""
    
    # 1. Настройка aiohttp
    app = web.Application()

    # 2. Добавляем Webhook Telegram
    webhook_path = f'/{TELEGRAM_BOT_TOKEN}'
    app.router.add_post(webhook_path, webapp_server.handle_telegram_webhook)

    # 3. Добавляем маршруты Web App
    app.router.add_get('/', webapp_server.handle_index)
    app.router.add_get('/drafts', webapp_server.handle_drafts_html) # Ваш HTML-файл
    
    # Добавляем объект Application и Bot в контекст aiohttp
    app['bot_app'] = application
    
    # 4. Установка Webhook
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
    
    # 5. Запуск сервера
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    print(f"Запуск aiohttp Web App на порту {PORT}")
    await site.start()
    
    # Бесконечный цикл, пока bot_app работает
    await application.start()
    await application.updater.start_polling()

# ----------------------------------------------------
#                      Запуск
# ----------------------------------------------------

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