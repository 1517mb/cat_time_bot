from django.apps import AppConfig

from core.constants import CONTENT_APP_VERBOSE


class ContentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "content"
    verbose_name = CONTENT_APP_VERBOSE
