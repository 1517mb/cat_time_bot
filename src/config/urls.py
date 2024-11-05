from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("catbot/", admin.site.urls),
    path("unicorn/", include("django_unicorn.urls")),
    path("", include("generator.urls")),
]
