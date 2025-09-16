import os
import requests
from collections import Counter
from telegram.ext import ContextTypes
from telegram import Update
import datetime
from dotenv import load_dotenv

load_dotenv()
OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')
CITY_LAT = 50.45
CITY_LON = 30.52

WEATHER_CHATS_FILE = 'weather_chats.txt'

def _save_chat_id(chat_id):
    """Зберігає chat_id у файл, якщо він ще не існує."""
    with open(WEATHER_CHATS_FILE, 'a+') as f:
        f.seek(0)
        existing_chats = f.read().splitlines()
        if str(chat_id) not in existing_chats:
            f.write(str(chat_id) + '\n')
            print(f"Новий чат збережено: {chat_id}")

def _get_all_chat_ids():
    """Читає всі збережені chat_ids з файлу."""
    if not os.path.exists(WEATHER_CHATS_FILE):
        return []
    with open(WEATHER_CHATS_FILE, 'r') as f:
        return [int(line.strip()) for line in f.readlines()]

def _get_wind_summary(period_data):
    """
    Аналізує дані за період, визначає переважний стан вітру
    і повертає кортеж (емодзі, слово, середня швидкість).
    """
    if not period_data:
        return "💨", "невідомо", "N/A"

    wind_speeds = [item['wind']['speed'] for item in period_data]
    avg_speed = sum(wind_speeds) / len(wind_speeds)
    rounded_speed = round(avg_speed, 1)

    if avg_speed <= 3.0:
        emoji, word = ("💨", "штиль")
    elif 3.5 < avg_speed <= 5.0:
        emoji, word = ("💨", "бриз")
    elif 5.5 < avg_speed <= 10.0:
        emoji, word = ("💨", "фреш")
    else:
        emoji, word = ("🌀", "шквал")

    return emoji, word, f"≈{rounded_speed} м/с"

def _get_period_summary(period_data, period_name):
    """
    Аналізує дані за період, визначає переважну погоду з пріоритетом на опади
    і повертає кортеж (емодзі, слово погоди, діапазон температур).
    """
    if not period_data:
        return "🤷", "невідомо", "N/A"

    temps = [item['main']['temp'] for item in period_data]
    temp_range = f"{round(min(temps))}/{round(max(temps))} °C"

    conditions = [item['weather'][0]['main'].lower() for item in period_data]
    
    priority_condition = None
    if 'thunderstorm' in conditions:
        priority_condition = 'thunderstorm'
    elif 'snow' in conditions:
        priority_condition = 'snow'
    elif 'rain' in conditions or 'drizzle' in conditions:
        priority_condition = 'rain'
    
    if priority_condition:
        dominant_condition = priority_condition
    else:
        condition_counts = Counter(conditions)
        dominant_condition = condition_counts.most_common(1)[0][0]

    emoji_map = {
        'thunderstorm': ("⛈️", "гроза"),
        'snow': ("❄️", "сніг"),
        'rain': ("☔️", "дощ"),
        'drizzle': ("☔️", "дощ"),
        'mist': ("🌫️", "туман"),
        'fog': ("🌫️", "туман"),
        'clear': ("☀️", "ясно"),
    }

    if dominant_condition == 'clouds':
        if period_name == 'morning':
            emoji, word = ("⛅️", "хмарно")
        elif period_name == 'day':
            emoji, word = ("🌤️", "хмарно")
        elif period_name == 'evening':
            emoji, word = ("🌥️", "хмарно")
        else:
            emoji, word = ("☁️", "хмарно")
    else:
        emoji, word = emoji_map.get(dominant_condition, ("🤷", "невідомо"))

    return emoji, word, temp_range

