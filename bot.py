import os
import json
import datetime
import asyncio
import pytz
import logging


from babel.dates import format_datetime
def format_date(dt, format_str="d MMMM", locale="ru_RU"):
    """Форматируем datetime на русском языке"""
    return format_datetime(dt, format_str, locale=locale)


import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import font_manager as fm

from geopy.geocoders import Nominatim
from timezonefinderL import TimezoneFinder

from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile, Location, ReplyKeyboardRemove
from aiogram.filters import Command


from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==== Настройки ====
API_TOKEN = "API"

DEFAULT_CITY = "Moscow"
DEFAULT_LAT, DEFAULT_LON = 55.75, 37.61
USERS_FILE = "users.json"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
geolocator = Nominatim(user_agent="WeatherBot")
tf = TimezoneFinder()

# ==== Работа с JSON ====
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

users = load_users()

# ==== Получение координат города ====
def get_city_coordinates(city_name):
    location = geolocator.geocode(city_name, timeout=10)
    if location:
        return location.latitude, location.longitude
    return None, None

# ==== Таймзона по координатам ====
def get_timezone(lat, lon):
    tz_name = tf.timezone_at(lat=lat, lng=lon)
    return tz_name if tz_name else "Europe/Moscow"
    
# ==== Получение погоды ====
import aiohttp
import time

# ==== Кеш погоды ====
weather_cache = {}  # ключ (lat, lon), значение { "time": timestamp, "data": response_json }
CACHE_TTL = 600  # 10 минут

# ==== Получение погоды ====
async def get_weather(lat, lon, tz_name="Europe/Moscow"):
    cache_key = (round(lat, 2), round(lon, 2))  # округлим координаты чтобы кеш был адекватным
    now = time.time()

    # Проверяем кеш
    if cache_key in weather_cache:
        cached = weather_cache[cache_key]
        if now - cached["time"] < CACHE_TTL:
            response = cached["data"]
        else:
            del weather_cache[cache_key]  # устарел
    else:
        response = None

    if response is None:
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&"
            f"hourly=temperature_2m,relative_humidity_2m,wind_speed_10m,"
            f"precipitation,weathercode,apparent_temperature&"
            f"daily=sunrise,sunset,temperature_2m_max,temperature_2m_min,"
            f"apparent_temperature_max,apparent_temperature_min,"
            f"precipitation_sum,uv_index_max,weathercode,"
            f"windspeed_10m_max,winddirection_10m_dominant&"
            f"timezone=auto"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                response = await resp.json()

        weather_cache[cache_key] = {"time": now, "data": response}

    # ==== Hourly (12 часов) ====
    hourly_data = response.get("hourly", {})
    all_times = hourly_data.get("time", [])
    all_temps = hourly_data.get("temperature_2m", [])
    all_humidity = hourly_data.get("relative_humidity_2m", [])
    all_wind = hourly_data.get("wind_speed_10m", [])
    all_rain = hourly_data.get("precipitation", [])
    all_codes = hourly_data.get("weathercode", [])
    all_app = hourly_data.get("apparent_temperature", [])

    # Таймзона
    tz = pytz.timezone(tz_name)
    now_dt = datetime.datetime.now(tz)

    start_index = 0
    for i, t in enumerate(all_times):
        t_dt = datetime.datetime.fromisoformat(t)
        if t_dt.tzinfo is None:
            t_dt = tz.localize(t_dt)
        if t_dt >= now_dt.replace(minute=0, second=0, microsecond=0):
            start_index = i
            break

    temps = all_temps[start_index:start_index+12]
    humidity = all_humidity[start_index:start_index+12]
    wind = all_wind[start_index:start_index+12]
    rain = all_rain[start_index:start_index+12]
    codes = all_codes[start_index:start_index+12]
    apparent = all_app[start_index:start_index+12]
    times_fmt = [
        datetime.datetime.fromisoformat(t).strftime("%H:%M")
        for t in all_times[start_index:start_index+12]
    ]

    min_temp = min(temps) if temps else None
    max_temp = max(temps) if temps else None
    avg_temp = round(sum(temps)/len(temps), 1) if temps else None
    avg_humidity = round(sum(humidity)/len(humidity), 1) if humidity else None
    avg_wind = round(sum(wind)/len(wind), 1) if wind else None
    rain_expected = any(r > 0 for r in rain) if rain else False

    summary = "🌡 Погода неизвестна"
    if codes:
        wmo_codes = {
            0: "☀️ Солнечно",
            1: "🌤 Почти ясно",
            2: "⛅ Переменная облачность",
            3: "☁️ Облачно",
            45: "🌫 Туман",
            48: "🌫 Туман с изморозью",
            51: "🌦 Лёгкий дождь",
            61: "🌧 Дождь",
            71: "❄️ Снег",
            80: "🌦 Ливень",
            95: "⛈ Гроза"
        }
        summary = wmo_codes.get(codes[0], summary)

    # ==== Daily (3 дня) ====
    daily = response.get("daily", {})
    daily_data = []
    for i in range(min(3, len(daily.get("time", [])))):
        daily_data.append({
            "date": daily["time"][i],
            "sunrise": daily["sunrise"][i],
            "sunset": daily["sunset"][i],
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "app_temp_max": daily["apparent_temperature_max"][i],
            "app_temp_min": daily["apparent_temperature_min"][i],
            "precip": daily["precipitation_sum"][i],
            "uv": daily["uv_index_max"][i],
            "wind_speed": daily["windspeed_10m_max"][i],
            "wind_dir": daily["winddirection_10m_dominant"][i],
            "code": daily["weathercode"][i]
        })

    return {
        "temps": temps,
        "times": times_fmt,
        "rain_list": rain,
        "codes": codes,
        "apparent": apparent,
        "min_temp": min_temp,
        "max_temp": max_temp,
        "avg_temp": avg_temp,
        "avg_humidity": avg_humidity,
        "avg_wind": avg_wind,
        "rain": rain_expected,
        "summary": summary,
        "daily_data": daily_data
    }



