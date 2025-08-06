import logging
import secrets
import string

from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_POST

from bot.models import DailytTips
from .forms import PasswordGeneratorForm

logger = logging.getLogger(__name__)

DEFAULT_PASSWORD_LENGTH = 12
PASSWORD_CHARSETS = {
    "letters": string.ascii_letters,
    "digits": string.digits,
    "special": string.punctuation,
}


def index(request):
    """Главная страница генератора паролей"""
    initial_data = {
        "length": DEFAULT_PASSWORD_LENGTH,
        "include_digits": True,
        "include_special_chars": False,
        "include_hyphen": True,
        "include_underscore": False
    }
    form = PasswordGeneratorForm(initial=initial_data)
    return render(request, "index.html", {"form": form})


@require_http_methods(["GET", "POST"])
def generate_password(request):
    """Генерация пароля через HTMX"""
    try:
        if request.method == "POST":
            form = PasswordGeneratorForm(request.POST)
            if form.is_valid():
                length = form.cleaned_data["length"]
                include_digits = form.cleaned_data["include_digits"]
                include_special_chars = form.cleaned_data[
                    "include_special_chars"]
                include_hyphen = form.cleaned_data.get("include_hyphen", False)
                include_underscore = form.cleaned_data.get(
                    "include_underscore", False)

                characters = PASSWORD_CHARSETS["letters"]
                if include_digits:
                    characters += PASSWORD_CHARSETS["digits"]
                if include_special_chars:
                    characters += PASSWORD_CHARSETS["special"]

                # Определяем обязательные разделители
                required_separators = []
                if include_hyphen:
                    required_separators.append("-")
                if include_underscore:
                    required_separators.append("_")
                min_required_length = len(required_separators) * 2
                if length < min_required_length:
                    logger.warning("Длина пароля меньше минимально необходимой: %s < %s", # noqa
                                   length, min_required_length)
                    return HttpResponse(f"Длина пароля должна быть не менее {min_required_length} символов для выбранных разделителей", status=400) # noqa

                if length < 8:
                    logger.warning("Слишком маленькая длина пароля: %s",
                                   length)
                    return HttpResponse("Минимальная длина пароля - 4 символа",
                                        status=400)

                # Генерируем пароль с обязательными разделителями
                password = generate_password_with_min_separators(
                    length, characters, required_separators
                )
                return render(request,
                              "password_partial.html",
                              {"password": password})
            logger.warning("Неверные данные формы: %s", form.errors)
            return render(request, "form_errors_partial.html", {"form": form})
        return index(request)
    except Exception as e:
        logger.error("Ошибка при генерации пароля: %s", str(e), exc_info=True)
        return HttpResponse("Внутренняя ошибка сервера", status=500)


def generate_password_with_min_separators(length, characters,
                                          required_separators):
    """Генерирует пароль с минимум 2 символами каждого
    обязательного разделителя"""
    if not required_separators:
        return "".join(secrets.choice(characters) for _ in range(length))
    password_chars = []
    for separator in required_separators:
        password_chars.extend([separator, separator])
    remaining_length = length - len(password_chars)
    for _ in range(remaining_length):
        password_chars.append(secrets.choice(characters))
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)


@require_POST
def copy_password(request):
    """Обработчик копирования пароля"""
    return JsonResponse({"status": "ok"})


def daily_tips_view(request):
    """Список полезных советов с пагинацией"""
    tips_list = DailytTips.objects.filter(
        is_published=True
    ).order_by("-pub_date")

    paginator = Paginator(tips_list, 6)
    page_number = request.GET.get("page")
    tips = paginator.get_page(page_number)

    current_page = tips.number
    total_pages = paginator.num_pages

    start_page = max(1, current_page - 2)
    end_page = min(total_pages, current_page + 2)
    page_range = range(start_page, end_page + 1)

    context = {
        "tips": tips,
        "page_range": page_range,
        "current_page": current_page,
        "total_pages": total_pages
    }
    return render(request, "tips.html", context)


def daily_tip_detail_view(request, pk):
    """Детальный просмотр совета"""
    tip = get_object_or_404(DailytTips, pk=pk, is_published=True)

    from django.db.models import F
    DailytTips.objects.filter(pk=tip.pk).update(
        views_count=F('views_count') + 1)

    tip.refresh_from_db()

    return render(request, "tip_detail.html", {"tip": tip})
