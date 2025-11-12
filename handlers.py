# handlers.py

import os
import json
import base64
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from dotenv import load_dotenv

from font_utils import convert_text_to_font

# Стан для /font
FONT_TEXT = 0

if os.getenv("RENDER") != "true":
    load_dotenv()

logger = logging.getLogger(__name__)


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

    draft_type, full_item_key, base64_payload = parts

    if draft_type == 'ART':
        try:
            # Валідація base64
            base64.b64decode(base64_payload, validate=True)
            await update.effective_message.reply_text(
                f"Арт (Ключ: `{full_item_key}`) прийнято!\n"
                f"*Надіслано для обробки.*",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            await update.effective_message.reply_text("Помилка при обробці арту.")
            logger.error(f"ART error: {e}")


# === 2. Автосхвалення заявки + ЛС (розбито на 3 повідомлення) + привітання в групі ===
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.chat.id
    user_id = update.from_user.id
    user_full_name = update.from_user.full_name
    chat_title = update.chat.title or "групи"

    try:
        # 1. Схвалюємо заявку
        await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
        logger.info(f"Заявка {user_id} схвалена в {chat_id}")

        # 2. ЛС користувачу — 3 окремі повідомлення
        # Повідомлення 1
        await context.bot.send_message(
            user_id,
            f"{user_full_name}! зᴀпит схвᴀʌᴇно.",
            parse_mode=ParseMode.MARKDOWN
        )

        # Повідомлення 2
        await context.bot.send_message(
            user_id,
            "шᴏ я ᴍᴏжу?\n\n"
            "➞ ᴀʙᴛᴏпᴘийᴏᴍ зᴀяʙᴏᴋ\n"
            "➞ ʙᴇʌᴋᴀᴍ з пᴘᴀʙиʌᴀᴍи\n"
            "➞ пᴇᴘᴇʙіᴘᴋᴀ пᴏᴄиʌᴀнь\n"
            "➞ /font - ᴛᴇᴋᴄᴛ ᴄᴛᴀйʌᴇᴘ\n"
            "➞ ШІ — дʌя чʌᴇніʙ ᴋʌубу\n"
            "(ʙ чᴀᴛᴀх: ᴛᴘигᴇᴘ ᴀʌᴏ)",
            parse_mode=ParseMode.MARKDOWN
        )

        # Повідомлення 3
        await context.bot.send_message(
            user_id,
            "➞ ᴘᴀɪɴᴛ ᴀᴘᴘ (ᴘʀᴏᴛᴏᴛʏᴘᴇ)\n"
            "t.me/MORSTRIXBOT/paint",
            parse_mode=ParseMode.MARKDOWN
        )

        # 3. Привітання в групі
        keyboard = [[InlineKeyboardButton("пᴘᴀʙиʌᴀ", callback_data="show_rules")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"ᴀйо {user_full_name}!\nᴏзнᴀйᴏᴍᴛᴇᴄя з пᴘᴀʙиʌᴀᴍи.",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Помилка автоприйому: {e}")


# === 3. Привітання при вступі (резерв, якщо без заявки) ===
async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if not member.is_bot:
            keyboard = [[InlineKeyboardButton("пᴘᴀʙиʌᴀ", callback_data="show_rules")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            welcome = f"ᴀйо {member.full_name}!\nᴏзнᴀйᴏᴍᴛᴇᴄя з пᴘᴀʙиʌᴀᴍи."

            thread_id = update.message.message_thread_id if update.message.is_topic_message else None
            await update.message.reply_text(welcome, reply_markup=reply_markup, message_thread_id=thread_id)


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

    msg = await update.message.reply_text("ᴋᴀᴛᴀй ᴛᴇᴋᴄᴛ.\n\n/cancel — скасувати.")
    context.user_data['font_bot_request_id'] = msg.message_id
    return FONT_TEXT


async def font_get_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_text = update.message.text
    chat_id = update.effective_chat.id

    if not user_text:
        await update.message.reply_text("Порожньо. Введіть текст або /cancel.")
        return FONT_TEXT

    # Тепер convert_text_to_font повертає готовий блок \`\`\`текст\`\`\`
    converted_block = convert_text_to_font(user_text)

    # Видаляємо старі повідомлення
    for key in ['font_command_id', 'font_bot_request_id']:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data.get(key))
        except: pass
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
    except: pass

    # Надсилаємо блок коду — з’явиться кнопка «Копіювати»
    await context.bot.send_message(
        chat_id=chat_id,
        text=converted_block,
        parse_mode=ParseMode.MARKDOWN_V2,   # ← обов’язково V2
        message_thread_id=update.message.message_thread_id
    )
    return ConversationHandler.END


async def font_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = context.user_data.get('font_chat_id', update.effective_chat.id)

    for key in ['font_bot_request_id', 'font_command_id']:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=context.user_data.get(key))
        except: pass

    await update.message.reply_text("Скасовано.", message_thread_id=update.message.message_thread_id)
    return ConversationHandler.END