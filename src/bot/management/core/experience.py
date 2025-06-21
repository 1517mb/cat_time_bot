import re

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
    base_exp = 10 + min(20, (daily_visits_count - 1) * 5)

    time_spent = activity.leave_time - activity.join_time
    total_minutes = time_spent.total_seconds() // 60

    time_exp = 0
    remaining_minutes = total_minutes
    rate_period = 5
    hour_block = 0
    while remaining_minutes > 0:
        block_minutes = min(remaining_minutes, 60)
        block_exp = block_minutes // rate_period
        time_exp += block_exp
        remaining_minutes -= block_minutes
        hour_block += 1
        rate_period = 5 + 5 * hour_block

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
