import asyncio
import json
import logging
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import aiohttp
from asgiref.sync import sync_to_async
from django.db.models import F

from bot.models import CurrencyRate

logger = logging.getLogger(__name__)

SOURCE_CBR = "CBR"
SOURCE_COINGECKO = "CoinGecko"

CBR_API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3/simple/price"

CURRENCY_CONFIG = {
    "USD": {
        "source": SOURCE_CBR,
        "api_id": "USD",
        "display_name": "USD/RUB",
        "emoji": "🇺🇸",
    },
    "EUR": {
        "source": SOURCE_CBR,
        "api_id": "EUR",
        "display_name": "EUR/RUB",
        "emoji": "🇪🇺",
    },
    "CNY": {
        "source": SOURCE_CBR,
        "api_id": "CNY",
        "display_name": "CNY/RUB",
        "emoji": "🇨🇳",
    },
    "BTC_RUB": {
        "source": SOURCE_COINGECKO,
        "api_id": "bitcoin",
        "target_currency": "rub",
        "display_name": "BTC/RUB",
        "emoji": "₿",
    },
    "BTC_USD": {
        "source": SOURCE_COINGECKO,
        "api_id": "bitcoin",
        "target_currency": "usd",
        "display_name": "BTC/USD",
        "emoji": "₿",
    },
    "ETH_RUB": {
        "source": SOURCE_COINGECKO,
        "api_id": "ethereum",
        "target_currency": "rub",
        "display_name": "ETH/RUB",
        "emoji": "🔷",
    },
    "ETH_USD": {
        "source": SOURCE_COINGECKO,
        "api_id": "ethereum",
        "target_currency": "usd",
        "display_name": "ETH/USD",
        "emoji": "🔷",
    },
    "TON_RUB": {
        "source": SOURCE_COINGECKO,
        "api_id": "the-open-network",
        "target_currency": "rub",
        "display_name": "TON/RUB",
        "emoji": "💎",
    },
    "TON_USD": {
        "source": SOURCE_COINGECKO,
        "api_id": "the-open-network",
        "target_currency": "usd",
        "display_name": "TON/USD",
        "emoji": "💎",
    },
    "SOL_RUB": {
        "source": SOURCE_COINGECKO,
        "api_id": "solana",
        "target_currency": "rub",
        "display_name": "SOL/RUB",
        "emoji": "🟣",
    },
    "SOL_USD": {
        "source": SOURCE_COINGECKO,
        "api_id": "solana",
        "target_currency": "usd",
        "display_name": "SOL/USD",
        "emoji": "🟣",
    },
    "XRP_RUB": {
        "source": SOURCE_COINGECKO,
        "api_id": "ripple",
        "target_currency": "rub",
        "display_name": "XRP/RUB",
        "emoji": "✖️",
    },
    "XRP_USD": {
        "source": SOURCE_COINGECKO,
        "api_id": "ripple",
        "target_currency": "usd",
        "display_name": "XRP/USD",
        "emoji": "✖️",
    },
    "LTC_RUB": {
        "source": SOURCE_COINGECKO,
        "api_id": "litecoin",
        "target_currency": "rub",
        "display_name": "LTC/RUB",
        "emoji": "Ł",
    },
    "LTC_USD": {
        "source": SOURCE_COINGECKO,
        "api_id": "litecoin",
        "target_currency": "usd",
        "display_name": "LTC/USD",
        "emoji": "Ł",
    },
}

ALL_TRACKED_CURRENCIES = list(CURRENCY_CONFIG.keys())


async def _fetch_cbr_rates(session):
    """Приватная функция для получения данных от ЦБР."""
    try:
        async with session.get(CBR_API_URL, timeout=10) as response:
            response.raise_for_status()
            text = await response.text()
            data = json.loads(text)
            return data.get("Valute", {})
    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        json.JSONDecodeError
    ) as e:
        logger.error(f"Ошибка при получении данных ЦБ: {e}")
        return None


async def _fetch_coingecko_rates(session):
    """Приватная функция для получения данных от CoinGecko."""
    coingecko_api_ids = set()
    coingecko_target_currencies = set()

    for key, config in CURRENCY_CONFIG.items():
        if config["source"] == SOURCE_COINGECKO:
            coingecko_api_ids.add(config["api_id"])
            coingecko_target_currencies.add(config["target_currency"])

    if not coingecko_api_ids or not coingecko_target_currencies:
        return {}

    ids_param = ",".join(coingecko_api_ids)
    vs_currencies_param = ",".join(coingecko_target_currencies)

    url = (
        f"{COINGECKO_BASE_URL}?ids={ids_param}"
        f"&vs_currencies={vs_currencies_param}"
    )
    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            return await response.json()
    except (
        aiohttp.ClientError,
        asyncio.TimeoutError,
        json.JSONDecodeError
    ) as e:
        logger.error(f"Ошибка при получении данных CoinGecko: {e}")
        return None


