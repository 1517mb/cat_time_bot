from django import forms
from django.contrib import admin
from django.utils.html import format_html
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import News, Program


class NewsAdminForm(forms.ModelForm):
    """Форма для новостей с расширенным редактором."""
    class Meta:
        model = News
        fields = "__all__"
        widgets = {
            "content": CKEditor5Widget(
                attrs={"class": "django_ckeditor_5"},
                config_name="extends"
            ),
        }


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    form = NewsAdminForm
    list_select_related = ("author",)
    list_display = ("id", "title", "author", "is_published",
                    "created_at", "display_image")
    list_display_links = ("id", "title")
    list_filter = ("is_published", "created_at", "author")
    search_fields = ("title", "content", "author__username")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "display_image_preview")
    list_editable = ("is_published",)
    date_hierarchy = "created_at"
    save_on_top = True

    fieldsets = (
        ("Основное", {
            "fields": ("title", "slug", "content", "author", "is_published")
        }),
        ("Медиа", {
            "fields": ("image", "display_image_preview"),
        }),
        ("Даты", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="Фото")
    def display_image(self, obj):
        """Для списка объектов (маленькая)"""
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; object-fit: cover;" />', obj.image.url) # noqa
        return "—"

    @admin.display(description="Предпросмотр")
    def display_image_preview(self, obj):
        """Для карточки редактирования (побольше)"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 200px;" />', obj.image.url)
        return "Нет изображения"

    def save_model(self, request, obj, form, change):
        """Автоматически устанавливаем автора при создании"""
        if not obj.pk and not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)


class ProgramAdminForm(forms.ModelForm):
    """Форма для программ с обычным редактором."""
    class Meta:
        model = Program
        fields = "__all__"
        widgets = {
            "description": CKEditor5Widget(
                attrs={"class": "django_ckeditor_5"},
                config_name="extends"
            ),
        }


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    form = ProgramAdminForm
    list_display = ("id", "name", "downloads",
                    "rating", "verified", "created_at")
    list_display_links = ("id", "name")
    list_filter = ("verified", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("downloads", "rating_sum", "ratings_count",
                       "created_at", "updated_at")
    save_on_top = True
    list_per_page = 20

    fieldsets = (
        ("Информация о программе", {
            "fields": ("name", "description", "image", "verified")
        }),
        ("Файлы", {
            "fields": ("file", "external_download_link")
        }),
        ("Статистика", {
            "fields": ("downloads", "rating_sum", "ratings_count"),
            "classes": ("collapse",)
        }),
        ("Даты", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
