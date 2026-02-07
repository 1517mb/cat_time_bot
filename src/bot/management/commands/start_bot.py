import logging
import os
import random
import re
import traceback
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from difflib import get_close_matches
from zoneinfo import ZoneInfo

import aiohttp
import pytz
import telegram
from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asgiref.sync import sync_to_async
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
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.management.core.bot_constants import (
    BotAchievementsCfg,
    BotMessages,
    SiteCfg,
)
from bot.management.core.bot_instance import get_bot_application
from bot.management.core.currency_utils import (
    fetch_currency_rates,
    save_currency_rates,
    send_currency_report,
)
from bot.management.core.experience import calculate_experience, get_level_info
from bot.management.core.statistics import (
    get_daily_statistics,
    get_daily_statistics_message,
    has_any_trips_on_date,
    update_daily_statistics,
)
from bot.management.core.utils import (
    create_progress_bar,
    get_time_declension,
    normalize_duration_to_seconds,
    truncate_markdown_safe,
)
from bot.management.core.weather import get_weather
from bot.models import (
    Achievement,
    Company,
    DailytTips,
    LevelTitle,
    Season,
    SeasonRank,
    UserActivity,
)

logger = logging.getLogger(__name__)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

JOIN_CO, SELECT_CO = range(2)

VALID_COMPANY_NAME_PATTERN = re.compile(r"^[А-Яа-яЁёA-Za-z0-9\s\-]+$")


scheduler = AsyncIOScheduler(timezone=ZoneInfo("Europe/Moscow"))


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Команда для отображения списка доступных команд.
    """
    help_text = SiteCfg.HELP_TEXT
    if update.effective_message:
        await update.effective_message.reply_text(
            help_text, parse_mode="Markdown"
        )


async def site(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет информацию о сайте"""
    site_info = SiteCfg.MSG_SITE
    if update.effective_message:
        await update.effective_message.reply_text(
            site_info, parse_mode="Markdown"
        )


async def check_achievements(
    user_id: int,
    username: str,
    activity: UserActivity,
    context: ContextTypes.DEFAULT_TYPE
) -> list:
    """Проверка и выдача достижений с оптимизированными запросами."""
    try:
        today = timezone.now().date()
        join_time = timezone.localtime(activity.join_time)
        leave_time = timezone.localtime(activity.leave_time)
        duration = (leave_time - join_time).total_seconds()
        new_achievements = []
        formatted_achievements = []

        user_stats = await sync_to_async(
            lambda: {
                "company_visits": UserActivity.objects.filter(
                    user_id=user_id,
                    company=activity.company
                ).count(),

                "same_day_users": UserActivity.objects.filter(
                    company__name__iexact=activity.company.name,
                    join_time__date=join_time.date()
                ).values("user_id").distinct().count(),

                "same_company_today": UserActivity.objects.filter(
                    user_id=user_id,
                    company=activity.company,
                    join_time__date=today
                ).count(),

                "today_trips": UserActivity.objects.filter(
                    user_id=user_id,
                    join_time__date=today
                ).count(),

                "weekly_trips": UserActivity.objects.filter(
                    user_id=user_id,
                    join_time__gte=today - timedelta(days=today.weekday())
                ).count(),

                "avg_duration": UserActivity.objects.filter(
                    user_id=user_id
                ).annotate(
                    duration=F("leave_time") - F("join_time")
                ).aggregate(avg=Avg("duration"))["avg"]
            }
        )()

        if user_stats["company_visits"] == 1:
            first_visit_achievements = [
                "🏕️ Я здесь впервые, правда же?",
                "🌱 Первый визит в компанию!",
                "👣 Следы первого посещения",
                "🎯 Дебют в компании состоялся!",
                "🆕 Новенький в этих краях",
                "🚩 Первая вылазка в данную локацию",
                "📌 Точка отсчета моего пути здесь"
            ]
            new_achievements.append(random.choice(first_visit_achievements))

        if user_stats["same_company_today"] > 1:
            revisit_achievements = [
                "🔄 Дежавю: Снова здесь!",
                "♻️ Экономлю на пропуске",
                "📌 Постоянный клиент дня",
                "🏃 Реверс-раунд: Туда и обратно",
                "🔄 Повторение - мать учения"
            ]
            new_achievements.append(random.choice(revisit_achievements))

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
                f"📅 Я люблю свою работу, я приду сюда в {day_name}"
            )
        if 18 <= join_time.hour < 24:
            night_achievements = [
                "🌚 Ночная смена? Или просто забыл уйти?",
                "🦇 Бэтмен бы позавидовал моему графику",
                "☕ Кофеиновая капельница подключена",
                "🌙 'Утро вечера мудренее' — а я ещё тут",
                "🌃 Ночной досмотр",
                "🌙 Сова компании",
                "🦉 Полуночный админ",
                "🌌 Лунатик"
            ]
            new_achievements.append(random.choice(night_achievements))

        if 0 <= join_time.hour < 9:
            morning_achievements = [
                "⏰ Проснулся раньше будильника... ха-ха, шутка",
                "💤 'Я бодр!' *спит*",
                "🌚 Ночь. Улица. Фонарь. Сервер.",
                "☕ Кофе? Ещё кофе! И лампочку в зубы...",
                "📉 Мой мозг сейчас в beta-тестировании",
                "☕ Кофеиновый марафонец",
                "🌇 Первый луч и на работе"
            ]
            new_achievements.append(random.choice(morning_achievements))

        duration_achievements = BotAchievementsCfg.DURATION_ACHIEVEMENTS

        for (min_val, max_val), achievements in duration_achievements.items():
            if min_val <= duration < max_val and achievements:
                new_achievements.append(random.choice(achievements))
                break

        avg_seconds = normalize_duration_to_seconds(user_stats["avg_duration"])
        if avg_seconds > 9000:
            new_achievements.append("🐢 Поспешишь - людей насмешишь")

        edit_achievements = {
            (1, 2): None,
            (2, 4): "🕰️ Читер: Часовщик II уровня",
            (4, float('inf')): "🕰️ Читер: Часовщик III уровня"
        }

        if activity.edited:
            new_achievements.append("🕵️♂️ Читер: Часовщик")
            for (min_edit, max_edit), achievement in edit_achievements.items():
                if min_edit <= activity.edit_count < max_edit and achievement:
                    new_achievements.append(achievement)

        if new_achievements:
            achievements_count = {}
            for ach in new_achievements:
                achievements_count[ach] = achievements_count.get(ach, 0) + 1

            formatted_achievements = [
                f"• {ach} x{count}" if count > 1 else f"• {ach}"
                for ach, count in achievements_count.items()
            ]

            achievements_to_create = [
                Achievement(
                    user_id=user_id,
                    username=username,
                    achievement_name=ach.split(
                        " ", 1)[1] if " " in ach else ach
                ) for ach in new_achievements
            ]
        else:
            achievements_to_create = []
            formatted_achievements = ["• Пока ничего 🐱"]
        if achievements_to_create:
            await sync_to_async(
                Achievement.objects.bulk_create)(achievements_to_create)

        group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
        formatted_achievements_text = "\n".join(formatted_achievements)
        if group_chat_id:
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
        else:
            logging.warning("TELEGRAM_GROUP_CHAT_ID не установлен, "
                            "уведомление о достижениях не отправлено.")
        achievement_names = []
        for ach in new_achievements:
            if " " in ach:
                achievement_names.append(ach.split(" ", 1)[1])
            else:
                achievement_names.append(ach)
        return achievement_names

    except Exception as e:
        logging.error(
            f"Ошибка при проверке достижений для {username}: {str(e)}\n"
            f"Детали: {traceback.format_exc()}",
            exc_info=True
        )
        return []


