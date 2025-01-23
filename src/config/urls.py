from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("catbot/", admin.site.urls),
    path("unicorn/", include("django_unicorn.urls")),
    path("markdownx/", include("markdownx.urls")),
    path("", include("generator.urls")),
]
