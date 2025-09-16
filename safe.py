import os
import requests
from telegram import Update, ReactionTypeEmoji
from telegram.ext import ContextTypes
from dotenv import load_dotenv

load_dotenv()
GOOGLE_SAFE_BROWSING_API_KEY = os.getenv('GOOGLE_SAFE_BROWSING_API_KEY')
GOOGLE_SAFE_BROWSING_URL = 'https://safebrowsing.googleapis.com/v4/threatMatches:find'


async def check_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перевіряє посилання у повідомленні через Google Safe Browsing API."""
    if not GOOGLE_SAFE_BROWSING_API_KEY:
        print("Помилка: GOOGLE_SAFE_BROWSING_API_KEY не знайдено.")
        return

    urls = []
    if update.message and update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'url':
                urls.append(update.message.text[entity.offset:entity.offset + entity.length])
            elif entity.type == 'text_link':
                urls.append(entity.url)

    if not urls:
        return

    payload = {
        "client": {"clientId": "your-telegram-bot", "clientVersion": "1.0.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url} for url in urls]
        }
    }

    try:
        response = requests.post(f'{GOOGLE_SAFE_BROWSING_URL}?key={GOOGLE_SAFE_BROWSING_API_KEY}', json=payload)
        response.raise_for_status()
        data = response.json()

        if 'matches' in data:
            # Реакція на небезпечне посилання (повідомлення не видаляється)
            await context.bot.set_message_reaction(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                reaction=[ReactionTypeEmoji("🤬")]
            )
        else:
            # Реакція на безпечне посилання
            await context.bot.set_message_reaction(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                reaction=[ReactionTypeEmoji("⚡️")]
            )
    except requests.exceptions.RequestException as e:
        print(f"Помилка при зверненні до Google Safe Browsing API: {e}")