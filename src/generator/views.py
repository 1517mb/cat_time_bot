import logging
import string

from django.core.cache import cache
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import F, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods, require_POST

from bot.models import DailytTips, DailytTipView, SiteStatistics, Tag
from bot.services import GamificationService

from .forms import PASSWORD_CHARSETS, IpLookupForm, PasswordGeneratorForm
from .utils import (
    calculate_crack_time,
    generate_password_safe,
    get_client_ip,
    get_ip_info,
    get_user_agent_info,
)

logger = logging.getLogger(__name__)

DEFAULT_PASSWORD_LENGTH = 12


def index(request: HttpRequest) -> HttpResponse:
    """Главная страница генератора паролей."""
    stats = SiteStatistics.get_stats()
    raw_count = stats.total_passwords_generated
    formatted_count = GamificationService.format_number(raw_count)
    random_tip = GamificationService.get_smart_random_tip(request)

    initial_data = {
        "length": DEFAULT_PASSWORD_LENGTH,
        "include_digits": True,
        "include_special_chars": False,
        "include_hyphen": True,
        "include_underscore": False
    }
    form = PasswordGeneratorForm(initial=initial_data)

    context = {
        "form": form,
        "total_passwords": formatted_count,
        "random_tip": random_tip
    }
    return render(request, "index.html", context)


@require_http_methods(["GET", "POST"])
def generate_password(request: HttpRequest) -> HttpResponse:
    """Генерация пароля через HTMX."""
    try:
        if request.method == "POST":
            form = PasswordGeneratorForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                chars = PASSWORD_CHARSETS["letters"]
                if data["include_digits"]:
                    chars += PASSWORD_CHARSETS["digits"]
                if data["include_special_chars"]:
                    chars += PASSWORD_CHARSETS["special"]

                req_separators = []
                if data.get("include_hyphen"):
                    req_separators.append("-")
                if data.get("include_underscore"):
                    req_separators.append("_")
                password = generate_password_safe(
                    data["length"], chars, req_separators
                )
                is_limited = GamificationService.is_rate_limited(request)
                if not is_limited:
                    new_cnt = GamificationService.increment_global_counter()
                    count_fmt = GamificationService.format_number(new_cnt)
                else:
                    stats = SiteStatistics.get_stats()
                    count_fmt = GamificationService.format_number(
                        stats.total_passwords_generated
                    )
                new_tip = GamificationService.get_smart_random_tip(request)
                crack_info = calculate_crack_time(data)
                main_html = render_to_string(
                    "password_partial.html",
                    {"password": password, "crack_info": crack_info},
                    request=request
                )
                gamification_html = render_to_string(
                    "generator/partials/gamification_oob.html",
                    {"total_passwords": count_fmt, "random_tip": new_tip},
                    request=request
                )
                return HttpResponse(main_html + gamification_html)
            return render(
                request, "form_errors_partial.html", {"form": form}
            )

        return index(request)
    except Exception as e:
        logger.error(
            "Error generating password: %s", str(e), exc_info=True
        )
        return HttpResponse("Внутренняя ошибка сервера", status=500)


@require_POST
def copy_password(request: HttpRequest) -> JsonResponse:
    """API endpoint для копирования (логирование, если нужно)."""
    return JsonResponse({"status": "ok"})


def daily_tips_view(request: HttpRequest) -> HttpResponse:
    """Список советов с пагинацией и кешированием популярных."""
    tips_qs = DailytTips.objects.filter(
        is_published=True
    ).prefetch_related("tags").order_by("-pub_date")

    all_tags = Tag.objects.all()
    search_query = request.GET.get("q")

    if search_query:
        tips_qs = tips_qs.filter(
            Q(title__icontains=search_query) |  # noqa
            Q(content__icontains=search_query)
        )
    selected_tags = request.GET.getlist("tags")
    if selected_tags:
        try:
            ids = [int(i) for i in selected_tags]
            tips_qs = tips_qs.filter(tags__id__in=ids).distinct()
        except (ValueError, TypeError):
            selected_tags = []

    paginator = Paginator(tips_qs, 6)
    page_number = request.GET.get("page")
    try:
        tips = paginator.page(page_number)  # type: ignore
    except PageNotAnInteger:
        tips = paginator.page(1)
    except EmptyPage:
        tips = paginator.page(paginator.num_pages)
    popular_tips = cache.get("popular_tips_sidebar")
    if not popular_tips:
        popular_tips = list(
            DailytTips.objects.filter(is_published=True)
            .order_by("-views_count")[:5]
        )
        cache.set("popular_tips_sidebar", popular_tips, 300)
    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "tips": tips,
        "search_query": search_query or "",
        "all_tags": all_tags,
        "selected_tag_ids": [int(x) for x in selected_tags],
        "page_range": paginator.get_elided_page_range(  # type: ignore
            number=tips.number, on_each_side=2, on_ends=1
        ),
        "popular_tips": popular_tips,
        "query_string": query_params.urlencode(),
    }
    return render(request, "tips.html", context)


def daily_tip_detail_view(
    request: HttpRequest, pk: int
) -> HttpResponse:
    """Детальный просмотр совета с навигацией."""
    tip = get_object_or_404(DailytTips, pk=pk)
    client_ip = get_client_ip(request)

    if not DailytTipView.already_viewed(
        tip.pk, client_ip, ttl_minutes=30
    ):
        DailytTips.objects.filter(pk=tip.pk).update(
            views_count=F("views_count") + 1
        )
        DailytTipView.log_view(tip, client_ip)
        tip.refresh_from_db()
        cache.delete("popular_tips_sidebar")
    next_tip = DailytTips.objects.filter(
        is_published=True, pub_date__gt=tip.pub_date
    ).order_by("pub_date").first()

    prev_tip = DailytTips.objects.filter(
        is_published=True, pub_date__lt=tip.pub_date
    ).order_by("-pub_date").first()

    context = {
        "tip": tip,
        "next_tip": next_tip,
        "prev_tip": prev_tip
    }
    return render(request, "tip_detail.html", context)


def my_ip_view(request: HttpRequest) -> HttpResponse:
    """Отображает техническую информацию о клиенте."""
    ip_address = get_client_ip(request)
    ua_string = request.META.get("HTTP_USER_AGENT", "")
    ua_data = get_user_agent_info(ua_string)
    context = {
        "ip_address": ip_address,
        "browser": ua_data["browser"],
        "os": ua_data["os"],
        "device": ua_data["device"],
        "is_mobile": ua_data["is_mobile"],
        "ua_raw": ua_string,
    }
    return render(request, "generator/tools/my_ip.html", context)


def whois_view(request: HttpRequest) -> HttpResponse:
    user_ip = get_client_ip(request)
    result_data = None
    error_message = None

    if "host" in request.GET:
        form = IpLookupForm(request.GET)
        if form.is_valid():
            target = form.cleaned_data["host"]
            result_data, error_message = get_ip_info(target)
            if result_data:
                if "latitude" in result_data and result_data["latitude"]:
                    result_data["latitude"] = str(
                        result_data["latitude"]).replace(",", ".")
                if "longitude" in result_data and result_data["longitude"]:
                    result_data["longitude"] = str(
                        result_data["longitude"]).replace(",", ".")
    else:
        form = IpLookupForm(initial={"host": user_ip})
    context = {
        "form": form,
        "result": result_data,
        "error": error_message,
        "user_ip": user_ip
    }
    return render(request, "generator/tools/whois.html", context)
