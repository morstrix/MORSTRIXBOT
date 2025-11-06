# handlers.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatJoinRequest, WebAppInfo # <--- ДОБАВЛЕНО WebAppInfo
from telegram.ext import ContextTypes, ConversationHandler
import asyncio

# !!! ОЧЕНЬ ВАЖНО: ЗАМЕНИТЕ ЭТУ ССЫЛКУ на URL вашего WebApp (где будет лежать drafts_grid.html) !!!
WEBAPP_URL = "https://github.com/morstrix" 

RULES_MESSAGE = "для зʙ'язᴋу з ʜᴇйᴘoxᴇʌпᴇᴘoᴍ - зʜɪᴍᴀй ᴋᴀᴄᴛᴘюʌю i ᴋᴏᴘиᴄᴛуйся ᴛᴘигᴇᴘом: ᴀʌо"

async def open_drafts_webapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляет кнопку для запуска Mini App (Drafts Grid).
    """
    if update.effective_chat.type != 'private':
        await update.message.reply_text("Это команда доступна только в личном чате.")
        return
        
    keyboard = [
        [
            InlineKeyboardButton(
                "💾 Черновики (Grid)",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Нажми, чтобы открыть статичную пиксельную сетку черновиков:",
        reply_markup=reply_markup,
        message_thread_id=update.message.message_thread_id
    )


async def handle_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        keyboard = [[InlineKeyboardButton("правила", callback_data="show_rules")]]
        await update.message.reply_html(
            f"{member.mention_html()}, вᴇʌᴋᴀᴍ дᴏ уᴍᴏʙної ᴦᴘи", 
            reply_markup=InlineKeyboardMarkup(keyboard),
            message_thread_id=update.message.message_thread_id
        )

# ... (остальные функции: handle_join_request, handle_callback_query)

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_request: ChatJoinRequest = update.chat_join_request
    try:
        await chat_request.approve()
        await context.bot.send_message(chat_id=chat_request.from_user.id, text=f"✅ ᴛʙᴏя зᴀяʙᴋᴀ схʙᴀʌᴇʜᴀ. \\nᴋидᴀй будь-яᴋi пиᴛᴀʜʜя.")
        print(f"Заявку від {chat_request.from_user.username or chat_request.from_user.id} схвалено.")
    except Exception as e:
        print(f"Помилка схвалення заявки від {chat_request.from_user.username or chat_request.from_user.id}: {e}")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "show_rules":
        await query.message.reply_text(
            RULES_MESSAGE,
            message_thread_id=query.message.message_thread_id
        )