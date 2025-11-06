# ai.py

import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import ContextTypes
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPICallError 

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID') 

# =========================================================================
# КОНСТАНТИ ДЛЯ GEMINI ТА ПЕРЕВІРКИ ПІДПИСКИ
# =========================================================================
MODEL_NAME = "gemini-2.5-flash" 
FORUM_INVITE_LINK = "https://t.me/+7Xmj6pPB0mEyMDky" 
FORUM_BUTTON_TEXT = "☇ ꜰ ☻‌ ʀ ᴜ ʍ❓" 

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Ошибка: GEMINI_API_KEY не найден в .env файле. Функциональность Gemini будет недоступна.")
    
if not TELEGRAM_CHAT_ID:
    print("Ошибка: TELEGRAM_CHAT_ID не найден в .env файле. Проверка подписки для личных сообщений не будет работать.")

last_request_time = 0
MIN_DELAY_SECONDS = 60

SYSTEM_PROMPT = (
    "Ты — бот-помощник, который отвечает коротко, культурно, конструктивно и грамотным украин..."
)

# ... (остальные функции _get_gemini_response, _check_and_reply_subscription, handle_gemini_message_group остаются без изменений)


async def handle_gemini_message_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает любое сообщение в личном чате с ботом (только текст).
    """
    # УДАЛЕНО: if context.user_data.get('state') == 'support': return

    user_text = update.message.text
    
    if not user_text or user_text.startswith('/'):
        return
    
    if not await _check_and_reply_subscription(update, context):
        return

    await update.message.reply_chat_action("typing")
    
    reply = await _get_gemini_response(user_text)

    if reply:
        await update.message.reply_text(
            reply,
            message_thread_id=update.message.message_thread_id
        )