from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from bot.models import DailytTips
from content.models import News, Program


class NewsSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return News.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at


class ProgramSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Program.objects.filter(verified=True)

    def lastmod(self, obj):
        return obj.updated_at


class TipsSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.9

    def items(self):
        return DailytTips.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.pub_date

    def location(self, obj):
        return reverse('tip_detail', args=[obj.pk])
