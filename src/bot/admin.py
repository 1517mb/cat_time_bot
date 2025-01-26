from django.contrib import admin
from django.utils import timezone
from import_export.admin import ExportActionModelAdmin
from import_export.formats import base_formats

from bot.models import Company, UserActivity
from bot.resources import UserActivityResource
from core.constants import SITE_HEADER, SITE_TITLE

from bot.models import DailytTips
from markdownx.admin import MarkdownxModelAdmin

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
    list_display = ("id", "title", "author", "pub_date")
    search_fields = ("title", "content")
    list_filter = ("author", "pub_date", "is_published")
    date_hierarchy = "pub_date"
    list_editable = (
        "is_published",
        "rating",
    )
