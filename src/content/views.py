import logging
from http import HTTPStatus

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import (
    Case,
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    Q,
    When,
)
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView
from django.views.generic.base import TemplateView

from bot.models import DailytTips

from .forms import ProgramFilterForm, RatingForm
from .models import News, Program, ProgramDownload, ProgramVote

logger = logging.getLogger(__name__)

User = get_user_model()


@never_cache
@require_http_methods(["GET", "HEAD"])
def custom_403(request, exception=None):
    return render(request, "errors/403.html", status=HTTPStatus.FORBIDDEN)


@never_cache
@require_http_methods(["GET", "HEAD"])
def custom_404(request, exception=None):
    return render(request, "errors/404.html", status=HTTPStatus.NOT_FOUND)


@never_cache
@require_http_methods(["GET", "HEAD"])
def custom_500(request):
    return render(request, "errors/500.html",
                  status=HTTPStatus.INTERNAL_SERVER_ERROR)


def robots_txt(request):
    content = """
    User-agent: *
    Disallow: /admin/
    Disallow: /accounts/
    Disallow: /private/
    Disallow: /catbot/
    Disallow: /static/
    Disallow: /media/
    Allow: /
    """
    return HttpResponse(content, content_type="text/plain")


def global_search_view(request):
    query = request.GET.get("q", "").strip()
    tips_results = []
    news_results = []

    if query:
        tips_results = DailytTips.objects.filter(
            is_published=True
        ).filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).distinct()
        news_results = News.objects.filter(
            is_published=True
        ).filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        ).distinct()

    context = {
        "query": query,
        "tips_results": tips_results,
        "news_results": news_results,
    }
    return render(request, "content/search_results.html", context)


