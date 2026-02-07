from asgiref.sync import sync_to_async

from bot.models import LevelTitle, SeasonRank

ACHIEVEMENT_BONUSES = {
    "Первая кровь": 1,
    "Лучший сотрудник": 5,
    "Командный игрок": 5,
    "А можно мне ещё выезд?": 5,
    "Экономлю на пропуске": 5,
    "Читер: Часовщик": -20,
}


async def get_level_info(rank: SeasonRank) -> dict:
    current_level_obj = await sync_to_async(
        lambda: LevelTitle.objects.filter(min_experience__lte=rank.experience)
                                  .order_by("-level")
                                  .first()
    )()

    if not current_level_obj:
        current_level_obj = await sync_to_async(
            lambda: LevelTitle.objects.order_by("level").first())()

    if not current_level_obj:
        return {
            "title": f"Уровень {rank.level}",
            "category": "legend",
            "progress": 0,
            "current_exp": rank.experience,
            "next_level_exp": 0,
            "exp_in_level": 0,
            "exp_to_next": 0,
        }
    next_level_obj = await sync_to_async(
        lambda: LevelTitle.objects.filter(
            level=current_level_obj.level + 1).first()
    )()

    title = current_level_obj.title
    category = current_level_obj.get_category_display()  # type: ignore

    base_exp = current_level_obj.min_experience

    if next_level_obj:
        target_exp = next_level_obj.min_experience
        exp_range = max(1, target_exp - base_exp)
        exp_gained = max(0, rank.experience - base_exp)

        progress = min(100, max(0, (exp_gained / exp_range) * 100))
        next_exp_display = target_exp
    else:
        exp_range = 0
        exp_gained = 0
        progress = 100
        next_exp_display = rank.experience

    return {
        "title": title,
        "category": category,
        "progress": progress,
        "current_exp": rank.experience,
        "next_level_exp": next_exp_display,
        "exp_in_level": exp_gained,
        "exp_to_next": exp_range,
        "effective_level": current_level_obj.level,
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
