import os
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Chat
from telegram.ext import ContextTypes
# ✅ ДОДАНО: Імпорт статусів для коректного порівняння
from telegram.constants import ChatMemberStatus 
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core.exceptions import GoogleAPICallError 

load_dotenv()
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID') 

# =========================================================================
# КОНСТАНТИ
# =========================================================================
MODEL_NAME = "gemini-2.5-flash" 
FORUM_INVITE_LINK = "https://t.me/+7Xmj6pPB0mEyMDky" 
FORUM_BUTTON_TEXT = "☇ ꜰ ☻‌ ʀ ᴜ ʍ❓" 

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ✅ Строкове представлення ID для коректного порівняння
TELEGRAM_CHAT_ID_STR = str(TELEGRAM_CHAT_ID) if TELEGRAM_CHAT_ID else None

last_request_time = 0
MIN_DELAY_SECONDS = 60

SYSTEM_PROMPT = (
    "Ты — бот-помощник. Отвечай максимально кратким, прямым, конструктивным и **грамотным украинским языком**. "
    "Избегай подробных объяснений и длинных абзацев. **Каждый твой ответ должен содержать один эмодзи**, соответствующий контексту. "
    "**КАТЕГОРИЧЕСКИ запрещено использовать символы Markdown, такие как звездочки (*), для выделения жирным или курсивом, "
    "а также другие форматирующие символы. Отвечай исключительно простым текстом.**"
)

async def _get_gemini_response(user_text):
    global last_request_time
    current_time = time.time()
    
    if current_time - last_request_time < MIN_DELAY_SECONDS:
        remaining_time = int(MIN_DELAY_SECONDS - (current_time - last_request_time))
        return f"почекай трохи 🫩 відпочину {remaining_time} секунд."

    if not GEMINI_API_KEY:
        return "у мене немає api ключа 🔑"

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME, 
            system_instruction=SYSTEM_PROMPT
        ) 
        response = model.generate_content([user_text])
        last_request_time = current_time
        return response.text
    except Exception as e:
        print(f"Error Gemini: {e}")
        return "щось зламалось 💔"

async def _check_and_reply_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Проверяет подписку, сравнивая статус как ОБЪЕКТ, а не строку.
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
        
        # ✅ ВИПРАВЛЕНО: Використовуємо об'єкти ChatMemberStatus, а не рядки.
        # Це виправляє баг, де адмін розпізнавався як "не підписаний".
        is_member = chat_member.status in [
            ChatMemberStatus.MEMBER, 
            ChatMemberStatus.ADMINISTRATOR, 
            ChatMemberStatus.OWNER
        ]

        if not is_member:
            await update.message.reply_text(
                "тільки для членів клубу 👑",
                reply_markup=reply_markup
            )
            return False
            
    except Exception as e:
        print(f"Помилка перевірки (можливо бот не адмін або ID невірний): {e}")
        # Якщо сталася помилка перевірки - на всяк випадок просимо підписатися
        await update.message.reply_text("не можу перевірити підписку ⚠️") 
        return False
    
    return True

async def handle_gemini_message_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: 
        return

    # Перевірка на ключове слово "ало"
    if update.message.text is None or "ало" not in update.message.text.lower():
        return
        
    current_chat_id_str = str(update.effective_chat.id)
    
    # 1. Якщо це цільовий чат - пропускаємо перевірку
    if TELEGRAM_CHAT_ID_STR and current_chat_id_str == TELEGRAM_CHAT_ID_STR:
        is_subscribed = True
    else:
        # 2. В інших чатах - перевіряємо через виправлену функцію
        is_subscribed = await _check_and_reply_subscription(update, context)

    if not is_subscribed:
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