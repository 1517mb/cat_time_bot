from django.db.models import Index

VERSION = "0.6.1 alpha"
SITE_HEADER = f"Cat-Time-Bot {VERSION}"
SITE_TITLE = "Панель управления"
BOT_APP_VERBOSE = "Данные приложения Cat-Time-Bot"
CONTENT_APP_VERBOSE = "Данные сайта"
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
    EDITED_V = "Редактировалось"
    EDITED_DEFAULT = False
    EDIT_COUNT_DEFAULT = 0
    EDIT_COUNT_V = "Счетчик правок"


class UserRankCfg:
    USER_ID_V = "Telegram ID"
    USER_ID_UNIQUE = True
    EXP_V = "Опыт"
    EXP_DEFAULT = 0
    LEVEL_V = "Уровень"
    LEVEL_DEFAULT = 1
    TOTAL_TIME_V = "Общее время"
    VISITS_COUNT_V = "Количество посещений"
    VISITS_COUNT_DEFAULT = 0
    META_NAME = "Текущий ранг"
    META_PL_NAME = "Текущие ранги"


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
    TAGS_V = "Теги"
    TAGS_BLANK = True
    TAGS_RELATED_NAME = "dailytips"


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


class ProgramCfg:
    NAME_V = "Название программы"
    NAME_MAX_LEN = 200
    DESCRIPTION_V = "Описание"
    EXT_DOWNLOAD_V = "Ссылка на скачивание"
    EXT_DOWNLOAD_BLANK = True
    EXT_DOWNLOAD_NULL = True
    FILE_V = "Файл с программой"
    FILE_UPLOAD_TO = "programs/%Y/%m/%d/"
    FILE_BLANK = True
    FILE_NULL = True
    META_NAME = "Программа"
    META_PL_NAME = "Программы"
    DOWNLOADS_V = "Количество скачиваний"
    DOWNLOADS_DEFAULT = 0
    VERIFIED_V = "Проверено"
    VERIFIED_DEFAULT = False
    CREATED_V = "Дата создания"
    CREATED_AUTO_NOW_ADD = True
    UPDATED_V = "Дата обновления"
    UPDATED_AUTO_NOW = True
    ORDERING = ("-created_at",)
    RATING_SUM_DEFAULT = 0.00
    RATING_SUM_V = "Сумма рейтингов"
    RATINGS_COUNT_DEFAULT = 0
    RATINGS_COUNT_V = "Количество оценок"


class TagCfg:
    NAME_V = "Название тега"
    SLUG_V = "URL-slug"
    META_NAME = "Тег"
    META_PL_NAME = "Теги"
    MAX_LEN_NAME = 100
    MAX_LEN_SLUG = 100
    UNIQUE_SLUG = True


class NewsCfg:
    TITLE_MAX_LEN = 255
    TITLE_V = "Заголовок"
    CONTENT_V = "Содержание"
    AUTHOR_V = "Автор"
    AUTHOR_RELATED = "news_posts"
    SLUG_MAX_LEN = 255
    SLUG_V = "URL-адрес"
    IMAGE_UPLOAD_TO = "news/%Y/%m/%d/"
    IMAGE_BLANK = True
    IMAGE_NULL = True
    IMAGE_V = "Изображение"
    IS_PUBLISHED_DEFAULT = False
    IS_PUBLISHED_V = "Опубликовано"
    CREATED_AUTO_NOW_ADD = True
    CREATED_V = "Дата создания"
    UPDATED_AUTO_NOW = True
    UPDATED_V = "Дата обновления"
    META_NAME = "Новость"
    META_PL_NAME = "Новости"
    ORDERING = ["-created_at"]
    INDEXES = [Index(fields=["-created_at", "is_published"])]
