from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("catbot/", admin.site.urls),
    path("markdownx/", include("markdownx.urls")),
    path("", include("generator.urls")),
]
