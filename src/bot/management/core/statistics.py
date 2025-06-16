import random

from asgiref.sync import sync_to_async
from django.utils import timezone

from bot.models import (
    Achievement,
    DailyStatistics,
    Quote,
    Season,
)


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
    stats = await get_daily_statistics()
    header = "📊 *Общая статистика за сегодня:*"
    quote = await get_random_quote()
    today = timezone.now().date()

    season_info = ""
    try:
        season = await sync_to_async(Season.objects.get)(is_active=True)
        season_info = f"🏆 *Текущий сезон: {season.name}*\n"
        now = timezone.now().date()
        days_left = (season.end_date - now).days
        season_info += f"⏳ До конца сезона: *{days_left} дней*\n\n"
    except Season.DoesNotExist:
        season_info = "ℹ️ *В данный момент сезон не активен*\n\n"

    user_stats = await sync_to_async(list)(
        DailyStatistics.objects.filter(date=today)
        .values("username", "total_trips", "total_time")
        .order_by("-total_trips")
    )

    achievements = await sync_to_async(list)(
        Achievement.objects.filter(achieved_at__date=today)
        .values("username", "achievement_name")
    )

    achievements_text = "\n\n🏆 *Персональная статистика:*\n"

    for user in user_stats[:5]:
        if user["total_trips"] > 0:
            avg_time = user["total_time"].total_seconds() / user["total_trips"]
            avg_min = int(avg_time // 60)
            avg_sec = int(avg_time % 60)
        else:
            avg_min = avg_sec = 0

        user_achs = [
            a["achievement_name"] for a in achievements
            if a["username"] == user["username"]]
        unique_achs = list(set(user_achs))[:3]

        achievements_text += (
            f"👤 @{user['username']}\n"
            f"   ▸ Выездов: {user['total_trips']} 🚗\n"
        )

        if user["total_trips"] > 0:
            achievements_text += (f"   ▸ Среднее время: {avg_min} мин"
                                  f" {avg_sec} сек ⏱\n")

        if unique_achs:
            achievements_text += f"   ▸ Достижения: {', '.join(unique_achs)}\n"

        achievements_text += "\n"

    if not user_stats:
        achievements_text = "\n\n🏆 *Сегодня ещё никто не отметился*"

    if stats["total_trips"] == 0:
        return (
            f"{season_info}"
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
        f"{season_info}"
        f"{header}\n"
        f"  - Всего выездов: {stats['total_trips']} 🚗\n"
        f"  - Общее время: {time_format} ⏱\n"
        f"  - Среднее время: {avg_minutes} мин 📌"
        f"{achievements_text}"
        f"\n\n{quote}"
    )
