import logging
import secrets
import string

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_POST

from bot.models import DailytTips, DailytTipView, Tag

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
                # Рассчитываем время взлома
                crack_info = estimate_cracking_time(form.cleaned_data)
                return render(request,
                              "password_partial.html",
                              {"password": password,
                               "crack_info": crack_info})
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


def estimate_cracking_time(form_data):
    """
    Рассчитывает время взлома и возвращает СЛОВАРЬ
    с текстом и CSS-классом цвета.
    """
    length = form_data.get("length")
    if not length:
        return {"text": "не удалось рассчитать",
                "color_class": "has-text-grey"}
    character_pool_size = len(string.ascii_letters)
    if form_data.get("include_digits"):
        character_pool_size += len(string.digits)
    if form_data.get("include_special_chars"):
        special_chars = string.punctuation.replace("-", "").replace("_", "")
        character_pool_size += len(special_chars)
    if form_data.get("include_hyphen"):
        character_pool_size += 1
    if form_data.get("include_underscore"):
        character_pool_size += 1
    total_combinations = character_pool_size ** length
    guesses_per_second = 10**10
    seconds_to_crack = (total_combinations / 2) / guesses_per_second
    if seconds_to_crack < 60 * 60 * 24:
        color_class = "has-text-danger"
        if seconds_to_crack < 1:
            text = "мгновенно"
        elif seconds_to_crack < 60:
            text = f"около {int(seconds_to_crack)} сек."
        elif seconds_to_crack < 60 * 60:
            text = f"около {int(seconds_to_crack / 60)} мин."
        else:
            text = f"около {int(seconds_to_crack / 3600)} ч."
        return {"text": text, "color_class": color_class}
    days = seconds_to_crack / (3600 * 24)
    if days < 365 * 100:
        color_class = "has-text-warning"
        if days < 365:
            text = f"около {int(days)} дн."
        else:
            text = f"около {int(days / 365)} лет"
        return {"text": text, "color_class": color_class}
    color_class = "has-text-success"
    years = days / 365
    if years < 1_000_000:
        text = f"около {int(years / 1_000)} тыс. лет"
    else:
        text = f"около {int(years / 1_000_000)} млн. лет"
    return {"text": text, "color_class": color_class}


@require_POST
def copy_password(request):
    """Обработчик копирования пароля"""
    return JsonResponse({"status": "ok"})


def daily_tips_view(request):
    """Список полезных советов с пагинацией, поиском и фильтрацией по тегам"""
    tips_list = DailytTips.objects.filter(
        is_published=True).order_by("-pub_date")
    all_tags = Tag.objects.all()
    search_query = request.GET.get('q')
    if search_query:
        tips_list = tips_list.filter(
            Q(title__icontains=search_query) | Q(
                content__icontains=search_query)
        )
    selected_tag_ids = request.GET.getlist('tags')
    if selected_tag_ids:
        try:
            selected_tag_ids = [int(id) for id in selected_tag_ids]
            tips_list = tips_list.filter(
                tags__id__in=selected_tag_ids).distinct()
        except (ValueError, TypeError):
            selected_tag_ids = []
    paginator = Paginator(tips_list, 6)
    page_number = request.GET.get("page")
    try:
        tips = paginator.page(page_number)
    except PageNotAnInteger:
        tips = paginator.page(1)
    except EmptyPage:
        tips = paginator.page(paginator.num_pages)
    page_range = paginator.get_elided_page_range(  # type: ignore
        number=tips.number,
        on_each_side=2,
        on_ends=1
    )
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']
    query_string = query_params.urlencode()
    popular_tips = DailytTips.objects.filter(
        is_published=True).order_by('-views_count')[:5]
    context = {
        "tips": tips,
        "search_query": search_query or '',
        "all_tags": all_tags,
        "selected_tag_ids": selected_tag_ids,
        "current_page": tips.number,
        "total_pages": paginator.num_pages,
        "popular_tips": popular_tips,
        "page_range": page_range,
        "ellipsis": "...",
        "query_string": query_string,
    }
    return render(request, "tips.html", context)


def get_client_ip(request):
    """Определение IP клиента"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def daily_tip_detail_view(request, pk):
    """Детальный просмотр совета с уникальным учётом и навигацией"""
    tip = get_object_or_404(DailytTips, pk=pk)
    client_ip = get_client_ip(request)
    if not DailytTipView.already_viewed(tip.pk, client_ip, ttl_minutes=30):
        DailytTips.objects.filter(pk=tip.pk).update(
            views_count=F('views_count') + 1)
        DailytTipView.log_view(tip, client_ip)

    tip.refresh_from_db()
    next_tip = DailytTips.objects.filter(
        is_published=True,
        pub_date__gt=tip.pub_date
    ).order_by('pub_date').first()
    prev_tip = DailytTips.objects.filter(
        is_published=True,
        pub_date__lt=tip.pub_date
    ).order_by('-pub_date').first()

    context = {
        "tip": tip,
        "next_tip": next_tip,
        "prev_tip": prev_tip,
    }
    return render(request, "tip_detail.html", context)
