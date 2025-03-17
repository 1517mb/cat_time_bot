import logging
import os
import re
import traceback
from datetime import datetime, timedelta
from difflib import get_close_matches
from zoneinfo import ZoneInfo

import aiohttp
import telegram
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Avg, F
from django.utils import timezone
from dotenv import load_dotenv
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.management.core.bot_constants import SiteCfg
from bot.management.core.statistics import (
    get_daily_statistics_message,
    update_daily_statistics,
)
from bot.models import Achievement, Company, DailytTips, UserActivity

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

JOIN_CO, SELECT_CO = range(2)

VALID_COMPANY_NAME_PATTERN = re.compile(r"^[А-Яа-яA-Za-z0-9\s\-]+$")


scheduler = AsyncIOScheduler(timezone=ZoneInfo("Europe/Moscow"))


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда для отображения списка доступных команд.
    """

    help_text = (
        "😺👋 Привет! Вот список доступных команд:\n"
        "\n"
        "*Основные команды:*\n"
        "/help - Показать это сообщение с инструкциями.\n"
        "/site - Информация о нашем сайте\n"
        "/join <Организация> - Прибыть к указанной организации.\n"
        "/leave - Покинуть текущую организацию и записать затраченное время.\n"
        "/edit\\_start <ЧЧ:ММ> - Изменить время прибытия "
        "в текущую организацию."
        "\n"
        "/edit\\_end <ЧЧ:ММ> - Изменить время убытия из текущей организации.\n"
        "\n"
        "*Планировщик:*\n"
        "/start\\_weather <ЧЧ:ММ> - Установить время отправки погоды\n"
        "/start\\_stats <ЧЧ:ММ> - Установить время отправки статистики\n"
        "/start\\_reminder <ЧЧ:ММ> - Установить время напоминаний\n"
        "/start\\_dailytips <ЧЧ:ММ> - Запустить ежедневные советы\n"
        "/stop\\_dailytips - Остановить рассылку советов\n"
        "/stop\\_scheduler - Остановить все задания\n"
        "\n"
        "*Дополнительно:*\n"
        "/mew - Получить фото кота\n"
        "/get\\_chat\\_info - Информация о чате"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def site(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет информацию о сайте"""
    site_info = SiteCfg.MSG_SITE
    await update.message.reply_text(site_info, parse_mode="Markdown")


