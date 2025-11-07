import os
import re
import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from telegram.constants import ChatType
from dotenv import load_dotenv

# Завантажуємо змінні оточення для використання в хендлерах, якщо потрібно
if os.getenv("RENDER") != "true":
    load_dotenv()

RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# --- Обробник нових учасників ---
async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if not member.is_bot:
            
            # Кнопка для правил
            keyboard = [[InlineKeyboardButton("Показати Правила", callback_data="show_rules")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            welcome_message = (
                f"Привіт, {member.full_name}! 👋\n"
                f"Ласкаво просимо до нашої спільноти. \n"
                f"Будь ласка, ознайомтеся з правилами."
            )
            
            # Перевіряємо, чи це група з темами (форум)
            thread_id = update.message.message_thread_id if update.message.is_topic_message else None

            await update.message.reply_text(
                welcome_message,
                reply_markup=reply_markup,
                message_thread_id=thread_id # Важливо для груп-форумів
            )

# --- Обробник запитів на приєднання ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.chat.id,
        text=f"Користувач {update.from_user.full_name} надіслав запит на приєднання."
    )
    # Автоматичне схвалення
    await update.chat_join_request.approve()
    await context.bot.send_message(
        chat_id=update.chat.id,
        text=f"Користувач {update.from_user.full_name} схвалено."
    )

# --- Обробник Callback-запитів (КНОПКИ) ---
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_rules":
        
        # ВИПРАВЛЕННЯ ДЛЯ 'Message thread not found': 
        # Визначаємо ID теми, якщо це група-форум, інакше None
        thread_id = query.message.message_thread_id if query.message.is_topic_message else None

        rules_text = (
            "📌 **ПРАВИЛА СПІЛЬНОТИ** 📌\n\n"
            "1. Поважайте інших учасників.\n"
            "2. Заборонено спам та нецензурна лексика.\n"
            "3. ... (Ваші інші правила тут)\n"
        )
        
        await query.message.reply_text(
            rules_text,
            parse_mode='Markdown',
            message_thread_id=thread_id # Передаємо thread_id
        )

# --- Обробник WebApp (Чернетки/Арти) ---
async def open_drafts_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != ChatType.PRIVATE:
        await update.message.reply_text("Ця команда працює лише в особистих повідомленнях.")
        return

    # WebApp URL: https://morstrixbot-afjc.onrender.com/drafts
    # (Переконайтеся, що шлях /drafts існує на Render)
    
    web_app_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/drafts" if RENDER_EXTERNAL_URL else "https://example.com/drafts"
    
    keyboard = [
        [InlineKeyboardButton(
            "🎨 Відкрити Чернетки/Арти ✍️", 
            web_app=WebAppInfo(url=web_app_url)
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Натисніть кнопку, щоб відкрити Web App для створення нотаток та арту:",
        reply_markup=reply_markup
    )