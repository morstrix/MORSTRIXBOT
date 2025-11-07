import os
import re
import json
import datetime
import base64
import io
from uuid import uuid4
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, InputFile, PhotoSize
from telegram.ext import ContextTypes
from telegram.constants import ChatType
from dotenv import load_dotenv

# Для роботи з зображеннями (збереження та надсилання)
from PIL import Image

# Завантажуємо змінні оточення для використання в хендлерах, якщо потрібно
if os.getenv("RENDER") != "true":
    load_dotenv()

RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

# --- Допоміжні функції для роботи з даними ---

# Спрощене "сховище" для нотаток та артів.
# У реальному проекті варто використовувати базу даних (SQLite, PostgreSQL тощо).
# Зберігаємо дані в пам'яті (небезпечно при перезапуску, але просто для прикладу)
user_data_storage = {} # {'user_id': {'notes': [{'id': str, 'text': str, 'timestamp': datetime}], 'arts': [{'id': str, 'image_data': str, 'timestamp': datetime}]}}

def _save_note(user_id, text):
    """Зберігає нотатку для користувача."""
    if user_id not in user_data_storage:
        user_data_storage[user_id] = {'notes': [], 'arts': []}
    
    note_id = str(uuid4())
    user_data_storage[user_id]['notes'].append({
        'id': note_id, 
        'text': text, 
        'timestamp': datetime.datetime.now(datetime.timezone.utc)
    })
    return note_id

def _save_art(user_id, image_base64):
    """Зберігає арт (зображення base64) для користувача."""
    if user_id not in user_data_storage:
        user_data_storage[user_id] = {'notes': [], 'arts': []}
        
    art_id = str(uuid4())
    user_data_storage[user_id]['arts'].append({
        'id': art_id, 
        'image_data': image_base64, 
        'timestamp': datetime.datetime.now(datetime.timezone.utc)
    })
    return art_id

def _get_user_notes(user_id):
    """Повертає список нотаток користувача."""
    return user_data_storage.get(user_id, {}).get('notes', [])

def _get_user_arts(user_id):
    """Повертає список артів користувача."""
    return user_data_storage.get(user_id, {}).get('arts', [])

def _get_note_by_id(user_id, note_id):
    """Знаходить нотатку за ID."""
    for note in _get_user_notes(user_id):
        if note['id'] == note_id:
            return note
    return None

def _get_art_by_id(user_id, art_id):
    """Знаходить арт за ID."""
    for art in _get_user_arts(user_id):
        if art['id'] == art_id:
            return art
    return None

def _delete_note(user_id, note_id):
    """Видаляє нотатку за ID."""
    if user_id in user_data_storage and 'notes' in user_data_storage[user_id]:
        initial_len = len(user_data_storage[user_id]['notes'])
        user_data_storage[user_id]['notes'] = [n for n in user_data_storage[user_id]['notes'] if n['id'] != note_id]
        return len(user_data_storage[user_id]['notes']) < initial_len
    return False

def _delete_art(user_id, art_id):
    """Видаляє арт за ID."""
    if user_id in user_data_storage and 'arts' in user_data_storage[user_id]:
        initial_len = len(user_data_storage[user_id]['arts'])
        user_data_storage[user_id]['arts'] = [a for a in user_data_storage[user_id]['arts'] if a['id'] != art_id]
        return len(user_data_storage[user_id]['arts']) < initial_len
    return False

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
                message_thread_id=thread_id
            )

# --- Обробник запитів на приєднання ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Логіка обробки запитів на приєднання (не змінювалась)
    pass