async def get_chat_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_chat or not update.effective_message:
        return
    chat_id = update.effective_chat.id
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
        await update.effective_message.reply_text(chat_info)
    except Exception as e:
        await update.effective_message.reply_text(
            f"🚨 *Ошибка при получении информации о чате:* {e}",
            parse_mode="Markdown")


async def send_weather_to_group(bot):
    """Асинхронная функция для отправки погоды в группу."""
    try:
        weather_message = await get_weather()
        group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")

        await bot.send_message(
            chat_id=group_chat_id,
            text=weather_message,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка при отправке погоды: {e}")
        group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
        if group_chat_id:
            await bot.send_message(
                chat_id=group_chat_id,
                text="🚨 Не удалось отправить погоду. 🚨",
                parse_mode="HTML"
            )


async def stop_scheduler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка планировщика."""
    if not update.effective_chat or not update.effective_message:
        return
    if scheduler.running:
        scheduler.shutdown(wait=False)
        await update.effective_message.reply_text(
            "🛑 Планировщик погоды остановлен. 🌧️"
        )
    else:
        await update.effective_message.reply_text(
            "🚦 Планировщик уже остановлен. 🚦"
        )


async def get_similar_companies(company_name):
    """
    Searches for companies with names similar to the given company_name.
    """
    similar_companies = await sync_to_async(list)(
        Company.objects.filter(
            name__icontains=company_name
        ).values_list("name", flat=True)
    )
    return get_close_matches(
        company_name, similar_companies, n=2, cutoff=0.6
    )


async def join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return ConversationHandler.END
    user_id = user.id
    username = user.username
    if not context.args:
        await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Пожалуйста, укажите название организации после команды /join.",
            parse_mode="Markdown")
        return ConversationHandler.END
    company_name = " ".join(context.args)

    if not VALID_COMPANY_NAME_PATTERN.match(company_name):
        await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Название организации должно содержать только"
            " буквы русского или английского алфавита, цифры и тире.",
            parse_mode="Markdown")
        return ConversationHandler.END

    active_activity = await sync_to_async(UserActivity.objects.filter(
        user_id=user_id, leave_time__isnull=True).exists)()

    if active_activity:
        await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Вы ещё не покинули предыдущую организацию.",
            parse_mode="Markdown")
        return ConversationHandler.END

    try:
        company = await sync_to_async(
            Company.objects.filter(name=company_name).first)()
        if company:
            local_time = timezone.localtime(timezone.now())
            await message.reply_text(
                f"🐱‍💻 *Вы прибыли в организацию `{company_name}`* 🐱‍💻\n"
                f"⏳ Время прибытия: {local_time.strftime('%H:%M')}.",
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
                if group_chat_id:
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
                await message.reply_text(
                    f"🚨 *Организации с названием \"{company_name}\" "
                    "не найдено.* 🚨\n"
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
                await message.reply_text(
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
                    UserActivity.objects.filter(
                        join_time__date=today).count
                )()
                if total_today == 1:
                    achievement = Achievement(
                        user_id=user_id,
                        username=username,
                        achievement_name="🩸 Первая кровь"
                    )
                    await sync_to_async(achievement.save)()
                    group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
                    if group_chat_id:
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
        await message.reply_text(
            "🚨 *Произошла ошибка при поиске или создании организации.* 🚨",
            parse_mode="Markdown"
        )
        return ConversationHandler.END


async def select_company(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback для выбора существующей организации."""
    user = update.effective_user
    message = update.effective_message
    if not user or not message or not message.text:
        return ConversationHandler.END

    user_id = user.id
    username = user.username
    selected_company = message.text

    if not VALID_COMPANY_NAME_PATTERN.match(selected_company):
        await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Название организации должно содержать только"
            " буквы русского алфавита и цифры.",
            parse_mode="Markdown")
        return ConversationHandler.END

    if selected_company == "Добавить новую организацию":
        await message.reply_text(
            "🐾 *Пожалуйста, введите название новой организации.* 🐾"
        )
        return JOIN_CO

    active_activity = await sync_to_async(UserActivity.objects.filter(
        user_id=user_id, leave_time__isnull=True).exists)()

    if active_activity:
        await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Вы ещё не покинули предыдущую организацию.",
            parse_mode="Markdown")
        return ConversationHandler.END

    company, created = await sync_to_async(
        Company.objects.get_or_create)(name=selected_company)
    local_time = timezone.localtime(timezone.now())
    await message.reply_text(
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
) -> tuple[bool, object]:
    """Вспомогательная функция для валидации и обновления времени."""
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return False, None
    user_id = user.id

    active_activity = await sync_to_async(
        UserActivity.objects.filter(
            user_id=user_id,
            leave_time__isnull=True
        ).select_related('company').first
    )()

    if not active_activity:
        msg = await message.reply_text(
            f"🚨 *Ошибка!* 🚨\n"
            f"У вас нет активной организации, для "
            f"которой можно изменить {error_message_prefix}.",
            parse_mode="Markdown"
        )
        return False, msg

    args = context.args
    if not args or len(args) != 1:
        msg = await message.reply_text(
            f"🚨 *Ошибка!* 🚨\n"
            f"⭕️ *Внимание! Неверный формат ввода*\n\n"
            f"🕒 Пожалуйста, укажите {error_message_prefix} "
            f"время в формате *ЧЧ:ММ*\n"
            f"Пример: *14:30*\n\n"
            f"📖 Для получения дополнительной информации "
            f"используйте команду /help",
            parse_mode="Markdown"
        )
        return False, msg

    try:
        new_time = datetime.strptime(args[0], '%H:%M').time()
    except ValueError:
        msg = await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Неверный формат времени. Пожалуйста, "
            "укажите время в формате *ЧЧ:ММ* (например, 09:15).",
            parse_mode="Markdown"
        )
        return False, msg

    current_time = timezone.localtime(timezone.now()).time()
    if new_time > current_time:
        msg = await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Вы не можете выбрать время, которое больше текущего. "
            "Пожалуйста, укажите время, которое меньше или равно текущему.",
            parse_mode="Markdown"
        )
        return False, msg

    current_tz = timezone.get_current_timezone()
    now = timezone.localtime(timezone.now())
    new_datetime = datetime.combine(now.date(),
                                    new_time,
                                    tzinfo=current_tz
                                    ).astimezone(dt_timezone.utc)

    if time_field == "leave_time" and new_datetime < active_activity.join_time:
        msg = await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Время убытия не может быть раньше времени прибытия. "
            "Ваше время прибытия: "
            f"{active_activity.join_time.strftime('%H:%M')}.",
            parse_mode="Markdown"
        )
        return False, msg

    if (time_field == "join_time"
        and active_activity.leave_time
            and new_datetime > active_activity.leave_time):
        msg = await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Время прибытия не может быть позже времени убытия. "
            "Ваше время убытия: "
            f"{active_activity.leave_time.strftime('%H:%M')}.",
            parse_mode="Markdown"
        )
        return False, msg

    setattr(active_activity, time_field, new_datetime)
    active_activity.edited = True
    active_activity.edit_count += 1
    await sync_to_async(active_activity.save)()

    company_name = active_activity.company.name
    local_time = timezone.localtime(new_datetime).strftime('%H:%M')

    msg = await message.reply_text(
        f"😻 *Успешно!* 😻\n"
        f"{success_message.format(
            company_name=company_name, time=local_time)}.",
        parse_mode="Markdown"
    )
    return True, msg


