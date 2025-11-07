import os
import re
import json
import datetime
from uuid import uuid4 # Потрібно для унікальних імен завдань
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from telegram.constants import ChatType
from dotenv import load_dotenv

# Завантажуємо змінні оточення для використання в хендлерах, якщо потрібно
if os.getenv("RENDER") != "true":
    load_dotenv()

RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# --- Обробник нових учасників ---
# (ОСЬ ФУНКЦІЯ, ЯКОЇ НЕ ВИСТАЧАЛО)
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
    if update.chat_join_request: # Додана перевірка
        user_name = update.chat_join_request.from_user.full_name
        chat_title = update.chat_join_request.chat.title if update.chat_join_request.chat else "чат"

        print(f"Отримано запит на приєднання від {user_name} до {chat_title}")
        
        try:
            # Автоматичне схвалення
            await update.chat_join_request.approve()
            print(f"Користувач {user_name} схвалено.")
        except Exception as e:
            print(f"Помилка схвалення {user_name}: {e}")
    else:
        print("Отримано оновлення 'handle_join_request' без об'єкта chat_join_request")


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

# --- Обробник WebApp (Відкриття) ---
async def open_drafts_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.type != ChatType.PRIVATE:
        await update.message.reply_text("Ця команда працює лише в особистих повідомленнях.")
        return

    # WebApp URL: https://morstrixbot-afjc.onrender.com/drafts
    
    web_app_url = f"{RENDER_EXTERNAL_URL.rstrip('/')}/drafts" if RENDER_EXTERNAL_URL else "https://example.com/drafts"
    
    keyboard = [
        [InlineKeyboardButton(
            "terminal: Відкрити Grid ✍️", # Оновлений текст кнопки
            web_app=WebAppInfo(url=web_app_url)
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Натисніть кнопку, щоб відкрити Web App (Pixel Grid):",
        reply_markup=reply_markup
    )

# -----------------------------------------------------------------
# --- НОВІ ФУНКЦІЇ ДЛЯ ОБРОБКИ ДАНИХ З НОВОЇ WEB APP ---
# -----------------------------------------------------------------

async def send_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Завдання, яке виконується JobQueue для надсилання нагадування.
    """
    job_data = context.job.data
    chat_id = job_data.get('chat_id')
    text = job_data.get('text')
    
    if chat_id and text:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏰ **НАГАДУВАННЯ** ⏰\n\n{text}",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Помилка надсилання нагадування {chat_id}: {e}")

async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє дані, отримані від Web App (Pixel Grid).
    """
    user = update.effective_user
    chat_id = user.id # Надсилаємо нагадування в особисті повідомлення
    
    if not update.message or not update.message.web_app_data:
        print("Помилка: оновлення WebApp не містить даних.")
        return

    try:
        data = json.loads(update.message.web_app_data.data)
        grid_state = data.get('grid', [])
        
        # Використовуємо JobQueue, який був переданий в Application
        job_queue = context.application.job_queue

        reminders_set = 0
        notes_saved = 0
        arts_saved = 0

        # Видаляємо всі попередні нагадування цього користувача, щоб уникнути дублів
        # (Простий спосіб, краще - керувати за ID)
        active_jobs = job_queue.get_jobs_by_name(f"reminder_user_{user.id}")
        for job in active_jobs:
            job.schedule_removal()

        for cell in grid_state:
            cell_type = cell.get('type')
            
            if cell_type == 'note':
                notes_saved += 1
                # (Тут можна додати логіку збереження нотатки в базу даних)
            
            elif cell_type == 'art':
                arts_saved += 1
                # (Тут можна додати логіку збереження base64 арту)
                # print(f"Art data (base64): {cell.get('data')[:50]}...")
            
            elif cell_type == 'reminder':
                text = cell.get('text')
                time_str = cell.get('time') # '2025-11-07T10:30:00.000Z'
                
                if text and time_str:
                    try:
                        # Конвертуємо час UTC з ISO формату
                        reminder_time_utc = datetime.datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        
                        # Перевіряємо, чи час у майбутньому
                        if reminder_time_utc > datetime.datetime.now(datetime.timezone.utc):
                            
                            # Створюємо унікальне ім'я для завдання
                            job_name = f"reminder_user_{user.id}"
                            
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
            f"✅ Дані з Grid збережено!\n"
            f"Нотаток: {notes_saved}\n"
            f"Артів: {arts_saved}\n"
            f"Нагадувань встановлено: {reminders_set}"
        )

    except json.JSONDecodeError:
        await update.message.reply_text("Помилка обробки даних з Web App.")
    except Exception as e:
        print(f"Помилка в handle_webapp_data: {e}")
        await update.message.reply_text(f"Сталася помилка: {e}")