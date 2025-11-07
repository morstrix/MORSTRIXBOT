# handlers.py

import os
import re
import json # ✅ ДОДАНО: Для обробки JSON-даних від Web App
import datetime # ✅ ДОДАНО: Хоча зараз не використовується, потрібен для Push (нагадувань)
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackContext 
from telegram.constants import ParseMode
from dotenv import load_dotenv

# ✅ НОВІ ІМПОРТИ для font
from font_utils import convert_text_to_font 

# Визначення станів діалогу
FONT_TEXT = 0

# Завантажуємо змінні оточення
if os.getenv("RENDER") != "true":
    load_dotenv()


# --- Функція для обробки даних, що надходять від Web App (drafts.html) ---
async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє дані, що надходять від Web App (наприклад, піксельний арт)."""
    
    web_app_data = update.effective_message.web_app_data
    if not web_app_data:
        return

    data_string = web_app_data.data
    user_id = update.effective_user.id
    
    parts = data_string.split('|', 2)
    
    if len(parts) < 3:
         await update.effective_message.reply_text("❌ Помилка: Невірний формат даних від Web App.")
         return

    draft_type, cell_key, json_payload = parts
    
    # 1. Обробка ART (Надсилання піксельного арту)
    if draft_type == 'ART_DATA':
        try:
            art_matrix = json.loads(json_payload)
            
            # ВІДПОВІДЬ: Надсилаємо підтвердження
            await update.effective_message.reply_text(
                f"🎨 Ваш піксельний арт (Ключ: `{cell_key}`) прийнято! \n"
                f"Розмір сітки: {len(art_matrix)}x{len(art_matrix[0])}.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await update.effective_message.reply_text("❌ Помилка при обробці АРТУ.")
            print(f"Помилка обробки ART: {e}")
            
    # 2. Обробка PUSH/NOTE (якщо цей функціонал буде додано пізніше)
    elif draft_type == 'NOTE':
         await update.effective_message.reply_text("📝 Замітка прийнята (функціонал зберігання буде реалізовано).")
    elif draft_type == 'PUSH':
         await update.effective_message.reply_text("⏰ Нагадування прийнято (функціонал планування буде реалізовано).")


# --- Обробник нових учасників (Автопривітання) ---
# ... (залишаємо handle_new_members без змін)
async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if not member.is_bot:
            
            # Кнопка для правил
            keyboard = [[InlineKeyboardButton("пᴘᴀʙиʌᴀ", callback_data="show_rules")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            welcome_message = (
                f"ᴀйо {member.full_name}! \n"
                f"ᴏзнᴀйᴏᴍᴛᴇᴄя з пᴘᴀʙиʌᴀᴍи."
            )
            
            # Перевіряємо, чи це група з темами (форум)
            thread_id = update.message.message_thread_id if update.message.is_topic_message else None

            await update.message.reply_text(
                welcome_message,
                reply_markup=reply_markup,
                message_thread_id=thread_id
            )

# --- Обробник запитів на приєднання (Автоприйом заявок + Автосмс) ---
# ... (залишаємо handle_join_request без змін)
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.chat.id
    user_id = update.from_user.id
    user_full_name = update.from_user.full_name
    
    try:
        # 1. Автоприйом
        await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        
        # 2. Автосмс (приватне повідомлення після схвалення)
        await context.bot.send_message(
            user_id, 
            f"✅ {user_full_name}! запит схвалено"
        )
        
    except Exception as e:
        print(f"Помилка схвалення запиту на приєднання або відправки автосмс: {e}")

# --- Обробник Callback Query (Inline кнопки для правил) ---
# ... (залишаємо handle_callback_query без змін)
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Завжди відповідаємо на query, щоб прибрати "годинник"

    if query.data == "show_rules":
        # Відредагувати повідомлення, щоб показати правила
        rules_text = (
            "ᴋᴏᴘиᴄᴛуйᴄя ᴛᴘигᴇᴘᴏᴍ ᴀʌᴏ"
        )
        try:
             await query.edit_message_text(text=rules_text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
             # Якщо повідомлення занадто старе, просто відправити нове
             await query.message.reply_text(rules_text, parse_mode=ParseMode.MARKDOWN)


# ----------------------------------------------------
#               💥 Обробники Діалогу /font 💥
# ----------------------------------------------------

# ... (font_start, font_get_text, font_cancel без змін)
async def font_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє команду /font, починаючи діалог."""
    
    # Зберігаємо ID команди та чату для подальшого видалення/взаємодії
    context.user_data['font_chat_id'] = update.effective_chat.id
    context.user_data['font_command_id'] = update.message.message_id
    
    # Відправляємо запит
    message = await update.message.reply_text(
        "ᴋᴀᴛᴀй ᴛᴇᴋᴄᴛ. \n\n"
        "/cancel дʌя ᴄᴋᴀᴄуʙᴀння."
    )
    # Зберігаємо ID повідомлення від бота, щоб потім його видалити
    context.user_data['font_bot_request_id'] = message.message_id

    return FONT_TEXT

async def font_get_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє введений користувачем текст, перетворює його та завершує діалог."""
    
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    if not user_text:
        await update.message.reply_text("Ви нічого не ввели. Будь ласка, введіть текст або /cancel.")
        return FONT_TEXT # Залишаємося в тому ж стані
    
    # 1. Перетворення тексту
    converted_text = convert_text_to_font(user_text)
    
    # 2. Видалення службових повідомлень (для чистоти чату)
    try:
        # Видаляємо команду користувача /font
        await context.bot.delete_message(
            chat_id=chat_id, 
            message_id=context.user_data.get('font_command_id')
        )
    except Exception as e:
        print(f"Помилка видалення команди /font: {e}")
        
    try:
        # Видаляємо повідомлення-запит від бота
        await context.bot.delete_message(
            chat_id=chat_id, 
            message_id=context.user_data.get('font_bot_request_id')
        )
    except Exception as e:
        print(f"Помилка видалення запиту бота: {e}")

    try:
        # Видаляємо повідомлення з введеним текстом від користувача
        await context.bot.delete_message(
            chat_id=chat_id, 
            message_id=update.message.message_id
        )
    except Exception as e:
        print(f"Помилка видалення введеного тексту: {e}")
        
    # 3. Надсилаємо результат
    await context.bot.send_message(
        chat_id=chat_id,
        text=converted_text,
        message_thread_id=update.message.message_thread_id # Зберігаємо контекст теми, якщо це група
    )
    
    # 4. Завершуємо діалог
    return ConversationHandler.END


async def font_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обробляє команду /cancel, завершуючи діалог."""
    
    chat_id = context.user_data.get('font_chat_id', update.effective_chat.id)
    
    # Спроба видалити повідомлення-запит від бота, якщо воно було надіслано
    try:
        await context.bot.delete_message(
            chat_id=chat_id, 
            message_id=context.user_data.get('font_bot_request_id')
        )
    except Exception:
        pass # Ігноруємо помилки, якщо повідомлення вже немає
        
    # Спроба видалити команду /font
    try:
        await context.bot.delete_message(
            chat_id=chat_id, 
            message_id=context.user_data.get('font_command_id')
        )
    except Exception:
        pass
        
    # Надсилаємо коротке повідомлення про скасування
    await update.message.reply_text(
        "❌ Діалог скасовано.",
        message_thread_id=update.message.message_thread_id
    )
    
    # Завершуємо діалог
    return ConversationHandler.END