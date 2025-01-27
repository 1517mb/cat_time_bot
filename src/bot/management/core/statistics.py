from datetime import timedelta

from asgiref.sync import sync_to_async
from django.db.models import DurationField, Sum
from django.utils import timezone

from bot.models import DailyStatistics, UserActivity


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

    return stats


async def get_daily_statistics_message():
    """
    Возвращает строку, содержащую общую статистику за сегодняшний день.
    Если сегодняшних данных нет, то возвращает сообщение, что данных нет.

    : возвращает: строку, описанную выше
    """
    stats = await get_daily_statistics()

    if not stats["total_trips"]:
        message = "📊 *Общая статистика за сегодня:*\nНет данных."
    else:
        total_trips = stats["total_trips"]
        total_time = stats["total_time"]

        total_hours = total_time.total_seconds() // 3600
        total_minutes = (total_time.total_seconds() % 3600) // 60

        message = (
            f"📊 *Общая статистика за сегодня:*\n"
            f"  - Всего выездов: {total_trips}\n"
            f"  - Общее время: {int(total_hours)} ч {int(total_minutes)} мин\n"
        )

    return message


async def update_daily_statistics(user_id, username):
    """
    Обновляет статистику пользователя за текущий день.
    """
    today = timezone.now().date()

    activities = await sync_to_async(list)(
        UserActivity.objects.filter(
            user_id=user_id,
            join_time__date=today,
            leave_time__isnull=False
        )
    )

    total_time = timedelta()
    total_trips = 0

    for activity in activities:
        time_spent = activity.leave_time - activity.join_time
        total_time += time_spent
        total_trips += 1

    stats, created = await sync_to_async(
        DailyStatistics.objects.get_or_create)(
        user_id=user_id,
        username=username,
        date=today,
        defaults={"total_time": total_time, "total_trips": total_trips}
    )

    if not created:
        stats.total_time = total_time
        stats.total_trips = total_trips
        await sync_to_async(stats.save)()