async def fetch_currency_rates():
    """
    Получение курсов валют из сконфигурированных источников.
    Возвращает словарь вида {"CURRENCY_CODE": Decimal(rate)}.
    """
    rates = {}
    async with aiohttp.ClientSession() as session:
        cbr_task = _fetch_cbr_rates(session)
        coingecko_task = _fetch_coingecko_rates(session)

        cbr_valute, coingecko_data = await asyncio.gather(
            cbr_task, coingecko_task
        )

        if cbr_valute:
            for code, conf in CURRENCY_CONFIG.items():
                if conf["source"] == SOURCE_CBR and conf["api_id"] in cbr_valute: # noqa
                    cbr_data = cbr_valute[conf["api_id"]]
                    try:
                        value = Decimal(str(cbr_data["Value"]))
                        nominal = Decimal(str(cbr_data.get("Nominal", 1)))
                        rates[code] = value / nominal
                    except (KeyError, TypeError, InvalidOperation) as e:
                        logger.warning(
                            f"Не удалось распарсить ЦБР для {code}: {e}, "
                            f"данные: {cbr_data}"
                        )

        if coingecko_data:
            for code, conf in CURRENCY_CONFIG.items():
                if conf["source"] == SOURCE_COINGECKO:
                    api_id = conf["api_id"]
                    target = conf["target_currency"]
                    if (
                        api_id in coingecko_data
                        and target in coingecko_data[api_id]
                    ):
                        try:
                            rate = Decimal(
                                str(coingecko_data[api_id][target])
                            )
                            rates[code] = rate
                        except (
                            KeyError, TypeError, InvalidOperation
                        ) as e:
                            logger.warning(
                                f"Err CoinGecko {code}: {e}, "
                                f"data: {coingecko_data.get(api_id, {})}"
                            )
    return rates


@sync_to_async
def _bulk_create_currency_rates(currency_rate_objects):
    """Вспомогательная функция для массового создания объектов."""
    CurrencyRate.objects.bulk_create(currency_rate_objects)


async def save_currency_rates(rates):
    """Массовое сохранение курсов валют в базу данных."""
    currency_rate_objects = []
    for currency, rate in rates.items():
        if rate is not None:
            currency_rate_objects.append(
                CurrencyRate(currency=currency, rate=rate)
            )

    if currency_rate_objects:
        try:
            await _bulk_create_currency_rates(currency_rate_objects)
            logger.info(
                f"Успешно сохранено {len(currency_rate_objects)} курсов."
            )
        except Exception as e:
            logger.error(f"Ошибка при массовом сохранении курсов: {e}")
    else:
        logger.info("Нет курсов для сохранения.")


async def get_currency_changes():
    """
    Получает текущие курсы и их изменения.
    Возвращает: {"CODE": {"current": Dec, "change": Dec, "percent": Dec}}
    """
    changes = {}
    latest_rates_query = CurrencyRate.objects.filter(
        currency__in=ALL_TRACKED_CURRENCIES
    ).order_by("currency", "-date")

    all_latest_rates = [item async for item in latest_rates_query]

    grouped_rates = {}
    for rate_obj in all_latest_rates:
        if rate_obj.currency not in grouped_rates:
            grouped_rates[rate_obj.currency] = []
        if len(grouped_rates[rate_obj.currency]) < 2:
            grouped_rates[rate_obj.currency].append(rate_obj)

    for currency in ALL_TRACKED_CURRENCIES:
        rates_for_curr = grouped_rates.get(currency, [])
        if len(rates_for_curr) < 1:
            logger.debug(
                f"Недостаточно данных для \"{currency}\" "
                f"для расчета изменений."
            )
            continue

        current = rates_for_curr[0].rate
        previous = (
            rates_for_curr[1].rate
            if len(rates_for_curr) > 1
            else current
        )

        if previous == Decimal(0):
            change = Decimal(0)
            percent = Decimal(0)
        else:
            change = current - previous
            percent = (change / previous) * Decimal(100)

        changes[currency] = {
            "current": current,
            "change": change,
            "percent": percent,
        }
    return changes


async def send_currency_report(bot):
    """Формирует и отправляет отчет в группу."""
    target_chat_id = os.getenv("TELEGRAM_GROUP_CHAT_ID")
    if not target_chat_id:
        logger.error("TELEGRAM_GROUP_CHAT_ID не определен в .env")
        return

    changes = await get_currency_changes()

    fiat_lines = []
    crypto_lines = []
    last_crypto_base = None

    for currency_code in ALL_TRACKED_CURRENCIES:
        config = CURRENCY_CONFIG.get(currency_code)
        if not config:
            continue
        data = changes.get(currency_code)
        if not data:
            continue

        current = data["current"]
        change = data["change"]
        percent = data["percent"]

        if change > 0:
            trend_emoji = "📈"
            sign = "+"
        elif change < 0:
            trend_emoji = "📉"
            sign = ""
        else:
            trend_emoji = "📊"
            sign = ""
        line_part1 = (
            f"{config['emoji']} *{config['display_name']}*: "
            f"{current:,.2f} {trend_emoji} "
        )
        line_part2 = f"(`{sign}{change:,.2f}` / `{sign}{percent:,.2f}%`)"
        line = line_part1 + line_part2

        if config["source"] == SOURCE_CBR:
            fiat_lines.append(line)
        else:
            current_base = currency_code.split('_')[0]
            if last_crypto_base and current_base != last_crypto_base:
                crypto_lines.append("")
            last_crypto_base = current_base
            crypto_lines.append(line)

    message_parts = ["💱 *Актуальные курсы валют:*"]

    if fiat_lines:
        message_parts.append("\n📌 *Фиатные валюты:*")
        message_parts.extend(fiat_lines)

    if crypto_lines:
        message_parts.append("\n⚡️ *Криптовалюты:*")
        message_parts.extend(crypto_lines)

    now_msk = datetime.now(ZoneInfo("Europe/Moscow")).strftime(
        "%d.%m.%Y %H:%M"
    )
    message_parts.append(f"\n🕒 *Обновлено:* `{now_msk}`")

    final_message = "\n".join(message_parts)

    try:
        await bot.send_message(
            chat_id=target_chat_id,
            text=final_message,
            parse_mode="Markdown"
        )
        logger.info(f"Отчет отправлен в чат {target_chat_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки отчета: {e}")
