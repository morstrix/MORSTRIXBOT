#!/usr/bin/env python3
import os
import sys
import asyncio
import threading
import logging
from flask import Flask, Response

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ========================================
# WEB SERVER FOR KOYEB HEALTH CHECKS (УПРОЩЕННЫЙ)
# ========================================
def run_flask_server():
    """Запускает простой Flask сервер для health checks"""
    app = Flask(__name__)
    
    @app.route('/')
    @app.route('/health')
    def health():
        return "✅ Бот работает", 200
    
    # Используем стандартный Flask dev сервер, но с отключенным debug
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)

# ========================================
# TELEGRAM BOT (ОСТАВЛЯЕМ ТВОЙ КОД)
# ========================================
async def run_telegram_bot():
    """Запускает Telegram бота"""
    try:
        # Импорты внутри функции
        from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
        from telegram.ext import (
            Application, CommandHandler, MessageHandler, filters,
            ChatJoinRequestHandler, CallbackQueryHandler,
            ContextTypes
        )
        from telegram.constants import ParseMode
        import google.generativeai as genai
        
        # Переменные окружения
        TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        
        if not TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN не найден!")
            return
        
        logger.info("🚀 Инициализация Telegram бота...")
        
        # Настройка Gemini
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
        
        # ========================================
        # GEMINI AI ФУНКЦИИ
        # ========================================
        async def get_gemini_response(user_text: str) -> str:
            if not GEMINI_API_KEY:
                return "API ключ не настроен 🔑"
            
            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(
                    f"Отвечай коротко и по делу. Используй украинский язык. Без markdown. Вопрос: {user_text}"
                )
                return response.text if response.text else "Не получил ответ от AI 🤔"
            except Exception as e:
                logger.error(f"Ошибка Gemini: {e}")
                return f"Ошибка AI"
        
        # ========================================
        # ОСНОВНЫЕ КОМАНДЫ БОТА
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
        
        async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "Доступные команды:\n"
                "/start - начало работы\n"
                "/font - стильный текст\n"
                "/help - эта справка\n\n"
                "В чатах бот реагирует на 'ало'"
            )
        
        # ========================================
        # FONT КОМАНДА
        # ========================================
        FONT_MAP = {
            'А': 'ᴀ', 'а': 'ᴀ', 'В': 'в', 'в': 'ʙ', 'Е': 'ᴇ', 'е': 'ᴇ',
            'К': 'ᴋ', 'к': 'ᴋ', 'М': 'ᴍ', 'м': 'ᴍ', 'О': 'ᴏ', 'о': 'ᴏ',
            'Р': 'ᴘ', 'р': 'ᴘ', 'С': 'ᴄ', 'с': 'ᴄ', 'Т': 'т', 'т': 'ᴛ',
        }
        
        async def font_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not context.args:
                await update.message.reply_text("Использование: /font <текст>")
                return
            
            text = ' '.join(context.args)
            if len(text) > 100:
                await update.message.reply_text("Текст слишком длинный (макс 100 символов)")
                return
            
            converted = ''.join([FONT_MAP.get(char, char) for char in text])
            await update.message.reply_text(f"```\n{converted}\n```", parse_mode=ParseMode.MARKDOWN_V2)
        
        # ========================================
        # ОБРАБОТЧИКИ СООБЩЕНИЙ
        # ========================================
        async def handle_message_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.message or not update.message.text:
                return
            
            user_text = update.message.text
            
            if user_text.startswith('/'):
                return
            
            await update.message.reply_chat_action("typing")
            reply = await get_gemini_response(user_text)
            await update.message.reply_text(reply)
        
        async def handle_message_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not update.message or not update.message.text:
                return
            
            text = update.message.text.lower()
            if 'ало' in text:
                await update.message.reply_chat_action("typing")
                reply = await get_gemini_response(update.message.text)
                await update.message.reply_text(
                    reply,
                    message_thread_id=update.message.message_thread_id
                )
        
        async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            
            if query.data == "show_rules":
                await query.edit_message_text(
                    "ᴋᴏᴘиᴄᴛуйᴄя ᴛᴘигᴇᴏᴍ ᴀʌᴏ",
                    parse_mode=ParseMode.MARKDOWN
                )
        
        async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
            try:
                join_req = update.chat_join_request
                chat_id = join_req.chat.id
                user_id = join_req.from_user.id
                
                await context.bot.approve_chat_join_request(
                    chat_id=chat_id, 
                    user_id=user_id
                )
                logger.info(f"✅ Заявка одобрена: {user_id}")
                
            except Exception as e:
                logger.error(f"Ошибка обработки заявки: {e}")
        
        async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
            for member in update.message.new_chat_members:
                if not member.is_bot:
                    keyboard = [[InlineKeyboardButton("пᴘᴀʙиʌᴀ", callback_data="show_rules")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    welcome = f"ᴀйо {member.full_name}!\nᴏзнᴀйᴏᴍᴛᴇᴄя з пᴘᴀʙиʌᴀᴍи."
                    thread_id = update.message.message_thread_id if update.message.is_topic_message else None
                    await update.message.reply_text(
                        welcome, 
                        reply_markup=reply_markup, 
                        message_thread_id=thread_id
                    )
        
        # ========================================
        # НАСТРОЙКА И ЗАПУСК БОТА
        # ========================================
        application = Application.builder().token(TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("font", font_command))
        
        application.add_handler(CallbackQueryHandler(handle_callback))
        application.add_handler(ChatJoinRequestHandler(handle_join_request))
        
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            handle_message_private
        ))
        
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS & filters.Regex(r'(?i)ало'),
            handle_message_group
        ))
        
        application.add_handler(MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            handle_new_members
        ))
        
        # Запускаем бота
        logger.info("✅ Telegram бот запущен в режиме polling...")
        await application.run_polling(
            poll_interval=0.5,
            timeout=30,
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в Telegram боте: {e}")
        import traceback
        traceback.print_exc()

# ========================================
# ГЛАВНАЯ ФУНКЦИЯ
# ========================================
def main():
    """Основная функция запуска"""
    logger.info("🚀 MORSTRIXBOT запускается на Koyeb...")
    
    # Запускаем Flask сервер в отдельном потоке
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