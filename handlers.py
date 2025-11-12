# handlers.py

import os
import re
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from dotenv import load_dotenv

from font_utils import convert_text_to_font

# Стан для /font
FONT_TEXT = 0

if os.getenv("RENDER") != "true":
    load_dotenv()


# === 1. Web App: тільки ART (рисовалка) ===
async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляє дані з DRAFTZ — тільки піксельний арт."""
    
    web_app_data = update.effective_message.web_app_data
    if not web_app_data:
        return

    data_string = web_app_data.data
    parts = data_string.split('|', 2)
    
    if len(parts) < 3:
        await update.effective_message.reply_text("Помилка: Невірний формат даних.")
        return

    draft_type, full_item_key, json_payload = parts

    if draft_type == 'ART':
        try:
            json.loads(json_payload)  # Просто перевіряємо валідність
            await update.effective_message.reply_text(
                f"Ваш арт (Ключ: `{full_item_key}`) прийнято!\n"
                f"*Надіслано для конвертації в зображення.*",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await update.effective_message.reply_text("Помилка при обробці арту.")
            print(f"ART error: {e}")


# === 2. Автопривітання при вступі (NEW_CHAT_MEMBERS) ===
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


# === 3. Автосхвалення заявки + ЛС + привітання в групі ===
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.chat.id
    user_id = update.from_user.id
    user_full_name = update.from_user.full_name
    chat_title = update.chat.title

    try:
        # Схвалюємо
        await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)

        # ЛС користувачу
        await context.bot.send_message(
            user_id,
            f"{user_full_name}! Ваш запит до *{chat_title}* схвалено.\n"
            f"Ласкаво просимо до ☇ ꜰ ☻‌ ʀ ᴜ ʍ❓",
            parse_mode=ParseMode.MARKDOWN
        )

        # Привітання в групі
        keyboard = [[InlineKeyboardButton("пᴘᴀʙиʌᴀ", callback_data="show_rules")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"ᴀйо {user_full_name}!\nᴏзнᴀйᴏᴍᴛᴇᴄя з пᴘᴀʙиʌᴀᴍи.",
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"Помилка автоприйому: {e}")


# === 4. Кнопка "ПРАВИЛА" ===
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_rules":
        rules = "ᴋᴏᴘиᴄᴛуйᴄя ᴛᴘигᴇᴘᴏᴍ ᴀʌᴏ"
        try:
            await query.edit_message_text(rules, parse_mode=ParseMode.MARKDOWN)
        except:
            await query.message.reply_text(rules, parse_mode=ParseMode.MARKDOWN)


# === 5. /font — стилізатор тексту ===
async def font_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['font_chat_id'] = update.effective_chat.id
    context.user_data['font_command_id'] = update.message.message_id

    msg = await update.message.reply_text(
        "ᴋᴀᴛᴀй ᴛᴇᴋᴄᴛ.\n\n/cancel — скасувати."
    )
    context.user_data['font_bot_request_id'] = msg.message_id
    return FONT_TEXT


async def font_get_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text
    chat_id = update.effective_chat.id

    if not user_text:
        await update.message.reply_text("Порожньо. Введіть текст або /cancel.")
        return FONT_TEXT

    converted = convert_text_to_font(user_text)

    # Видаляємо старі повідомлення
    for msg_id in ['font_command_id', 'font_bot_request_id']:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data.get(msg_id))
        except: pass
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
    except: pass

    await context.bot.send_message(
        chat_id=chat_id,
        text=converted,
        message_thread_id=update.message.message_thread_id
    )
    return ConversationHandler.END


async def font_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = context.user_data.get('font_chat_id', update.effective_chat.id)

    for msg_id in ['font_bot_request_id', 'font_command_id']:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data.get(msg_id))
        except: pass

    await update.message.reply_text("Скасовано.", message_thread_id=update.message.message_thread_id)
    return ConversationHandler.END