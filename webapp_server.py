# webapp_server.py (НОВЫЙ ФАЙЛ)

import os
from aiohttp import web
from telegram import Update

# ----------------------------------------------------
#           💥 Обробники AIOHTTP (Web App) 💥
# ----------------------------------------------------

async def handle_telegram_webhook(request):
    """Обробляє запити Webhook від Telegram."""
    bot_app = request.app['bot_app']
    
    # Ограничение размера запроса
    if request.content_length > 10**6: 
        print("Запрос слишком большой, игнорируется.")
        return web.Response(text="request too large", status=413)
        
    try:
        data = await request.json()
    except Exception as e:
        print(f"Ошибка получения JSON: {e}")
        return web.Response(text="bad request", status=400)
        
    await bot_app.update_queue.put(Update.de_json(data=data, bot=bot_app.bot))
    return web.Response(text="ok", status=200)

async def handle_drafts_html(request):
    """Обслуговує HTML-файл для Web App."""
    
    # Читаем файл синхронно, так как aiohttp будет асинхронно его отдавать
    try:
        with open('drafts.html', 'rb') as f:
            content = f.read()
        
        # Отдаем содержимое файла с корректным MIME-типом
        return web.Response(body=content, content_type='text/html', status=200)
    except FileNotFoundError:
        return web.Response(text="drafts.html не найден", status=404)

async def handle_index(request):
    """Простая страница, чтобы проверить, работает ли сервер."""
    return web.Response(text="Aiohttp server is running and ready for webhook.", status=200)