async def check_achievements(
    user_id: int,
    username: str,
    activity: UserActivity,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Проверка и выдача достижений с
    оптимизированными запросами и логированием"""
    try:
        today = timezone.now().date()
        join_time = activity.join_time
        leave_time = activity.leave_time
        duration = (leave_time - join_time).total_seconds()
        new_achievements = []

        user_stats = await sync_to_async(
            lambda: {
                "company_visits": UserActivity.objects.filter(
                    user_id=user_id,
                    company=activity.company
                ).count(),

                "same_day_users": UserActivity.objects.filter(
                    company=activity.company,
                    join_time__date=join_time.date()
                ).values("user_id").distinct().count(),


                "today_trips": UserActivity.objects.filter(
                    user_id=user_id,
                    join_time__date=today
                ).count(),


                "weekly_trips": UserActivity.objects.filter(
                    user_id=user_id,
                    join_time__gte=today - timedelta(days=today.weekday())
                ).count(),


                "avg_duration": UserActivity.objects.filter(
                    user_id=user_id).annotate(
                        duration=F(
                            "leave_time") - F("join_time")).aggregate(
                                avg=Avg("duration"))["avg"]
            }
        )()

        if user_stats["company_visits"] == 1:
            new_achievements.append("🏕️ Я здесь впервые, правда же?")

        if user_stats["same_day_users"] >= 2:
            new_achievements.append("👥 Командный игрок")

        if user_stats["today_trips"] > 3:
            new_achievements.append("🔁 А можно мне ещё выезд?")

        if user_stats["weekly_trips"] > 16:
            new_achievements.append("🏆 Лучший сотрудник")

        weekday = join_time.weekday()
        if weekday in [5, 6]:
            day_name = "субботу" if weekday == 5 else "воскресенье"
            new_achievements.append(
                f"📅 Я люблю свою работу, я приду сюда в {day_name}")

        duration_achievements = {
            (0, 300): None,
            (300, 1200): "🚀 Экспресс-админ",
            (1200, 1800): "⏱️ Справлюсь с этим за полчаса",
            (1800, 3660): None,
            (3660, 7200): "🐢 Король промедления",
            (7200, 10800): None,
            (10800, 14400): "🛠️ Делаю, делаю, по три раза переделаю",
        }

        for (min_val, max_val), achievement in duration_achievements.items():
            if min_val <= duration < max_val and achievement:
                new_achievements.append(achievement)

        if (user_stats["avg_duration"] and user_stats[
                "avg_duration"].total_seconds() > 9000):
            new_achievements.append("🐢 Поспешишь - людей насмешишь")

        edit_achievements = {
            (1, 3): None,
            (3, 5): "🕰️ Читер: Часовщик II уровня",
            (5, float('inf')): "🕰️ Читер: Часовщик III уровня"
        }

        if activity.edited:
            new_achievements.append("🕵️♂️ Читер: Часовщик")
            for (min_edit, max_edit), achievement in edit_achievements.items():
                if min_edit <= activity.edit_count < max_edit and achievement:
                    new_achievements.append(achievement)

        if new_achievements:
            achievements_count = {}
            for ach in new_achievements:
                if ach in achievements_count:
                    achievements_count[ach] += 1
                else:
                    achievements_count[ach] = 1

            formatted_achievements = []
            for ach, count in achievements_count.items():
                if count > 1:
                    formatted_achievements.append(f"• {ach} x{count}")
                else:
                    formatted_achievements.append(f"• {ach}")

            achievements_to_create = [
                Achievement(
                    user_id=user_id,
                    username=username,
                    achievement_name=(
                        ach.split(" ", 1)[1] if " " in ach else ach)
                ) for ach in new_achievements
            ]

        await sync_to_async(
            Achievement.objects.bulk_create)(achievements_to_create)

        group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
        formatted_achievements_text = "\n".join(formatted_achievements)
        await context.bot.send_message(
            chat_id=group_chat_id,
            text=(
                "🏆 *Новое достижение!*\n"
                f"Сотрудник: @{username}\n"
                f"Заслуги:\n{formatted_achievements_text}\n"
                "Поздравляем! 🎉"
            ),
            parse_mode="Markdown"
        )

    except Exception as e:
        logging.error(
            f"Ошибка при проверке достижений для {username}: {str(e)}\n"
            f"Детали: {traceback.format_exc()}",
            exc_info=True
        )


async def get_chat_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    try:
        chat = await context.bot.get_chat(chat_id)
        try:
            member_count = await chat.get_member_count()
        except Exception:
            member_count = (
                "Недоступно (группа приватная или бот не имеет доступа)")
        chat_info = f"""
🔍 Информация о чате:
- ID: {chat.id}
- Название: {chat.title}
- Тип: {chat.type}
- Количество участников: {member_count}
- Описание: {chat.description if chat.description else "Нет описания"}
- Ссылка: {chat.invite_link if chat.invite_link else "Недоступна"}
        """
        await update.message.reply_text(chat_info)
    except Exception as e:
        await update.message.reply_text(
            f"🚨 *Ошибка при получении информации о чате:* {e}",
            parse_mode="Markdown")


async def get_weather():
    """Асинхронная функция для получения погоды."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    city = "Zelenograd"
    city_ru = "Зеленограде"
    url = ("http://api.openweathermap.org/data/2.5/"
           + f"weather?q={city}&appid={api_key}&units=metric&lang=ru")

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if data["cod"] == 200:
                temp = data["main"]["temp"]
                feels_like = data["main"]["feels_like"]
                pressure_hpa = data["main"]["pressure"]
                pressure_mmhg = pressure_hpa * 0.750062
                humidity = data["main"]["humidity"]
                description = data["weather"][0]["description"]
                clouds = data["clouds"]["all"]
                wind_speed = data["wind"]["speed"]
                wind_gust = data["wind"].get("gust", 0)
                wind_deg = data["wind"].get("deg", 0)

                def get_wind_direction(deg):
                    """
                    Определяет направление ветра по заданному углу.

                    :param deg: Угол направления ветра.
                    :return: Строка, представляющая кардинальное направление
                    ветра.
                    """

                    directions = [
                        "северный", "северо-восточный", "восточный",
                        "юго-восточный", "южный", "юго-западный",
                        "западный", "северо-западный"
                    ]
                    index = round((deg % 360) / 45) % 8
                    return directions[index]

                wind_direction = get_wind_direction(wind_deg)

                sunrise = datetime.fromtimestamp(
                    data["sys"]["sunrise"]).strftime("%H:%M")
                sunset = datetime.fromtimestamp(
                    data["sys"]["sunset"]).strftime("%H:%M")

                forecast_url = ("http://api.openweathermap.org/data/2.5/"
                                + f"forecast?q={city}&appid={api_key}&"
                                + "units=metric&lang=ru")
                async with session.get(forecast_url) as forecast_response:
                    forecast_data = await forecast_response.json()
                    if forecast_data["cod"] == "200":
                        current_date = datetime.now().date()

                        morning_temp = None

                        day_temp = None
                        evening_temp = None

                        for entry in forecast_data["list"]:
                            entry_time = datetime.fromtimestamp(entry["dt"])
                            if entry_time.date() == current_date:
                                time = entry_time.strftime("%H:%M")
                                if time == "09:00":
                                    morning_temp = entry["main"]["temp"]
                                elif time == "15:00":
                                    day_temp = entry["main"]["temp"]
                                elif time == "21:00":
                                    evening_temp = entry["main"]["temp"]

                        forecast_temp_message = (
                            f"🌅 Утром: {morning_temp}°C\n"
                            f"🌞 Днём: {day_temp}°C\n"
                            f"🌇 Вечером: {evening_temp}°C"
                        )
                    else:
                        forecast_temp_message = (
                            "🚨 Не удалось получить прогноз температуры. 🚨")

                weather_emoji = {
                    "дождь": "🌧️",
                    "снег": "❄️",
                    "сильный снегопад": "🌨️",
                    "небольшой снег": "🌨️",
                    "ясно": "☀️",
                    "облачно": "☁️",
                    "облачно с прояснениями": "⛅",
                    "пасмурно": "🌥️",
                    "небольшая морось": "🌧️",
                    "плотный туман": "🌫️",
                    "туман": "🌫️",
                    "гроза": "⛈️",
                    "ветер": "💨",
                }

                emoji = weather_emoji.get(description.lower(), "❓")

                weather_message = (
                    f"Погода в {city_ru}:\n"
                    f"{emoji} {description}\n"
                    f"🌡 Температура: {temp}°C, ощущается как {feels_like}°C\n"
                    f"🌥 Облачность: {clouds}%\n"
                    f"💨 Скорость ветра: {wind_speed} м/с, {wind_direction}\n"
                    f"🌬 Порывы ветра: {wind_gust} м/с\n"
                    f"📊 Давление: {pressure_mmhg:.1f} мм рт. ст.\n"
                    f"💧 Влажность: {humidity}%\n"
                    f"\n"
                    f"Длина дня в {city_ru}:\n"
                    f"🌅 Восход: {sunrise}\n"
                    f"🌇 Закат: {sunset}\n"
                    f"\n"
                    f"Прогноз температуры на сегодня:\n"
                    f"{forecast_temp_message}\n"
                    f"\n"
                    f"** По данным openweathermap.org"
                )
                return weather_message
            else:
                return "🚨 Не удалось получить погоду. 🚨"


async def send_weather_to_group(bot):
    """Асинхронная функция для отправки погоды в группу."""
    try:
        weather_message = await get_weather()
        group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
        await bot.send_message(chat_id=group_chat_id, text=weather_message)
    except Exception as e:
        logging.error(f"Ошибка при отправке погоды: {e}")
        await bot.send_message(
            chat_id=group_chat_id, text="🚨 Не удалось отправить погоду. 🚨"
        )


async def stop_scheduler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка планировщика."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        await update.message.reply_text("🛑 Планировщик погоды остановлен. 🌧️")
    else:
        await update.message.reply_text("🚦 Планировщик уже остановлен. 🚦")


async def get_similar_companies(company_name):
    """
    Searches for companies with names similar to the given company_name
    and returns a list of the closest matches (up to 2 matches with a
    similarity cutoff of 0.6).

    :param company_name: The company name to search for.
    :return: A list of strings of the closest company name matches.
    """
    similar_companies = await sync_to_async(list)(
        Company.objects.filter(name__icontains=company_name).values_list(
            "name", flat=True)
    )
    return get_close_matches(company_name, similar_companies, n=2, cutoff=0.6)


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    company_name = " ".join(context.args)

    if not company_name:
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Пожалуйста, укажите название организации после команды /join.",
            parse_mode="Markdown")
        return ConversationHandler.END

    if not VALID_COMPANY_NAME_PATTERN.match(company_name):
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Название организации должно содержать только"
            + " буквы русского или английского алфавита, цифры и тире.",
            parse_mode="Markdown")
        return ConversationHandler.END

    active_activity = await sync_to_async(UserActivity.objects.filter(
        user_id=user_id, leave_time__isnull=True).exists)()

    if active_activity:
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Вы ещё не покинули предыдущую организацию.",
            parse_mode="Markdown")
        return ConversationHandler.END

    try:
        company = await sync_to_async(
            Company.objects.filter(name=company_name).first)()
        if company:
            local_time = timezone.localtime(timezone.now())
            await update.message.reply_text(
                f"🐱‍💻 *Вы прибыли в организацию {company_name}* 🐱‍💻\n"
                f"Время прибытия: {local_time.strftime('%H:%M')}.",
                parse_mode="Markdown"
            )
            await sync_to_async(UserActivity.objects.create)(
                user_id=user_id,
                username=username,
                company=company
            )

            today = timezone.now().date()
            total_today = await sync_to_async(
                UserActivity.objects.filter(join_time__date=today).count
            )()
            if total_today == 1:
                achievement = Achievement(
                    user_id=user_id,
                    username=username,
                    achievement_name="🩸 Первая кровь"
                )
                await sync_to_async(achievement.save)()
                group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
                await context.bot.send_message(
                    chat_id=group_chat_id,
                    text=(
                        "🏆 *Новое достижение!*\n"
                        f"Сотрудник: @{username}\n"
                        f"Заслуги: 🩸 Первая кровь!\n"
                        "Поздравляем! 🎉"
                    ),
                    parse_mode="Markdown"
                )

            return ConversationHandler.END
        else:
            similar_companies = await get_similar_companies(company_name)
            if similar_companies:
                similar_companies_text = "\n".join(
                    [f"{i + 1}. {company}" for i, company in enumerate(
                        similar_companies)])
                reply_keyboard = [
                    [KeyboardButton(company)] for company in similar_companies
                ] + [[KeyboardButton("Добавить новую организацию")]]
                await update.message.reply_text(
                    f"🚨 *Организации с названием \"{company_name}\" "
                    + "не найдено.* 🚨\n"
                    f"Возможно, вы имели в виду:\n{similar_companies_text}\n"
                    "Выберите из списка или добавьте новую организацию.",
                    parse_mode="Markdown",
                    reply_markup=ReplyKeyboardMarkup(
                        reply_keyboard, one_time_keyboard=True)
                )
                return SELECT_CO
            else:
                company, created = await sync_to_async(
                    Company.objects.get_or_create)(name=company_name)
                local_time = timezone.localtime(timezone.now())
                await update.message.reply_text(
                    f"🐱‍💻 *Вы прибыли в организацию {company_name}* 🐱‍💻\n"
                    f"Время прибытия: {local_time.strftime('%H:%M')}.",
                    parse_mode="Markdown"
                )
                await sync_to_async(UserActivity.objects.create)(
                    user_id=user_id,
                    username=username,
                    company=company
                )

                today = timezone.now().date()
                total_today = await sync_to_async(
                    UserActivity.objects.filter(join_time__date=today).count
                )()
                if total_today == 1:
                    achievement = Achievement(
                        user_id=user_id,
                        username=username,
                        achievement_name="🩸 Первая кровь"
                    )
                    await sync_to_async(achievement.save)()
                    group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
                    await context.bot.send_message(
                        chat_id=group_chat_id,
                        text=(
                            "🏆 *Новое достижение!*\n"
                            f"Сотрудник: @{username}\n"
                            f"Заслуги: 🩸 Первая кровь!\n"
                            "Поздравляем! 🎉"
                        ),
                        parse_mode="Markdown"
                    )

                return ConversationHandler.END
    except Exception:
        await update.message.reply_text(
            "🚨 *Произошла ошибка при поиске или создании организации.* 🚨",
            parse_mode="Markdown"
        )
        return ConversationHandler.END


