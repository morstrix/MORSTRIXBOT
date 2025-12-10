# safe.py
"""
Модуль для проверки безопасности ссылок через Google Safe Browsing API.
Упрощенная версия без использования реакций Telegram, чтобы избежать
конфликтов версий библиотеки python-telegram-bot.
"""

import os
import logging
import asyncio
import requests
from telegram import Update
from telegram.ext import ContextTypes
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)

# Конфигурация Google Safe Browsing
GOOGLE_SAFE_BROWSING_API_KEY = os.getenv('GOOGLE_SAFE_BROWSING_API_KEY')
GOOGLE_SAFE_BROWSING_URL = 'https://safebrowsing.googleapis.com/v4/threatMatches:find'

async def check_links(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Проверяет ссылки в сообщении через Google Safe Browsing API.
    
    Вместо установки реакций (которые требуют специфичной версии PTB),
    просто логирует результат проверки.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст обработчика
    """
    
    # Если API ключ не настроен, пропускаем проверку
    if not GOOGLE_SAFE_BROWSING_API_KEY:
        logger.debug("Google Safe Browsing API ключ не настроен, пропускаем проверку.")
        return
    
    # Если нет сообщения, выходим
    if not update.message or not update.message.text:
        return
    
    # Извлекаем все ссылки из сообщения
    urls = []
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'url':
                url = update.message.text[entity.offset:entity.offset + entity.length]
                urls.append(url)
                logger.info(f"Найдена ссылка: {url}")
            elif entity.type == 'text_link':
                urls.append(entity.url)
                logger.info(f"Найдена текстово-гиперссылка: {entity.url}")
    
    # Если ссылок нет, выходим
    if not urls:
        return
    
    logger.info(f"Проверяем {len(urls)} ссылок через Google Safe Browsing...")
    
    # Подготавливаем запрос к Google Safe Browsing API
    payload = {
        "client": {
            "clientId": "telegram-bot-safety-check",
            "clientVersion": "1.0.0"
        },
        "threatInfo": {
            "threatTypes": [
                "MALWARE", 
                "SOCIAL_ENGINEERING", 
                "UNWANTED_SOFTWARE", 
                "POTENTIALLY_HARMFUL_APPLICATION"
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url} for url in urls]
        }
    }
    
    try:
        # Отправляем запрос к Google Safe Browsing API
        response = requests.post(
            f'{GOOGLE_SAFE_BROWSING_URL}?key={GOOGLE_SAFE_BROWSING_API_KEY}',
            json=payload,
            timeout=5  # Таймаут 5 секунд
        )
        response.raise_for_status()  # Проверяем на ошибки HTTP
        
        data = response.json()
        
        # Анализируем ответ
        if 'matches' in data and data['matches']:
            dangerous_urls = [match['threat']['url'] for match in data['matches']]
            logger.warning(f"Обнаружены опасные ссылки: {dangerous_urls}")
            
            # Уведомляем пользователя в чате (без реакций)
            warning_msg = "⚠️ *Внимание!* В сообщении обнаружены потенциально опасные ссылки."
            await update.message.reply_text(
                warning_msg,
                parse_mode='Markdown',
                reply_to_message_id=update.message.message_id
            )
        else:
            logger.info("Все ссылки безопасны.")
            # Можно добавить уведомление о безопасности, если нужно
            # safe_msg = "✅ Все ссылки в сообщении безопасны."
            # await update.message.reply_text(safe_msg, reply_to_message_id=update.message.message_id)
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при обращении к Google Safe Browsing API: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при проверке ссылок: {e}")

# Альтернативная упрощенная версия без API проверки
async def check_links_simple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Упрощенная версия проверки ссылок без внешних API вызовов.
    Просто логирует найденные ссылки.
    
    Args:
        update: Объект Update от Telegram
        context: Контекст обработчика
    """
    if not update.message or not update.message.text:
        return
    
    urls = []
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == 'url':
                url = update.message.text[entity.offset:entity.offset + entity.length]
                urls.append(url)
            elif entity.type == 'text_link':
                urls.append(entity.url)
    
    if urls:
        logger.info(f"В сообщении найдены ссылки: {urls}")
        # Можно добавить базовую логику проверки по черным спискам и т.д.

# Вспомогательная функция для проверки одной ссылки (синхронная)
def check_single_url(url: str) -> bool:
    """
    Проверяет одну ссылку через Google Safe Browsing API (синхронно).
    
    Args:
        url: Ссылка для проверки
        
    Returns:
        True если ссылка безопасна, False если опасна или произошла ошибка
    """
    if not GOOGLE_SAFE_BROWSING_API_KEY:
        logger.warning("API ключ не настроен, возвращаем True")
        return True
    
    payload = {
        "client": {
            "clientId": "telegram-bot-safety-check",
            "clientVersion": "1.0.0"
        },
        "threatInfo": {
            "threatTypes": [
                "MALWARE", 
                "SOCIAL_ENGINEERING", 
                "UNWANTED_SOFTWARE", 
                "POTENTIALLY_HARMFUL_APPLICATION"
            ],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }
    
    try:
        response = requests.post(
            f'{GOOGLE_SAFE_BROWSING_URL}?key={GOOGLE_SAFE_BROWSING_API_KEY}',
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        
        data = response.json()
        return 'matches' not in data or not data['matches']
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при проверке ссылки {url}: {e}")
        return True  # В случае ошибки считаем ссылку безопасной
    except Exception as e:
        logger.error(f"Неожиданная ошибка при проверке {url}: {e}")
        return True