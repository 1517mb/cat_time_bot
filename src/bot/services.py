import logging
import random
from typing import Optional

from django.core.cache import cache
from django.db.models import F
from django.http import HttpRequest

from bot.models import DailytTips, SiteStatistics

logger = logging.getLogger(__name__)


class GamificationService:
    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

    @staticmethod
    def is_rate_limited(request: HttpRequest,
                        limit: int = 5,
                        timeout: int = 2) -> bool:
        """
        Простая защита от накрутки: не более `limit`
        запросов за `timeout` секунд.
        Возвращает True, если лимит превышен.
        """
        ip = GamificationService.get_client_ip(request)
        cache_key = f"pwd_gen_throttle_{ip}"
        attempts = cache.get(cache_key, 0)
        if attempts >= limit:
            return True
        cache.set(cache_key, attempts + 1, timeout)
        return False

    @staticmethod
    def increment_global_counter() -> int:
        """
        Атомарно увеличивает счетчик паролей.
        Возвращает обновленное значение.
        """
        try:
            SiteStatistics.objects.filter(pk=1).update(
                total_passwords_generated=F('total_passwords_generated') + 1
            )
            stats = SiteStatistics.get_stats()
            stats.refresh_from_db()
            return stats.total_passwords_generated
        except Exception as e:
            logger.error(f"Failed to increment global counter: {e}")
            return 0

    @staticmethod
    def format_number(value: int) -> str:
        """
        Форматирует большие числа:
        1200 -> 1 200
        1500000 -> 1.5M
        """
        if value >= 1_000_000:
            return f"{value / 1_000_000:.1f}M".replace(',', '.')
        return "{:,}".format(value).replace(",", " ")

    @staticmethod
    def get_smart_random_tip(request: HttpRequest) -> Optional[DailytTips]:
        """
        Возвращает случайный совет, который
        пользователь еще не видел в этой сессии.
        """
        published_tips = list(
            DailytTips.objects.filter(
                is_published=True).values_list('id', flat=True))
        if not published_tips:
            return None
        seen_tips = request.session.get('seen_tips', [])
        available_tips = list(set(published_tips) - set(seen_tips))
        if not available_tips:
            seen_tips = []
            available_tips = published_tips
            request.session['seen_tips'] = []
        if not available_tips:
            return None

        chosen_id = random.choice(available_tips)
        seen_tips.append(chosen_id)
        request.session['seen_tips'] = seen_tips
        request.session.modified = True

        return DailytTips.objects.get(id=chosen_id)
