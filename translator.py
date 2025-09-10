import os
from deep_translator import GoogleTranslator, exceptions
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from dotenv import load_dotenv
from langdetect import detect, DetectorFactory
from telegram.constants import ParseMode

load_dotenv()
DetectorFactory.seed = 0

# Стан для ConversationHandler
TRANSLATE_STATE = 1

async def translate_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє команду /translate, видаляє її та просить користувача ввести текст.
    """
    # Зберігаємо ID повідомлення з командою для подальшого видалення
    context.user_data['command_message_id'] = update.message.message_id
    
    # Видаляємо команду /translate
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        print(f"Помилка видалення команди /translate: {e}")

    reply_message = await update.effective_chat.send_message(
        "введіть текст для перекладу:"
    )
    # Зберігаємо ID повідомлення-відповіді бота
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
            await update.message.reply_text(
                text=f"```\n{translated_text}\n```", 
                parse_mode=ParseMode.MARKDOWN_V2
            )
            # Видаляємо повідомлення користувача
            try:
                await update.message.delete()
            except Exception as e:
                print(f"Помилка видалення повідомлення користувача: {e}")
            
            # Видаляємо повідомлення бота, якщо воно було збережене
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
    
    # Завершуємо розмову
    context.user_data.pop('command_message_id', None)
    context.user_data.pop('reply_message_id', None)
    return ConversationHandler.END

async def auto_translate_en_to_ua(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') == 'awaiting_translate':
        return

    if not update.message or not update.message.text:
        return
        
    if update.message.text.startswith('/'):
        return

    text_to_translate = update.message.text.strip()
    
    try:
        detected_lang = detect(text_to_translate)

        if detected_lang == 'en':
            translator = GoogleTranslator(source='en', target='uk')
            translated_text = translator.translate(text_to_translate)
            
            if translated_text:
                await update.message.reply_text(f"🌐 {translated_text}")
            else:
                print("Ошибка автоматического перевода: не удалось перевести текст.")
    except Exception as e:
        print(f"Помилка автоматичного перекладу: {e}")