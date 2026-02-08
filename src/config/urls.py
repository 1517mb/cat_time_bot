from django.conf import settings
from django.conf.urls import handler403, handler404, handler500
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from content.sitemaps import NewsSitemap, ProgramSitemap, TipsSitemap
from content.views import robots_txt, security_txt
from django.views.generic import TemplateView

sitemaps = {
    "news": NewsSitemap,
    "programs": ProgramSitemap,
    "tips": TipsSitemap,
}

handler403 = "content.views.custom_403" # noqa
handler404 = "content.views.custom_404" # noqa
handler500 = "content.views.custom_500" # noqa

urlpatterns = [
    path("catbot/", admin.site.urls),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("", include("generator.urls")),
    path("content/", include("content.urls")),
    path("pages/", include("pages.urls")),
    path("robots.txt", robots_txt),
    path(
        "security/",
        TemplateView.as_view(
            template_name="pages/security.html",
            extra_context={"security_email": settings.SECURITY_CONTACT_EMAIL},
        ),
        name="security",
    ),
    path(".well-known/security.txt", security_txt),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps},
         name="django.contrib.sitemaps.views.sitemap"),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
