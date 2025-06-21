import logging

from django.conf import settings
from telegram import Bot as SyncBot
from telegram.ext import Application

logger = logging.getLogger(__name__)


_bot_application = None
_is_initialized = False


def get_bot_application():
    """Возвращает глобальный экземпляр Telegram Application"""
    global _bot_application
    if _bot_application is None:
        logger.info("Создание нового экземпляра Telegram Application")
        try:
            _bot_application = Application.builder().token(
                settings.TELEGRAM_BOT_TOKEN
            ).build()
            logger.info("Экземпляр приложения успешно создан")
        except Exception as e:
            logger.error(f"Ошибка создания приложения: {e}")
            raise
    return _bot_application


async def initialize_bot_application():
    """Инициализирует и запускает приложение бота"""
    global _is_initialized, _bot_application
    if _is_initialized:
        return

    if _bot_application is None:
        get_bot_application()

    try:
        logger.info("Инициализация Telegram Application...")
        await _bot_application.initialize()
        await _bot_application.start()
        _is_initialized = True
        logger.info("Telegram Application успешно инициализирован")
    except Exception as e:
        logger.error(f"Ошибка инициализации приложения: {e}")
        raise


async def shutdown_bot_application():
    """Корректно завершает работу приложения бота"""
    global _is_initialized, _bot_application
    if not _is_initialized or _bot_application is None:
        return
    try:
        logger.info("Завершение работы Telegram Application...")
        await _bot_application.stop()
        await _bot_application.shutdown()
        _is_initialized = False
        logger.info("Telegram Application успешно остановлен")
    except Exception as e:
        logger.error(f"Ошибка завершения работы приложения: {e}")
    finally:
        pass


def get_bot_sync():
    """Синхронная версия бота для использования в Django-командах"""
    return SyncBot(settings.TELEGRAM_BOT_TOKEN)
