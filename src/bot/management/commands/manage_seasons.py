import logging
import os
import random
from datetime import datetime, timedelta

from asgiref.sync import async_to_sync
from dateutil.relativedelta import relativedelta
from django.core.management.base import BaseCommand
from django.db.models import Sum, Avg
from django.utils import timezone

from bot.management.commands.start_bot import application
from bot.models import Achievement, Season, SeasonRank

logger = logging.getLogger(__name__)

SEASON_IT_NAMES = {
    'winter': [
        "❄️ Морозный аптайм",
        "⛄ Зимнее шифрование",
        "🧊 Ледяной RAID-массив",
        "🛡️ Фаервол-мороз",
        "❄️ Снежный дата-центр",
        "🧣 Шарфо-сетевая инфраструктура",
        "🔥 Горячий кофе на холодном сервере",
        "🌨️ Снежный DNS-шторм",
        "💻 Зимняя дефрагментация",
        "❄️ Морозный бэкап"
    ],
    'spring': [
        "🌱 Весенний рефакторинг",
        "🌸 Цветущий деплой",
        "🌧️ Дождевой бэкап",
        "🐞 Сезон багфиксов",
        "🔄 Весенний ребут",
        "💾 Роса на SSD",
        "🌿 Зеленый код в производство",
        "🌼 Цветущий API-интерфейс",
        "🚿 Весенняя чистка кода",
        "🪴 Рост нагрузки на сервера"
    ],
    'summer': [
        "☀️ Летний оверклокинг",
        "🏖️ Песочное тестирование",
        "🌊 Волновой DDOS",
        "🔥 Жаркий процессор",
        "🍉 Арбузный компресс",
        "⛱️ Пляжный режим ядра",
        "🌴 Пальмовое дерево зависимостей",
        "🏄‍♂️ Серфинг по логам",
        "🌞 Солнечный аптайм",
        "🍦 Мороженое для серверов"
    ],
    'autumn': [
        "🍁 Листопадный Git Merge",
        "🍂 Осенний сбор мусора",
        "🌧️ Дождливый бэкап",
        "🦃 Индейский аптайм",
        "☕ Кофейный дебаггинг",
        "📉 Падающие листья и показатели",
        "🍄 Грибной рост нагрузки",
        "🌰 Жесткий диск с орехами",
        "🍎 Яблочный патч-вторник",
        "🕸️ Паутина зависимостей"
    ]
}


IT_MEMES = [
    "Попробуйте выключить и включить сезон",
    "Это не баг, это фича сезона",
    "У меня работает, а у васне работает!?",
    "Сезонное обновление: исправлены 99999 багов",
    "Чуть более стабильно, чем прошлый сезон",
    "Быстрее, выше, сильнее... или просто перезагрузите",
    "Тестировалось в продакшене (как всегда)",
    "Документация? Какая документация?",
    "Наш CI/CD пайплайн теперь с видом на океан",
    "Новый сезон - новые непредсказуемые ошибки!"
]


