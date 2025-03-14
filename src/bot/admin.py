from django.contrib import admin
from django.utils import timezone
from import_export.admin import ExportActionModelAdmin
from import_export.formats import base_formats
from markdownx.admin import MarkdownxModelAdmin

from bot.models import (
    Achievement,
    Company,
    DailyStatistics,
    DailytTips,
    Quote,
    UserActivity,
)
from bot.resources import UserActivityResource
from core.constants import SITE_HEADER, SITE_TITLE

admin.site.site_header = SITE_HEADER
admin.site.site_title = SITE_TITLE


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name", )


@admin.register(UserActivity)
class UserActivityAdmin(ExportActionModelAdmin):
    resource_class = UserActivityResource
    list_display = (
        "id",
        "username",
        "company",
        "join_time",
        "leave_time",
        "get_spent_time")
    list_filter = ("username", "join_time")
    search_fields = ("username", "company__name")
    readonly_fields = ("get_spent_time", )

    def get_spent_time(self, obj):
        return obj.get_spent_time
    get_spent_time.short_description = "Общее время"

    def get_export_formats(self):
        formats = (
            base_formats.XLS,
            base_formats.XLSX,
        )
        return [f for f in formats if f().can_export()]

    get_export_formats.short_description = "Форматы экспорта"

    actions = ["mark_as_left"]

    def mark_as_left(self, request, queryset):
        queryset.update(leave_time=timezone.now())
    mark_as_left.short_description = "Пометить как покинувших организацию"


@admin.register(DailytTips)
class DailytTipsAdmin(MarkdownxModelAdmin):
    list_display = ("id", "title", "author",
                    "pub_date", "is_published", "rating")
    search_fields = ("title", "content")
    list_filter = ("author", "pub_date", "is_published")
    date_hierarchy = "pub_date"
    list_editable = (
        "is_published",
        "rating",
    )


@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "username",
                    "achievement_name", "achieved_at")
    list_filter = ("achievement_name", "achieved_at")
    search_fields = ("username", "achievement_name")
    ordering = ("-achieved_at",)


@admin.register(DailyStatistics)
class DailyStatisticsAdmin(admin.ModelAdmin):
    list_display = ("id", "user_id", "username",
                    "date", "total_time", "total_trips")
    list_filter = ("date",)
    search_fields = ("username",)
    ordering = ("-date",)


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "source",
                    "text", "is_active")
    search_fields = ("author", "source", "text")
    list_filter = ("is_active",)
