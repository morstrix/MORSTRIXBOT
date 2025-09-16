from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest
from telegram.ext import ContextTypes, ConversationHandler
import asyncio

RULES_MESSAGE = "для зʙ'язᴋу з ʜᴇйᴘoxᴇʌпᴇᴘoᴍ - зʜɪᴍᴀй ᴋᴀᴄᴛᴘюʌю i ᴋᴏᴘиᴄᴛуйся ᴛᴘигᴇᴘом: ᴀʌо"

# Стани для розмови про скаргу
AWAITING_LINK = 1

async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        keyboard = [[InlineKeyboardButton("правила", callback_data="show_rules")]]
        await update.message.reply_html(
            f"{member.mention_html()}, вᴇʌᴋᴀᴍ дᴏ пᴘиʙᴀᴛʜoгᴏ ᴋʌубу", 
            reply_markup=InlineKeyboardMarkup(keyboard),
            message_thread_id=update.message.message_thread_id
        )

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_request: ChatJoinRequest = update.chat_join_request
    try:
        await chat_request.approve()
        await context.bot.send_message(chat_id=chat_request.from_user.id, text=f"✅ ᴛʙᴏя зᴀяʙᴋᴀ схʙᴀʌᴇʜᴀ. \nᴋидᴀй будь-яᴋi пиᴛᴀʜʜя.")
        print(f"Заявку від {chat_request.from_user.username or chat_request.from_user.id} схвалено.")
    except Exception as e:
        print(f"Не вдалося обробити заявку або надіслати повідомлення користувачу {chat_request.from_user.id}: {e}")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "show_rules":
        await query.answer(text=RULES_MESSAGE, show_alert=True)


# --- Нова логіка для обробки скарг на YouTube Music ---

async def start_complaint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Починає процес скарги на посилання YouTube Music."""
    query = update.callback_query
    await query.answer()
    
    try:
        await query.message.delete()
    except Exception as e:
        print(f"Не вдалося видалити кнопку скарги: {e}")
    
    sent_message = await query.message.reply_text(
        "кидай лiнка на виніс:",
        message_thread_id=query.message.message_thread_id
    )
    
    context.user_data['complaint_messages_to_delete'] = [sent_message.message_id]
    
    return AWAITING_LINK

async def receive_replacement_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отримує нове посилання, відправляє підтвердження та запускає автоочищення."""
    user_message_id = update.message.message_id
    message_thread_id = update.message.message_thread_id
    context.user_data.get('complaint_messages_to_delete', []).append(user_message_id)

    sent_msg_1 = await update.message.reply_text("отправлено ✅", message_thread_id=message_thread_id)
    context.user_data['complaint_messages_to_delete'].append(sent_msg_1.message_id)
    
    await asyncio.sleep(1)

    sent_msg_2 = await update.message.reply_text("4", message_thread_id=message_thread_id)
    context.user_data['complaint_messages_to_delete'].append(sent_msg_2.message_id)

    await asyncio.sleep(1)

    sent_msg_3 = await update.message.reply_text("3", message_thread_id=message_thread_id)
    context.user_data['complaint_messages_to_delete'].append(sent_msg_3.message_id)
    
    await asyncio.sleep(2)

    for message_id in context.user_data.get('complaint_messages_to_delete', []):
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
        except Exception as e:
            print(f"Не вдалося видалити повідомлення {message_id}: {e}")
            
    context.user_data.pop('complaint_messages_to_delete', None)
    
    return ConversationHandler.END

async def cancel_complaint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Скасовує процес скарги та видаляє повідомлення."""
    if 'complaint_messages_to_delete' in context.user_data:
        for message_id in context.user_data['complaint_messages_to_delete']:
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message_id)
            except Exception:
                pass 
        context.user_data.pop('complaint_messages_to_delete', None)

    await update.message.reply_text(
        "скасовано.",
        message_thread_id=update.message.message_thread_id
    )
    return ConversationHandler.END