async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Устаревшая команда."""
    message = BotMessages.EDIT_MSG
    if update.effective_message:
        await update.effective_message.reply_text(
            message, parse_mode="Markdown"
        )


async def edit_arrival_time(update: Update,
                            context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда для изменения времени прибытия в организацию."""
    user = update.effective_user
    if not user:
        return
    await _validate_and_update_time(
        update,
        context,
        time_field="join_time",
        error_message_prefix="время прибытия",
        success_message=("Время прибытия в организацию {company_name} "
                         "успешно изменено на {time}"),
    )
    user_id = user.id
    username = user.username
    await update_daily_statistics(user_id, username)


async def edit_departure_time(update: Update,
                              context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    user_id = user.id
    username = user.username or f"User_{user_id}"

    success, _ = await _validate_and_update_time(
        update,
        context,
        time_field="leave_time",
        error_message_prefix="время убытия",
        success_message=("Время убытия из организации {company_name} "
                         "успешно изменено на {time}"),
    )

    if success:
        try:
            activity = await sync_to_async(
                UserActivity.objects.select_related("company").filter(
                    user_id=user_id,
                    leave_time__isnull=False).latest)("leave_time")

            if activity:
                achievements_list = await check_achievements(
                    user_id, username, activity, context)
                today = timezone.now().date()
                daily_visits_count = await sync_to_async(
                    UserActivity.objects.filter(
                        user_id=user_id,
                        join_time__date=today
                    ).count)()
                exp_earned = calculate_experience(
                    activity, achievements_list, daily_visits_count)
                activity.experience_gained = exp_earned
                if not activity.leave_time:
                    logging.error(f"Activity {activity.pk} has no leave_time")
                    return
                time_spent = activity.leave_time - activity.join_time
                rank, level_up, new_level = await update_season_rank(
                    user_id, exp_earned, time_spent, username)
                await sync_to_async(activity.save)()
                await update_daily_statistics(user_id, username)
                company_name = activity.company.name
                spent_time = activity.get_spent_time

                msg_text = (
                    f"⌛ *Обновленные данные о посещении* ⌛\n"
                    f"🏭 Организация: *{company_name}*\n"
                    f"⏳ Новое затраченное время: {spent_time}.\n"
                    f"🔰 Получено опыта: {exp_earned}"
                )
                if level_up and rank:
                    level_info = await get_level_info(rank)
                    progress_bar = create_progress_bar(level_info["progress"])
                    msg_text += (
                        "\n\n🎉 *Поздравляем с повышением уровня!* 🎉\n"
                        f"🏆 Новый уровень: *{new_level} lvl - "
                        f"{level_info['title']}*\n"
                        f"📚 Категория: *{level_info['category']}*"
                        f"📊 Прогресс: {progress_bar} *{int(level_info['progress'])}%*\n"
                        f"✨ Опыт: *{level_info['current_exp']}/{level_info['next_level_exp']}*"
                    )

                await message.reply_text(
                    msg_text, parse_mode="Markdown"
                )
            else:
                logging.warning(
                    f"Активность не найдена для пользователя {user_id}")
                await message.reply_text(
                    "⚠️ *Предупреждение:* "
                    + "Не удалось найти данные о посещении.",
                    parse_mode="Markdown"
                )

        except Exception as e:
            logging.error(f"Ошибка при выполнении команды /edit_end: {e}")
            await message.reply_text(
                "🚨 *Произошла ошибка при обработке команды.* 🚨",
                parse_mode="Markdown"
            )


async def add_new_company(
        update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Callback для добавления новой организации."""
    user = update.effective_user
    message = update.effective_message
    if not user or not message or not message.text:
        return ConversationHandler.END
    user_id = user.id
    username = user.username
    company_name = message.text

    active_activity = await sync_to_async(UserActivity.objects.filter(
        user_id=user_id, leave_time__isnull=True).exists)()

    if active_activity:
        await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Вы ещё не покинули предыдущую организацию.",
            parse_mode="Markdown")
        return ConversationHandler.END

    if not VALID_COMPANY_NAME_PATTERN.match(company_name):
        await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Название организации должно содержать только"
            " буквы русского или английского алфавита и цифры",
            parse_mode="Markdown")
        return ConversationHandler.END
    local_time = timezone.localtime(timezone.now())
    company, created = await sync_to_async(
        Company.objects.get_or_create)(name=company_name)
    await message.reply_text(
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
    """Callback для ухода из организации."""
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    user_id = user.id
    username = user.username or f"User_{user_id}"
    try:
        activity = await sync_to_async(UserActivity.objects.select_related(
            "company").filter(
                user_id=user_id,
                leave_time__isnull=True).latest)("join_time")
        achievements_list = await check_achievements(
            user_id, username, activity, context)
        today = timezone.now().date()
        daily_visits_count = await sync_to_async(UserActivity.objects.filter(
            user_id=user_id,
            join_time__date=today,
        ).count)()
        current_time = timezone.now()
        activity.leave_time = current_time
        exp_earned = calculate_experience(activity, achievements_list,
                                          daily_visits_count)
        activity.experience_gained = exp_earned
        join_time_val = activity.join_time
        if join_time_val is None:
            logging.error(f"Activity {activity.pk} has no join_time")
            return
        time_spent = current_time - join_time_val
        rank, level_up, new_level = await update_season_rank(
            user_id, exp_earned, time_spent, username)
        await sync_to_async(activity.save)()

        await update_daily_statistics(user_id, username)

        company_name = activity.company.name
        spent_time = activity.get_spent_time
        local_time = timezone.localtime(timezone.now())

        msg_text = (
            f"🐾👋 *Вы покинули организацию {company_name}* 🐾👋\n"
            f"⌛️ Время ухода: {local_time.strftime('%H:%M')}.\n"
            f"⏳ Затраченное время: {spent_time}.\n"
            f"🔰 Получено опыта: {exp_earned}"
        )

        if level_up and rank:
            level_info = await get_level_info(rank)
            progress_bar = create_progress_bar(level_info["progress"])
            msg_text += (
                "\n\n🎉 *Поздравляем с повышением уровня!* 🎉\n"
                f"🏆 Новый уровень: *{new_level} lvl - "
                f"{level_info['title']}*\n"
                f"📚 Категория: *{level_info['category']}*"
                f"📊 Прогресс: {progress_bar} *{int(level_info['progress'])}%*\n"
                f"✨ Опыт: *{level_info['current_exp']}/{level_info['next_level_exp']}*"
            )
        await message.reply_text(msg_text, parse_mode="Markdown")

    except UserActivity.DoesNotExist:
        await message.reply_text(
            "❌ *Ошибка!* ❌\n"
            "Вы не прибыли ни к одной организации.", parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка при выполнении команды /leave: {e}")
        await message.reply_text(
            "🚨 *Произошла ошибка при обработке вашего запроса.* 🚨",
            parse_mode="Markdown")


async def remind_to_leave(bot):
    """Функция для напоминания пользователям о необходимости /leave."""
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
            company_name = await sync_to_async(
                lambda: activity.company.name)()
            users.append(f"{username} ({company_name})")
        message = (
            "⚠️ *Внимание!* ⚠️\n\n"
            "Следующие сотрудники всё ещё находятся в организациях:\n"
            f"{'\n'.join(users)}\n\n"
            "🛠️ *Что нужно сделать?*\n"
            "1. Если вы уже покинули организацию — "
            "*проигнорируйте это сообщение*.\n"
            "2. Если ещё не ушли — выберите действие:\n\n"

            "📍 *Доступные команды:*\n"
            "• /edit\\_start <ЧЧ:ММ> — скорректировать время прибытия "
            "(пример: /edit\\_start 09:30)\n"
            "• /edit\\_end <ЧЧ:ММ> — изменить время убытия и "
            "завершить сессию (пример: /edit\\_end 18:15)"""
            "Команда работает как leave\n\n"

            "❗ *Важно:*\n"
            "— Работает только для *активных* сессий "
            "(где вы сейчас числитесь программно)\n"
            "— Формат времени: 09:00, 14:30 (24-часовой)"
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


async def check_and_send_transport_reminder(bot):
    """
    Проверяет и отправляет напоминание о транспортных
    расходах за месяц.
    """
    try:
        today = timezone.now().date()
        if today.month == 12:
            last_day = today.replace(
                year=today.year + 1, month=1, day=1
            ) - timedelta(days=1)
        else:
            last_day = today.replace(
                month=today.month + 1, day=1
            ) - timedelta(days=1)

        days_left = (last_day - today).days
        if days_left in [7, 4, 2, 1]:
            group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
            if not group_chat_id:
                logging.error(
                    "TELEGRAM_GROUP_CHAT_ID не установлен в .env"
                )
                return
            verb, day_word = get_time_declension(days_left)
            messages = [
                (
                    f"😱 *ПАНИКА!* (ну почти)\n{verb} всего {days_left} "
                    f"{day_word}! Если не заполнить транспортные расходы "
                    "сейчас, catbot начнет являться вам в ночных "
                    "кошмарах."
                ),
                (
                    f"🏃‍♂️ *Финишная прямая!*\n{verb} {days_left} "
                    f"{day_word}. Быстрее заполняйте расходы по транспорту, "
                    "а то ваша карета превратится в тыкву (и денег за "
                    "проезд не дадут)!"
                ),
                (
                    f"🕵️‍♂️ *Внимание, розыск!*\nИщем человека, который "
                    f"забыл заполнить транспортные расходы. {verb} {days_left} {day_word} " # noqa E501
                    "до закрытия. Не заставляйте нас применять паяльник... "
                    "шутка! Просто заполните расходы."
                ),
                (
                    f"📉 *Аттракцион невиданной щедрости закрывается!*\n"
                    f"{verb} {days_left} {day_word}. Кто не успел заполнить "
                    "расходы - тот работает в этом месяце за 'спасибо' "
                    "и печеньки. Шутка."
                ),
                (
                    f"💀 *Memento Mori.*\nПомни месяц скоро закончиться. {verb} " # noqa E501
                    f"{days_left} {day_word}.А транспортные расходы сами "
                    "себя не внесут (мы проверяли, магия не работает)."
                ),
                (
                    f"🦖 *Астероид приближается!*\n{verb} {days_left} "
                    f"{day_word} до конца месяца. Не будьте как динозавры, "
                    "заполните расходы, чтобы выжить (финансово)."
                ),
                (
                    f"🔮 *Битва экстрасенсов.*\nЯ пытался угадать ваши "
                    f"расходы силой мысли, но не вышло. {verb} {days_left} "
                    f"{day_word}. Придется вам заполнять их самим!"
                ),
                (
                    f"🆘 *Хьюстон, у нас проблемы!*\n{verb} {days_left} "
                    f"{day_word}, а полет нормальный только у тех, кто "
                    "звполнил расходы на транспорт. Остальные рискуют остаться в " # noqa E501
                    "открытом космосе без выплат."
                ),
                (
                    f"🕸 *Вжух! И месяца как не бывало.*\n{verb} "
                    f"{days_left} {day_word}. Ваш кошелек скажет вам "
                    "громкое 'СПАСИБО', если вы прямо сейчас откроете "
                    " сайт и заполните расходы."
                ),
            ]
            message_text = random.choice(messages)

            await bot.send_message(
                chat_id=group_chat_id,
                text=message_text,
                parse_mode="Markdown"
            )
            logging.info(
                f"Отправлено напоминание о транспорте. "
                f"Осталось дней: {days_left}"
            )

    except telegram.error.BadRequest as e:
        logging.error(f"Ошибка отправки сообщения: {str(e)}")
    except Exception as e:
        logging.error(
            f"Неожиданная ошибка в transport_reminder: {str(e)}",
            exc_info=True
        )


async def mew(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет случайное фото котика."""
    url = "https://api.thecatapi.com/v1/images/search"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    cat_photo_url = data[0]["url"]
                    if update.effective_message:
                        await update.effective_message.reply_photo(
                            photo=cat_photo_url
                        )
                else:
                    if update.effective_message:
                        await update.effective_message.reply_text(
                            "😿 Не удалось получить фото котика. 😿")
        except Exception as e:
            logging.error(f"Ошибка при запросе к API котиков: {e}")
            if update.effective_message:
                await update.effective_message.reply_text(
                    "😿 Произошла ошибка при получении фото котика. 😿")


async def send_daily_statistics_to_group(bot):
    """Асинхронно отправляет ежедневное статистическое сообщение."""
    try:
        tz = pytz.timezone("Europe/Moscow")
        now = datetime.now(tz)
        today_date = now.date()
        any_trips_today = await has_any_trips_on_date(today_date)

        if not any_trips_today:
            logging.info(f"Пропуск статистики {today_date} - нет выездов.")
            return
        stats = await get_daily_statistics()
        if stats["total_trips"] <= 0 and stats[
                "total_time"].total_seconds() <= 0:  # noqa
            logging.info(
                f"Пропуск статистики {today_date} - нет данных для отправки.")
            return
        message = await get_daily_statistics_message()
        group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
        if not group_chat_id:
            logging.error("TELEGRAM_GROUP_CHAT_ID не установлен в .env")
            return
        await bot.send_message(chat_id=group_chat_id,
                               text=message,
                               parse_mode="Markdown")
        logging.info(f"Статистика за {today_date} успешно отправлена.")
    except Exception as e:
        logging.error(f"Ошибка отправки статистики: {str(e)}", exc_info=True)


async def get_current_season():
    try:
        return await sync_to_async(Season.objects.get)(is_active=True)
    except Season.DoesNotExist:
        return None


async def update_season_rank(userid: int, expearned: int,
                             timespent: timedelta, username: str):
    season = await get_current_season()
    if not season:
        return None, False, 0

    rank, created = await sync_to_async(SeasonRank.objects.get_or_create)(
        user_id=userid,
        season=season,
        defaults={
            "username": username,
            "experience": expearned,
            "total_time": timespent,
            "visits_count": 1,
        }
    )

    old_level = rank.level
    if not created:
        rank.experience += expearned
        rank.total_time += timespent
        rank.visits_count += 1
    else:
        rank.username = username  # на всякий случай

    correct = await sync_to_async(
        lambda: LevelTitle.objects.filter(min_experience__lte=rank.experience).order_by("-level").first()
    )()

    if correct and correct.level != rank.level:
        rank.level = correct.level
        rank.level_title = correct

    levelup = rank.level > old_level
    await sync_to_async(rank.save)()
    return rank, levelup, rank.level


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if not user or not message:
        return
    user_id = user.id

    try:
        season = await get_current_season()
        if not season:
            await message.reply_text(
                "ℹ️ В данный момент сезон не активен. "
                "Ожидайте начала нового сезона!",
                parse_mode="Markdown"
            )
            return

        rank = await sync_to_async(
            SeasonRank.objects.select_related("level_title")
            .get
        )(user_id=user_id, season=season)

        level_info = await get_level_info(rank)

        total_hours = int(rank.total_time.total_seconds() // 3600)
        total_minutes = int((rank.total_time.total_seconds() % 3600) // 60)
        time_str = f"{total_hours}ч {total_minutes}м"

        now = timezone.now().date()
        if season.end_date:
            days_left = (season.end_date - now).days
        else:
            days_left = 0
        progress_bar = create_progress_bar(level_info["progress"])
        theme_name = getattr(season, "get_theme_display")()
        msg_text = (
            f"🏆 *Текущий сезон: {season.name}*\n"
            f"⏳ До конца сезона: *{days_left} дней*\n\n"
            "👤 *Ваш профиль*\n\n"
            f"🎯 Уровень: *{rank.level}*\n"
            f"🎖 Звание: *{level_info['title']}*\n"
            f"📚 Категория: *{level_info['category']}*\n"
            f"⭐ Опыт: *{level_info['current_exp']}/"
            f"{level_info['next_level_exp']}*\n"
            f"📊 Прогресс: {progress_bar} {int(level_info['progress'])}%\n"
            f"⏱ Всего времени в организациях: *{time_str}*\n"
            f"🚗 Всего выездов: *{rank.visits_count}*\n\n"
            f"{theme_name} продолжается! "
            "Успейте достичь новых высот!"
        )
    except SeasonRank.DoesNotExist:
        msg_text = (
            "👤 *Ваш профиль*\n\n"
            "Вы ещё не совершали выездов в текущем сезоне.\n"
            "Используйте команду /join чтобы начать!")
    await message.reply_text(msg_text, parse_mode="Markdown")


async def start_weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ежедневной отправки погоды в указанное время"""
    message = update.effective_message
    if not message:
        return
    if not context.args:
        await message.reply_text(
            "❌ Укажите время в формате ЧЧ:ММ (например: /start_weather 9:30)"
        )
        return

    time_str = context.args[0]
    try:
        hour, minute = map(int, time_str.split(":"))
    except ValueError:
        await message.reply_text("❌ Неверный формат времени")
        return

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await message.reply_text("❌ Некорректное время")
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

    await message.reply_text(
        f"⛅ Задание для отправки погоды установлено на {hour:02}:{minute:02}"
    )


async def start_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ежедневной отправки статистики"""
    message = update.effective_message
    if not message:
        return
    if not context.args:
        await message.reply_text(
            "❌ Укажите время в формате ЧЧ:ММ (например: /start_stats 20:00)"
        )
        return

    time_str = context.args[0]
    try:
        hour, minute = map(int, time_str.split(':'))
    except ValueError:
        await message.reply_text("❌ Неверный формат времени")
        return

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await message.reply_text("❌ Некорректное время")
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

    await message.reply_text(
        f"📊 Задание для отправки "
        f"статистики установлено на {hour:02}:{minute:02}"
    )


async def start_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск напоминаний о необходимости покинуть организацию"""
    message = update.effective_message
    if not message:
        return
    if not context.args:
        await message.reply_text(
            "❌ Укажите время в формате ЧЧ:ММ "
            "(например: /start_reminder 19:45)"
        )
        return

    time_str = context.args[0]
    try:
        hour, minute = map(int, time_str.split(':'))
    except ValueError:
        await message.reply_text("❌ Неверный формат времени")
        return

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        await message.reply_text("❌ Некорректное время")
        return

    for job_id in ["reminder_job", "transport_reminder"]:
        try:
            scheduler.remove_job(job_id)
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

    scheduler.add_job(
        check_and_send_transport_reminder,
        trigger="cron",
        hour=9,
        minute=0,
        args=[context.bot],
        id="transport_reminder",
        timezone=ZoneInfo("Europe/Moscow"))

    if not scheduler.running:
        scheduler.start()

    response_message = (
        "🔔 Напоминания успешно установлены:\n\n"
        "• Проверка активности в организациях — "
        f"ежедневно в {hour:02}:{minute:02}\n"
        "• Транспортные расходы — ежедневно в 09:00 "
        "(только за 7/4/1 дней до конца месяца)"
    )

    await message.reply_text(response_message)


async def send_daily_tip(bot):
    """Асинхронная функция для отправки ежедневного совета"""
    try:
        unpublished_tip = await sync_to_async(DailytTips.objects.filter(
            is_published=False
        ).order_by("pub_date").first)()

        if unpublished_tip:
            tip = unpublished_tip
            tip.is_published = True
            tip.pub_date = timezone.now()
            await sync_to_async(tip.save)()
            message_prefix = "🌟 *Новый совет дня!*\n\n"
        else:
            tip = await sync_to_async(DailytTips.objects.filter(
                is_published=True
            ).order_by("?").first)()
            message_prefix = "🔁 *Лучшие советы*\n\n"

        if not tip:
            logging.warning("Нет доступных советов для отправки")
            return

        content_preview = truncate_markdown_safe(tip.content, max_length=50)

        site_base_url = os.getenv("SITE_URL")
        tip_detail_url = f"{site_base_url}/tips/{tip.pk}/"

        message = (
            f"{message_prefix}"
            f"📌 *{tip.title}*\n\n"
            f"{content_preview}\n\n"
        )
        message += f"👁‍🗨 Просмотров: {tip.views_count}\n\n"

        tags = await sync_to_async(list)(tip.tags.all())
        if tags:
            tag_list = " ".join(
                [f"#{tag.slug.replace('-', r'\_')}" for tag in tags])
            message += f"🏷 *Теги:* {tag_list}\n\n"
        message += f"🔗 [Читать полностью]({tip_detail_url})\n\n"
        if tip.external_link:
            message += f"ℹ️ [Дополнительная информация]({tip.external_link})"

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
    message = update.effective_message
    if not message:
        return
    if not context.args:
        await message.reply_text(
            "❌ Укажите время в формате ЧЧ:ММ "
            "(например: /start_dailytips 10:00)"
        )
        return

    try:
        hour, minute = map(int, context.args[0].split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        await message.reply_text("❌ Неверный формат времени")
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

    await message.reply_text(
        f"✅ Ежедневные советы будут отправляться в {hour:02}:{minute:02}\n"
        "Логика отправки:\n"
        "1. Приоритет у неопубликованных советов\n"
        "2. Если все опубликованы - случайный выбор"
    )


async def stop_dailytips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка ежедневных советов"""
    message = update.effective_message
    if not message:
        return
    try:
        scheduler.remove_job("dailytips_job")
        await message.reply_text(
            "✅ Рассылка советов остановлена"
        )
    except JobLookupError:
        await message.reply_text(
            "⚠️ Активная рассылка не найдена"
        )


async def handle_unknown_command(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    """Обработчик только для неизвестных команд."""
    message = update.effective_message
    if not message or not message.text:
        return
    try:
        command = message.text.split()[0].lower()
        if not command.startswith("/"):
            return
        if command.lstrip("/") in BotMessages.AVAILABLE_COMMANDS:
            return

        user_input = command.lstrip("/")
        matches = get_close_matches(user_input,
                                    BotMessages.AVAILABLE_COMMANDS,
                                    n=1, cutoff=0.4)

        if matches:
            suggestion = f"/{matches[0]}"
            reply_text = (
                f"🔍 *Неизвестная команда* `{command}`\n\n"
                f"Возможно вы имели в виду: {suggestion}?\n\n"
                "📝 Для списка команд используйте /help"
            )
        else:
            reply_text = (
                f"❌ *Неизвестная команда* `{command}`\n\n"
                "📝 Используйте /help для просмотра доступных команд"
            )
        await message.reply_text(
            reply_text,
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove()
        )

    except Exception as e:
        logging.error(f"Ошибка обработки команды: {str(e)}", exc_info=True)


async def active_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает всех сотрудников, находящихся в организациях в данный момент.
    """
    message = update.effective_message
    if not message:
        return
    try:
        active_activities = await sync_to_async(list)(
            UserActivity.objects.select_related("company")
            .filter(leave_time__isnull=True)
        )

        if not active_activities:
            await message.reply_text(
                "ℹ️ *Статус:* В данный момент никто "
                "не находится в организациях.",
                parse_mode="Markdown"
            )
            return

        companies = {}
        tz = ZoneInfo("Europe/Moscow")

        for activity in active_activities:
            company_name = activity.company.name
            join_time = activity.join_time.astimezone(tz).strftime("%H:%M")

            username = (f"@{activity.username}"
                        if activity.username
                        else f"ID:{activity.user_id}")

            if company_name not in companies:
                companies[company_name] = []
            companies[company_name].append((username, join_time))

        message_lines = ["🚀 *Сотрудники в организациях:*\n"]
        for company, users in companies.items():
            message_lines.append(f"\n🏢 *{company}*:")
            for i, (username, join_time) in enumerate(users, 1):
                message_lines.append(
                    f"{i}. {username} - прибыл в {join_time}")

        msg_text = "\n".join(message_lines)
        await message.reply_text(
            msg_text, parse_mode="Markdown"
        )

    except Exception as e:
        logging.error(f"Ошибка при выполнении команды /status: {e}")
        await message.reply_text(
            "🚨 Произошла ошибка при получении статуса сотрудников",
            parse_mode="Markdown"
        )


async def send_currency_rates_to_group(bot):
    """
    Асинхронная функция для обновления и отправки курсов.
    Использует логику из currency_utils.py.
    """
    try:
        rates = await fetch_currency_rates()
        await save_currency_rates(rates)
        await send_currency_report(bot)
    except Exception as e:
        logger.error(f"Ошибка в цикле обновления курсов: {e}", exc_info=True)


async def start_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск ежедневной отправки курсов в указанное время"""
    message = update.effective_message
    if not message:
        return
    if not context.args:
        await message.reply_text(
            "❌ Укажите время в формате ЧЧ:ММ (например: /start_currency 8:00)"
        )
        return

    time_str = context.args[0]
    try:
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        await message.reply_text("❌ Неверный формат времени")
        return

    try:
        scheduler.remove_job("currency_job")
    except JobLookupError:
        pass

    scheduler.add_job(
        send_currency_rates_to_group,
        trigger="cron",
        hour=hour,
        minute=minute,
        args=[context.bot],
        id="currency_job",
        timezone=ZoneInfo("Europe/Moscow")
    )

    if not scheduler.running:
        scheduler.start()

    await message.reply_text(
        f"💱 Задание для отправки курсов установлено на {hour:02}:{minute:02}\n"
        "Курс будет обновляться ежедневно в это время"
    )


async def stop_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка ежедневной рассылки курсов"""
    message = update.effective_message
    if not message:
        return
    try:
        scheduler.remove_job("currency_job")
        await message.reply_text(
            "✅ Рассылка курсов остановлена"
        )
    except JobLookupError:
        await message.reply_text(
            "⚠️ Активная рассылка не найдена"
        )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет диалог."""
    if update.effective_message:
        await update.effective_message.reply_text(
            "Действие отменено.",
            reply_markup=ReplyKeyboardRemove()
        )
    return ConversationHandler.END


class Command(BaseCommand):
    help = "Запуск бота Телеграмм"

    def handle(self, *args, **options):
        application = get_bot_application()

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
            fallbacks=[CommandHandler("cancel", cancel)],
        )

        application.add_handler(conv_handler)
        application.add_handler(CommandHandler("help", help))
        application.add_handler(CommandHandler("site", site))
        application.add_handler(
            CommandHandler("get_chat_info", get_chat_info))
        application.add_handler(CommandHandler("leave", leave))
        application.add_handler(CommandHandler("mew", mew))
        application.add_handler(
            CommandHandler("start_weather", start_weather))
        application.add_handler(CommandHandler("start_stats", start_stats))
        application.add_handler(CommandHandler("profile", profile))
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
        application.add_handler(CommandHandler("status", active_users))
        application.add_handler(CommandHandler(
            "start_currency", start_currency))
        application.add_handler(CommandHandler(
            "stop_currency", stop_currency))
        application.add_handler(
            MessageHandler(filters.COMMAND, handle_unknown_command)
        )
        self.stdout.write(self.style.SUCCESS("Бот запускается... "
                                             "Нажмите Ctrl+C для остановки."))
        try:
            logger.info("Запуск бота в режиме polling...")
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            logger.error(f"Критическая ошибка при работе бота: {e}")
        self.stdout.write(self.style.SUCCESS("Бот успешно остановлен."))
