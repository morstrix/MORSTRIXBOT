import os
import time
# ✅ Видалено ChatMember, залишено Chat
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
    "Ты — бот-помощник, который отвечает коротко, культурно, конструктивно и грамотным украинским языком. "
    "Каждый твой ответ должен содержать эмодзи, соответствующий контексту и быть максимально полезным. "
)

async def _get_gemini_response(user_text):
    """
    Получает ответ от Gemini (только текст).
    """
    global last_request_time

    current_time = time.time()
    if current_time - last_request_time < MIN_DELAY_SECONDS:
        remaining_time = int(MIN_DELAY_SECONDS - (current_time - last_request_time))
        return f"почекай трохи 🫩 відпочину {remaining_time}"

    if not GEMINI_API_KEY:
        print("API ключ не настроен. Невозможно получить ответ.")
        return "у мене немає api ключа 🔑"

    try:
        model = genai.GenerativeModel(MODEL_NAME, system_instruction=SYSTEM_PROMPT) 
        
        response = model.generate_content(
            user_text
        )

        last_request_time = current_time
        return response.text

    except GoogleAPICallError as e:
        error_message = str(e)
        print(f"Ошибка при работе с Gemini API: {error_message}")
        if "401" in error_message or "Invalid API Key" in error_message:
            return "ой 😔, мій API ключ не дійсний"
        elif "429" in error_message or "Rate limit exceeded" in error_message:
            return "забагато запитів 🥵, почекай хвилину"
        elif "404" in error_message:
             return "помилка 404 🧐: модель не знайдена. Перевір ім'я моделі в ai.py."
        else:
            return f"не можу відповісти 🤯: {error_message[:50]}..." 

    except Exception as e:
        print(f"Неизвестная ошибка: {e}")
        return "щось зламалось 💔"


async def _check_and_reply_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Проверяет, является ли пользователь участником целевого чата.
    Использует строковые константы статуса для старых версий python-telegram-bot.
    """
    if not TELEGRAM_CHAT_ID:
        return True

    user_id = update.effective_user.id
    
    keyboard = [[InlineKeyboardButton(FORUM_BUTTON_TEXT, url=FORUM_INVITE_LINK)]] 
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        chat_member = await context.bot.get_chat_member(
            chat_id=TELEGRAM_CHAT_ID,
            user_id=user_id
        )
        
        # ✅ ИСПРАВЛЕНИЕ: Используем строковые значения, так как константы Chat.MEMBER не найдены.
        # Эти строковые значения универсальны для всех версий Telegram API.
        is_member = chat_member.status in [
            'member', 'administrator', 'creator'
        ]

        if not is_member:
            await update.message.reply_text(
                "тільки для членів клубу",
                reply_markup=reply_markup
            )
            return False
    except Exception as e:
        # Эта ветка обрабатывает ошибки, связанные с неправильным ID чата или правами бота.
        print(f"Помилка перевірки підписки для користувача {user_id}: {e}")
        await update.message.reply_text("не можу перевірити підписку") 
        return False
    
    return True

async def handle_gemini_message_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает сообщения в групповом чате, содержащие слово "ало" (только текст).
    """
    if not await _check_and_reply_subscription(update, context):
        return

    if not update.message.text:
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
    Обрабатывает любое сообщение в личном чате с ботом (только текст).
    """
    if context.user_data.get('state') == 'support':
        return

    user_text = update.message.text
    
    if not user_text or user_text.startswith('/'):
        return
    
    if not await _check_and_reply_subscription(update, context):
        return

    await update.message.reply_chat_action("typing")
    
    reply = await _get_gemini_response(user_text)
    
    if reply:
        await update.message.reply_text(reply)