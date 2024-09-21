from django.contrib import admin
from import_export.admin import ExportMixin
from import_export.formats import base_formats

from bot.models import Company, UserActivity
from bot.resources import UserActivityResource
from core.constants import SITE_HEADER, SITE_TITLE

admin.site.site_header = SITE_HEADER
admin.site.site_title = SITE_TITLE


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name", )


@admin.register(UserActivity)
class UserActivityAdmin(ExportMixin, admin.ModelAdmin):
    resource_class = UserActivityResource
    list_display = (
        "id",
        "username",
        "company",
        "join_time",
        "leave_time",
        "get_spent_time")
    list_filter = ("company", "username")
    search_fields = ("username", "company__name")

    def get_export_formats(self):
        formats = (
            base_formats.XLS,
            base_formats.XLSX,
        )
        return [f for f in formats if f().can_export()]
