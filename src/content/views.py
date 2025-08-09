import logging
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import ExtractMonth, ExtractYear
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView
from django.views.generic.base import TemplateView

from bot.models import DailytTips

from .forms import ProgramFilterForm
from .models import News, Program

logger = logging.getLogger(__name__)

User = get_user_model


@never_cache
@require_http_methods(["GET", "HEAD"])
def custom_403(request, exception=None):
    """Обработчик ошибок 403 Forbidden"""
    return render(
        request,
        "errors/403.html",
        status=HTTPStatus.FORBIDDEN
    )


@never_cache
@require_http_methods(["GET", "HEAD"])
def custom_404(request, exception=None):
    """Обработчик ошибок 404 Not Found"""
    return render(
        request,
        "errors/404.html",
        status=HTTPStatus.NOT_FOUND
    )


@never_cache
@require_http_methods(["GET", "HEAD"])
def custom_500(request):
    """Обработчик ошибок 500 Internal Server Error"""
    return render(
        request,
        "errors/500.html",
        status=HTTPStatus.INTERNAL_SERVER_ERROR
    )


def robots_txt(request):
    """
    Возвращает содержимое файла robots.txt, которое инструктирует
    веб-роботов, как взаимодействовать с сайтом. Он запрещает доступ к
    определенным директориям и разрешает доступ к другим.
    """

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
    return HttpResponse(content,
                        content_type="text/plain")


def global_search_view(request):
    """Страница глобального поиска по сайту"""
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
    """Список новостей"""
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
                Q(title__icontains=search_query) | # noqa
                Q(content__icontains=search_query)
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
    """Детальный просмотр новости"""
    model = News
    template_name = "content/news_detail.html"
    context_object_name = "news"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return News.objects.filter(is_published=True)


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
    template_name = "news/by_author.html"
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
    paginate_by = 9

    def get_queryset(self):
        queryset = Program.objects.filter(verified=True)
        form = ProgramFilterForm(self.request.GET)

        if form.is_valid():
            search = form.cleaned_data.get("search")
            search_in = form.cleaned_data.get("search_in")
            sort_by = form.cleaned_data.get("sort_by")
            min_rating = form.cleaned_data.get("min_rating")

            # Поиск
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
                queryset = queryset.filter(rating__gte=min_rating)

            if sort_by:
                queryset = queryset.order_by(sort_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = ProgramFilterForm(self.request.GET)
        return context


class ProgramDetailView(DetailView):
    model = Program
    template_name = "content/program_detail.html"
    context_object_name = "program"

    def get_queryset(self):
        return Program.objects.filter(verified=True)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        obj.increment_downloads()
        return obj
