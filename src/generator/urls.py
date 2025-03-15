from django.urls import path

from generator import views

urlpatterns = [
    path("", views.index, name="index"),
    path("tips/", views.daily_tips_view, name="tips"),
    path("generate-password/",
         views.generate_password,
         name="generate_password"),
    path("copy-password/",
         views.copy_password,
         name="copy_password"),
]
