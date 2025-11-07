import os
import requests
from collections import Counter
from telegram.ext import ContextTypes
from telegram import Update
from dotenv import load_dotenv

load_dotenv()
OPENWEATHERMAP_API_KEY = os.getenv('OPENWEATHERMAP_API_KEY')
CITY_LAT = 50.45
CITY_LON = 30.52

# FIX: Видалено функції для збереження/читання chat_id, оскільки автопостинг вимкнено
# _save_chat_id, _get_all_chat_ids

def _get_wind_summary(period_data):
    if not period_data:
        return "💨", "невідомо", "N/A"
    wind_speeds = [item['wind']['speed'] for item in period_data]
    avg_speed = sum(wind_speeds) / len(wind_speeds)
    rounded_speed = round(avg_speed, 1)

    if avg_speed <= 3.0: emoji, word = ("💨", "штиль")
    elif 3.5 < avg_speed <= 5.0: emoji, word = ("💨", "бриз")
    elif 5.5 < avg_speed <= 10.0: emoji, word = ("💨", "фреш")
    else: emoji, word = ("🌀", "шквал")
    return emoji, word, f"≈{rounded_speed} м/с"

def _get_period_summary(period_data, period_name):
    if not period_data:
        return "🤷", "невідомо", "N/A"

    temps = [item['main']['temp'] for item in period_data]
    temp_range = f"{round(min(temps))}/{round(max(temps))} °C"
    conditions = [item['weather'][0]['main'].lower() for item in period_data]
    
    priority_condition = None
    if 'thunderstorm' in conditions: priority_condition = 'thunderstorm'
    elif 'snow' in conditions: priority_condition = 'snow'
    elif 'rain' in conditions or 'drizzle' in conditions: priority_condition = 'rain'
    
    dominant_condition = priority_condition if priority_condition else Counter(conditions).most_common(1)[0][0]

    emoji_map = {
        'thunderstorm': ("⛈️", "гроза"), 'snow': ("❄️", "сніг"),
        'rain': ("☔️", "дощ"), 'drizzle': ("☔️", "дощ"),
        'mist': ("🌫️", "туман"), 'fog': ("🌫️", "туман"), 'clear': ("☀️", "ясно"),
    }

    if dominant_condition == 'clouds':
        if period_name == 'morning': emoji, word = ("⛅️", "хмарно")
        elif period_name == 'day': emoji, word = ("🌤️", "хмарно")
        elif period_name == 'evening': emoji, word = ("🌥️", "хмарно")
        else: emoji, word = ("☁️", "хмарно")
    else:
        emoji, word = emoji_map.get(dominant_condition, ("🤷", "невідомо"))
    return emoji, word, temp_range

def get_weather_forecast():
    if not OPENWEATHERMAP_API_KEY:
        return "Помилка: Ключ API для OpenWeatherMap не знайдено."

    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={CITY_LAT}&lon={CITY_LON}&appid={OPENWEATHERMAP_API_KEY}&units=metric&lang=ua&cnt=8"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if data.get('cod') == '200':
            forecast_list = data['list']
            morning_data, day_data, evening_data = forecast_list[0:2], forecast_list[2:4], forecast_list[4:6]
            
            m_emoji, m_word, m_temp = _get_period_summary(morning_data, 'morning')
            d_emoji, d_word, d_temp = _get_period_summary(day_data, 'day')
            e_emoji, e_word, e_temp = _get_period_summary(evening_data, 'evening')
            
            m_wind_emoji, m_wind_word, m_wind_speed = _get_wind_summary(morning_data)
            d_wind_emoji, d_wind_word, d_wind_speed = _get_wind_summary(day_data)
            e_wind_emoji, e_wind_word, e_wind_speed = _get_wind_summary(evening_data)

            return (
                f"• ᴘᴀнᴏᴋ\n  {m_emoji} {m_word} {m_temp}\n  {m_wind_emoji} {m_wind_word} {m_wind_speed}\n\n"
                f"• дᴇнь\n  {d_emoji} {d_word} {d_temp}\n  {d_wind_emoji} {d_wind_word} {d_wind_speed}\n\n"
                f"• вᴇчiᴘ\n  {e_emoji} {e_word} {e_temp}\n  {e_wind_emoji} {e_wind_word} {e_wind_speed}"
            )
        else:
            return "Помилка отримання прогнозу погоди."
    except requests.exceptions.RequestException as e:
        print(f"Помилка OpenWeather API: {e}")
        return "⚠️ Помилка при отриманні прогнозу погоди."

async def delete_message_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.data.get('chat_id')
    message_id = context.job.data.get('message_id')
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        print(f"Помилка видалення повідомлення {message_id}: {e}")

# FIX: Видалено функцію post_weather_job, оскільки вона більше не потрібна

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    CHANGE: Логіка значно спрощена. Більше не зберігає ID чату і не планує розсилку.
    Просто надсилає прогноз у відповідь на команду та планує видалення повідомлень.
    """
    chat_id = update.effective_chat.id
    user_command_id = update.message.message_id
    message_thread_id = update.message.message_thread_id

    await update.message.reply_chat_action("typing")
    
    forecast_message = await update.message.reply_text(
        text=get_weather_forecast(),
        message_thread_id=message_thread_id
    )

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