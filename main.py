#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
import threading
from flask import Flask, Response

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ========================================
# WEB SERVER FOR KOYEB HEALTH CHECKS
# ========================================
def run_flask_server():
    """Запускает Flask сервер для health checks"""
    app = Flask(__name__)
    
    @app.route('/')
    @app.route('/health')
    def health():
        return "✅ Бот работает", 200
    
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)

# ========================================
# TELEGRAM BOT - ПОЛНЫЙ ФУНКЦИОНАЛ
# ========================================
async def run_telegram_bot():
    """Запускает Telegram бота со ВСЕМ функционалом"""
    try:
        # Импортируем ВСЕ модули
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import (
            Application, CommandHandler, MessageHandler, filters,
            ChatJoinRequestHandler, CallbackQueryHandler,
            ContextTypes
        )
        from telegram.constants import ParseMode
        import google.generativeai as genai
        
        # Импортируем твои модули
        from ai import handle_gemini_message_private, handle_gemini_message_group
        from safe import check_links
        from handlers import (
            handle_web_app_data, handle_join_request, 
            handle_new_members, handle_callback_query,
            font_start, font_get_text, font_cancel
        )
        from font_utils import convert_text_to_font
        
        TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        
        if not TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
            return
        
        logger.info("🚀 Инициализация Telegram бота...")
        
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
        
        # ========================================
        # ВСЕ КОМАНДЫ БОТА
        # ========================================
        async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Обработчик команды /start"""
            keyboard = [[InlineKeyboardButton("ПРАВИЛА", callback_data="show_rules")]]
            await update.message.reply_text(
                "ᴡᴇʟᴄᴏᴍᴇ \n\n"
                "➞ ᴀʙᴛᴏᴘᴘийᴏᴍ зᴀяʙᴏᴋ\n"
                "➞ пᴇᴘᴇʙіᴘᴋᴀ пᴏᴄиʌᴀнь\n"
                "➞ /font - ᴛᴇᴋᴄᴛ ᴄᴛᴀйʌᴇᴘ\n\n"
                "➞ ШІ — дʌя чʌᴇніʙ ᴋʌубу (ᴀʌᴏ)\n"
                "➞ ᴘᴀɪɴᴛ ᴀᴘᴘ (ᴘʀᴏᴛᴏᴛʏᴘᴇ)\n"
                "➞ /tetris - играть в тетрис",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        
        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "Доступные команды:\n"
                "/start - начало работы\n"
                "/font - стильный текст\n"
                "/tetris - играть в тетрис\n"
                "/help - эта справка\n\n"
                "Бот также:\n"
                "• Отвечает на 'ало' в группах\n"
                "• Проверяет ссылки на безопасность\n"
                "• Обрабатывает заявки в группы"
            )
        
        async def tetris_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Команда /tetris"""
            await update.message.reply_text(
                "🎮 TETRIS Game\n\n"
                "Игра доступна по ссылке:\n"
                "https://grimexframe.github.io/MORSTRXBOT/tetris.html\n\n"
                "Или используй Web App если настроено.",
                parse_mode=ParseMode.MARKDOWN
            )
        
        # ========================================
        # ОБРАБОТЧИКИ ИЗ ТВОИХ МОДУЛЕЙ
        # ========================================
        
        # AI обработчики
        async def handle_ai_private_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await handle_gemini_message_private(update, context)
        
        async def handle_ai_group_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await handle_gemini_message_group(update, context)
        
        # Safe links проверка
        async def check_links_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await check_links(update, context)
        
        # Web app данные
        async def handle_web_app_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await handle_web_app_data(update, context)
        
        # Join request
        async def handle_join_request_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await handle_join_request(update, context)
        
        # New members
        async def handle_new_members_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await handle_new_members(update, context)
        
        # Callback queries
        async def handle_callback_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await handle_callback_query(update, context)
        
        # ========================================
        # НАСТРОЙКА И ЗАПУСК БОТА
        # ========================================
        application = Application.builder().token(TOKEN).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("tetris", tetris_command))
        
        # FONT команда (если есть ConversationHandler)
        try:
            from handlers import FONT_TEXT
            from telegram.ext import ConversationHandler
            
            font_conv_handler = ConversationHandler(
                entry_points=[CommandHandler("font", font_start)],
                states={
                    FONT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, font_get_text)]
                },
                fallbacks=[CommandHandler("cancel", font_cancel)]
            )
            application.add_handler(font_conv_handler)
        except:
            # Упрощенная версия font команды
            async def simple_font_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
                if not context.args:
                    await update.message.reply_text("Использование: /font <текст>")
                    return
                
                text = ' '.join(context.args)
                if len(text) > 500:
                    await update.message.reply_text("Текст слишком длинный (макс 500 символов)")
                    return
                
                converted = convert_text_to_font(text)
                await update.message.reply_text(converted, parse_mode=ParseMode.MARKDOWN_V2)
            
            application.add_handler(CommandHandler("font", simple_font_command))
        
        # Добавляем остальные обработчики
        application.add_handler(CallbackQueryHandler(handle_callback_wrapper))
        application.add_handler(ChatJoinRequestHandler(handle_join_request_wrapper))
        
        # Обработчики сообщений
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            handle_ai_private_wrapper
        ))
        
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS & filters.Regex(r'(?i)ало'),
            handle_ai_group_wrapper
        ))
        
        application.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            handle_new_members_wrapper
        ))
        
        # Проверка ссылок (для всех сообщений с ссылками)
        application.add_handler(MessageHandler(
            filters.TEXT & filters.Entity("url"),
            check_links_wrapper
        ))
        
        # Web app данные
        application.add_handler(MessageHandler(
            filters.StatusUpdate.WEB_APP_DATA,
            handle_web_app_wrapper
        ))
        
        # ========================================
        # ЗАПУСК БОТА
        # ========================================
        logger.info("✅ Telegram бот запущен в режиме polling...")
        
        # Запускаем бота (без signal handlers)
        await application.initialize()
        await application.start()
        await application.updater.start_polling(
            poll_interval=0.5,
            timeout=30,
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
        # Бесконечный цикл
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в Telegram боте: {e}")
        import traceback
        traceback.print_exc()

# ========================================
# ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА
# ========================================
def main():
    """Запускает Flask и Telegram бота"""
    logger.info("🚀 MORSTRIXBOT запускается на Koyeb...")
    
    # Запускаем Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask_server, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask сервер запущен на порту 8080")
    
    # Запускаем Telegram бота
    try:
        asyncio.run(run_telegram_bot())
    except KeyboardInterrupt:
        logger.info("⏹ Бот остановлен")
    except Exception as e:
        logger.error(f"💀 Фатальная ошибка: {e}")

if __name__ == "__main__":
    main()