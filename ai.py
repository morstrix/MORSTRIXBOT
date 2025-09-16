import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import ContextTypes
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Ошибка: GEMINI_API_KEY не найден в .env файле. Функциональность Gemini будет недоступна.")
    
if not TELEGRAM_CHAT_ID:
    print("Ошибка: TELEGRAM_CHAT_ID не найден в .env файле. Проверка подписки для личных сообщений не будет работать.")

last_request_time = 0
MIN_DELAY_SECONDS = 60

SYSTEM_PROMPT = (
    "Ты — бот-помощник, который отвечает коротко, культурно, конструктивно и грамотным украинским языком. "
    "Каждый твой ответ должен содержать эмодзи, соответствующий контексту и быть максимально полезным. "
)

async def _get_gemini_response(user_text):
    global last_request_time

    current_time = time.time()
    if current_time - last_request_time < MIN_DELAY_SECONDS:
        remaining_time = int(MIN_DELAY_SECONDS - (current_time - last_request_time))
        return f"почекай трохи 🫩 відпочину {remaining_time}"

    if not GEMINI_API_KEY:
        return "сорян, але в мене перерва"

    try:
        model_name = 'gemini-1.5-flash'
        model = genai.GenerativeModel(model_name)
        combined_prompt = f"{SYSTEM_PROMPT}\nКористувач: {user_text}\nБот:"
        response = model.generate_content(combined_prompt)
        reply = response.text.strip()
        last_request_time = time.time()
        return reply

    except Exception as e:
        print(f"Ошибка при работе с Gemini API: {e}")
        return "шось не працює"

async def _check_and_reply_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not TELEGRAM_CHAT_ID:
        await update.message.reply_text("не можу перевірити підписку")
        return False
        
    try:
        chat_member = await context.bot.get_chat_member(chat_id=int(TELEGRAM_CHAT_ID), user_id=user_id)
        if chat_member.status not in ["member", "creator", "administrator"]:
            keyboard = [[InlineKeyboardButton("ꜰ ☻‌ ʀ ᴜ ʍ", url="https://t.me/+7Xmj6pPB0mEyMDky")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "тільки для членів клубу",
                reply_markup=reply_markup
            )
            return False
    except Exception as e:
        print(f"Помилка перевірки підписки для користувача {user_id}: {e}")
        await update.message.reply_text("не можу перевірити підписку")
        return False
    
    return True

async def handle_gemini_message_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает сообщения в групповом чате, содержащие слово "ало".
    """
    if not await _check_and_reply_subscription(update, context):
        return

    await update.message.reply_chat_action("typing")
    user_text = update.message.text
    reply = await _get_gemini_response(user_text)
    
    if reply:
        await update.message.reply_text(
            reply,
            message_thread_id=update.message.message_thread_id
        )

async def handle_gemini_message_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает любое сообщение в личном чате с ботом.
    """
    if context.user_data.get('state') == 'support':
        return

    user_text = update.message.text
    
    if user_text and user_text.startswith('/'):
        return
    
    if not await _check_and_reply_subscription(update, context):
        return

    await update.message.reply_chat_action("typing")
    reply = await _get_gemini_response(user_text)

    if reply:
        await update.message.reply_text(reply)