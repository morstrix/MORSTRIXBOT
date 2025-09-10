import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from dotenv import load_dotenv

load_dotenv()
ADMIN_ID = os.getenv('ADMIN_ID')
if not ADMIN_ID:
    print("Ошибка: ADMIN_ID не найден в .env файле. Функция поддержки будет недоступна.")

# Імпортуємо функцію з ai.py
from ai import handle_gemini_message_private


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает команду /support и отправляет пользователю кнопку для связи в личном чате.
    """
    keyboard = [[InlineKeyboardButton("❓ꜱᴜᴘᴘᴏʀᴛ", url=f"https://t.me/morstrixbot?start=support")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("зᴀxᴏдь", reply_markup=reply_markup)


async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Единая точка входа для всех личных сообщений.
    Перенаправляет сообщения либо в поддержку, либо в AI.
    """
    user_id = str(update.effective_user.id)

    # Если сообщение от администратора, это ответ на тикет
    if user_id == ADMIN_ID and context.user_data.get('state') == 'support':
        await reply_to_user(update, context)
        return
    
    # Если пользователь находится в состоянии поддержки, пересылаем сообщение админу
    if context.user_data.get('state') == 'support':
        await forward_to_admin(update, context)
        context.user_data['state'] = 'ai'
        
    # Иначе, это запрос к AI
    else:
        await handle_gemini_message_private(update, context)


async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Пересылает сообщение от пользователя в личный чат администратора.
    Добавляет к сообщению ID пользователя и возможность ответить ему.
    """
    if not ADMIN_ID:
        return

    user = update.effective_user
    message = update.message
    
    keyboard = [[InlineKeyboardButton("⚠️", callback_data=f"reply_to_{user.id}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    caption = f"🫥❓ @{user.username} ({user.full_name}):"
    
    try:
        if message.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=message.photo[-1].file_id,
                caption=caption,
                reply_markup=reply_markup
            )
        elif message.document:
            await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=message.document.file_id,
                caption=caption,
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"{caption}\n\n{message.text}",
                reply_markup=reply_markup
            )
        await update.message.reply_text("✅ вiдпᴘᴀвᴧᴇнᴏ!")

    except Exception as e:
        print(f"Помилка пересилання повідомлення до адміністратора: {e}")
        await update.message.reply_text("на жаль, не вдалося відправити ваше повідомлення. Спробуйте пізніше.")


async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает ответы администратора и пересылает их пользователю.
    """
    if not ADMIN_ID:
        return
        
    admin_id = int(ADMIN_ID)
    if update.effective_user.id != admin_id:
        return

    user_to_reply_id = context.user_data.get('reply_user_id')
    if not user_to_reply_id:
        await update.message.reply_text("Помилка: не вдалося знайти ідентифікатор користувача. Будь ласка, натисніть кнопку 'Відповісти' ще раз.")
        return
    
    reply_text = f"ʍɵ‌ʀᔕᴛʀɪ𒉽: {update.message.text}"
    
    try:
        keyboard = [[InlineKeyboardButton("⚠️", callback_data=f"reply_to_{user_to_reply_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(chat_id=user_to_reply_id, text=reply_text, reply_markup=reply_markup)
        await update.message.reply_text("✅ вiдпᴘᴀвᴧᴇнᴏ!")
    except Exception as e:
        print(f"Помилка пересилання відповіді до користувача: {e}")
        await update.message.reply_text(f"Помилка: не вдалося надіслати відповідь. {e}")

    context.user_data.pop('reply_user_id', None)
    context.user_data['state'] = 'ai'


async def handle_reply_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє натискання кнопки "Відповісти" як для адміністратора, так і для користувача.
    """
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    callback_data = query.data.split('_')
    
    user_to_reply_id = callback_data[-1]

    # Якщо натиснув адміністратор
    if user_id == ADMIN_ID:
        context.user_data['reply_user_id'] = user_to_reply_id
        context.user_data['state'] = 'support'
        await context.bot.send_message(
            chat_id=ADMIN_ID, 
            text="ᴋᴀтᴀй ᴏдним ᴄᴧᴏвᴏᴍ",
        )
    # Якщо натиснув користувач
    else:
        context.user_data['state'] = 'support'
        await context.bot.send_message(
            chat_id=user_id, 
            text="ᴋᴀтᴀй ᴏдним ᴄᴧᴏвᴏᴍ",
        )