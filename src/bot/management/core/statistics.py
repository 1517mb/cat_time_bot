import logging
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.db.models import DurationField, Sum
from django.utils import timezone

from bot.management.core.experience import get_level_info
from bot.management.core.utils import create_progress_bar
from bot.models import (
    Achievement,
    DailyStatistics,
    Season,
    SeasonRank,
    UserActivity,
)

logger = logging.getLogger(__name__)


def format_duration(seconds):
    """Вспомогательная функция для красивого вывода времени"""
    if not seconds:
        return "0 мин"
    minutes = int(seconds // 60)
    remaining_seconds = int(seconds % 60)
    if minutes >= 60:
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours} ч {minutes} мин"
    return f"{minutes} мин {remaining_seconds} сек"


async def has_any_trips_on_date(target_date):
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
    today = timezone.now().date()
    stats = await get_daily_statistics()
    header = "📊 *Общая статистика за сегодня:*"
    try:
        season = await sync_to_async(Season.objects.get)(is_active=True)
        days_left = (season.end_date - today).days  # type: ignore
        season_info = (
            f"🏆 *Сезон: {season.name}*\n"
            f"⏳ До конца: *{days_left} дн.*"
        )
    except Season.DoesNotExist:
        season = None
        season_info = "ℹ️ *Сезон не активен*"
    user_stats_qs = await sync_to_async(list)(
        DailyStatistics.objects.filter(date=today)
        .values("user_id", "username", "total_trips", "total_time")
    )

    if not user_stats_qs:
        return f"{header}\n\nСегодня выездов не было 😴"
    user_ids = [u["user_id"] for u in user_stats_qs]
    ranks_map = {}
    if season:
        ranks = await sync_to_async(list)(
            SeasonRank.objects.filter(
                user_id__in=user_ids,
                season=season
            ).select_related("level_title")
        )
        ranks_map = {r.user_id: r for r in ranks}
    achievements = await sync_to_async(list)(
        Achievement.objects.filter(achieved_at__date=today)
        .values("username", "achievement_name")
    )
    achievements_map = {}
    for ach in achievements:
        uname = ach["username"]
        if uname not in achievements_map:
            achievements_map[uname] = []
        if ach["achievement_name"] not in achievements_map[uname]:
            achievements_map[uname].append(ach["achievement_name"])
    today_activities_exp = await sync_to_async(list)(
        UserActivity.objects.filter(
            user_id__in=user_ids,
            leave_time__date=today
        ).values_list('experience_gained', flat=True)
    )
    total_exp_earned_today = sum(filter(None, today_activities_exp))
    display_data = []
    for user in user_stats_qs:
        u_id = user["user_id"]
        rank = ranks_map.get(u_id)
        data_item = {
            "username": user["username"],
            "trips": user["total_trips"],
            "avg_time_str": "0 мин",
            "level": 0,
            "exp": 0,
            "visits_total": 0,
            "rank_text": "",
            "achievements_str": "Пока нет"
        }
        if user["total_trips"] > 0:
            avg_sec = user["total_time"].total_seconds() / user["total_trips"]
            data_item["avg_time_str"] = format_duration(avg_sec)
        if rank:
            level_info = await get_level_info(rank)
            progress_bar = create_progress_bar(level_info["progress"])
            data_item["level"] = rank.level
            data_item["exp"] = rank.experience
            data_item["visits_total"] = rank.visits_count
            data_item["rank_text"] = (
                f"▸ Уровень: *{rank.level}* | *{level_info['title']}*\n"
                f"▸ Прогресс: {progress_bar} *{int(level_info['progress'])}%*\n" # noqa
                f"▸ Опыт: *{level_info['current_exp']}/{level_info['next_level_exp']}*\n" # noqa
            )
        user_achs = achievements_map.get(user["username"], [])[:3]
        if user_achs:
            data_item["achievements_str"] = ", ".join(user_achs)

        display_data.append(data_item)
    display_data.sort(
        key=lambda x: (-x["level"], -x["exp"], -x["visits_total"]))
    user_info_blocks = []
    for item in display_data:
        block = (
            f"👤 *@{item['username']}*\n"
            f"{item['rank_text']}"
            f"▸ Выездов сегодня: *{item['trips']}* 🚗\n"
            f"▸ Среднее время: *{item['avg_time_str']}* ⏱\n"
            f"▸ Достижения: {item['achievements_str']}"
        )
        user_info_blocks.append(block)
    total_time_str = format_duration(stats["total_time"].total_seconds())
    total_trips = stats["total_trips"]
    global_avg_str = "0 мин"
    if total_trips > 0:
        global_avg_sec = stats["total_time"].total_seconds() / total_trips
        global_avg_str = format_duration(global_avg_sec)

    general_stats_block = (
        f"{season_info}\n"
        f"⭐ *Общий опыт за день:* {total_exp_earned_today}\n\n"
        "📈 *Показатели:*\n"
        f" • Всего выездов: *{total_trips}*\n"
        f" • Общее время: *{total_time_str}*\n"
        f" • Среднее время: *{global_avg_str}*\n"
    )

    message = (
        f"{header}\n\n"
        f"{general_stats_block}\n"
        f"🏅 *Участники:*\n\n"
        f"{'\n\n'.join(user_info_blocks)}"
    )
    return message


async def update_daily_statistics(user_id, username):
    """
    Обновляет статистику. Логику оставили прежней, она рабочая.
    """
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

        if join_time and leave_time:
            total_time += leave_time - join_time
            valid_trips += 1
        else:
            logger.warning(
                f"Пустое время: user={user_id}, "
                f"join={join_time}, leave={leave_time}"
            )

    await sync_to_async(DailyStatistics.objects.update_or_create)(
        user_id=user_id,
        date=today,
        defaults={
            "username": username,
            "total_time": total_time,
            "total_trips": valid_trips
        }
    )
