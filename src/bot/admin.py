from django.contrib import admin
from bot.models import Company, UserActivity
from core.constants import SITE_HEADER, SITE_TITLE

admin.site.site_header = SITE_HEADER
admin.site.site_title = SITE_TITLE


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name", )


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "username",
        "company",
        "join_time",
        "leave_time",
        "get_spent_time")
    list_filter = ("company", "username")
    search_fields = ("username", "company__name")