async def select_company(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Callback для выбора существующей организации.

    Пользователь может выбрать организацию из списка предложенных
    или добавить новую. Если пользователь выбрал существующую
    организацию, то он будет зарегистрирован в ней, иначе
    он будет предложен ввести название новой организации.

    :param update: update от Telegram
    :param context: context от Telegram
    :return: следующий шаг в ConversationHandler
    """
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    selected_company = update.message.text

    if not VALID_COMPANY_NAME_PATTERN.match(selected_company):
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Название организации должно содержать только"
            + " буквы русского алфавита и цифры.",
            parse_mode="Markdown")
        return ConversationHandler.END

    if selected_company == "Добавить новую организацию":
        await update.message.reply_text(
            "🐾 *Пожалуйста, введите название новой организации.* 🐾"
        )
        return JOIN_CO

    active_activity = await sync_to_async(UserActivity.objects.filter(
        user_id=user_id, leave_time__isnull=True).exists)()

    if active_activity:
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Вы ещё не покинули предыдущую организацию.",
            parse_mode="Markdown")
        return ConversationHandler.END

    company, created = await sync_to_async(
        Company.objects.get_or_create)(name=selected_company)
    local_time = timezone.localtime(timezone.now())
    await update.message.reply_text(
        f"🐱‍💻 *Вы прибыли в организацию {selected_company}* 🐱‍💻\n"
        f"Время прибытия: {local_time.strftime('%H:%M')}.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    await sync_to_async(UserActivity.objects.create)(
        user_id=user_id,
        username=username,
        company=company
    )
    return ConversationHandler.END


async def _validate_and_update_time(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    time_field: str,
    error_message_prefix: str,
    success_message: str,
) -> None:
    """
    Вспомогательная функция для валидации и обновления времени.
    """
    user_id = update.message.from_user.id

    active_activity = await sync_to_async(
        UserActivity.objects.filter(
            user_id=user_id,
            leave_time__isnull=True
        ).select_related('company').first
    )()

    if not active_activity:
        await update.message.reply_text(
            f"🚨 *Ошибка!* 🚨\n"
            f"У вас нет активной организации, для "
            f"которой можно изменить {error_message_prefix}.",
            parse_mode="Markdown"
        )
        return

    args = context.args
    if not args or len(args) != 1:
        await update.message.reply_text(
            f"🚨 *Ошибка!* 🚨\n"
            f"⭕️ *Внимание! Неверный формат ввода*\n\n"
            f"🕒 Пожалуйста, укажите {error_message_prefix} "
            f"время в формате *ЧЧ:ММ*\n"
            f"Пример: *14:30*\n\n"
            f"📖 Для получения дополнительной информации "
            f"используйте команду /help",
            parse_mode="Markdown"
        )
        return

    try:
        new_time = datetime.strptime(args[0], '%H:%M').time()
    except ValueError:
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Неверный формат времени. Пожалуйста, "
            "укажите время в формате *ЧЧ:ММ* (например, 09:15).",
            parse_mode="Markdown"
        )
        return

    current_time = timezone.localtime(timezone.now()).time()
    if new_time > current_time:
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Вы не можете выбрать время, которое больше текущего. "
            "Пожалуйста, укажите время, которое меньше или равно текущему.",
            parse_mode="Markdown"
        )
        return

    today = timezone.now().date()
    new_datetime = timezone.make_aware(datetime.combine(today, new_time))

    if time_field == "leave_time" and new_datetime < active_activity.join_time:
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Время убытия не может быть раньше времени прибытия. "
            "Ваше время прибытия: "
            f"{active_activity.join_time.strftime('%H:%M')}.",
            parse_mode="Markdown"
        )
        return

    if (time_field == "join_time"
        and active_activity.leave_time
            and new_datetime > active_activity.leave_time):
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Время прибытия не может быть позже времени убытия. "
            "Ваше время убытия: "
            f"{active_activity.leave_time.strftime('%H:%M')}.",
            parse_mode="Markdown"
        )
        return

    setattr(active_activity, time_field, new_datetime)
    active_activity.edited = True
    active_activity.edit_count += 1
    await sync_to_async(active_activity.save)()

    company_name = active_activity.company.name
    local_time = timezone.localtime(new_datetime).strftime('%H:%M')

    await update.message.reply_text(
        f"😻 *Успешно!* 😻\n"
        f"{success_message.format(
            company_name=company_name, time=local_time)}.",
        parse_mode="Markdown"
    )


async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Устаревшая команда для редактирования времени.
    Информирует пользователя о новых командах.
    """
    message = (
        "ℹ️ *Команда /edit устарела в версии 0.5.*\n\n"
        "Используйте вместо этого:\n"
        "/edit\\_start <ЧЧ:ММ> - Изменить время прибытия "
        "в текущую организацию.\n"
        "/edit\\_end <ЧЧ:ММ> - Изменить время убытия из текущей организации."
    )
    await update.message.reply_text(message, parse_mode="Markdown")


async def edit_arrival_time(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда для изменения времени прибытия в организацию.
    """
    await _validate_and_update_time(
        update,
        context,
        time_field="join_time",
        error_message_prefix="время прибытия",
        success_message=("Время прибытия в организацию {company_name} "
                         "успешно изменено на {time}"),
    )

    user_id = update.message.from_user.id
    username = update.message.from_user.username
    await update_daily_statistics(user_id, username)


async def edit_departure_time(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда для изменения времени убытия из организации.
    """
    await _validate_and_update_time(
        update,
        context,
        time_field="leave_time",
        error_message_prefix="время убытия",
        success_message=("Время убытия из организации {company_name} "
                         "успешно изменено на {time}"),
    )

    user_id = update.message.from_user.id
    username = update.message.from_user.username
    await update_daily_statistics(user_id, username)


async def add_new_company(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Callback для добавления новой организации.

    Пользователь может ввести название новой организации,
    и если оно не существует, то она будет создана,
    иначе - будет предложено выбрать существующую
    организацию.

    :param update: update от Telegram
    :param context: context от Telegram
    :return: следующий шаг в ConversationHandler
    """
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    company_name = update.message.text

    active_activity = await sync_to_async(UserActivity.objects.filter(
        user_id=user_id, leave_time__isnull=True).exists)()

    if active_activity:
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Вы ещё не покинули предыдущую организацию.",
            parse_mode="Markdown")
        return ConversationHandler.END

    if not VALID_COMPANY_NAME_PATTERN.match(company_name):
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Название организации должно содержать только"
            + " буквы русского или английского алфавита и цифры",
            parse_mode="Markdown")
        return ConversationHandler.END
    local_time = timezone.localtime(timezone.now())
    company, created = await sync_to_async(
        Company.objects.get_or_create)(name=company_name)
    await update.message.reply_text(
        f"🐱‍💻 *Вы прибыли к новой организации {company_name}* 🐱‍💻\n"
        f"Время прибытия: {local_time.strftime('%H:%M')}.\n ",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    await sync_to_async(UserActivity.objects.create)(
        user_id=user_id,
        username=username,
        company=company
    )
    return ConversationHandler.END


async def leave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Callback для ухода из организации.

    Если пользователь отправит команду /leave,
    то он покинет организацию, к которой он
    прибыл, и будет отображено затраченное время.

    :param update: update от Telegram
    :param context: context от Telegram
    :return: None
    """

    user_id = update.message.from_user.id
    username = update.message.from_user.username
    try:
        activity = await sync_to_async(UserActivity.objects.select_related(
            "company").filter(
                user_id=user_id,
                leave_time__isnull=True).latest)("join_time")

        activity.leave_time = timezone.now()
        await sync_to_async(activity.save)()

        await check_achievements(user_id, username, activity, context)

        await update_daily_statistics(user_id, username)

        company_name = activity.company.name
        spent_time = activity.get_spent_time
        local_time = timezone.localtime(timezone.now())

        await update.message.reply_text(
            f"🐾👋 *Вы покинули организацию {company_name}* 🐾👋\n"
            f"Время ухода: {local_time.strftime('%H:%M')}.\n"
            f"Затраченное время: {spent_time}.",
            parse_mode="Markdown"
        )

    except UserActivity.DoesNotExist:
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Вы не прибыли ни к одной организации.", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка при выполнении команды /leave: {e}")
        await update.message.reply_text(
            "🚨 *Произошла ошибка при обработке вашего запроса.* 🚨",
            parse_mode="Markdown")


async def remind_to_leave(bot):
    """Функция для напоминания пользователям о необходимости
    ввести команду /leave."""
    try:
        group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
        if not group_chat_id:
            logging.error("TELEGRAM_GROUP_CHAT_ID не установлен в .env")
            return
        active_activities = await sync_to_async(
            lambda: list(UserActivity.objects.filter(leave_time__isnull=True))
        )()

        if not active_activities:
            return

        users = []
        for activity in active_activities:
            username = (
                f"@{activity.username}"
                if activity.username
                else f"ID: {activity.user_id}")
            company_name = await sync_to_async(lambda: activity.company.name)()
            users.append(f"{username} ({company_name})")
        message = (
            "⚠️ *Внимание!* ⚠️\n\n"
            "Следующие сотрудники всё ещё находятся в организациях:\n"
            f"{'\n'.join(users)}\n\n"
            "Пожалуйста, выполните:\n"
            "• /leave - чтобы покинуть организацию\n"
            "• /edit\\_start <ЧЧ:ММ> - изменить время прибытия\n"
            "• /edit\\_end <ЧЧ:ММ> - изменить время убытия"
        )
        try:
            await bot.send_message(
                chat_id=group_chat_id,
                text=message,
                parse_mode="Markdown",
                disable_notification=False)
            logging.info(f"Напоминание отправлено в группу {group_chat_id}")
        except telegram.error.BadRequest as e:
            logging.error(f"Ошибка отправки в группу: {e.message}")
            if "chat not found" in str(e).lower():
                logging.critical(
                    "Бот не добавлен в группу или chat_id неверный!")
        except telegram.error.Forbidden as e:
            logging.error(f"Нет прав на отправку: {e.message}")
            if "bot was blocked" in str(e).lower():
                logging.critical("Бот заблокирован в группе!")
        except Exception as e:
            logging.error(f"Неизвестная ошибка: {str(e)}", exc_info=True)

    except Exception as e:
        logging.error(
            f"Критическая ошибка в remind_to_leave: {e}", exc_info=True)


async def mew(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет случайное фото котика."""
    url = "https://api.thecatapi.com/v1/images/search"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    cat_photo_url = data[0]["url"]
                    await update.message.reply_photo(photo=cat_photo_url)
                else:
                    await update.message.reply_text(
                        "😿 Не удалось получить фото котика. 😿")
        except Exception as e:
            logging.error(f"Ошибка при запросе к API котиков: {e}")
            await update.message.reply_text(
                "😿 Произошла ошибка при получении фото котика. 😿")


async def send_daily_statistics_to_group(bot):
    """
    Асинхронно отправляет ежедневное статистическое сообщение
    заранее определенной группе.

    Функция извлекает ежедневное статистическое сообщение и отправляет его в
    групповой чат, указанный в переменной среды TELEGRAM_GROUP_CHAT_ID.
    Сообщение отправляется в формате Markdown.

    :param bot: Экземпляр Telegram-бота, использованный для отправки сообщения.
    """

    message = await get_daily_statistics_message()
    group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
    await bot.send_message(chat_id=group_chat_id,
                           text=message,
                           parse_mode="Markdown")


async def start_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ежедневной отправки погоды в указанное время"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите время в формате ЧЧ:ММ (например: /start_weather 9:30)"
        )
        return

    time_str = context.args[0]
    try:
        hour, minute = map(int, time_str.split(":"))
    except ValueError:
        await update.message.reply_text("❌ Неверный формат времени")
        return

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await update.message.reply_text("❌ Некорректное время")
        return

    try:
        scheduler.remove_job("weather_job")
    except JobLookupError:
        pass

    scheduler.add_job(
        send_weather_to_group,
        trigger="cron",
        hour=hour,
        minute=minute,
        args=[context.bot],
        id="weather_job"
    )

    if not scheduler.running:
        scheduler.start()

    await update.message.reply_text(
        f"⛅ Задание для отправки погоды установлено на {hour:02}:{minute:02}"
    )


async def start_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ежедневной отправки статистики"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите время в формате ЧЧ:ММ (например: /start_stats 20:00)"
        )
        return

    time_str = context.args[0]
    try:
        hour, minute = map(int, time_str.split(':'))
    except ValueError:
        await update.message.reply_text("❌ Неверный формат времени")
        return

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await update.message.reply_text("❌ Некорректное время")
        return

    try:
        scheduler.remove_job("stats_job")
    except JobLookupError:
        pass

    scheduler.add_job(
        send_daily_statistics_to_group,
        trigger="cron",
        hour=hour,
        minute=minute,
        args=[context.bot],
        id="stats_job"
    )

    if not scheduler.running:
        scheduler.start()

    await update.message.reply_text(
        f"📊 Задание для отправки "
        f"статистики установлено на {hour:02}:{minute:02}"
    )


async def start_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск напоминаний о необходимости покинуть организацию"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите время в формате ЧЧ:ММ (например: /start_reminder 19:45)"
        )
        return

    time_str = context.args[0]
    try:
        hour, minute = map(int, time_str.split(':'))
    except ValueError:
        await update.message.reply_text("❌ Неверный формат времени")
        return

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await update.message.reply_text("❌ Некорректное время")
        return

    try:
        scheduler.remove_job("reminder_job")
    except JobLookupError:
        pass

    scheduler.add_job(
        remind_to_leave,
        trigger="cron",
        hour=hour,
        minute=minute,
        args=[context.bot],
        id="reminder_job"
    )

    if not scheduler.running:
        scheduler.start()

    await update.message.reply_text(
        f"🔔 Напоминания будут приходить в {hour:02}:{minute:02}"
    )


async def send_daily_tip(bot):
    """Асинхронная функция для отправки ежедневного совета"""
    try:
        unpublished_tip = await sync_to_async(DailytTips.objects.filter(
            is_published=False
        ).order_by("pub_date").first)()

        if unpublished_tip:
            tip = unpublished_tip
            tip.is_published = True
            message_prefix = "🌟 *Новый совет дня!*\n\n"
        else:
            tip = await sync_to_async(DailytTips.objects.filter(
                is_published=True
            ).order_by("?").first)()
            message_prefix = "🔁 *Лучшие советы*\n\n"

        if not tip:
            logging.warning("Нет доступных советов для отправки")
            return

        message = (
            f"{message_prefix}"
            f"📌 *{tip.title}*\n\n"
            f"{tip.content}\n\n"
        )

        if tip.external_link:
            message += f"🔗 [Подробнее]({tip.external_link})"

        group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
        await bot.send_message(
            chat_id=group_chat_id,
            text=message,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

        tip.views_count += 1
        await sync_to_async(tip.save)()

    except Exception as e:
        logging.error(f"Ошибка при отправке совета: {str(e)}", exc_info=True)


async def start_dailytips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ежедневной отправки советов в указанное время"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите время в формате ЧЧ:ММ "
            "(например: /start_dailytips 10:00)"
        )
        return

    try:
        hour, minute = map(int, context.args[0].split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Неверный формат времени")
        return

    try:
        scheduler.remove_job("dailytips_job")
    except JobLookupError:
        pass

    scheduler.add_job(
        send_daily_tip,
        trigger='cron',
        hour=hour,
        minute=minute,
        args=[context.bot],
        id="dailytips_job",
        timezone=ZoneInfo("Europe/Moscow")
    )

    if not scheduler.running:
        scheduler.start()

    await update.message.reply_text(
        f"✅ Ежедневные советы будут отправляться в {hour:02}:{minute:02}\n"
        "Логика отправки:\n"
        "1. Приоритет у неопубликованных советов\n"
        "2. Если все опубликованы - случайный выбор"
    )


async def stop_dailytips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка ежедневных советов"""
    try:
        scheduler.remove_job("dailytips_job")
        await update.message.reply_text("✅ Рассылка советов остановлена")
    except JobLookupError:
        await update.message.reply_text("⚠️ Активная рассылка не найдена")


class Command(BaseCommand):
    help = "Запуск бота Телеграмм"

    def handle(self, *args, **options):
        application = ApplicationBuilder().token(
            settings.TELEGRAM_BOT_TOKEN).build()

        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("join", join),
            ],
            states={
                SELECT_CO: [MessageHandler(
                    filters.TEXT & ~filters.COMMAND, select_company)],
                JOIN_CO: [MessageHandler(
                    filters.TEXT & ~filters.COMMAND, add_new_company)],
            },
            fallbacks=[CommandHandler(
                "cancel", lambda update, context: ConversationHandler.END)],
        )

        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("help", help))
        application.add_handler(CommandHandler("site", site))
        application.add_handler(CommandHandler("get_chat_info", get_chat_info))
        application.add_handler(CommandHandler("leave", leave))
        application.add_handler(CommandHandler("mew", mew))
        application.add_handler(CommandHandler("start_weather", start_weather))
        application.add_handler(CommandHandler("start_stats", start_stats))
        application.add_handler(
            CommandHandler("start_reminder", start_reminder))
        application.add_handler(CommandHandler(
            "stop_scheduler", stop_scheduler))
        application.add_handler(CommandHandler("edit", edit))
        application.add_handler(
            CommandHandler("edit_start", edit_arrival_time))
        application.add_handler(
            CommandHandler("edit_end", edit_departure_time))
        application.add_handler(CommandHandler(
            "start_dailytips", start_dailytips))
        application.add_handler(CommandHandler(
            "stop_dailytips", stop_dailytips))

        try:
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("Бот остановлен."))
            application.stop()
