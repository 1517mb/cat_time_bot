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

from .models import News

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
    template_name = "news/latest.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["latest_news"] = News.objects.filter(
            is_published=True
        ).order_by("-created_at")[:5]
        return context