# ==== Совет по одежде ====
def clothing_advice(temp, wind, rain):
    advice = ""
    if temp < 0:
        advice += "Очень холодно 🥶 — тёплая куртка, шапка и перчатки.\n"
    elif temp < 10:
        advice += "Прохладно ❄️ — лучше надеть куртку или толстовку.\n"
    elif temp < 20:
        advice += "Умеренно 🌤 — лёгкая куртка или свитер.\n"
    else:
        advice += "Тепло ☀️ — подойдёт футболка и лёгкая одежда.\n"

    if wind > 6:
        advice += "Сильный ветер 💨 — возьми ветровку.\n"
    if rain:
        advice += "Ожидаются осадки ☔ — не забудь зонт или дождевик.\n"
    elif rain and temp < 2:
        advice += "❄️ Возможен снег — возьми тёплую обувь.\n"
    return advice

def check_weather_changes(daily_data):
    """
    Проверяет резкие изменения погоды между сегодняшним и завтрашним днем.
    Возвращает строку с предупреждениями или пустую строку.
    """
    if len(daily_data) < 2:
        return ""

    today, tomorrow = daily_data[0], daily_data[1]
    alerts = []

    # Резкое изменение температуры
    diff_max = tomorrow["temp_max"] - today["temp_max"]
    diff_min = tomorrow["temp_min"] - today["temp_min"]

    if diff_max >= 8 or diff_min >= 8:
        alerts.append(f"☀️ Завтра потеплеет на {max(diff_max, diff_min)}°C")
    if diff_max <= -8 or diff_min <= -8:
        alerts.append(f"❄️ Завтра похолодает на {abs(min(diff_max, diff_min))}°C")

    # Появление осадков
    if tomorrow["precip"] > 0 and today["precip"] == 0:
        alerts.append("☔ Завтра ожидаются осадки")

    # Гроза
    if tomorrow["code"] in [95, 96, 99]:
        alerts.append("⛈ Возможна гроза")

    return "\n".join(alerts)


