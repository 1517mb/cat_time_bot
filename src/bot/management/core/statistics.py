import logging
import random
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.db.models import DurationField, Sum
from django.utils import timezone

from bot.management.core.experience import get_level_info
from bot.management.core.utils import create_progress_bar
from bot.models import (
    Achievement,
    DailyStatistics,
    Quote,
    Season,
    SeasonRank,
    UserActivity,
)

logger = logging.getLogger(__name__)


async def get_random_quote():
    active_quotes = await sync_to_async(list)(
        Quote.objects.filter(is_active=True))
    if not active_quotes:
        return "«Иногда отсутствие выбора — лучший выбор...»\n— Алиса"
    quote = random.choice(active_quotes)
    return f"«{quote.text}»\n— {quote.source} | {quote.author}"


async def has_any_trips_on_date(target_date):
    """
    Проверяет, были ли зарегистрированы выезды (UserActivity) в указанный день.
    Проверяется по наличию записей с join_time в этот день.
    """
    try:
        has_trips = await sync_to_async(
            lambda: UserActivity.objects.filter(
                join_time__date=target_date
            ).exists()
        )()
        return has_trips
    except Exception as e:
        logger.error(f"Ошибка при проверке выездов за {target_date}: {e}")
        return True


async def get_daily_statistics():
    today = timezone.now().date()
    stats = await sync_to_async(
        DailyStatistics.objects.filter(date=today).aggregate)(
        total_trips=Sum("total_trips"),
        total_time=Sum("total_time", output_field=DurationField())
    )
    return {
        "total_trips": stats["total_trips"] or 0,
        "total_time": stats["total_time"] or timedelta()
    }


