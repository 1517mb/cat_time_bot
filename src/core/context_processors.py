from django.conf import settings


def analytics(request):
    return {
        'YANDEX_METRIKA_ID': settings.YANDEX_METRIKA_COUNTER_ID,
        'debug': settings.DEBUG
    }