# ==== Отправка погоды ====
async def send_weather(chat_id: int):
    user = users.get(str(chat_id), {"city": DEFAULT_CITY, "lat": DEFAULT_LAT, "lon": DEFAULT_LON, "tz": "Europe/Moscow"})
    city = user["city"]
    data = await get_weather(user["lat"], user["lon"])

    avg_app_temp = round(sum(data.get("apparent", []))/len(data.get("apparent", [1])), 1)

    tz = pytz.timezone(user.get("tz", "Europe/Moscow"))
    now = datetime.datetime.now(tz)
    date_str = format_date(now, "d MMMM")  # вместо now.strftime("%d %B")
    
    today_uv = None
    if data.get("daily_data") and len(data["daily_data"]) > 0:
        today_uv = data["daily_data"][0].get("uv")

    text = (
        f"📅 {date_str}\n\n"
        f"📍 Погода в {city}\n"
        f"{data['summary']}\n"
        f"🌡 Температура: {data['avg_temp']}°C (min: {data['min_temp']}°C, max: {data['max_temp']}°C), ощущается: {avg_app_temp}°C\n"
        f"💧 Влажность: {data['avg_humidity']}%\n"
        f"💨 Ветер: {data['avg_wind']} м/с\n"
        f"☔ Осадки: {'Да' if data['rain'] else 'Нет'}\n"
        f"👕 Совет:\n{clothing_advice(data['avg_temp'], data['avg_wind'], data['rain'])}"
    )

    # Добавляем предупреждения отдельно, уже после строки
    alerts = check_weather_changes(data["daily_data"])
    if alerts:
        text += f"\n\n⚠️ Предупреждения:\n{alerts}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить прогноз", callback_data="update_weather"),
                InlineKeyboardButton(text="🌆 Сменить город", callback_data="choose_city"),
                InlineKeyboardButton(text="ℹ️ Подробнее", callback_data="extended_weather")
            ],
        ]
    )

# ==== Создание графика с минималистичными цветными маркерами и легендой ====

    precip_colors = {
        51: "skyblue", 53: "skyblue", 55: "skyblue",  # дождь мелкий
        61: "blue", 63: "blue", 65: "blue",           # дождь сильный
        71: "white", 73: "white", 75: "white",        # снег
        80: "cyan", 81: "cyan", 82: "cyan",           # ливневой дождь
        95: "purple", 96: "purple", 99: "purple",     # гроза
    }

    filename = f"weather_{chat_id}.png"
    plt.figure(figsize=(7, 4), facecolor="black")
    plt.plot(data["times"], data["temps"], marker="o", color="deepskyblue", linewidth=2)

    # Цветные маркеры осадков
    plt.plot(data["times"], data["temps"], marker="o", color="deepskyblue", linewidth=2, zorder=1)
    for t, temp, code in zip(data["times"], data["temps"], data["codes"]):
        if code in precip_colors:
            plt.scatter(t, temp, color=precip_colors[code], s=60, zorder=2, edgecolors="white",linewidth=1)


    # Минималистичная легенда
    import matplotlib.patches as mpatches
    legend_elements = [
        mpatches.Patch(color="skyblue", label="Морось"),
        mpatches.Patch(color="blue", label="Дождь"),
        mpatches.Patch(color="cyan", label="Ливень"),
        mpatches.Patch(color="white", label="Снег"),
        mpatches.Patch(color="purple", label="Гроза"),
    ]

    # Создаём легенду
    legend = plt.legend(
        handles=legend_elements,
        fontsize=8,
        loc="upper left",
        labelcolor="white",
        frameon=False  # сразу убираем рамку
    )

    # Делаем фон прозрачным (на случай если тема меняется)
    legend.get_frame().set_facecolor("none")


    plt.title("Температура на ближайшие часы", color="deepskyblue", fontsize=12)
    plt.xlabel("Время", color="white")
    plt.ylabel("°C", color="white")
    plt.grid(color="gray", linestyle="--", alpha=0.3)
    plt.xticks(color="white")
    plt.yticks(color="white")
    plt.gca().set_facecolor("black")
    plt.tight_layout()
    plt.savefig(filename, dpi=150, facecolor="black")
    plt.close()
    
    # ==== Отправка фото и текста ====
    photo = FSInputFile(filename)
    await bot.send_photo(chat_id, photo, caption=text, reply_markup=keyboard)
    os.remove(filename)

