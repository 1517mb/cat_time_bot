from django.apps import AppConfig
from core.constants import BOT_APP_VERBOSE


class BotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "bot"
    verbose_name = BOT_APP_VERBOSE
