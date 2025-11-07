handlers.py
import os
import re
import json
import datetime
import base64
import io
from uuid import uuid4
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
                f"Привіт, {member.full_name}! 👋\\n"
                f"Ласкаво просимо до нашої спільноти. \\n"
                f"Будь ласка, ознайомтеся з правилами."
            )
            
            # Перевіряємо, чи це група з темами (форум)
            thread_id = update.message.message_thread_id if update.message.is_topic_message else None

            await update.message.reply_text(
                welcome_message,
                reply_markup=reply_markup,
                message_thread_id=thread_id
            )

# --- Обробник запиту на вступ ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    chat = update.chat_join_request.chat

    # Автоматично схвалюємо запит
    await update.chat_join_request.approve()
    
    welcome_message = (
        f"Раді бачити тебе, {user.full_name}! ✅\\n"
        f"Запит на вступ до чату **{chat.title}** схвалено автоматично."
    )

    try:
        # Надсилаємо вітальне повідомлення в приватний чат користувачу
        await context.bot.send_message(
            chat_id=user.id,
            text=welcome_message
        )
    except Exception as e:
        print(f"Не вдалося надіслати вітальне повідомлення користувачу {user.id}: {e}")

# --- Обробник Inline-кнопок ---
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_rules":
        rules_text = (
            "**📜 Правила нашої спільноти:**\\n"
            "1. Повага до всіх учасників.\\n"
            "2. Заборона спаму та образ.\\n"
            "3. Тільки конструктивне спілкування.\\n"
        )
        await query.edit_message_text(text=rules_text, parse_mode='Markdown')

# --- Команда для відкриття WebApp ---
async def open_drafts_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not RENDER_EXTERNAL_URL:
        # У цьому випадку RENDER_EXTERNAL_URL, ймовірно, містить URL GitHub Pages
        await update.message.reply_text("Помилка: URL Web App (RENDER_EXTERNAL_URL) не встановлено.")
        return

    # 💡 ВИПРАВЛЕННЯ: Додано розширення .html
    # Припускається, що RENDER_EXTERNAL_URL містить Base URL для GitHub Pages
    webapp_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/drafts.html"

    keyboard = [[InlineKeyboardButton("🎨 Створити Pixel-Art", web_app=WebAppInfo(url=webapp_url))]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Натисніть кнопку, щоб відкрити Web App для створення чернеток:",
        reply_markup=reply_markup,
        message_thread_id=update.message.message_thread_id
    )

# --- Нагадування (Job Queue) ---
async def send_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data.get('chat_id')
    text = context.job.data.get('text')
    
    await context.bot.send_message(
        chat_id=chat_id, 
        text=f"⏰ Нагадування: {text}"
    )

# --- Обробник даних з Web App ---
async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє дані (JSON) надіслані з Telegram Web App.
    Очікує: {"type": "pixel_art", "data": "base64_image_data", "note": "text"}
    """
    
    if not update.message.web_app_data:
        return

    data = update.message.web_app_data.data
    user = update.message.from_user
    chat_id = update.effective_chat.id
    
    # Отримуємо JobQueue з контексту, щоб встановлювати нагадування
    job_queue = context.application.job_queue 

    try:
        payload = json.loads(data)
        
        # Ініціалізація лічильників
        arts_saved = 0
        notes_saved = 0
        reminders_set = 0
        note_text = payload.get('note', '') # Отримуємо нотаток незалежно від типу

        # ------------------------------------------------------------------
        # 🎨 Обробка Pixel Art (data: base64_image_data)
        # ------------------------------------------------------------------
        if payload.get('type') == 'pixel_art':
            base64_data = payload.get('data')
            
            if base64_data and base64_data.startswith('data:image/png;base64,'):
                # 1. Витягуємо чистий Base64 рядок
                img_data_b64 = base64_data.split(';base64,')[1]
                
                # 2. Декодуємо Base64 у байтовий потік
                image_bytes = base64.b64decode(img_data_b64)
                image_stream = io.BytesIO(image_bytes)
                
                # 3. Відправляємо зображення користувачу
                caption = f"🎨 **Pixel Art** від {user.full_name}"
                if note_text:
                    caption += f"\n📝 **Нотаток:** {note_text}"
                
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=image_stream, # Надсилаємо байтовий потік
                    caption=caption,
                    parse_mode='Markdown',
                    message_thread_id=update.message.message_thread_id
                )
                arts_saved += 1
                
        # ------------------------------------------------------------------
        # 📝 Обробка Нотатка (note: text, якщо немає art)
        # ------------------------------------------------------------------
        if note_text and arts_saved == 0:
            # Тут можна додати логіку збереження нотатка (наприклад, у базу даних)
            # Наразі просто відправимо його назад користувачу
            await update.message.reply_text(
                f"📝 **Нотаток збережено:**\\n{note_text}",
                parse_mode='Markdown',
                message_thread_id=update.message.message_thread_id
            )
            notes_saved += 1
            
        # ------------------------------------------------------------------
        # ⏰ Обробка Нагадувань (reminders: [{"time": "...", "text": "..."}])
        # ------------------------------------------------------------------
        reminders = payload.get('reminders', [])
        if reminders:
            for reminder in reminders:
                time_str = reminder.get('time')
                text = reminder.get('text', 'Без назви')
                
                if time_str and job_queue:
                    try:
                        # Парсимо час (очікуємо ISO формат, наприклад, 2025-01-01T10:00:00Z)
                        reminder_time_utc = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        
                        # Перевіряємо, чи час у майбутньому
                        if reminder_time_utc > datetime.datetime.now(datetime.timezone.utc):
                            
                            # Створюємо унікальне ім'я для завдання
                            job_name = f"reminder_user_{user.id}_{uuid4()}"
                            
                            # Плануємо завдання
                            job_queue.run_once(
                                send_reminder_job,
                                reminder_time_utc, # Час у UTC
                                data={'chat_id': chat_id, 'text': text},
                                name=job_name
                            )
                            reminders_set += 1
                        
                    except (ValueError, TypeError) as e:
                        print(f"Помилка парсингу часу нагадування: {e}")

        # Відповідь користувачу про успішне збереження
        await update.message.reply_text(
            f"✅ Дані з Drafts збережено!\\n"
            f"Нотаток: {notes_saved}\\n"
            f"Артів: {arts_saved}\\n"
            f"Нагадувань встановлено: {reminders_set}",
            message_thread_id=update.message.message_thread_id
        )

    except json.JSONDecodeError:
        await update.message.reply_text("Помилка обробки даних з Web App.")
    except Exception as e:
        print(f"Помилка в handle_webapp_data: {e}")
        await update.message.reply_text(f"Сталася помилка: {e}")