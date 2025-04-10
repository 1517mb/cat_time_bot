from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from http import HTTPStatus
import logging

logger = logging.getLogger(__name__)


@never_cache
@require_http_methods(["GET", "HEAD"])
def custom_403(request, exception=None):
    """Handler for 403 Forbidden errors"""
    return render(
        request,
        "errors/403.html",
        status=HTTPStatus.FORBIDDEN
    )


@never_cache
@require_http_methods(["GET", "HEAD"])
def custom_404(request, exception=None):
    """Handler for 404 Not Found errors"""
    return render(
        request,
        "errors/404.html",
        status=HTTPStatus.NOT_FOUND
    )


@never_cache
@require_http_methods(["GET", "HEAD"])
def custom_500(request):
    """Handler for 500 Internal Server Error"""
    return render(
        request,
        "errors/500.html",
        status=HTTPStatus.INTERNAL_SERVER_ERROR
    )