class Command(BaseCommand):
    help = ("Управление жизненным циклом сезонов: "
            "создание, завершение, уведомления")

    def handle(self, *args, **options):
        """Основной обработчик команды управления сезонами"""
        try:
            self.process_expired_seasons()
            self.activate_upcoming_seasons()
            self.create_season_if_needed()
            self.send_ending_soon_notifications()
            logger.info("Управление сезонами успешно завершено")
        except Exception as e:
            logger.error(f"Критическая ошибка в manage_seasons: {e}",
                         exc_info=True)
            self.send_telegram_message(
                f"🚨 *Ошибка управления сезонами!* 🚨\n"
                f"Система столкнулась с проблемой: `{str(e)}`\n"
                f"Пожалуйста, проверьте логи для деталей."
            )

    def process_expired_seasons(self):
        """Завершает истекшие сезоны и награждает победителей"""
        now = timezone.now().date()
        expired_seasons = Season.objects.filter(
            end_date__lt=now,
            is_active=True
        )

        for season in expired_seasons:
            try:
                season.is_active = False
                season.save()
                logger.info(f"Сезон завершен: {season.name}")
                self.award_season_winners(season)
                self.send_season_end_notification(season)
            except Exception as e:
                logger.error(f"Ошибка обработки сезона {season.name}: {e}")

    def activate_upcoming_seasons(self):
        """Активирует сезоны, у которых наступила дата начала"""
        now = timezone.now().date()
        upcoming_seasons = Season.objects.filter(
            start_date__lte=now,
            end_date__gte=now,
            is_active=False
        )

        for season in upcoming_seasons:
            try:
                Season.objects.filter(is_active=True).update(is_active=False)
                season.is_active = True
                season.save()
                logger.info(f"Активирован сезон: {season.name}")
                self.send_season_start_notification(season)
            except Exception as e:
                logger.error(f"Ошибка активации сезона {season.name}: {e}")

    def create_season_if_needed(self):
        """Создает новый сезон, если нет активных"""
        if Season.objects.filter(is_active=True).exists():
            return

        today = timezone.now().date()

        try:
            theme = self.determine_season_theme()
            season_name = self.generate_season_name(theme)
            new_season = Season.objects.create(
                name=season_name,
                theme=theme,
                start_date=today,
                end_date=today + relativedelta(months=3)
            )
            logger.info(f"Создан новый сезон: {season_name}")
            self.send_season_start_notification(new_season)
        except Exception as e:
            logger.error(f"Ошибка создания нового сезона: {e}")
            self.send_telegram_message(
                f"🚨 *Не удалось создать новый сезон!* 🚨\n"
                f"Ошибка: `{str(e)}`\n"
                f"Текущий активный сезон отсутствует!"
            )

    def send_ending_soon_notifications(self):
        """Уведомляет о скором окончании сезона (за 3 дня)"""
        warning_date = timezone.now().date() + timedelta(days=3)
        ending_seasons = Season.objects.filter(
            end_date=warning_date,
            is_active=True
        )
        for season in ending_seasons:
            try:
                self.send_season_ending_soon_notification(season)
            except Exception as e:
                logger.error(
                    f"Ошибка уведомления о конце сезона {season.name}: {e}")

    def determine_season_theme(self) -> str:
        """Определяет тему сезона по текущему месяцу"""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "winter"
        elif month in [3, 4, 5]:
            return "spring"
        elif month in [6, 7, 8]:
            return "summer"
        else:
            return "autumn"

    def generate_season_name(self, theme: str) -> str:
        """Генерирует уникальное IT-тематическое название для сезона"""
        year = datetime.now().year
        it_titles = SEASON_IT_NAMES.get(theme, [])
        if not it_titles:
            return f"Сезон {theme.capitalize()} {year}"
        base_name = random.choice(it_titles)
        season_name = f"{base_name} {year}"
        counter = 1
        while Season.objects.filter(name=season_name).exists():
            season_name = f"{base_name} {year} v{counter}"
            counter += 1
        return season_name

    def generate_it_stats(self) -> str:
        """Генерирует фейковую IT-статистику для уведомлений"""
        stats = [
            f"CPU Usage: {random.randint(30, 90)}%",
            f"RAM: {random.randint(16, 128)}GB/{random.randint(128, 256)}GB",
            f"Uptime: {random.randint(30, 90)} days",
            f"Pending updates: {random.randint(5, 800)}",
            f"Security patches: {random.randint(1, 50)} critical",
            f"Network: {random.randint(100, 1000)}MB/s",
            f"Storage: {random.randint(20, 90)}% full"
        ]
        return "\n".join(stats)

    def award_season_winners(self, season):
        """Награждает топ-3 системных администраторов
           сезона специальными достижениями"""
        try:
            top_admins = SeasonRank.objects.filter(
                season=season
            ).order_by('-experience')[:3]
            if not top_admins:
                logger.info(
                    f"Нет данных для награждения в сезоне {season.name}")
                return
            rewards = {1: "🥇", 2: "🥈", 3: "🥉"}
            roles = {
                1: "Главный выездной системный администратор",
                2: "Ведущий выездной системный администратор",
                3: "Старший выездной системный администратор"
            }
            for position, admin in enumerate(top_admins, 1):
                username = admin.username or f"admin_{admin.user_id}"
                achievement_name = (
                    f"{rewards[position]} {roles[position]}"
                    f" сезона {season.name} "
                    f"(Уровень {admin.level})"
                )
                Achievement.objects.create(
                    user_id=admin.user_id,
                    username=username,
                    achievement_name=achievement_name
                )
            logger.info(
                f"Награждены топ-3 выездных системных "
                f"администратора сезона {season.name}")
        except Exception as e:
            logger.error(
                f"Ошибка награждения топ-админов сезона {season.name}: {e}")

    def send_telegram_message(self, message: str):
        """Отправляет сообщение в Telegram группу"""
        try:
            group_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
            if not group_chat_id:
                logger.error("TELEGRAM_GROUP_CHAT_ID не установлен в .env")
                return

            async_to_sync(application.bot.send_message)(
                chat_id=group_chat_id,
                text=message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения в Telegram: {e}")

    def send_season_start_notification(self, season):
        """Отправляет уведомление о начале IT-сезона"""
        meme = random.choice(IT_MEMES)
        stats = self.generate_it_stats()
        message = (
            f"🚀 *Запущен новый IT-сезон: {season.name}!*\n\n"
            f"📅 Период: {season.start_date.strftime('%d.%m.%Y')} - "
            f"{season.end_date.strftime('%d.%m.%Y')}\n\n"
            f"⚙️ *Технические характеристики сезона:*\n"
            f"```\n{stats}\n```\n"
            f"💡 {meme}\n\n"
            f"🔥 *Как участвовать?*\n"
            f"- Используйте команду /join при посещении компании\n"
            f"- Покидайте организации командой /leave\n"
            f"- Зарабатывайте опыт и повышайте уровень\n"
            f"- Следите за своим прогрессом командой /profile\n\n"
            f"🏆 Топ-3 выездных специалиста получат "
            f"специальные награды в конце сезона! Нет. :)"
        )
        self.send_telegram_message(message)

    def send_season_end_notification(self, season):
        """Отправляет уведомление о завершении сезона"""
        try:
            top_admin = SeasonRank.objects.filter(
                season=season
            ).order_by('-experience').first()
            winner_text = ""
            if top_admin:
                username = top_admin.username or f"admin_{top_admin.user_id}"
                winner_text = (
                    f"\n\n🏆 *Лучший системный администратор сезона:* "
                    f"@{username} "
                    f"(Уровень {top_admin.level})"
                )
            season_stats = SeasonRank.objects.filter(season=season).aggregate(
                total_visits=Sum("visits_count"),
                avg_level=Avg("level")
            )

            total_visits = season_stats["total_visits"] or 0
            avg_level = season_stats["avg_level"] or 0

            message = (
                f"🏁 *Сезон {season.name} завершен!*\n\n"
                f"📊 Итоги сезона:\n"
                f"- Участников: {SeasonRank.objects.filter(
                    season=season).count()}\n"
                f"- Всего выездов: {total_visits}\n"
                f"- Средний уровень: {avg_level:.1f}\n"
                f"{winner_text}\n\n"
                f"🏅 Топ-3 выездных специалиста "
                f"получили специальные награды!\n"
                f"📝 Проверьте свой профиль командой /profile"
            )
            self.send_telegram_message(message)
        except Exception as e:
            logger.error(
                f"Ошибка отправки уведомления о завершении сезона: {e}")

    def send_season_ending_soon_notification(self, season):
        """Уведомляет о скором окончании сезона (за 3 дня)"""
        days_left = (season.end_date - timezone.now().date()).days
        meme = random.choice(IT_MEMES)

        leader = SeasonRank.objects.filter(
            season=season
        ).order_by('-experience').first()

        leader_text = ""
        if leader:
            username = leader.username or f"admin_{leader.user_id}"
            leader_text = (f"\n👑 Текущий лидер: @{username} "
                           f"(Уровень {leader.level})")

        message = (
            f"⏰ *Внимание! Осталось {days_left} дня "
            f"до окончания сезона {season.name}*\n\n"
            f"🏃‍♂️ Успейте заработать последние очки опыта!\n"
            f"🏆 Топ-3 выездных админа получат "
            f"специальные награды!{leader_text}\n\n"
            f"💡 {meme}\n\n"
            f"📊 Проверьте свой прогресс командой /profile"
        )
        self.send_telegram_message(message)
