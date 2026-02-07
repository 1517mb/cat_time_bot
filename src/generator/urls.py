from django.urls import path

from generator import views

urlpatterns = [
    path("", views.index, name="index"),
    path("tips/", views.daily_tips_view, name="tips"),
    path("tips/<int:pk>/", views.daily_tip_detail_view, name="tip_detail"),
    path("generate-password/",
         views.generate_password,
         name="generate_password"),
    path("copy-password/",
         views.copy_password,
         name="copy_password"),
    path("tools/my-ip/", views.my_ip_view, name="my_ip"),
    path("tools/whois/", views.whois_view, name="whois"),
]