class NewsListView(ListView):
    model = News
    template_name = "content/list.html"
    context_object_name = "news_list"
    paginate_by = 10

    def get_queryset(self):
        queryset = News.objects.filter(
            is_published=True
        ).order_by("-created_at")

        search_query = self.request.GET.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | Q(
                    content__icontains=search_query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["total_news"] = News.objects.count()
        context["published_news"] = News.objects.filter(
            is_published=True).count()
        return context


class NewsDetailView(DetailView):
    model = News
    template_name = "content/news_detail.html"
    context_object_name = "news"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return News.objects.filter(is_published=True)

    def get_context_data(self, **kwargs):
        """
        Добавляем в контекст список последних новостей для виджета.
        """
        context = super().get_context_data(**kwargs)
        context["latest_news"] = News.objects.filter(
            is_published=True
        ).exclude(
            pk=self.object.pk
        ).order_by("-created_at")[:5]
        return context


class NewsByMonthView(ListView):
    """Новости за определенный месяц"""
    model = News
    template_name = "content/list.html"
    context_object_name = "news_list"
    paginate_by = 10
    allow_empty = False

    def get_queryset(self):
        return News.objects.filter(
            is_published=True,
            created_at__year=self.kwargs["year"],
            created_at__month=self.kwargs["month"]
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["page_title"] = f"Новости за {self.kwargs['month']}.{self.kwargs['year']}" # noqa
        return context


class NewsArchiveView(ListView):
    """Архив новостей"""
    model = News
    template_name = "content/archive.html"
    context_object_name = "news_list"
    paginate_by = 20

    def get_queryset(self):
        return News.objects.filter(
            is_published=True
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["archive_data"] = News.objects.filter(
            is_published=True
        ).annotate(
            year=ExtractYear("created_at"),
            month=ExtractMonth("created_at")
        ).values("year", "month").annotate(
            count=Count("id")
        ).order_by("-year", "-month")
        return context


class NewsByAuthorView(ListView):
    """Новости по автору"""
    model = News
    template_name = "content/news_list.html"
    context_object_name = "news_list"
    paginate_by = 10

    def get_queryset(self):
        self.author = get_object_or_404(User, id=self.kwargs["author_id"])
        return News.objects.filter(
            author=self.author,
            is_published=True
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["author"] = self.author
        author_name = self.author.get_full_name() or self.author.username
        context["page_title"] = f"Публикации автора: {author_name}"
        return context


class LatestNewsView(TemplateView):
    """Последние новости (для виджетов)"""
    template_name = "content/news_latest.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_news"] = News.objects.filter(
            is_published=True
        ).order_by("-created_at")[:5]
        return context


class ProgramListView(ListView):
    model = Program
    template_name = "content/program_list.html"
    context_object_name = "programs"
    paginate_by = 12

    def get_queryset(self):
        queryset = Program.objects.filter(verified=True)
        # Оптимизированная аннотация рейтинга
        queryset = queryset.annotate(
            calculated_rating=ExpressionWrapper(
                Case(
                    When(ratings_count=0, then=0.0),
                    default=1.0 * F("rating_sum") / F("ratings_count"),
                    output_field=FloatField()
                ),
                output_field=FloatField()
            )
        )

        form = ProgramFilterForm(self.request.GET)

        if form.is_valid():
            search = form.cleaned_data.get("search")
            search_in = form.cleaned_data.get("search_in")
            sort_by = form.cleaned_data.get("sort_by")
            min_rating = form.cleaned_data.get("min_rating")

            if search:
                if search_in == "name":
                    queryset = queryset.filter(name__icontains=search)
                elif search_in == "description":
                    queryset = queryset.filter(description__icontains=search)
                else:
                    queryset = queryset.filter(
                        Q(name__icontains=search) | Q(
                            description__icontains=search)
                    )

            if min_rating is not None:
                queryset = queryset.filter(
                    calculated_rating__gte=float(min_rating)
                )

            if sort_by:
                if sort_by == "-rating":
                    queryset = queryset.order_by("-calculated_rating")
                elif sort_by == "rating":
                    queryset = queryset.order_by("calculated_rating")
                elif sort_by == "-downloads":
                    queryset = queryset.order_by("-downloads")
                elif sort_by == "-created_at":
                    queryset = queryset.order_by("-created_at")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = ProgramFilterForm(self.request.GET)
        return context


class ProgramDetailView(DetailView):
    model = Program
    template_name = "content/program_detail.html"
    context_object_name = "program"

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def has_user_voted(self, program_id, client_ip):
        """Проверяет, голосовал ли пользователь по IP за программу"""
        ip_hash = ProgramVote.get_ip_hash(client_ip)
        return ProgramVote.objects.filter(
            program_id=program_id,
            ip_hash=ip_hash
        ).exists()

    def increment_download_with_limit(self, program):
        client_ip = self.get_client_ip(self.request)
        if not ProgramDownload.already_downloaded(program.pk,
                                                  client_ip,
                                                  ttl_hours=24):
            program.increment_downloads()
            ProgramDownload.log_download(program, client_ip)

    def get_queryset(self):
        return Program.objects.filter(verified=True)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        self.increment_download_with_limit(obj)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        program_id = self.object.pk
        client_ip = self.get_client_ip(self.request)
        # Проверка флага в сессии о только что совершенном голосовании
        session_key = f"just_voted_{program_id}"
        just_voted = self.request.session.get(session_key, False)
        if just_voted:
            # Удаляем флаг из сессии после использования
            del self.request.session[session_key]
        # Проверка голосования по куки и IP
        cookie_name = f"voted_program_{program_id}"
        has_voted_cookie = cookie_name in self.request.COOKIES
        has_voted_ip = self.has_user_voted(program_id, client_ip)
        context["rating_form"] = RatingForm()
        context["has_voted"] = has_voted_cookie or has_voted_ip or just_voted
        if just_voted:
            context["vote_method"] = "just_voted"
        else:
            context["vote_method"] = "cookie" if has_voted_cookie else ("ip" if has_voted_ip else None) # noqa
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        program_id = self.object.pk
        client_ip = self.get_client_ip(request)
        cookie_name = f"voted_program_{program_id}"
        # Проверка на повторное голосование по куки
        if cookie_name in request.COOKIES:
            messages.error(request, "Вы уже оценили эту программу (по куки).")
            return redirect("content:program_detail", pk=program_id)
        # Проверка на повторное голосование по IP
        if self.has_user_voted(program_id, client_ip):
            messages.error(request, "Вы уже оценили эту программу (по IP).")
            response = redirect("content:program_detail", pk=program_id)
            response.set_cookie(
                cookie_name,
                "voted",
                max_age=365 * 24 * 60 * 60,
                httponly=True,
                samesite="Lax"
            )
            return response
        form = RatingForm(request.POST)
        if form.is_valid():
            rating_value = int(form.cleaned_data["rating"])
            try:
                with transaction.atomic():
                    self.object.add_rating(rating_value)
                    ProgramVote.create_vote(self.object, client_ip)
                    messages.success(request, "Спасибо за вашу оценку!")
                    response = redirect("content:program_detail",
                                        pk=program_id)
                    response.set_cookie(
                        cookie_name,
                        "voted",
                        max_age=365 * 24 * 60 * 60,
                        httponly=True,
                        samesite="Lax"
                    )
                    request.session[f"just_voted_{program_id}"] = True
                    return response
            except ValidationError as e:
                messages.error(request, str(e))
            except Exception as e:
                logger.error(f"Ошибка при голосовании: {str(e)}")
                messages.error(request,
                               "Произошла ошибка при обработке вашего голоса.")
        else:
            messages.error(request, "Пожалуйста, выберите оценку.")
        return redirect("content:program_detail", pk=program_id)
