import asyncio
import logging
import os
from datetime import datetime
from datetime import timezone as dt_timezone
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp


def get_kp_description(kp_index: int) -> str:
    """Возвращает описание Kp-индекса (магнитного поля)."""
    if kp_index <= 1:
        return f"K-индекс {kp_index} (Спокойное 😌)"
    elif kp_index == 2:
        return f"K-индекс {kp_index} (Слабо возмущенное 😐)"
    elif kp_index == 3:
        return f"K-индекс {kp_index} (Нестабильное 😕)"
    elif kp_index == 4:
        return f"K-индекс {kp_index} (Возмущенное 😟)"
    elif kp_index == 5:
        return f"K-индекс {kp_index} (Слабая буря G1 🌩️)"
    elif kp_index == 6:
        return f"K-индекс {kp_index} (Средняя буря G2 ⛈️)"
    elif kp_index == 7:
        return f"K-индекс {kp_index} (Сильная буря G3 ⚡)"
    elif kp_index == 8:
        return f"K-индекс {kp_index} (Очень сильная буря G4 🔥)"
    else:
        return f"K-индекс {kp_index} (Экстремальная буря G5 🌋)"


def get_moon_translation(moon_phase_en: str) -> str:
    """Переводит фазу луны с английского и добавляет эмодзи."""
    phases = {
        "New Moon": "Новолуние 🌑",
        "Waxing Crescent": "Растущий серп 🌒",
        "First Quarter": "Первая четверть 🌓",
        "Waxing Gibbous": "Растущая Луна 🌔",
        "Full Moon": "Полнолуние 🌕",
        "Waning Gibbous": "Убывающая Луна 🌖",
        "Last Quarter": "Последняя четверть 🌗",
        "Waning Crescent": "Убывающий серп 🌘",
    }
    return phases.get(moon_phase_en, moon_phase_en)


async def fetch_owm_weather(session, city, api_key):
    """Получает ТЕКУЩУЮ погоду с OpenWeatherMap."""
    url = (
        "http://api.openweathermap.org/data/2.5/"
        f"weather?q={city}&appid={api_key}&units=metric&lang=ru"
    )
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            logging.warning(f"OWM Weather API error: {response.status}")
    except Exception as e:
        logging.error(f"OWM weather fetch error: {e}")
    return None


async def fetch_owm_forecast(session, city, api_key):
    """Получает ПРОГНОЗ погоды с OpenWeatherMap."""
    url = (
        "http://api.openweathermap.org/data/2.5/"
        f"forecast?q={city}&appid={api_key}&units=metric&lang=ru"
    )
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            logging.warning(f"OWM Forecast API error: {response.status}")
    except Exception as e:
        logging.error(f"OWM forecast fetch error: {e}")
    return None


async def fetch_mag_data(session):
    """Получает Kp-индекс (магнитное поле) с NOAA."""
    url = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            logging.warning(f"NOAA Mag API error: {response.status}")
    except Exception as e:
        logging.error(f"NOAA mag fetch error: {e}")
    return None


async def fetch_moon_data(session, city):
    """Получает фазу Луны с wttr.in."""
    url = f"https://wttr.in/{city}?format=j1"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            logging.warning(f"Moon API (wttr.in) error: {response.status}")
    except Exception as e:
        logging.error(f"Moon fetch error: {e}")
    return None


