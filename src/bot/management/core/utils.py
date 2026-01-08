def create_progress_bar(progress: float, length: int = 10) -> str:
    filled = min(length, max(0, int(progress / 100 * length)))
    return f"[{'■' * filled}{'□' * (length - filled)}]"


def truncate_markdown_safe(text: str, max_length: int) -> str:
    """
    Безопасно обрезает текст, сохраняя валидность Markdown разметки.

    Эта функция обрезает текст по последнему слову в пределах max_length
    и автоматически закрывает любые незакрытые теги форматирования
    (такие как *, **, _, ~, `).

    Args:
        text: Исходный текст для обрезки.
        max_length: Максимальная желаемая длина.

    Returns:
        Обрезанный и отформатированный текст с многоточием.
    """
    if len(text) <= max_length:
        return text
    truncated_text = text[:max_length].rsplit(" ", 1)[0]
    markdown_pairs = [
        ("**", "**"), ("*", "*"), ("_", "_"),
        ("~", "~"), ("`", "`")
    ]
    for open_tag, close_tag in markdown_pairs:
        if truncated_text.count(open_tag) % 2 != 0:
            truncated_text += close_tag

    return truncated_text + "..."


def get_time_declension(days: int) -> tuple[str, str]:
    """
    Возвращает правильную форму глагола и существительного для дней.
    Пример:
    1 -> ("Остался", "день")
    2 -> ("Осталось", "дня")
    5 -> ("Осталось", "дней")
    """
    if 11 <= days % 100 <= 19:
        day_word = "дней"
    else:
        last_digit = days % 10
        if last_digit == 1:
            day_word = "день"
        elif 2 <= last_digit <= 4:
            day_word = "дня"
        else:
            day_word = "дней"
    verb = "Остался" if days == 1 else "Осталось"
    return verb, day_word
