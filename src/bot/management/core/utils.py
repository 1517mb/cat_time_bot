def create_progress_bar(progress: float, length: int = 10) -> str:
    filled = min(length, max(0, int(progress / 100 * length)))
    return f"[{'■' * filled}{'□' * (length - filled)}]"
