from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("catbot/", admin.site.urls),
    path("markdownx/", include("markdownx.urls")),
    path("", include("generator.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
