from django.contrib import admin
from .models import Program


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("name", "downloads", "rating", "verified")
    list_filter = ("verified", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("downloads", "created_at", "updated_at")
