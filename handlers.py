# handlers.py

import os
import re
import json 
import datetime 
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackContext 
from telegram.constants import ParseMode
from dotenv import load_dotenv

from font_utils import convert_text_to_font 

# Вынесено из тела файла для предотвращения ошибок
FONT_TEXT = 0

if os.getenv("RENDER") != "true":
    load_dotenv()

# --- Функція для виконання запланованого пуша ---
async def send_scheduled_push(context: ContextTypes.DEFAULT_TYPE):
    """Надсилає заплановане нагадування (пуш) користувачеві."""
    job = context.job
    user_id = job.chat_id
    text = job.data['text']
    item_id = job.data['item_id']
    
    try:
        await context.bot.send_message(
            user_id, 
            f"🔔 НАГАДУВАННЯ ({item_id}):\n\n*_{text}_*", 
            parse_mode=ParseMode.MARKDOWN
        )
        print(f"✅ Нагадування надіслано користувачу {user_id}")
    except Exception as e:
        print(f"Помилка відправки нагадування: {e}")


# --- Обробник даних, що надходять від Web App (drafts.html) ---
async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє дані, що надходять від Web App (Art, Push, Note)."""
    
    web_app_data = update.effective_message.web_app_data
    if not web_app_data:
        return

    data_string = web_app_data.data
    user_id = update.effective_user.id
    
    parts = data_string.split('|', 2)
    
    if len(parts) < 3:
         await update.effective_message.reply_text("❌ Помилка: Невірний формат даних від Web App.")
         return

    draft_type, full_item_key, json_payload = parts
    
    # Ключ тепер виглядає як CATALOG_ID_ITEM_ID
    
    # 1. Обробка ART (Надсилання піксельного арту)
    if draft_type == 'ART':
        try:
            art_matrix = json.loads(json_payload)
            
            await update.effective_message.reply_text(
                f"🎨 Ваш піксельний арт (Ключ: `{full_item_key}`) прийнято! \n"
                f"*_Арт надіслано для подальшої обробки (конвертації в зображення)._*",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await update.effective_message.reply_text("❌ Помилка при обробці АРТУ.")
            print(f"Помилка обробки ART: {e}")
            
    # 2. Обробка PUSH (Планування нагадування)
    elif draft_type == 'PUSH':
        try:
            push_data = json.loads(json_payload)
            text = push_data.get('text', 'Нагадування')
            datetime_str = push_data.get('datetime')
            
            if not datetime_str:
                 await update.effective_message.reply_text("❌ Помилка: Не вказано час для нагадування.")
                 return
                 
            # Конвертуємо рядок часу у datetime об'єкт.
            # Нагадування з Web App надсилається з локальним часом, 
            # але datetime.fromisoformat обробляє його як 'наївний' (без часової зони), 
            # що нормально для JobQueue (виконає за годинником сервера)
            schedule_time = datetime.datetime.fromisoformat(datetime_str)
            
            now_utc = datetime.datetime.now() 
            if schedule_time < now_utc:
                # Якщо час у минулому, або минулий локальний час, плануємо на 5 секунд пізніше поточного часу UTC
                schedule_time = now_utc + datetime.timedelta(seconds=5) 
                
            # Додаємо завдання в JobQueue
            context.job_queue.run_once(
                send_scheduled_push, 
                when=schedule_time, 
                chat_id=user_id, # Надсилаємо приватно
                name=f"push_{full_item_key}",
                data={'text': text, 'item_id': full_item_key}
            )
            
            formatted_time = schedule_time.strftime("%d.%m о %H:%M:%S")
            
            await update.effective_message.reply_text(
                f"⏰ Нагадування заплановано на *{formatted_time}* (час сервера). \n"
                f"Ключ: `{full_item_key}`",
                parse_mode=ParseMode.MARKDOWN
            )
        except ValueError:
            await update.effective_message.reply_text("❌ Помилка формату часу.")
        except Exception as e:
            await update.effective_message.reply_text("❌ Помилка при плануванні НАГАДУВАННЯ.")
            print(f"Помилка обробки PUSH: {e}")
    
    # 3. Обробка NOTE (Тільки підтвердження, оскільки зберігання в LocalStorage)
    elif draft_type == 'NOTE':
        await update.effective_message.reply_text(
            f"📝 Замітка (Ключ: `{full_item_key}`) збережена у вашому Local Storage Web App.",
            parse_mode=ParseMode.MARKDOWN
        )

# --- Інші обробники (без змін) ---
async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if not member.is_bot:
            keyboard = [[InlineKeyboardButton("пᴘᴀʙиʌᴀ", callback_data="show_rules")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            welcome_message = (
                f"ᴀйо {member.full_name}! \n"
                f"ᴏзнᴀйᴏᴍᴛᴇᴄя з пᴘᴀʙиʌᴀᴍи."
            )
            
            thread_id = update.message.message_thread_id if update.message.is_topic_message else None

            await update.message.reply_text(
                welcome_message,
                reply_markup=reply_markup,
                message_thread_id=thread_id
            )

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.chat.id
    user_id = update.from_user.id
    user_full_name = update.from_user.full_name
    
    try:
        await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        
        await context.bot.send_message(
            user_id, 
            f"✅ {user_full_name}! запит схвалено"
        )
        
    except Exception as e:
        print(f"Помилка схвалення запиту на приєднання або відправки автосмс: {e}")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 

    if query.data == "show_rules":
        rules_text = ("ᴋᴏᴘиᴄᴛуйᴄя ᴛᴘигᴇᴘᴏᴍ ᴀʌᴏ")
        try:
             await query.edit_message_text(text=rules_text, parse_mode=ParseMode.MARKDOWN)
        except Exception:
             await query.message.reply_text(rules_text, parse_mode=ParseMode.MARKDOWN)

# --- Обробники Діалогу /font (без змін) ---
async def font_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['font_chat_id'] = update.effective_chat.id
    context.user_data['font_command_id'] = update.message.message_id
    
    message = await update.message.reply_text(
        "ᴋᴀᴛᴀй ᴛᴇᴋᴄᴛ. \n\n"
        "/cancel дʌя ᴄᴋᴀᴄуʙᴀння."
    )
    context.user_data['font_bot_request_id'] = message.message_id

    return FONT_TEXT

async def font_get_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text
    chat_id = update.effective_chat.id
    
    if not user_text:
        await update.message.reply_text("Ви нічого не ввели. Будь ласка, введіть текст або /cancel.")
        return FONT_TEXT
    
    converted_text = convert_text_to_font(user_text)
    
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data.get('font_command_id'))
    except Exception: pass
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data.get('font_bot_request_id'))
    except Exception: pass
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
    except Exception: pass
        
    await context.bot.send_message(
        chat_id=chat_id,
        text=converted_text,
        message_thread_id=update.message.message_thread_id
    )
    
    return ConversationHandler.END


async def font_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = context.user_data.get('font_chat_id', update.effective_chat.id)
    
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data.get('font_bot_request_id'))
    except Exception: pass 
        
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data.get('font_command_id'))
    except Exception: pass

    await update.message.reply_text("❌ Діалог скасовано.", message_thread_id=update.message.message_thread_id)
    
    return ConversationHandler.END