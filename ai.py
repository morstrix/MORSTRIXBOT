import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import ContextTypes
# ✅ ДОДАНО: Необхідні імпорти для PTB 22.5 та логування
from telegram.constants import ChatMemberStatus 
from telegram.error import Forbidden, BadRequest
import logging 
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

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.error("Ошибка: GEMINI_API_KEY не найден в .env файле. Функциональность Gemini будет недоступна.")
    
if not TELEGRAM_CHAT_ID:
    logger.warning("Ошибка: TELEGRAM_CHAT_ID не найден в .env файле. Проверка подписки для личных сообщений не будет работать.")

# ✅ Очищене строкове представлення ID
TELEGRAM_CHAT_ID_STR = str(TELEGRAM_CHAT_ID).strip() if TELEGRAM_CHAT_ID else None

last_request_time = 0
MIN_DELAY_SECONDS = 60

SYSTEM_PROMPT = (
    "Ты — бот-помощник, который отвечает коротко, конструктивно и грамотньім зумерским сленгом. "
    "Каждый твой ответ должен содержать эмодзи, соответствующий контексту. "
    "Используй украинский язык. не используй markdown розмітку"
)

async def _get_gemini_response(user_text):
    """
    Получает ответ от Gemini (только текст).
    """
    global last_request_time

    current_time = time.time()
    if current_time - last_request_time < MIN_DELAY_SECONDS:
        remaining_time = int(MIN_DELAY_SECONDS - (current_time - last_request_time))
        return f"почекай трохи 🫩 {remaining_time} сек."

    if not GEMINI_API_KEY:
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
        logger.error(f"Ошибка при работе с Gemini API: {error_message}")
        if "401" in error_message or "Invalid API Key" in error_message:
            return "ой 😔, мій API ключ не дійсний"
        elif "429" in error_message or "Rate limit exceeded" in error_message:
            return "забагато запитів 🥵, почекай хвилину"
        elif "404" in error_message:
             return "помилка 404 🧐: модель не знайдена."
        else:
            return f"не можу відповісти 🤯: {error_message[:30]}..." 

    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        # ✅ ПРИМІТКА: Ця помилка ("щось зламалось 💔") виникає, коли виклик API провалюється
        return "щось зламалось 💔"


async def _check_and_reply_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Проверяет, является ли пользователь участником целевого чата (используется только для личных сообщений).
    """
    if not TELEGRAM_CHAT_ID:
        # ✅ КОМЕНТАР: Якщо TELEGRAM_CHAT_ID відсутній, підписка не потрібна.
        return True

    cleaned_chat_id = TELEGRAM_CHAT_ID_STR 
    
    if not cleaned_chat_id:
        logger.error("TELEGRAM_CHAT_ID містить лише пробіли або відсутній після очищення.")
        await update.message.reply_text("не можу перевірити підписку 💔: ID чату порожній.")
        return False 

    user_id = update.effective_user.id
    
    keyboard = [[InlineKeyboardButton(FORUM_BUTTON_TEXT, url=FORUM_INVITE_LINK)]] 
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        chat_member = await context.bot.get_chat_member(
            chat_id=cleaned_chat_id, 
            user_id=user_id
        )
        
        # Логіка, яка виключає лише LEFT та KICKED (використовує ChatMemberStatus)
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
            
    except Forbidden as e:
        logger.error(f"Помилка Forbidden: Бот не може отримати інформацію про членство в чаті {cleaned_chat_id}. Перевір, чи є бот адміністратором. Помилка: {e}")
        await update.message.reply_text(
            "не можу перевірити підписку ⚠️\n"
            "Помилка доступу. Бот не адмін у чаті."
        ) 
        # ✅ ЗМІНА: Повертаємо False, оскільки перевірка не вдалася, і ми не можемо гарантувати підписку.
        return False 
        
    except BadRequest as e:
        logger.error(f"Помилка BadRequest: Невірний TELEGRAM_CHAT_ID '{cleaned_chat_id}' або інші помилки. Помилка: {e}")
        await update.message.reply_text(
            "не можу перевірити підписку ⚠️\n"
            "Помилка запиту. Перевір ID чату."
        ) 
        # ✅ ЗМІНА: Повертаємо False, оскільки ID чату невірний.
        return False 
        
    except Exception as e:
        logger.error(f"Неизвестная ошибка проверки подписки: {e}")
        await update.message.reply_text("не можу перевірити підписку 💔") 
        return False
    
    return True

async def handle_gemini_message_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает сообщения в групповом чате, содержащие слово "ало" (только текст).
    Проверка подписки в группах полностью отключена.
    """
    if not update.message: 
        return

    # Перевірка на ключове слово "ало"
    if update.message.text is None or "ало" not in update.message.text.lower():
        return

    # ✅ ИЗМЕНЕНИЕ: Проверка подписки полностью удалена для группы.
    
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
    Проверка подписки остается.
    """
    if not update.message:
        return

    user_text = update.message.text
    
    if not user_text or user_text.startswith('/'):
        return
    
    # Проверка остается для личных сообщений
    if not await _check_and_reply_subscription(update, context):
        return

    await update.message.reply_chat_action("typing")
    
    reply = await _get_gemini_response(user_text)
    
    if reply:
        await update.message.reply_text(reply)