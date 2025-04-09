from django_ckeditor_5.widgets import CKEditor5Widget
from django import forms
from django.contrib import admin
from django.utils.html import format_html

from .models import News, Program


class NewsAdminForm(forms.ModelForm):
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
    list_display = ("title", "author", "is_published",
                    "created_at", "updated_at", "display_image")
    list_filter = ("is_published", "created_at", "author")
    search_fields = ("title", "content", "author__username")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    list_editable = ("is_published",)
    date_hierarchy = "created_at"
    fieldsets = (
        (None, {
            "fields": ("title", "slug", "content",
                       "author", "image", "is_published")
        }),
        ("Даты", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def display_image(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" />', obj.image.url)
        return "Нет изображения"

    display_image.short_description = "Изображение"

    def get_readonly_fields(self, request, obj=None):
        """Запрещаем редактирование автора после создания"""
        if obj:
            return self.readonly_fields + ("author",)
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        """Автоматически устанавливаем автора при создании"""
        if not obj.pk and not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)


class ProgramAdminForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = "__all__"
        widgets = {
            "description": CKEditor5Widget(
                attrs={"class": "django_ckeditor_5"},
                config_name="default"
            ),
        }


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    form = ProgramAdminForm
    list_display = ("name", "downloads", "rating", "verified")
    list_filter = ("verified", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("downloads", "created_at", "updated_at")
