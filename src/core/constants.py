VERSION = "0.5 alpha"
SITE_HEADER = f"Cat-Time-Bot {VERSION}"
SITE_TITLE = "Панель управления"
BOT_APP_VERBOSE = "Данные приложения Cat-Time-Bot"
MAX_LEN = 255


class CompanyCfg:
    VERBOSE_NAME = "Название"
    META_NAME = "Организация"
    META_PL_NAME = "Организации"


class UserActivityCfg:
    USER_ID_V = "Telegram ID"
    USERNAME_V = "Имя пользователя Telegram"
    COMPANY_V = "Название компании"
    JOIN_TIME_V = "Время прибытия"
    LEAVE_TIME_V = "Время убытия"
    SPENT_TIME_V = "Время, проведенное пользователем"
    SPENT_TIME_PLURAL_V = "Время, проведенное пользователями"


class DailytTipsCfg:
    VERBOSE_NAME = "Название"
    CONTENT_V = "Текст (Markdown)"
    PUB_DATE_V = "Дата публикации"
    AUTHOR_V = "Автор совета"
    IS_PUBLISHED_V = "Опубликовано"
    EXTERNAL_LINK_V = "Ссылка на внешний ресурс"
    RATING_V = "Рейтинг"
    RATING_DEFAULT = 0.0
    VIEWS_V = "Количество просмотров"
    VIEWS_DEFAULT = 0
    META_NAME = "Совет дня"
    META_PL_NAME = "Советы дня"


class AchievementCfg:
    USER_ID_V = "Telegram ID"
    USERNAME_V = "Имя пользователя Telegram"
    ACHIEVEMENT_NAME_V = "Название достижения"
    ACHIEVED_AT_V = "Дата достижения"
    META_NAME = "Достижение"
    META_PL_NAME = "Достижения"


class DailyStatisticsCfg:
    USER_ID_V = "Telegram ID"
    USERNAME_V = "Имя пользователя Telegram"
    DATE_V = "Дата"
    TOTAL_TIME_V = "Общее время"
    TOTAL_TRIPS_V = "Общее количество выездов"
    META_NAME = "Дневная статистика"
    META_PL_NAME = "Дневная статистика"


class QuoteCfg:
    TEXT_V = "Текст"
    AUTHOR_V = "Автор"
    SOURCE_V = "Источник"
    TAGS_V = "Теги"
    IS_ACTIVE_V = "Активна"
    META_NAME = "Цитата"
    META_PL_NAME = "Цитаты"
    MAX_LEN_AUTHOR = 100
    MAX_LEN_SOURCE = 200
    MAX_LEN_TAGS = 200
    BLANK_TAGS = True
    IS_ACTIVE_DEFAULT = True
