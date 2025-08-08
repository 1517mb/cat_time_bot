from django.urls import path
from . import views

app_name = "pages"

urlpatterns = [
    path("about/", views.AboutView.as_view(), name="about"),
    path("privacy-policy/", views.PrivacyPolicyView.as_view(),
         name="privacy_policy"),
    path("terms-of-use/", views.TermsOfUseView.as_view(), name="terms_of_use"),
]
