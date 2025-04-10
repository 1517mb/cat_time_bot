from django.conf import settings
from django.conf.urls import handler403, handler404, handler500
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

handler403 = "content.views.custom_403" # noqa
handler404 = "content.views.custom_404" # noqa
handler500 = "content.views.custom_500" # noqa

urlpatterns = [
    path("catbot/", admin.site.urls),
    path("markdownx/", include("markdownx.urls")),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("", include("generator.urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
