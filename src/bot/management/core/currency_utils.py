import json
import logging

import aiohttp

from bot.models import CurrencyRate

logger = logging.getLogger(__name__)

CBR_API_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
COINGECKO_API_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin&vs_currencies=usd,rub"
)

CURRENCIES = ("USD", "EUR", "CNY")
CRYPTO_PAIRS = ("BTC_USD", "BTC_RUB")
ALL_CURRENCIES = (*CURRENCIES, *CRYPTO_PAIRS)


async def fetch_currency_rates():
    """Получение курсов валют из двух источников."""
    rates = {}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(CBR_API_URL, timeout=10) as response:
                if response.status == 200:
                    text = await response.text()
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка декодирования JSON: {e}")
                        raise
                    valute = data.get("Valute", {})
                    for currency in CURRENCIES:
                        if currency in valute:
                            rates[currency] = valute[currency]["Value"]
        except (aiohttp.ClientError, KeyError,
                TimeoutError, json.JSONDecodeError) as e:
            logger.error(f"Ошибка при получении данных ЦБ: {e}")

        try:
            async with session.get(COINGECKO_API_URL, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    bitcoin = data.get("bitcoin", {})
                    rates["BTC_USD"] = bitcoin.get("usd")
                    rates["BTC_RUB"] = bitcoin.get("rub")
        except (aiohttp.ClientError, KeyError, TimeoutError) as e:
            logger.error(f"Ошибка при получении данных CoinGecko: {e}")

    return rates


async def save_currency_rates(rates):
    """Сохранение курсов валют в базу данных."""
    for currency, rate in rates.items():
        if rate is not None:
            try:
                await CurrencyRate.objects.acreate(
                    currency=currency, rate=rate)
            except Exception as e:
                logger.error(f"Ошибка сохранения {currency}: {e}")


async def get_currency_changes():
    changes = {}
    for currency in ALL_CURRENCIES:
        try:
            queryset = CurrencyRate.objects.filter(
                currency=currency).order_by("-date")
            last_two = [item async for item in queryset[:2]]

            if not last_two:
                continue

            current = last_two[0].rate
            previous = last_two[1].rate if len(last_two) > 1 else current
            diff = current - previous
            changes[currency] = {
                "current": current,
                "change": diff,
                "percent": (diff / previous * 100) if previous != 0 else 0
            }
        except Exception as e:
            logger.error(f"Ошибка при обработке {currency}: {e}")
    return changes
