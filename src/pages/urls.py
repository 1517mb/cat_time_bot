from django.urls import path
from . import views

app_name = "pages"

urlpatterns = [
    path("about/", views.AboutView.as_view(), name="about"),
    path("privacy-policy/", views.PrivacyPolicyView.as_view(),
         name="privacy_policy"),
    path("terms-of-use/", views.TermsOfUseView.as_view(), name="terms_of_use"),
    path("password-guide/", views.PasswordGuideView.as_view(),
         name="password_guide"),
    path("admin-checklist/", views.AdminChecklistView.as_view(),
         name="admin_checklist"),
    path("security-tools/", views.SecurityToolsView.as_view(),
         name="security_tools"),
    path("faq/", views.FAQView.as_view(), name="faq"),
]
