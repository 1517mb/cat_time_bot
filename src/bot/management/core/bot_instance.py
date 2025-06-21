import logging

from django.conf import settings
from telegram import Bot
from telegram.ext import ApplicationBuilder

logger = logging.getLogger(__name__)

bot_instance = None


def get_bot_instance():
    """
    Возвращает экземпляр Telegram Application (асинхронный)
    Создает новый экземпляр при первом вызове
    """
    global bot_instance
    if bot_instance is None:
        logger.info("Создание нового экземпляра Telegram бота")
        try:
            bot_instance = ApplicationBuilder().token(
                settings.TELEGRAM_BOT_TOKEN
            ).build()
            logger.info("Экземпляр бота успешно создан")
        except Exception as e:
            logger.error(f"Ошибка создания экземпляра бота: {e}")
            raise
    return bot_instance


def get_bot_sync():
    """
    Возвращает синхронный экземпляр Bot для простых операций
    Работает даже если основной Application не инициализирован
    """
    try:
        application = get_bot_instance()
        return application.bot
    except Exception as e:
        logger.warning(f"Не удалось получить бота из Application: {e}")
        logger.info("Создаем простой синхронный экземпляр Bot")
        try:
            return Bot(token=settings.TELEGRAM_BOT_TOKEN)
        except Exception as fallback_e:
            logger.error(
                f"Критическая ошибка создания fallback бота: {fallback_e}")
            raise
