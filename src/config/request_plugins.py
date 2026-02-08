from django.utils.translation import gettext_lazy as _
from request.plugins import (
    LatestRequests,
    TopBrowsers,
    TopErrorPaths,
    TopPaths,
    TopReferrers,
    TopSearchPhrases,
    TrafficInformation,
)


class RuTrafficInformation(TrafficInformation):
    verbose_name = _("Информация о трафике")
    template = "request/plugins/trafficinformation.html"


class RuLatestRequests(LatestRequests):
    verbose_name = _("Последние запросы")
    template = "request/plugins/latestrequests.html"


class RuTopPaths(TopPaths):
    verbose_name = _("Топ путей")
    template = "request/plugins/toppaths.html"


class RuTopErrorPaths(TopErrorPaths):
    verbose_name = _("Топ путей с ошибками")
    template = "request/plugins/toppaths.html"


class RuTopReferrers(TopReferrers):
    verbose_name = _("Топ рефереров")
    template = "request/plugins/topreferrers.html"


class RuTopSearchPhrases(TopSearchPhrases):
    verbose_name = _("Топ поисковых фраз")
    template = "request/plugins/topsearchphrases.html"


class RuTopBrowsers(TopBrowsers):
    verbose_name = _("Топ браузеров")
    template = "request/plugins/topbrowsers.html"
