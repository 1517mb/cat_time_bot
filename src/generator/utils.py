import secrets
import socket
import string
from typing import Any, Dict, List

import requests
from django.http import HttpRequest
from ua_parser import user_agent_parser


def get_client_ip(request: HttpRequest) -> str:
    """Получает IP-адрес клиента с учетом прокси."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")  # type: ignore


def generate_password_safe(
    length: int, chars: str, separators: List[str]
) -> str:
    """
    Генерирует криптостойкий пароль с гарантированным наличием
    указанных разделителей.
    """
    if not separators:
        return "".join(secrets.choice(chars) for _ in range(length))

    pwd_chars = []
    for sep in separators:
        pwd_chars.extend([sep, sep])

    remaining = length - len(pwd_chars)
    for _ in range(remaining):
        pwd_chars.append(secrets.choice(chars))

    secrets.SystemRandom().shuffle(pwd_chars)
    return "".join(pwd_chars)


def calculate_crack_time(data: Dict[str, Any]) -> Dict[str, str]:
    """
    Оценивает время взлома.
    Скорость: 1 триллион переборов/сек (мощный GPU-кластер).
    """
    length = data.get("length", 0)
    if not length:
        return {"text": "ошибка", "color_class": "has-text-grey"}
    pool_size = len(string.ascii_letters)
    if data.get("include_digits"):
        pool_size += 10
    if data.get("include_special_chars"):
        specials = string.punctuation.replace("-", "").replace("_", "")
        pool_size += len(specials)
    if data.get("include_hyphen"):
        pool_size += 1
    if data.get("include_underscore"):
        pool_size += 1
    guesses_per_second = 10**12
    combinations = pool_size ** length
    seconds = (combinations / 2) / guesses_per_second
    if seconds < 3600:
        color = "has-text-danger"
    elif seconds < 31536000:
        color = "has-text-warning"
    else:
        color = "has-text-success"
    minute = 60
    hour = minute * 60
    day = hour * 24
    month = day * 30
    year = day * 365

    if seconds < 1:
        return {"text": "мгновенно", "color_class": color}
    if seconds < minute:
        return {"text": f"{int(seconds)} сек.", "color_class": color}
    if seconds < hour:
        return {"text": f"{int(seconds / minute)} мин.", "color_class": color}
    if seconds < day:
        return {"text": f"{int(seconds / hour)} ч.", "color_class": color}
    if seconds < month:
        return {"text": f"{int(seconds / day)} дн.", "color_class": color}
    if seconds < year:
        return {"text": f"{int(seconds / month)} мес.", "color_class": color}
    years = seconds / year
    if years < 1000:
        return {"text": f"около {int(years)} лет", "color_class": color}
    suffixes = [
        (1_000, "тыс. лет"),
        (1_000_000, "млн. лет"),
        (1_000_000_000, "млрд. лет"),
        (1_000_000_000_000, "трлн. лет"),
        (1_000_000_000_000_000, "квадр. лет"),
        (1_000_000_000_000_000_000, "квинт. лет"),
        (1_000_000_000_000_000_000_000, "секст. лет"),
        (1_000_000_000_000_000_000_000_000, "септ. лет"),
    ]

    for limit, suffix in suffixes:
        if years < limit * 1000:
            value = int(years / limit)
            return {"text": f"около {value} {suffix}", "color_class": color}
    import math
    exponent = int(math.log10(years))
    return {
        "text": f"около 10^{exponent} лет",
        "color_class": color
    }


def get_user_agent_info(ua_string: str) -> Dict[str, Any]:
    """Парсит User-Agent строку и возвращает структурированные данные."""
    parsed = user_agent_parser.Parse(ua_string)

    device_info = parsed.get("device", {})
    device_family = device_info.get("family", "Other")
    is_desktop = "Mac" in device_family or "Windows" in device_family
    is_mobile = device_family != "Other" and not is_desktop

    ua_info = parsed.get("user_agent", {})
    browser = f"{ua_info.get('family')} {ua_info.get('major')}"

    os_info = parsed.get("os", {})
    os_sys = f"{os_info.get('family')} {os_info.get('major')}"

    display_device = (
        device_family if device_family != "Other" else "Desktop"
    )

    return {
        "browser": browser,
        "os": os_sys,
        "device": display_device,
        "is_mobile": is_mobile,
    }


def resolve_host(host):
    """Преобразует домен в IP. Если это уже IP, возвращает его же."""
    host = host.strip()
    if host.startswith("http://"):
        host = host[7:]
    if host.startswith("https://"):
        host = host[8:]
    if "/" in host:
        host = host.split("/")[0]

    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return None


def get_ip_info(host_input):
    """
    Получает информацию об IP или домене.
    Сначала резолвит домен в IP, потом делает запрос к API.
    """
    ip_address = resolve_host(host_input)
    if not ip_address:
        return None, f"Не удалось найти IP для '{host_input}'. Проверьте правильность адреса." # noqa
    try:
        url = f"https://ipwhois.app/json/{ip_address}?lang=ru"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if not data.get('success', True):
            return None, data.get('message', 'Ошибка API')
        if host_input != ip_address:
            data['original_host'] = host_input
        return data, None
    except requests.RequestException:
        return None, "Не удалось соединиться с сервером проверки."
