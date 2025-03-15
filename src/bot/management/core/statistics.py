import random
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.db.models import DurationField, Sum
from django.utils import timezone

from bot.models import DailyStatistics, Quote, UserActivity, Achievement


async def get_random_quote():
    active_quotes = await sync_to_async(list)(
        Quote.objects.filter(is_active=True))
    if not active_quotes:
        return "«Иногда отсутствие выбора — лучший выбор...»\n— Алиса"
    quote = random.choice(active_quotes)
    return f"«{quote.text}»\n— {quote.source} | {quote.author}"


async def get_daily_statistics():
    """
    Возвращает словарь с двумя ключами: total_trips и total_time.
    total_trips - это сумма всех поездок, совершенных за сегодняшний день,
    а total_time - это сумма всего времени,
    проведенного в приложении за сегодняшний день.

    : возвращает: Словарь, как описано выше
    """
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
    Возвращает строку, содержащую общую статистику за сегодняшний день.
    """
    stats = await get_daily_statistics()
    header = "📊 *Общая статистика за сегодня:*"
    quote = await get_random_quote()
    today = timezone.now().date()

    user_stats = await sync_to_async(list)(
        DailyStatistics.objects.filter(date=today)
        .values('username', 'total_trips', 'total_time')
        .order_by('-total_trips')
    )

    achievements = await sync_to_async(list)(
        Achievement.objects.filter(achieved_at__date=today)
        .values('username', 'achievement_name')
    )

    achievements_text = "\n\n🏆 *Персональная статистика:*\n"

    for user in user_stats[:5]:
        avg_time = user['total_time'].total_seconds() / user['total_trips']
        avg_min = int(avg_time // 60)
        avg_sec = int(avg_time % 60)

        user_achs = [
            a['achievement_name'] for a in achievements
            if a['username'] == user['username']]
        unique_achs = list(set(user_achs))[:3]

        achievements_text += (
            f"👤 @{user['username']}\n"
            f"   ▸ Выездов: {user['total_trips']} 🚗\n"
            f"   ▸ Среднее время: {avg_min} мин {avg_sec} сек ⏱\n"
        )

        if unique_achs:
            achievements_text += f"   ▸ Достижения: {', '.join(unique_achs)}\n"

        achievements_text += "\n"

    if not user_stats:
        achievements_text = "\n\n🏆 *Сегодня ещё никто не отметился*"

    if stats["total_trips"] == 0:
        return (
            f"{header}\n"
            f"📌 *Текущая ситуация:*\n"
            f"   Ого, сегодня ещё ни одного выезда! ☘️\n"
            f"{achievements_text}"
            f"\n✨ *А вот и обещанная цитата:*\n{quote}"
        )

    total_time = stats["total_time"]
    hours = int(total_time.total_seconds() // 3600)
    minutes = int((total_time.total_seconds() % 3600) // 60)
    avg_minutes = int(total_time.total_seconds() // stats["total_trips"] // 60)
    time_format = f"{hours} ч" + (f" {minutes} мин" if minutes else "")

    return (
        f"{header}\n"
        f"  - Всего выездов: {stats['total_trips']} 🚗\n"
        f"  - Общее время: {time_format} ⏱\n"
        f"  - Среднее время: {avg_minutes} мин 📌"
        f"{achievements_text}"
        f"\n\n{quote}"
    )


async def update_daily_statistics(user_id, username):
    """
    Оптимизированное обновление статистики с batch-обработкой
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
    total_trips = len(activities)

    for activity in activities:
        total_time += activity["leave_time"] - activity["join_time"]

    await sync_to_async(DailyStatistics.objects.update_or_create)(
        user_id=user_id,
        date=today,
        defaults={
            "username": username,
            "total_time": total_time,
            "total_trips": total_trips
        }
    )