def parse_current_weather(data):
    """Парсит 'сырой' JSON от OWM Weather."""
    if not data or data["cod"] != 200:
        return None

    try:
        def get_wind_direction(deg):
            directions = [
                "северный", "северо-восточный", "восточный",
                "юго-восточный", "южный", "юго-западный",
                "западный", "северо-западный"
            ]
            index = round((deg % 360) / 45) % 8
            return directions[index]
        weather_emoji = {
            "дождь": "🌧️", "небольшой дождь": "🌧️", "снег": "❄️",
            "сильный снегопад": "🌨️", "небольшой снег": "🌨️",
            "ясно": "☀️", "облачно": "☁️", "переменная облачность": "☁️",
            "небольшая облачность": "⛅", "облачно с прояснениями": "⛅",
            "пасмурно": "🌥️", "небольшая морось": "🌧️",
            "плотный туман": "🌫️", "туман": "🌫️", "гроза": "⛈️",
            "ветер": "💨",
        }

        if "grnd_level" in data["main"]:
            pressure_hpa = data["main"]["grnd_level"]
        else:
            pressure_hpa = data["main"]["pressure"]
            logging.warning("Нет данных о давлении \"grnd_level\". "
                            + "Возвращаемся к значению \"давление\""
                            + "(уровень моря).")
        pressure_mmhg = pressure_hpa * 0.750062
        description = data["weather"][0]["description"]

        if pressure_mmhg < 735:
            pressure_status = "Низкое (Критическое) 📉"
        elif pressure_mmhg < 740:
            pressure_status = "Пониженное 😕"
        elif 745.5 <= pressure_mmhg <= 746.5:
            pressure_status = "Идеальное ✨"
        elif pressure_mmhg <= 755:
            pressure_status = "Нормальное ✅"
        elif pressure_mmhg <= 760:
            pressure_status = "Повышенное 😕"
        else:
            pressure_status = "Высокое (Критическое) 📈"

        return {
            "temp": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "pressure_mmhg": pressure_mmhg,
            "pressure_status": pressure_status,
            "humidity": data["main"]["humidity"],
            "description": description.capitalize(),
            "clouds": data["clouds"]["all"],
            "wind_speed": data["wind"]["speed"],
            "wind_gust": data["wind"].get("gust", 0),
            "wind_direction": get_wind_direction(data["wind"].get("deg", 0)),
            "sunrise": datetime.fromtimestamp(
                data["sys"]["sunrise"]).strftime("%H:%M"),
            "sunset": datetime.fromtimestamp(
                data["sys"]["sunset"]).strftime("%H:%M"),
            "emoji": weather_emoji.get(description.lower(), "❓"),
        }
    except Exception as e:
        logging.error(f"Error parsing OWM weather: {e}")
        return None


def parse_forecast(data):
    """Парсит 'сырой' JSON от OWM Forecast."""
    if not data or data["cod"] != "200":
        return None

    try:
        moscow_tz = ZoneInfo("Europe/Moscow")
        current_date = datetime.now(moscow_tz).date()
        forecast: dict[str, Any] = {"morning": None,
                                    "day": None, "evening": None}

        for entry in data["list"]:
            entry_time_utc = datetime.fromtimestamp(
                entry["dt"], tz=dt_timezone.utc)
            entry_time_moscow = entry_time_utc.astimezone(moscow_tz)
            if entry_time_moscow.date() == current_date:
                time_str = entry_time_moscow.strftime("%H:%M")
                desc = entry["weather"][0]["description"]
                temp = entry["main"]["temp"]

                if time_str == "09:00":
                    forecast["morning"] = {"temp": temp, "desc": desc}
                elif time_str == "15:00":
                    forecast["day"] = {"temp": temp, "desc": desc}
                elif time_str == "21:00":
                    forecast["evening"] = {"temp": temp, "desc": desc}
        return forecast
    except Exception as e:
        logging.error(f"Error parsing OWM forecast: {e}")
        return None


def parse_mag_data(data):
    """Парсит 'сырой' JSON от NOAA."""
    if not data:
        return None
    try:
        latest_entry = data[-1]
        kp_index = latest_entry["kp_index"]
        return {"status": get_kp_description(kp_index)}
    except Exception as e:
        logging.warning(f"Mag parse error: {e}. Data received: {data}")
        return None


def parse_moon_data(data):
    """Парсит 'сырой' JSON от wttr.in."""
    if not data:
        return None
    try:
        moon_phase_en = data["weather"][0]["astronomy"][0]["moon_phase"]
        return {"phase": get_moon_translation(moon_phase_en)}
    except Exception as e:
        logging.warning(f"Moon parse error: {e}")
        return None


