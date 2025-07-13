import aiohttp
from bot.models import CurrencyRate


CBR_API_URL = "https://www.cbr-xml-daily.ru/daily_json.xml"
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

        async with session.get(CBR_API_URL) as response:
            if response.status == 200:
                data = await response.json()
                valute = data.get("Valute", {})
                for currency in CURRENCIES:
                    if currency in valute:
                        rates[currency] = valute[currency]["Value"]

        async with session.get(COINGECKO_API_URL) as response:
            if response.status == 200:
                data = await response.json()
                bitcoin = data.get("bitcoin", {})
                rates["BTC_USD"] = bitcoin.get("usd")
                rates["BTC_RUB"] = bitcoin.get("rub")

    return rates


async def save_currency_rates(rates):
    """Сохранение курсов валют в базу данных."""
    for currency, rate in rates.items():
        await CurrencyRate.objects.acreate(currency=currency, rate=rate)


async def get_currency_changes():
    """Расчет изменений курсов валют."""
    changes = {}

    for currency in ALL_CURRENCIES:
        last_two = await CurrencyRate.objects.filter(
            currency=currency
        ).order_by("-date")[:2].alist()

        if len(last_two) == 2:
            current = last_two[0].rate
            previous = last_two[1].rate
            change = current - previous
            changes[currency] = {
                "current": current,
                "change": change,
                "percent": (change / previous) * 100 if previous else 0
            }

    return changes