def get_weather_forecast():
    """
    Отримує та форматує прогноз погоди у фінальному стилі, включаючи вітер.
    """
    if not OPENWEATHERMAP_API_KEY:
        return "Помилка: Ключ API для OpenWeatherMap не знайдено."

    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={CITY_LAT}&lon={CITY_LON}&appid={OPENWEATHERMAP_API_KEY}&units=metric&lang=ua&cnt=8"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data.get('cod') == '200':
            forecast_list = data['list']
            
            morning_data = forecast_list[0:2]
            day_data = forecast_list[2:4]
            evening_data = forecast_list[4:6]
            
            morning_emoji, morning_word, morning_temp = _get_period_summary(morning_data, 'morning')
            day_emoji, day_word, day_temp = _get_period_summary(day_data, 'day')
            evening_emoji, evening_word, evening_temp = _get_period_summary(evening_data, 'evening')
            
            morning_wind_emoji, morning_wind_word, morning_wind_speed = _get_wind_summary(morning_data)
            day_wind_emoji, day_wind_word, day_wind_speed = _get_wind_summary(day_data)
            evening_wind_emoji, evening_wind_word, evening_wind_speed = _get_wind_summary(evening_data)

            return (
                f"• ᴘᴀнᴏᴋ\n  {morning_emoji} {morning_word} {morning_temp}\n  {morning_wind_emoji} {morning_wind_word} {morning_wind_speed}\n\n"
                f"• дᴇнь\n  {day_emoji} {day_word} {day_temp}\n  {day_wind_emoji} {day_wind_word} {day_wind_speed}\n\n"
                f"• вᴇчiᴘ\n  {evening_emoji} {evening_word} {evening_temp}\n  {evening_wind_emoji} {evening_wind_word} {evening_wind_speed}"
            )
        else:
            return "Помилка отримання прогнозу погоди."
            
    except requests.exceptions.RequestException as e:
        print(f"Помилка OpenWeather API: {e}")
        return "⚠️ Помилка при отриманні прогнозу погоди."

async def delete_message_job(context: ContextTypes.DEFAULT_TYPE):
    """Видаляє повідомлення, вказане в job.data."""
    chat_id = context.job.data.get('chat_id')
    message_id = context.job.data.get('message_id')
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        print(f"Повідомлення {message_id} видалено з чату {chat_id}.")
    except Exception as e:
        print(f"Помилка видалення повідомлення {message_id}: {e}")

async def post_weather_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Надсилає щоденний прогноз погоди та ставить завдання на його видалення через 4 години.
    """
    message_text = get_weather_forecast()
    
    chat_id = context.job.chat_id
    
    try:
        sent_message = await context.bot.send_message(
            chat_id=chat_id,
            text=message_text
        )
        context.job_queue.run_once(
            delete_message_job,
            14400,
            data={'chat_id': chat_id, 'message_id': sent_message.message_id}
        )
    except Exception as e:
        print(f"Помилка надсилання прогнозу погоди в чат {chat_id}: {e}")

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Відповідає на команду /weather, надсилаючи прогноз, зберігаючи ID чату
    та плануючи видалення повідомлень.
    """
    chat_id = update.effective_chat.id
    user_command_id = update.message.message_id
    message_thread_id = update.message.message_thread_id

    if update.effective_chat.type in ["group", "supergroup"]:
        _save_chat_id(chat_id)
        notification_msg = await update.message.reply_text(
            "Погода для цього чату тепер буде відправлятися щодня.",
            message_thread_id=message_thread_id
        )
        # Плануємо видалення повідомлення-сповіщення через 15 секунд
        context.job_queue.run_once(
            delete_message_job,
            15,
            data={'chat_id': chat_id, 'message_id': notification_msg.message_id},
            name=f'del_weather_notify_{notification_msg.message_id}'
        )

    await update.message.reply_chat_action("typing")
    
    # Відправляємо прогноз погоди
    forecast_message = await update.message.reply_text(
        text=get_weather_forecast(),
        message_thread_id=message_thread_id
    )

    # Негайно видаляємо команду користувача
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=user_command_id)
    except Exception as e:
        print(f"Не вдалося видалити команду /weather: {e}")

    # Плануємо видалення прогнозу погоди через 4 години
    context.job_queue.run_once(
        delete_message_job,
        14400, # 4 hours
        data={'chat_id': chat_id, 'message_id': forecast_message.message_id},
        name=f'del_weather_cmd_{forecast_message.message_id}'
    )