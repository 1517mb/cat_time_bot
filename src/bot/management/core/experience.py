import re
from asgiref.sync import sync_to_async
from bot.models import SeasonRank

COMPANY_BONUSES = {
    r'(?i)ум|ума|ум аркитекс': 50,
    r'(?i)прогресс|фирма прогресс': 30,
    r'(?i)инел|дисплей': 25,
    r'(?i)тсн|tsn': 15,
    r'(?i)имбиан|imbian|имбиан лаб': 10,
}

ACHIEVEMENT_BONUSES = {
    "Первая кровь": 10,
    "Ночная смена? Или просто забыл уйти?": 15,
    "Кофеиновый марафонец": 10,
    "Сова компании": 10,
    "Лучший сотрудник": 30,
    "Командный игрок": 15,
    "А можно мне ещё выезд?": 10,
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

    title = await sync_to_async(lambda: rank.level_title.title)()
    category = await sync_to_async(
        lambda: rank.level_title.get_category_display())()
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
    base_exp = 10 + min(20, max(0, (daily_visits_count - 1)) * 5)

    time_spent = activity.leave_time - activity.join_time
    total_minutes = time_spent.total_seconds() / 60

    time_exp = 0
    hour_blocks = total_minutes // 60

    for hour in range(int(hour_blocks)):
        if hour == 0:
            time_exp += 12
        elif hour == 1:
            time_exp += 6
        else:
            time_exp += 4

    remaining_minutes = total_minutes % 60
    if hour_blocks == 0:
        time_exp += remaining_minutes / 5
    elif hour_blocks == 1:
        time_exp += remaining_minutes / 10
    else:
        time_exp += remaining_minutes / 15

    company_bonus = 0
    company_name = activity.company.name
    for pattern, bonus in COMPANY_BONUSES.items():
        if re.search(pattern, company_name):
            company_bonus = bonus
            break

    achievements_exp = 0
    if not achievements:
        achievements = []
    for achievement in achievements:
        if achievement in ACHIEVEMENT_BONUSES:
            achievements_exp += ACHIEVEMENT_BONUSES[achievement]

    return base_exp + time_exp + company_bonus + achievements_exp