# --- Обробник натискань кнопок (callback) ---
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Регулярний вираз для парсингу команд: view_note:<id> або delete_note:<id>
    note_match = re.match(r'(view|delete)_note:([a-f0-9-]+)', data)
    art_match = re.match(r'(view|delete)_art:([a-f0-9-]+)', data)

    if data == "show_rules":
        rules_text = (
            "📜 **Правила Спільноти** 📜\n\n"
            "1. Будьте ввічливими та поважайте інших.\n"
            "2. Заборонено спам та реклама.\n"
            "3. Використовуйте українську мову.\n"
            "4. Заборонені образи та розпалювання ворожнечі."
        )
        # Надсилаємо правила, а не редагуємо привітальне повідомлення
        await query.message.reply_text(rules_text, reply_to_message_id=query.message.message_id)
        
    elif data == "show_drafts":
        # Створюємо меню для перегляду нотаток та артів
        notes = _get_user_notes(user_id)
        arts = _get_user_arts(user_id)
        
        keyboard = []
        
        if notes:
            keyboard.append([InlineKeyboardButton(f"📝 Нотатки ({len(notes)})", callback_data="list_notes")])
        if arts:
            keyboard.append([InlineKeyboardButton(f"🎨 Арти ({len(arts)})", callback_data="list_arts")])
            
        if not keyboard:
            await query.edit_message_text("У вас немає збережених чернеток.")
            return

        keyboard.append([InlineKeyboardButton("🔙 Назад до меню", callback_data="close_draft_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Оберіть, що хочете переглянути:", reply_markup=reply_markup)
        
    elif data == "list_notes":
        notes = _get_user_notes(user_id)
        keyboard = []
        for i, note in enumerate(notes[:10]): # Показуємо перші 10
            keyboard.append([InlineKeyboardButton(f"{i+1}. {note['text'][:20]}...", callback_data=f"view_note:{note['id']}")])
            
        if notes:
            keyboard.append([InlineKeyboardButton("❌ Видалити все", callback_data="confirm_delete_all_notes")])
            
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="show_drafts")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = "📝 **Ваші Нотатки:**\n\n"
        if not notes:
            message_text += "Нотаток немає."
            
        await query.edit_message_text(message_text, reply_markup=reply_markup)
        
    elif data == "list_arts":
        arts = _get_user_arts(user_id)
        keyboard = []
        for i, art in enumerate(arts[:10]): # Показуємо перші 10
            keyboard.append([InlineKeyboardButton(f"🎨 Арт #{i+1} ({art['timestamp'].strftime('%d.%m %H:%M')})", callback_data=f"view_art:{art['id']}")])
            
        if arts:
            keyboard.append([InlineKeyboardButton("❌ Видалити все", callback_data="confirm_delete_all_arts")])
            
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="show_drafts")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = "🎨 **Ваші Арти:**\n\n"
        if not arts:
            message_text += "Артів немає."
            
        await query.edit_message_text(message_text, reply_markup=reply_markup)

    elif note_match:
        action, note_id = note_match.groups()
        
        if action == 'view':
            note = _get_note_by_id(user_id, note_id)
            if note:
                message_text = (
                    f"📝 **Нотатка (ID: {note_id[:8]})**\n"
                    f"**Створено:** {note['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                    f"```\n{note['text']}\n```"
                )
                keyboard = [
                    [InlineKeyboardButton("🗑️ Видалити", callback_data=f"delete_note:{note_id}")],
                    [InlineKeyboardButton("🔙 До списку нотаток", callback_data="list_notes")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Відправляємо нове повідомлення (бо ліміт на редагування занадто великого тексту)
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=message_text,
                    reply_markup=reply_markup
                )
                await query.delete_message() # Видаляємо старе повідомлення зі списком
            else:
                await query.edit_message_text("Нотатку не знайдено.")
        
        elif action == 'delete':
            if _delete_note(user_id, note_id):
                await query.edit_message_text("✅ Нотатку видалено.")
                # Повертаємо до списку нотаток
                await context.application.create_task(handle_callback_query(update, context))
            else:
                await query.edit_message_text("Помилка видалення нотатки.")

    elif art_match:
        action, art_id = art_match.groups()
        
        if action == 'view':
            art = _get_art_by_id(user_id, art_id)
            if art:
                # 1. Декодуємо base64 в байти
                image_bytes = base64.b64decode(art['image_data'])
                # 2. Створюємо файловий об'єкт у пам'яті
                image_file = io.BytesIO(image_bytes)
                image_file.name = f"art_{art_id[:8]}.png"

                # 3. Надсилаємо фото
                caption = (
                    f"🎨 **Арт (ID: {art_id[:8]})**\n"
                    f"**Створено:** {art['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}"
                )
                keyboard = [
                    [InlineKeyboardButton("🗑️ Видалити", callback_data=f"delete_art:{art_id}")],
                    [InlineKeyboardButton("🔙 До списку артів", callback_data="list_arts")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Надсилаємо як фото, а не редагуємо повідомлення
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=image_file,
                    caption=caption,
                    reply_markup=reply_markup
                )
                await query.delete_message() # Видаляємо старе повідомлення зі списком
            else:
                await query.edit_message_text("Арт не знайдено.")
                
        elif action == 'delete':
            if _delete_art(user_id, art_id):
                await query.edit_message_text("✅ Арт видалено.")
                # Повертаємо до списку артів
                await context.application.create_task(handle_callback_query(update, context))
            else:
                await query.edit_message_text("Помилка видалення арту.")
    
    elif data == "confirm_delete_all_notes":
        keyboard = [
            [InlineKeyboardButton("✅ ТАК, видалити всі нотатки", callback_data="delete_all_notes")],
            [InlineKeyboardButton("❌ Ні, повернутися", callback_data="list_notes")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("⚠️ **Ви впевнені, що хочете видалити ВСІ нотатки?**", reply_markup=reply_markup)

    elif data == "delete_all_notes":
        if user_id in user_data_storage:
            notes_count = len(user_data_storage[user_id].get('notes', []))
            user_data_storage[user_id]['notes'] = []
            await query.edit_message_text(f"✅ Всі {notes_count} нотаток видалено.")
            await context.application.create_task(handle_callback_query(update, context)) # Повертаємо до меню
        else:
            await query.edit_message_text("Нотатки не знайдено.")
            
    elif data == "confirm_delete_all_arts":
        keyboard = [
            [InlineKeyboardButton("✅ ТАК, видалити всі арти", callback_data="delete_all_arts")],
            [InlineKeyboardButton("❌ Ні, повернутися", callback_data="list_arts")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("⚠️ **Ви впевнені, що хочете видалити ВСІ арти?**", reply_markup=reply_markup)
        
    elif data == "delete_all_arts":
        if user_id in user_data_storage:
            arts_count = len(user_data_storage[user_id].get('arts', []))
            user_data_storage[user_id]['arts'] = []
            await query.edit_message_text(f"✅ Всі {arts_count} арти видалено.")
            await context.application.create_task(handle_callback_query(update, context)) # Повертаємо до меню
        else:
            await query.edit_message_text("Арти не знайдено.")

    elif data == "close_draft_menu":
        await query.delete_message()


# --- Обробник команди /drafts ---
async def open_drafts_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not RENDER_EXTERNAL_URL:
        await update.message.reply_text("Помилка: RENDER_EXTERNAL_URL не налаштовано.")
        return

    # Змінюємо кнопку: відкрити WebApp або показати збережені чернетки
    keyboard = [
        [InlineKeyboardButton("✏️ Створити нову чернетку", web_app=WebAppInfo(url=f"{RENDER_EXTERNAL_URL.rstrip('/')}/drafts"))],
        [InlineKeyboardButton("📚 Переглянути збережені", callback_data="show_drafts")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Оберіть дію з чернетками:",
        reply_markup=reply_markup,
        message_thread_id=update.message.message_thread_id
    )

# --- Обробник даних з WebApp ---
# Додаємо send_reminder_job
async def send_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """Надсилає нагадування користувачеві."""
    chat_id = context.job.data.get('chat_id')
    text = context.job.data.get('text')
    
    if chat_id and text:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔔 **НАГАДУВАННЯ:**\n\n_{text}_"
            )
        except Exception as e:
            print(f"Помилка відправки нагадування в чат {chat_id}: {e}")

# Оновлений handle_webapp_data
async def handle_webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє дані, надіслані з Telegram Web App (drafts.html).
    Зберігає нотатки, арти та встановлює нагадування.
    """
    if not update.message.web_app_data:
        return

    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Отримуємо JobQueue
    job_queue = context.application.job_queue
    
    try:
        # Парсимо JSON дані
        data = json.loads(update.message.web_app_data.data)
        
        notes_saved = 0
        arts_saved = 0
        reminders_set = 0
        
        # 1. Зберігання нотаток та нагадувань
        notes = data.get('notes', [])
        for note_data in notes:
            text = note_data.get('text')
            reminder_iso = note_data.get('reminder')
            
            if text:
                # Зберігаємо як нотатку
                _save_note(user.id, text)
                notes_saved += 1
                
                # Обробка нагадувань
                if reminder_iso:
                    try:
                        # Парсимо час у UTC
                        reminder_time_utc = datetime.datetime.fromisoformat(reminder_iso.replace('Z', '+00:00'))
                        
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

        # 2. Зберігання артів
        arts = data.get('arts', [])
        for art_data in arts:
            image_base64 = art_data.get('image')
            if image_base64:
                # Зберігаємо арт
                _save_art(user.id, image_base64)
                arts_saved += 1

        # Відповідь користувачу про успішне збереження
        await update.message.reply_text(
            f"✅ Дані з Drafts збережено!\n"
            f"Нотаток: {notes_saved}\n"
            f"Артів: {arts_saved}\n"
            f"Нагадувань встановлено: {reminders_set}",
            message_thread_id=update.message.message_thread_id
        )

    except json.JSONDecodeError:
        await update.message.reply_text("Помилка обробки даних з Web App.")
    except Exception as e:
        print(f"Помилка в handle_webapp_data: {e}")
        await update.message.reply_text(f"Сталася помилка: {e}")