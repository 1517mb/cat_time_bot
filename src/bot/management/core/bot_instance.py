import logging
from typing import Optional

from django.conf import settings
from telegram import Bot as SyncBot
from telegram.ext import Application
from telegram.request import HTTPXRequest

logger = logging.getLogger(__name__)

_bot_application: Optional[Application] = None
_sync_bot: Optional[SyncBot] = None
_is_initialized = False


def get_bot_application() -> Application:
    """
    Возвращает глобальный экземпляр Telegram Application.
    С настройками тайм-аутов для стабильности сети.
    """
    global _bot_application

    if _bot_application is None:
        logger.info("Создание нового экземпляра Telegram Application")
        try:
            request = HTTPXRequest(
                connection_pool_size=8,
                connect_timeout=20.0,
                read_timeout=20.0,
            )
            _bot_application = Application.builder()\
                .token(settings.TELEGRAM_BOT_TOKEN)\
                .request(request)\
                .build()
            logger.info("Экземпляр приложения успешно создан")
        except Exception as e:
            logger.error(f"Ошибка создания приложения: {e}")
            raise
    if _bot_application is None:
        raise RuntimeError("Не удалось инициализировать Application")

    return _bot_application


async def initialize_bot_application():
    """Инициализирует и запускает приложение бота"""
    global _is_initialized, _bot_application
    if _is_initialized:
        return
    if _bot_application is None:
        get_bot_application()
    if _bot_application is None:
        logger.error("Application is None in initialize_bot_application")
        return

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


def get_bot_sync() -> SyncBot:
    """
    Синхронная версия бота.
    Создается один раз (кэшируется), чтобы не тратить память.
    """
    global _sync_bot
    if _sync_bot is None:
        try:
            _sync_bot = SyncBot(token=settings.TELEGRAM_BOT_TOKEN)
        except Exception as e:
            logger.error(f"Ошибка создания синхронного бота: {e}")
            raise
    if _sync_bot is None:
        raise RuntimeError("Не удалось создать SyncBot")

    return _sync_bot
