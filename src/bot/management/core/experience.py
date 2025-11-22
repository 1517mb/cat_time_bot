from asgiref.sync import sync_to_async

from bot.models import SeasonRank

ACHIEVEMENT_BONUSES = {
    "Первая кровь": 10,
    "Ночная смена? Или просто забыл уйти?": 15,
    "Кофеиновый марафонец": 10,
    "Сова компании": 10,
    "Лучший сотрудник": 50,
    "Командный игрок": 15,
    "А можно мне ещё выезд?": 10,
    "Экономлю на пропуске": 5,
    "Читер: Часовщик": -20,
}


async def get_level_info(rank: SeasonRank) -> dict:

    level_title = await sync_to_async(lambda: rank.level_title)()

    if not level_title:
        return {
            "title": f"Уровень {rank.level}",
            "category": "Новичок",
            "progress": min(100, (rank.experience / (rank.level * 100)) * 100),
            "current_exp": rank.experience,
            "next_level_exp": rank.level * 100
        }

    title = await sync_to_async(
        lambda: rank.level_title.title)()  # type: ignore
    category = await sync_to_async(
        lambda: rank.level_title.get_category_display())()  # type: ignore
    next_level_exp = rank.level * 100
    progress = (rank.experience / next_level_exp) * 100

    return {
        "title": title,
        "category": category,
        "progress": progress,
        "current_exp": rank.experience,
        "next_level_exp": next_level_exp
    }


def calculate_experience(activity,
                         achievements,
                         daily_visits_count: int) -> int:
    """
    Рассчитывает опыт для активности с учетом времени,
    бонусов за организацию и достижений

    :param activity: Объект UserActivity
    :param achievements: Список названий достижений
    :return: Количество опыта
    """

    if activity.leave_time < activity.join_time:
        return 0

    base_exp = 10 + min(20, max(0, (daily_visits_count - 1)) * 5)

    time_spent = activity.leave_time - activity.join_time
    total_minutes = time_spent.total_seconds() / 60

    if total_minutes >= 721:
        return 0

    time_exp = 0

    if total_minutes <= 40:
        time_exp = total_minutes * 0.12
    elif total_minutes <= 80:
        time_exp = 4.8 + (total_minutes - 40) * 0.28
    elif total_minutes <= 120:
        time_exp = 15.2 + (total_minutes - 80) * 0.12
    else:
        extra_time = total_minutes - 120
        time_exp = 20.0 + (extra_time ** 0.7) * 0.05

    achievements_exp = 0
    if not achievements:
        achievements = []
    for achievement in achievements:
        if achievement in ACHIEVEMENT_BONUSES:
            achievements_exp += ACHIEVEMENT_BONUSES[achievement]
    total_exp = base_exp + time_exp + achievements_exp
    return max(0, int(round(total_exp)))
