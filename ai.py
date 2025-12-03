import os
import time
# ✅ Видалено ChatMember, залишено Chat
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import ContextTypes
# ✅ ДОДАНО: Імпорт статусів та помилок для коректної перевірки та діагностики
from telegram.constants import ChatMemberStatus 
from telegram.error import Forbidden, BadRequest
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

# ✅ НОВЕ: Строкове представлення ID для коректного порівняння
TELEGRAM_CHAT_ID_STR = str(TELEGRAM_CHAT_ID) if TELEGRAM_CHAT_ID else None

last_request_time = 0
MIN_DELAY_SECONDS = 60

SYSTEM_PROMPT = (
    "Ты — бот-помощник, который отвечает коротко, конструктивно и грамотным украинским языком. "
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
        
        # ✅ ФІНАЛЬНЕ ВИПРАВЛЕННЯ: Явно виключаємо лише 'LEFT' та 'KICKED'. 
        # Будь-який інший статус (member, administrator, creator, restricted) вважається підпискою.
        is_member = chat_member.status not in [
            ChatMemberStatus.LEFT, 
            ChatMemberStatus.KICKED
        ]

        if not is_member:
            await update.message.reply_text(
                "тільки для членів клубу 👑",
                reply_markup=reply_markup
            )
            return False
            
    except (Forbidden, BadRequest) as e:
        # Forbidden: Бот не админ в целевом чате (TELEGRAM_CHAT_ID) или его там нет.
        # BadRequest: Неверный TELEGRAM_CHAT_ID или другие ошибки.
        print(f"Помилка перевірки (Forbidden/BadRequest). Це часто означає, що ID чату невірний або бот не є адміністратором у ньому: {e}")
        await update.message.reply_text(
            "не можу перевірити підписку ⚠️\n"
            "перевір TELEGRAM_CHAT_ID та права бота в ньому"
        ) 
        return False
        
    except Exception as e:
        print(f"Неизвестная ошибка проверки подписки: {e}")
        await update.message.reply_text("не можу перевірити підписку 💔") 
        return False
    
    return True

async def handle_gemini_message_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает сообщения в групповом чате, содержащие слово "ало" (только текст).
    """
    if not update.message: 
        return

    # Перевірка на ключове слово "ало"
    if update.message.text is None or "ало" not in update.message.text.lower():
        return

    current_chat_id_str = str(update.effective_chat.id)
    
    # ✅ НОВЕ: Пропускаємо перевірку підписки, якщо повідомлення прийшло з цільового чату.
    if TELEGRAM_CHAT_ID_STR and current_chat_id_str == TELEGRAM_CHAT_ID_STR:
        is_subscribed = True
    else:
        is_subscribed = await _check_and_reply_subscription(update, context)

    if not is_subscribed:
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
    if not update.message:
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