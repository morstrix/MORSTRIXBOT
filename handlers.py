from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest
from telegram.ext import ContextTypes, ConversationHandler
import asyncio

RULES_MESSAGE = "для зʙ'язᴋу з ʜᴇйᴘoxᴇʌпᴇᴘoᴍ - зʜɪᴍᴀй ᴋᴀᴄᴛᴘюʌю i ᴋᴏᴘиᴄᴛуйся ᴛᴘигᴇᴘом: ᴀʌо"

async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        keyboard = [[InlineKeyboardButton("правила", callback_data="show_rules")]]
        await update.message.reply_html(
            f"{member.mention_html()}, вᴇʌᴋᴀᴍ дᴏ уᴍᴏʙної ᴦᴘи", 
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