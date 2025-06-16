import asyncio
import os

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from telegram import Bot

from bot.models import Season


class Command(BaseCommand):
    help = "Управление сезонами: создание нового и завершение текущего"

    def handle(self, *args, **kwargs):
        now = timezone.now().date()

        active_seasons = Season.objects.filter(is_active=True,
                                               end_date__lte=now)
        for season in active_seasons:
            season.is_active = False
            season.save()
            self.stdout.write(f"Завершен сезон: {season.name}")

            asyncio.run(self.send_season_end_message(season))

        if not Season.objects.filter(is_active=True).exists():
            new_season = self.create_new_season(now)
            self.stdout.write(f"Создан новый сезон: {new_season.name}")
            asyncio.run(self.send_new_season_message(new_season))

    def create_new_season(self, now):
        """Создает новый сезон на основе текущего месяца"""
        month_to_theme = {
            1: ("winter", "Ледяное царство админов"),
            2: ("winter", "Морозные сервера"),
            3: ("spring", "Весеннее обновление"),
            4: ("spring", "Цветущие патчи"),
            5: ("spring", "Майские багфиксы"),
            6: ("summer", "Летний апдейт"),
            7: ("summer", "Пляжные бекапы"),
            8: ("summer", "Солнечные сервера"),
            9: ("autumn", "Осенний рефакторинг"),
            10: ("autumn", "Листопад фич"),
            11: ("autumn", "Туманные деплои"),
            12: ("winter", "Новогодние сбои"),
        }

        theme, name = month_to_theme.get(now.month, ("winter", "Новый сезон"))

        return Season.objects.create(
            name=f"{name} {now.year}",
            theme=theme,
            start_date=now
        )

    async def send_season_end_message(self, season):
        """Асинхронно отправляет сообщение о завершении сезона"""
        try:
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
            if group_chat_id:
                await bot.send_message(
                    chat_id=group_chat_id,
                    text=(
                        f"🏁 *Сезон {season.name} завершен!*\n\n"
                        "Благодарим всех участников! Результаты сезона "
                        "будут опубликованы в ближайшее время.\n"
                        "Ожидайте начало нового сезона!"
                    ),
                    parse_mode="Markdown"
                )
        except Exception as e:
            self.stdout.write(f"Ошибка отправки сообщения: {e}")

    async def send_new_season_message(self, season):
        """Асинхронно отправляет сообщение о начале нового сезона"""
        try:
            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
            if group_chat_id:
                await bot.send_message(
                    chat_id=group_chat_id,
                    text=(
                        f"🎉 *Начался новый сезон!* 🎉\n\n"
                        f"*{season.name}*\n"
                        f"Период: *{season.start_date.strftime("%d.%m.%Y")} -"
                        f" {season.end_date.strftime("%d.%m.%Y")}*\n\n"
                        "Все уровни и опыт сброшены. Удачи в новом сезоне!\n"
                        "Проверьте свой профиль командой /profile"
                    ),
                    parse_mode="Markdown"
                )
        except Exception as e:
            self.stdout.write(f"Ошибка отправки сообщения: {e}")
