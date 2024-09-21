from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("catbot/", admin.site.urls),
]
