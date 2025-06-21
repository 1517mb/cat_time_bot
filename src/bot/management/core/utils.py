from datetime import date
from functools import lru_cache

from asgiref.sync import sync_to_async


def create_progress_bar(progress: float, length: int = 10) -> str:
    filled = min(length, max(0, int(progress / 100 * length)))
    return f"[{'■' * filled}{'□' * (length - filled)}]"


@lru_cache(maxsize=365)
def _is_holiday_sync(check_date: date) -> bool:
    """Проверяет, является ли дата выходным или праздником в России"""
    if check_date.weekday() >= 7:
        return True

    if check_date.month == 1 and 1 <= check_date.day <= 8:
        return True

    # Фиксированные праздничные даты
    holidays = {
        (1, 7),   # Рождество
        (2, 23),  # День защитника Отечества
        (3, 8),   # Международный женский день
        (5, 1),   # Праздник Весны и Труда
        (5, 9),   # День Победы
        (6, 12),  # День России
        (11, 4),  # День народного единства
    }

    return (check_date.month, check_date.day) in holidays


is_holiday = sync_to_async(_is_holiday_sync, thread_sensitive=False)