async def get_daily_statistics_message():
    """
    Функция для сбора и формирования ежедневной статистики

    Функция собирает информацию о количестве выездов, общем времени
    и среднем времени, а также информацию о рангах и статистике
    пользователей. Затем на основе этой информации формирует и
    возвращает готовое сообщение со статистикой.
    """
    today = timezone.now().date()
    stats = await get_daily_statistics()
    header = "📊 *Общая статистика за сегодня:*"
    quote = await get_random_quote()

    season_info = ""
    best_user = None
    total_exp_earned_today = 0

    try:
        season = await sync_to_async(Season.objects.get)(is_active=True)
        season_info = f"🏆 *Текущий сезон: {season.name}*\n"
        now = timezone.now().date()
        days_left = (season.end_date - now).days
        season_info += f"⏳ До конца сезона: *{days_left} дней*\n"
    except Season.DoesNotExist:
        season_info = "ℹ️ *В данный момент сезон не активен*\n"

    user_stats = await sync_to_async(list)(
        DailyStatistics.objects.filter(date=today)
        .values("user_id", "username", "total_trips", "total_time")
        .order_by("-total_trips")
    )

    achievements = await sync_to_async(list)(
        Achievement.objects.filter(achieved_at__date=today)
        .values("username", "achievement_name")
    )

    user_info = []
    user_ranks = []

    total_trips = stats["total_trips"]
    total_seconds = stats["total_time"].total_seconds()
    if total_trips > 0:
        avg_seconds = total_seconds / total_trips
        avg_min = int(avg_seconds // 60)
        avg_sec = int(avg_seconds % 60)
        avg_time_str = f"{avg_min} мин {avg_sec} сек"
    else:
        avg_time_str = "0 мин"
    unique_users = {stat["user_id"] for stat in user_stats}

    for user in user_stats:
        rank = None
        level_info = {}
        if season:
            rank = await sync_to_async(SeasonRank.objects.filter(
                user_id=user["user_id"],
                season=season
            ).select_related("level_title").first)()
            if rank:
                level_info = await get_level_info(rank)
                user_ranks.append({
                    "username": user["username"],
                    "level": rank.level,
                    "exp": rank.experience,
                    "visits": rank.visits_count,
                    "rank_obj": rank,
                    "level_info": level_info
                })

        if user["total_trips"] > 0:
            user_avg_time = (
                user["total_time"].total_seconds() / user["total_trips"])
            user_avg_min = int(user_avg_time // 60)
            user_avg_sec = int(user_avg_time % 60)
            user_avg_time_str = f"{user_avg_min} мин {user_avg_sec} сек"
        else:
            user_avg_time_str = "0 мин"

        user_achs = [
            a["achievement_name"] for a in achievements
            if a["username"] == user["username"]]
        unique_achs = list(set(user_achs))[:3]
        achievements_str = (", ".join(unique_achs)
                            if unique_achs else "Пока нет")
        user_text = f"👤 *@{user['username']}*\n"
        if rank and level_info:
            progress_bar = create_progress_bar(level_info["progress"])
            user_text += (
                f"▸ Уровень: *{rank.level}* | *{level_info['title']}*\n"
                f"▸ Прогресс: {progress_bar} "
                f"*{int(level_info['progress'])}%*\n"
                f"▸ Опыт: *{level_info['current_exp']}/"
                f"{level_info['next_level_exp']}*\n"
            )
        user_text += (
            f"▸ Выездов: *{user['total_trips']}* 🚗\n"
            f"▸ Среднее время: *{user_avg_time_str}* ⏱\n"
            f"▸ Достижения: {achievements_str}\n"
        )
        user_info.append(user_text)
    if user_stats:
        today_activities_exp = await sync_to_async(list)(
            UserActivity.objects.filter(
                user_id__in=list(unique_users),
                leave_time__date=today
            ).values_list('experience_gained', flat=True)
        )
        total_exp_earned_today = sum(today_activities_exp)

    # Проверяем, было ли больше одного уникального
    # пользователя для определения ЛИДЕРА
    if len(unique_users) > 1 and user_ranks:
        user_ranks.sort(key=lambda x: (
            -x["level"],
            -x["exp"],
            -x["visits"]
        ))
        best_user = user_ranks[0]

    total_time = stats["total_time"]
    hours = int(total_time.total_seconds() // 3600)
    minutes = int((total_time.total_seconds() % 3600) // 60)
    time_format = f"{hours} ч" + (f" {minutes} мин" if minutes else "")

    leader_info = ""
    # Отображаем лидера только если он определен (т.е. > 1 участник)
    if best_user:
        level_info = best_user["level_info"]
        leader_info = (
            f"👑 *Лидер сезона:* @{best_user['username']}\n"
            f"▸ Уровень: *{best_user['level']} lvl - {level_info['title']}*\n"
            f"▸ Опыт: *{best_user['exp']}*\n"
            f"▸ Выездов: *{best_user['visits']}*\n\n"
        )
    general_info = (
        f"{season_info}\n"
        f"⭐ *Общий опыт за день:* {total_exp_earned_today}\n\n"
        f"{leader_info}"
    )
    stats_info = (
        "📈 *Общие показатели за день:*\n"
        f"  - Всего выездов: *{stats['total_trips']}* 🚗\n"
        f"  - Общее время: *{time_format}* ⏱\n"
        f"  - Среднее время: *{avg_time_str}* 📌\n\n"
    )
    # Сортировка user_info по рангу пользователей
    if user_ranks and len(unique_users) > 1:
        rank_map = {u["username"]: u for u in user_ranks}
        # Создаем временный список кортежей
        # (user_info_text, user_data) для сортировки
        user_info_with_data = list(zip(user_info, user_stats))
        # Сортируем по рангам
        user_info_with_data.sort(key=lambda item: (
            -rank_map.get(item[1]["username"], {}).get("level", 0),
            -rank_map.get(item[1]["username"], {}).get("exp", 0),
            -rank_map.get(item[1]["username"], {}).get("visits", 0)
        ))
        # Обновляем список user_info отсортированными элементами
        user_info = [info for info, _ in user_info_with_data]

    message = (
        f"{header}\n\n"
        f"{general_info}"
        f"{stats_info}"
        f"🏅 *Прогресс и статистика участников:*\n\n"
        f"{'\n\n'.join(user_info) if user_info else 'Сегодня никто не выезжал 🙁'}\n\n" # noqa
        f"✨ *Мудрая мысль дня:*\n{quote}"
    )
    return message


async def update_daily_statistics(user_id, username):
    today = timezone.now().date()

    activities = await sync_to_async(list)(
        UserActivity.objects.filter(
            user_id=user_id,
            join_time__date=today,
            leave_time__isnull=False
        ).values("join_time", "leave_time")
    )

    total_time = timedelta()
    valid_trips = 0
    for activity in activities:
        join_time = activity["join_time"]
        leave_time = activity["leave_time"]

        if join_time is not None and leave_time is not None:
            total_time += leave_time - join_time
            valid_trips += 1
        else:
            logger.warning(
                f"Найдена запись с пустым временем: user={user_id},"
                f" join={join_time}, leave={leave_time}")

    await sync_to_async(DailyStatistics.objects.update_or_create)(
        user_id=user_id,
        date=today,
        defaults={
            "username": username,
            "total_time": total_time,
            "total_trips": valid_trips
        }
    )
