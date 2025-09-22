from deep_translator import GoogleTranslator, exceptions
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# FIX: Видалено непотрібні імпорти (os, load_dotenv, langdetect)

# Стан для ConversationHandler
TRANSLATE_STATE = 1

async def translate_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє команду /translate, видаляє її та просить користувача ввести текст.
    """
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        print(f"Помилка видалення команди /translate: {e}")

    reply_message = await update.effective_chat.send_message(
        "слух",
        message_thread_id=update.message.message_thread_id
    )
    context.user_data['reply_message_id'] = reply_message.message_id
    
    return TRANSLATE_STATE

async def handle_translation_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Переводить текст, видаляє повідомлення бота та користувача.
    """
    text_to_translate = update.message.text.strip()
    
    if not text_to_translate:
        await update.message.reply_text("ви не ввели текст")
        return ConversationHandler.END

    try:
        translator = GoogleTranslator(source='auto', target='en')
        translated_text = translator.translate(text_to_translate)
        
        if translated_text:
            # Екранування символів для MarkdownV2
            escaped_text = translated_text.replace('`', '\\`').replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
            
            await update.message.reply_text(
                text=f"```\n{escaped_text}\n```", 
                parse_mode=ParseMode.MARKDOWN_V2,
                message_thread_id=update.message.message_thread_id
            )
            try:
                await update.message.delete()
            except Exception as e:
                print(f"Помилка видалення повідомлення користувача: {e}")
            
            reply_message_id = context.user_data.get('reply_message_id')
            if reply_message_id:
                try:
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=reply_message_id
                    )
                except Exception as e:
                    print(f"Помилка видалення повідомлення бота: {e}")
        else:
            await update.message.reply_text("помилка 🤷 не вдалося перекласти текст")

    except exceptions.NotValidPayload:
        await update.message.reply_text("помилка 🤷 не можу перекласти цей текст")
    except Exception as e:
        print(f"Помилка при перекладі: {e}")
        await update.message.reply_text("шось пішло не так 🤷")
    
    context.user_data.pop('reply_message_id', None)
    return ConversationHandler.END

# FIX: Видалено функцію auto_translate_en_to_ua