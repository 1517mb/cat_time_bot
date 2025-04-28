import logging
from http import HTTPStatus

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


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
