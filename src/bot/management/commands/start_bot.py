import asyncio
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from difflib import get_close_matches

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
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

from bot.models import Company, UserActivity

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

JOIN_CO, SELECT_CO = range(2)

VALID_COMPANY_NAME_PATTERN = re.compile(r"^[А-Яа-яA-Za-z0-9\s\-]+$")

executor = ThreadPoolExecutor()
scheduler = BackgroundScheduler()


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "😺 Привет! 😺 Вот список доступных команд:\n"
        "\n"
        "*Основные команды:*\n"
        "/help - Показать это сообщение с инструкциями.\n"
        "/join <Организация> - Прибыть к указанной организации.\n"
        "/leave - Покинуть текущую организацию и записать затраченное время.\n"
        "/edit - Изменить время прибытия в текущую организацию.\n"
        "\n"
        "*Дополнительные команды:*\n"
        "/start\\_scheduler - Запустить задание для отправки погоды.\n"
        "/get\\_chat\\_info - Получить информацию о чате.\n"
        "/mew - Получить случайное фото кота."
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


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


def get_weather():
    api_key = os.getenv("OPENWEATHER_API_KEY")
    city = "Zelenograd"
    city_ru = "Зеленограде"
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru" # noqa
    response = requests.get(url)
    data = response.json()
    if data["cod"] == 200:
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        description = data["weather"][0]["description"]
        clouds = data["clouds"]["all"]
        wind_speed = data["wind"]["speed"]
        wind_gust = data["wind"].get("gust", 0)

        weather_emoji = {
            "дождь": "🌧️",
            "снег": "❄️",
            "сильный снегопад": "🌨️",
            "небольшой снег": "🌨️",
            "ясно": "☀️",
            "облачно": "☁️",
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
            f"💨 Скорость ветра: {wind_speed} м/с\n"
            f"🌬 Порывы ветра: {wind_gust} м/с\n"
            "** По данным openweathermap.org"
        )
        return weather_message
    else:
        return "🚨 Не удалось получить погоду. 🚨"


async def send_weather_to_group(bot):
    try:
        loop = asyncio.get_event_loop()
        weather_message = await loop.run_in_executor(executor, get_weather)
        group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
        await bot.send_message(chat_id=group_chat_id, text=weather_message)
    except Exception as e:
        logging.error(f"Ошибка при отправке погоды: {e}")
        await bot.send_message(
            chat_id=group_chat_id, text="🚨 Не удалось отправить погоду. 🚨")


def run_send_weather_to_group(bot):
    """Функция для запуска асинхронной корутины в потоке."""
    asyncio.run(send_weather_to_group(bot))


async def start_scheduler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    scheduler.remove_all_jobs()

    scheduler.add_job(
        run_send_weather_to_group,
        "cron",
        day_of_week="*",
        hour=7,
        minute=30,
        args=[context.bot]
    )
    scheduler.start()
    await update.message.reply_text("☀️ Планировщик погоды запущен. ⛈️")


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
                f"😺 *Вы прибыли в организацию {company_name}* 😺\n"
                f"Время прибытия: {local_time.strftime('%H:%M')}.",
                parse_mode="Markdown"
            )
            await sync_to_async(UserActivity.objects.create)(
                user_id=user_id,
                username=username,
                company=company
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
                    f"😺 *Вы прибыли в организацию {company_name}* 😺\n"
                    f"Время прибытия: {local_time.strftime('%H:%M')}.",
                    parse_mode="Markdown"
                )
                await sync_to_async(UserActivity.objects.create)(
                    user_id=user_id,
                    username=username,
                    company=company
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
        f"😺 *Вы прибыли в организацию {selected_company}* 😺\n"
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


async def edit_arrival_time(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда для изменения времени прибытия в организацию.
    """
    user_id = update.message.from_user.id

    active_activity = await sync_to_async(UserActivity.objects.filter(
        user_id=user_id, leave_time__isnull=True).first)()

    if not active_activity:
        await update.message.reply_text(
            "🚨 *Ошибка!* 🚨\n"
            "У вас нет активной организации, "
            "для которой можно изменить время прибытия.",
            parse_mode="Markdown")
        return

    args = context.args
    if not args or len(args) != 1:
        await update.message.reply_text(
            "🚨 *Ошибка!* 🚨\n"
            "Пожалуйста, укажите новое время прибытия "
            "в формате *ЧЧ:ММ* (например, /edit 10:15).",
            parse_mode="Markdown")
        return

    new_arrival_time_str = args[0]

    try:
        new_arrival_time = datetime.strptime(
            new_arrival_time_str, '%H:%M').time()
    except ValueError:
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Неверный формат времени. "
            "Пожалуйста, укажите время в формате *ЧЧ:ММ* (например, 09:15).",
            parse_mode="Markdown")
        return

    current_time = timezone.localtime(timezone.now()).time()

    if new_arrival_time > current_time:
        await update.message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Вы не можете выбрать время, которое больше текущего. "
            "Пожалуйста, укажите время, которое меньше или равно текущему.",
            parse_mode="Markdown")
        return

    today = timezone.now().date()
    new_arrival_datetime = datetime.combine(today, new_arrival_time)

    new_arrival_datetime = timezone.make_aware(new_arrival_datetime)

    active_activity.join_time = new_arrival_datetime
    await sync_to_async(active_activity.save)()

    company_name = await sync_to_async(lambda: active_activity.company.name)()
    local_join_time = timezone.localtime(new_arrival_datetime)

    await update.message.reply_text(
        f"😻 *Успешно!* 😻\n"
        f"Время прибытия в организацию {company_name} успешно"
        + f" изменено на {local_join_time.strftime('%H:%M')}.",
        parse_mode="Markdown")


async def add_new_company(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        f"😺 *Вы прибыли к новой организации {company_name}* 😺\n"
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
    user_id = update.message.from_user.id
    try:
        activity = await sync_to_async(UserActivity.objects.select_related(
            "company").filter(
                user_id=user_id,
                leave_time__isnull=True).latest)("join_time")

        activity.leave_time = timezone.now()
        await sync_to_async(activity.save)()

        company_name = activity.company.name
        spent_time = activity.get_spent_time
        local_time = timezone.localtime(timezone.now())

        await update.message.reply_text(
            f"😺 *Вы покинули организацию {company_name}* 😺\n"
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


async def mew(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    response = requests.get("https://api.thecatapi.com/v1/images/search")
    if response.status_code == 200:
        cat_photo_url = response.json()[0]["url"]
        await update.message.reply_photo(photo=cat_photo_url)
    else:
        await update.message.reply_text("😿 Не удалось получить фото котика. 😿")


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
        application.add_handler(CommandHandler("get_chat_info", get_chat_info))
        application.add_handler(CommandHandler("leave", leave))
        application.add_handler(CommandHandler("mew", mew))
        application.add_handler(CommandHandler(
            "start_scheduler", start_scheduler))
        application.add_handler(CommandHandler("edit", edit_arrival_time))

        try:
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("Бот остановлен."))
            application.stop()
