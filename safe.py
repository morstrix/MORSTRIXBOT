# safe.py - исправленная версия
import os
import requests
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ReactionEmoji  # ✅ ПРАВИЛЬНЫЙ ИМПОРТ

from dotenv import load_dotenv

load_dotenv()
GOOGLE_SAFE_BROWSING_API_KEY = os.getenv('GOOGLE_SAFE_BROWSING_API_KEY')
GOOGLE_SAFE_BROWSING_URL = 'https://safebrowsing.googleapis.com/v4/threatMatches:find'


async def check_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет ссылки через Google Safe Browsing API."""
    if not GOOGLE_SAFE_BROWSING_API_KEY:
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
        "client": {"clientId": "telegram-bot", "clientVersion": "1.0.0"},
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
            # Опасная ссылка
            await update.message.set_reaction(
                reaction=[ReactionEmoji(emoji="🤬")],
                is_big=False
            )
        else:
            # Безопасная ссылка
            await update.message.set_reaction(
                reaction=[ReactionEmoji(emoji="⚡")],
                is_big=False
            )
    except Exception as e:
        print(f"Ошибка проверки ссылок: {e}")