# ==== Регистрация задачи ====
def register_job(chat_id: int):
    user = users.get(str(chat_id))
    if not user:
        return

    tz_name = user.get("tz", "Europe/Moscow")
    tz = pytz.timezone(tz_name)

    # Удаляем старую задачу
    job_id = f"weather_{chat_id}"
    existing_job = scheduler.get_job(job_id)
    if existing_job:
        scheduler.remove_job(job_id)

    hour = user.get("notify_hour", 7)
    minute = user.get("notify_minute", 0)

    # Добавляем задачу корректно для AsyncIOScheduler
    scheduler.add_job(
        send_weather,          # асинхронная функция
        trigger="cron",
        args=[chat_id],        # аргументы для функции
        hour=hour,
        minute=minute,
        timezone=tz,
        id=job_id,
        coalesce=True,         # если пропущена задача, выполнится сразу
        max_instances=1        # не запускать несколько одновременно
    )

    print(f"✅ Registered weather job for chat {chat_id} at {hour:02d}:{minute:02d} {tz_name}")


# ==== Хендлеры команд ====
@dp.message(Command("help"))
async def help_cmd(message: Message):
    help_text = (
        "📌 *Список команд погоды:*\n\n"
        "/start — Запустить бота и зарегистрироваться\n"
        "/weather — Получить текущий прогноз погоды\n"
        "/setcity <город> — Установить город для прогноза\n"
        "/mylocation — Отправить текущую локацию для прогноза\n"
        "/settime HH:MM — Установить время ежедневного уведомления\n"
        "/help — Показать это сообщение\n\n"
        "ℹ️ Также можно использовать кнопки для обновления прогноза, смены города и просмотра расширенного прогноза."
    )
    await message.answer(help_text, parse_mode="Markdown")
# Команда для запроса локации
@dp.message(Command("mylocation"))
async def mylocation_cmd(message: Message):
    await message.answer(
        "📍 Пожалуйста, отправь мне свою текущую локацию.",
        reply_markup=ReplyKeyboardRemove()  # убираем обычную клавиатуру
    )

# Хендлер для обработки присланной геолокации
@dp.message(lambda m: m.location is not None)
async def location_handler(message: Message):
    if not message.location:
        await message.answer("❌ Не удалось получить локацию. Отправь локацию с помощью функции Telegram.")
        return

    lat = message.location.latitude
    lon = message.location.longitude
    chat_id = message.chat.id

    # Определяем город через геолокатор
    location = geolocator.reverse((lat, lon), language="ru")
    city_name = location.raw.get("address", {}).get("city") or location.raw.get("address", {}).get("town") or "Неизвестно"

    tz = get_timezone(lat, lon)

    # Сохраняем данные для пользователя
    users[str(chat_id)] = {"city": city_name, "lat": lat, "lon": lon, "tz": tz}
    save_users()
    register_job(chat_id)

    await message.answer(f"✅ Локация принята. Прогноз будет для {city_name}")
    await send_weather(chat_id)


@dp.callback_query(lambda c: c.data == "extended_weather")
async def extended_weather_callback(callback: CallbackQuery):
    chat_id = callback.from_user.id
    user = users.get(str(chat_id), {"city": DEFAULT_CITY, "lat": DEFAULT_LAT, "lon": DEFAULT_LON})
    city = user["city"]
    data = await get_weather(user["lat"], user["lon"])

    wmo_codes = {
        0: "☀️ ясно",
        1: "🌤 почти ясно",
        2: "⛅ переменная облачность",
        3: "☁️ облачно",
        45: "🌫 туман",
        48: "🌫 туман с изморозью",
        51: "🌦 лёгкий дождь",
        61: "🌧 дождь",
        71: "❄️ снег",
        80: "🌦 ливень",
        95: "⛈ гроза"
    }

    extended_text = f"📍 Расширенный прогноз на 3 дня для {city}:\n\n"

    for day in data["daily_data"]:
        date_str = datetime.datetime.fromisoformat(day["date"]).strftime("%d %B")
        sunrise = datetime.datetime.fromisoformat(day['sunrise']).strftime("%H:%M")
        sunset = datetime.datetime.fromisoformat(day['sunset']).strftime("%H:%M")
        date_str = format_date(datetime.datetime.fromisoformat(day['date']), "d MMMM")
        
        extended_text += (
            f"📅 {date_str} — {wmo_codes.get(day['code'], '🌡 неизвестно')}\n"
            f"🌡 {day['temp_min']}°C…{day['temp_max']}°C (ощущается {day['app_temp_min']}°C…{day['app_temp_max']}°C)\n"
            f"💨 Ветер: {day['wind_speed']} м/с, направление {day['wind_dir']}°\n"
            f"☔ Осадки: {day['precip']} мм\n"
            f"🔆 UV Index: {day['uv']}\n"
            f"🌅 {sunrise} | 🌇 {sunset}\n\n"
        )

    await callback.message.answer(extended_text)
    await callback.answer()

