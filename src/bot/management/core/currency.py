import logging

import aiohttp
from asgiref.sync import sync_to_async
from django.conf import settings

from bot.models import CurrencyRate

logger = logging.getLogger(__name__)


async def fetch_currency_rates():
    """Получение курсов валют и сохранение в БД"""
    cbr_url = "https://www.cbr-xml-daily.ru/daily_json.js"
    coingecko_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=rub,usd" # noqa

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(cbr_url) as response:
                data = await response.json()
                usd_rate = data["Valute"]["USD"]["Value"]
                eur_rate = data["Valute"]["EUR"]["Value"]
                cny_rate = data["Valute"]["CNY"]["Value"]

            async with session.get(coingecko_url) as response:
                btc_data = await response.json()
                btc_rub = btc_data["bitcoin"]["rub"]
                btc_usd = btc_data["bitcoin"]["usd"]

            currencies = {
                "USD": usd_rate,
                "EUR": eur_rate,
                "CNY": cny_rate,
                "BTC_RUB": btc_rub,
                "BTC_USD": btc_usd
            }

            for currency, rate in currencies.items():
                await sync_to_async(CurrencyRate.objects.create)(
                    currency=currency,
                    rate=rate
                )

            return currencies

        except Exception as e:
            logger.error(f"Ошибка получения курсов: {e}")
            return None


async def send_currency_report(bot):
    """Отправка отчета в чат"""
    rates = await fetch_currency_rates()
    if not rates:
        return

    message = (
        "📊 *Курсы валют на сегодня:*\n\n"
        f"🇺🇸 USD/RUB: *{rates['USD']:.2f}*\n"
        f"🇪🇺 EUR/RUB: *{rates['EUR']:.2f}*\n"
        f"🇨🇳 CNY/RUB: *{rates['CNY']:.2f}*\n"
        f"₿ BTC/RUB: *{rates['BTC_RUB']:,.2f}*\n"
        f"₿ BTC/USD: *{rates['BTC_USD']:,.2f}*"
    )

    group_chat_id = settings.TELEGRAM_GROUP_CHAT_ID
    await bot.send_message(
        chat_id=group_chat_id,
        text=message,
        parse_mode="Markdown"
    )
