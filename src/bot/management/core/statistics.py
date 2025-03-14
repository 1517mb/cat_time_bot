import random
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.db.models import DurationField, Sum
from django.utils import timezone

from bot.models import DailyStatistics, Quote, UserActivity


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
    Если сегодняшних данных нет, то возвращает сообщение, что данных нет.

    : возвращает: строку, описанную выше
    """
    stats = await get_daily_statistics()
    header = "📊 *Общая статистика за сегодня:*"
    quote = await get_random_quote()

    if stats["total_trips"] == 0:
        return (
            f"{header}\n"
            f"📌 *Текущая ситуация:*\n"
            f"   Ого, сегодня ещё ни одного выезда! ☘️\n\n"
            f"✨ *А вот и обещанная цитата:*\n{quote}"
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
