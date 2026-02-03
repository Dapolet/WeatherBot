import os
import json
import datetime
import asyncio
import pytz
import logging

from babel.dates import format_datetime

def format_date(dt, format_str="d MMMM", locale="ru_RU"):
    """Formats datetime into a readable string"""
    return format_datetime(dt, format_str, locale=locale)

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from geopy.geocoders import Nominatim
from timezonefinderL import TimezoneFinder

from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile, Location, ReplyKeyboardRemove
from aiogram.filters import Command

from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ==== Configuration ====
logging.basicConfig(level=logging.INFO)
API_TOKEN = "API"
DEFAULT_CITY = "Moscow"
DEFAULT_LAT, DEFAULT_LON = 55.75, 37.61
USERS_FILE = "users.json"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()
geolocator = Nominatim(user_agent="WeatherBot")
tf = TimezoneFinder()

# ==== JSON Handling ====
def load_users():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Failed to load users from {USERS_FILE}: {e}")
        return {}


def save_users():
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Failed to save users to {USERS_FILE}: {e}")

users = load_users()

# ==== Geo-coordinate Lookup ====
def get_city_coordinates(city_name):
    try:
        location = geolocator.geocode(city_name, timeout=10)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        logging.error(f"Failed to fetch city coordinates for {city_name}: {e}")
    return None, None

# ==== Timezone Retrieval ====
def get_timezone(lat, lon):
    try:
        tz_name = tf.timezone_at(lat=lat, lng=lon)
        return tz_name if tz_name else "Europe/Moscow"
    except Exception as e:
        logging.error(f"Failed to determine timezone for coordinates ({lat}, {lon}): {e}")
        return "Europe/Moscow"

# ==== Weather Data ==== (with caching)
import aiohttp
import time

weather_cache = {}
CACHE_TTL = 600  # 10 minutes

async def get_weather(lat, lon, tz_name="Europe/Moscow"):
    try:
        cache_key = (round(lat, 2), round(lon, 2))
        now = time.time()

        # Check Cache
        if cache_key in weather_cache:
            cached = weather_cache[cache_key]
            if now - cached["time"] < CACHE_TTL:
                return cached["data"]
            else:
                del weather_cache[cache_key]

        # Fetch Weather Data
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
                if resp.status != 200:
                    logging.error(f"Weather API returned status code {resp.status}")
                    return None
                response = await resp.json()
                weather_cache[cache_key] = {"time": now, "data": response}
                return response

    except aiohttp.ClientError as e:
        logging.error(f"Failed to fetch weather data: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in fetching weather data: {e}")

    return None

# Additional functions/classes remain the same; error handling propagated as shown above.

if __name__ == "__main__":
    logging.info("Starting Bot")
    asyncio.run(main())