def format_weather_message(city_ru, weather_data,
                           forecast_data, mag_data, moon_data):
    """Собирает финальное HTML-сообщение из обработанных данных."""

    if not weather_data:
        return "🚨 Не удалось получить данные о погоде."

    lines = [
        f"<b>🏙️ Погода в {city_ru}:</b> "
        f"{weather_data['emoji']} {weather_data['description']}\n",
        "<b>🌡 Основные параметры:</b>",
        f"- Температура: {weather_data['temp']:.1f}°C",
        f"- Ощущается как: {weather_data['feels_like']:.1f}°C",
        f"- Облачность: {weather_data['clouds']}%",
        f"- Ветер: {weather_data['wind_speed']:.1f} м/с,"
        f" {weather_data['wind_direction']}",
        f"- Порывы: {weather_data['wind_gust']:.1f} м/с",
        f"- Давление: {weather_data['pressure_mmhg']:.1f} мм рт.ст."
        f" ({weather_data['pressure_status']})",
        f"- Влажность: {weather_data['humidity']}%\n",
    ]

    moon_status = moon_data["phase"] if moon_data else "нет данных"
    mag_status = mag_data["status"] if mag_data else "нет данных"
    lines.extend([
        "<b>🌌 Астро-обстановка:</b>",
        f"- 🌕 Луна: {moon_status}",
        f"- 📡 Магн. поле: {mag_status}\n",
    ])

    lines.extend([
        f"<b>⏳ Длина дня в {city_ru}:</b>",
        f"- 🌅 Восход: {weather_data['sunrise']}",
        f"- 🌇 Закат: {weather_data['sunset']}\n",
    ])

    lines.append("<b>🔮 Прогноз на сегодня:</b>")
    if forecast_data:
        weather_emoji_map = {
            "дождь": "🌧️", "небольшой дождь": "🌧️", "снег": "❄️",
            "сильный снегопад": "🌨️", "небольшой снег": "🌨️",
            "ясно": "☀️", "облачно": "☁️", "переменная облачность": "☁️",
            "небольшая облачность": "⛅", "облачно с прояснениями": "⛅",
            "пасмурно": "🌥️", "небольшая морось": "🌧️",
            "плотный туман": "🌫️", "туман": "🌫️", "гроза": "⛈️",
            "ветер": "💨",
        }

        for time_name, data in [("Утром", forecast_data['morning']),
                                ("Днём", forecast_data['day']),
                                ("Вечером", forecast_data['evening'])]:
            if data:
                emoji = weather_emoji_map.get(data['desc'].lower(), "❓")
                lines.append(
                    f"<b>{emoji} {time_name}:</b> "
                    f"{data['temp']:.1f}°C ({data['desc']})"
                )
            else:
                lines.append(f"<b>❓ {time_name}:</b> нет данных")
    else:
        lines.append("<i>Прогноз недоступен</i>")

    lines.append("\n<i>По данным openweathermap.org, "
                 "swpc.noaa.gov, wttr.in</i>")
    return "\n".join(lines)


async def get_weather():
    """
    Асинхронно получает, парсит и форматирует
    все погодные данные параллельно.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")
    city = "Zelenograd"
    city_ru = "Зеленограде"

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(
            fetch_owm_weather(session, city, api_key),
            fetch_owm_forecast(session, city, api_key),
            fetch_mag_data(session),
            fetch_moon_data(session, city)
        )
        owm_weather_raw, owm_forecast_raw, mag_raw, moon_raw = results
        weather_data = parse_current_weather(owm_weather_raw)
        forecast_data = parse_forecast(owm_forecast_raw)
        mag_data = parse_mag_data(mag_raw)
        moon_data = parse_moon_data(moon_raw)
        return format_weather_message(
            city_ru,
            weather_data,
            forecast_data,
            mag_data,
            moon_data
        )