@dp.message(Command("settime"))
async def settime_cmd(message: Message):
    chat_id = message.chat.id
    parts = message.text.split()
    if len(parts) != 2:
        await message.answer("❌ Укажи время в формате HH:MM. Например: /settime 07:30")
        return

    try:
        hour, minute = map(int, parts[1].split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используй HH:MM от 00:00 до 23:59.")
        return

    if str(chat_id) not in users:
        users[str(chat_id)] = {"city": DEFAULT_CITY, "lat": DEFAULT_LAT, "lon": DEFAULT_LON, "tz": "Europe/Moscow"}

    users[str(chat_id)]["notify_hour"] = hour
    users[str(chat_id)]["notify_minute"] = minute
    save_users()
    register_job(chat_id)

    await message.answer(f"✅ Время ежедневного прогноза изменено на {hour:02d}:{minute:02d}")

@dp.message(Command("start"))
async def start_cmd(message: Message):
    chat_id = message.chat.id
    if str(chat_id) not in users:
        users[str(chat_id)] = {"city": DEFAULT_CITY, "lat": DEFAULT_LAT, "lon": DEFAULT_LON, "tz": "Europe/Moscow"}
        save_users()
        register_job(chat_id)

    await message.answer(
        "Привет! Я буду каждый день в 7:00 по твоему времени присылать прогноз 🌦\n"
        "Используй /weather чтобы получить прогноз сейчас.\n"
        "Используй /setcity <город>, чтобы сменить город."
    )

@dp.message(Command("weather"))
async def weather_cmd(message: Message):
    await send_weather(message.chat.id)

@dp.message(Command("setcity"))
async def setcity_cmd(message: Message):
    chat_id = message.chat.id
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Укажи город. Пример: /setcity Moscow")
        return

    city_name = parts[1]
    lat, lon = get_city_coordinates(city_name)
    if lat is None:
        await message.answer("❌ Не удалось найти такой город.")
        return

    tz = get_timezone(lat, lon)
    users[str(chat_id)] = {"city": city_name, "lat": lat, "lon": lon, "tz": tz}
    save_users()
    register_job(chat_id)

    await message.answer(f"✅ Город изменён на {city_name}. Прогноз будет приходить в 7:00 по времени {tz}")

# ==== Кнопки выбора города ====
popular_cities = ["Moscow", "Saint Petersburg", "Kaliningrad", "Krasnodar"]

@dp.callback_query(lambda c: c.data == "choose_city")
async def choose_city_callback(callback: CallbackQuery):
    city_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=city, callback_data=f"city_{city}")] for city in popular_cities]
    )
    await callback.message.answer("Выберите город:", reply_markup=city_keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("city_"))
async def setcity_callback(callback: CallbackQuery):
    city_name = callback.data.replace("city_", "")
    chat_id = callback.from_user.id

    lat, lon = get_city_coordinates(city_name)
    if lat is None:
        await callback.message.answer("❌ Не удалось найти такой город.")
        await callback.answer()
        return

    tz = get_timezone(lat, lon)
    users[str(chat_id)] = {"city": city_name, "lat": lat, "lon": lon, "tz": tz}
    save_users()
    register_job(chat_id)

    await callback.message.answer(f"✅ Город изменён на {city_name}. Прогноз будет приходить в 7:00 по времени {tz}")
    await send_weather(chat_id)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "update_weather")
async def update_callback(callback: CallbackQuery):
    await send_weather(callback.from_user.id)
    await callback.answer("Обновлено ✅")

# ==== Запуск бота ====
async def main():
    for chat_id in users.keys():
        register_job(int(chat_id))

    scheduler.start()
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

