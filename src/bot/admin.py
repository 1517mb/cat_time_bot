from django.contrib import admin
from django.utils import timezone
from import_export.admin import ExportActionModelAdmin
from import_export.formats import base_formats

from bot.models import (
    Achievement,
    Company,
    CurrencyRate,
    DailyStatistics,
    DailytTips,
    LevelTitle,
    Quote,
    Season,
    SeasonRank,
    Tag,
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


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(DailytTips)
class DailytTipsAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "author",
                    "pub_date", "is_published", "rating", "views_count")
    filter_horizontal = ("tags",)
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


@admin.register(SeasonRank)
class SeasonRankAdmin(admin.ModelAdmin):
    list_display = (
        "user_id",
        "username",
        "season",
        "level",
        "experience",
        "formatted_total_time",
        "visits_count",
        "level_title",
        "achieved_at"
    )
    list_filter = (
        "season",
        "level_title",
        "achieved_at"
    )
    search_fields = (
        "user_id",
        "username"
    )
    list_select_related = (
        "season",
        "level_title"
    )
    raw_id_fields = ("season", "level_title")
    readonly_fields = ("achieved_at",)
    list_editable = ("level", "experience", "level_title")
    list_per_page = 25

    def formatted_total_time(self, obj):
        """Форматирует DurationField в читаемый вид (ДНИ ЧАСЫ:ММ:СС)"""
        total_seconds = int(obj.total_time.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days}d {hours}:{minutes:02d}:{seconds:02d}"

    formatted_total_time.short_description = "Общее время"
    formatted_total_time.admin_order_field = "total_time"


@admin.register(LevelTitle)
class LevelTitleAdmin(admin.ModelAdmin):
    list_display = (
        "level",
        "title",
        "category_display",
        "min_experience",
        "short_description"
    )
    list_filter = ("category",)
    search_fields = (
        "title",
        "description"
    )
    list_editable = (
        "title",
        "min_experience"
    )
    ordering = ("level",)
    list_per_page = 25

    def category_display(self, obj):
        """Отображает человеко-читаемое название категории"""
        return dict(
            LevelTitle.LEVEL_CATEGORIES).get(obj.category, obj.category)

    def short_description(self, obj):
        """Сокращает описание для табличного вида"""
        if obj.description:
            return (obj.description[:50] + "..."
                    if len(obj.description) > 50 else obj.description)
        return "-"

    category_display.short_description = "Категория"
    short_description.short_description = "Описание"


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "theme_display",
        "start_date",
        "end_date",
        "is_active",
        "duration_days"
    )
    list_filter = (
        "theme",
        "is_active"
    )
    search_fields = ("name",)
    list_editable = ("is_active",)
    date_hierarchy = "start_date"
    readonly_fields = ("duration_days",)
    list_per_page = 25
    fieldsets = (
        (None, {
            "fields": ("name", "theme", "is_active")
        }),
        ("Даты", {
            "fields": ("start_date", "end_date")
        }),
        ("Дополнительно", {
            "fields": ("duration_days",),
            "classes": ("collapse",)
        })
    )

    def theme_display(self, obj):
        """Отображает тему с эмодзи"""
        return obj.get_theme_display()

    def duration_days(self, obj):
        """Рассчитывает длительность сезона в днях"""
        if obj.start_date and obj.end_date:
            return (obj.end_date - obj.start_date).days
        return "-"

    theme_display.short_description = "Тематика"
    duration_days.short_description = "Длит. (дней)"


@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ("currency", "get_currency_display_name", "rate", "date")
    list_filter = ("currency", "date")
    search_fields = ("currency",)
    ordering = ("-date", "currency")
    list_per_page = 20
    date_hierarchy = "date"

    fields = ("currency", "rate", "date")
    readonly_fields = ("date",)

    def get_currency_display_name(self, obj):
        return obj.get_currency_display()
    get_currency_display_name.short_description = "Валюта"
    get_currency_display_name.admin_order_field = "currency"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs

    def get_search_results(self, request, queryset, search_term):
        queryset, use_distinct = super().get_search_results(
            request, queryset, search_term)
        return queryset, use_distinct
