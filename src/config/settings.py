import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

DEBUG = os.getenv("DEBUG") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",")


USE_X_FORWARDED_HOST = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_TRUSTED_ORIGINS = os.getenv("TRUSTED_ORIGINS", "").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "bot.apps.BotConfig",
    "core.apps.CoreConfig",
    "generator.apps.GeneratorConfig",
    "content.apps.ContentConfig",
    "pages.apps.PagesConfig",
    "import_export",
    "markdownify",
    "markdownx",
    "django_ckeditor_5",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(BASE_DIR, "data", "db.sqlite3"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "ru-ru"

USE_TZ = True

USE_I18N = True

TIME_ZONE = "Europe/Moscow"

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")

MEDIA_URL = "media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MARKDOWNX_MARKDOWN_EXTENSIONS = [
    "markdown.extensions.extra",
    "markdown.extensions.codehilite",
]

MARKDOWNIFY = {
    "default": {
        "WHITELIST_TAGS": [
            "h1", "h2", "h3", "h4", "h5", "h6",
            "a", "p", "ul", "ol", "li", "strong", "em",
            "code", "pre", "blockquote", "img", "table",
            "thead", "tbody", "tr", "th", "td", "br", "hr"
        ],
        "MARKDOWN_EXTENSIONS": [
            "markdown.extensions.extra",
            "markdown.extensions.sane_lists"
        ]
    }
}

MARKDOWNX_EDITOR_RESIZABLE = True
MARKDOWNX_UPLOAD_MAX_SIZE = 50 * 1024 * 1024

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True, parents=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
        "file": {
            "format": "%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple"
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/django.log"),
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 5,
            "formatter": "file",
            "encoding": "utf-8",
        },
        "error_file": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/errors.log"),
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 5,
            "formatter": "file",
            "encoding": "utf-8",
        },
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "filters": ["require_debug_false"],
        }
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": True,
        },
        "bot": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "generator": {
            "handlers": ["console", "file", "error_file"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["mail_admins", "error_file"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

CKEDITOR_5_CUSTOM_CSS = "css/ckeditor5-dark.css"
CKEDITOR_5_UPLOAD_PATH = "uploads/"
CKEDITOR_5_ALLOW_ALL_FILE_TYPES = True
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880


CKEDITOR_5_CONFIGS = {
    "default": {
        "toolbar": [
            "heading", "|",
            "bold", "italic", "link", "bulletedList", "numberedList", "blockQuote",
            "imageUpload", "undo", "redo"
        ],
        "language": "ru",
        "mediaEmbed": {"previewsInData": "true"},
    },
    "extends": {
        "blockToolbar": [
            "paragraph", "heading1", "heading2", "heading3",
            "|", "bulletedList", "numberedList",
            "|", "blockQuote", "imageUpload"
        ],
        "language": "ru",
        "mediaEmbed": {"previewsInData": "true"},
        "toolbar": [
            "heading", "|",
            "outdent", "indent", "|",
            "bold", "italic", "link", "underline", "strikethrough", "code",
            "subscript", "superscript", "highlight", "|",
            "codeBlock", "sourceEditing", "insertImage", "|",
            "bulletedList", "numberedList", "todoList", "|",
            "blockQuote", "imageUpload", "|",
            "fontSize", "fontFamily", "fontColor", "fontBackgroundColor", "|",
            "alignment", "|",
            "undo", "redo"
        ],
        "image": {
            "toolbar": ["imageTextAlternative", "|", "imageStyle:alignLeft", "imageStyle:alignRight", "imageStyle:alignCenter", "imageStyle:side", "|"],
            "styles": ["full", "side", "alignLeft", "alignRight", "alignCenter"],
        },
        "table": {
            "contentToolbar": ["tableColumn", "tableRow", "mergeTableCells"]
        },
        "heading": {
            "options": [
                {"model": "paragraph", "title": "Paragraph", "class": "ck-heading_paragraph"},
                {"model": "heading1", "view": "h1", "title": "Heading 1", "class": "ck-heading_heading1"},
                {"model": "heading2", "view": "h2", "title": "Heading 2", "class": "ck-heading_heading2"}
            ]
        }
    }
}

if DEBUG:
    STATICFILES_DIRS = [
        os.path.join(BASE_DIR, "static"),
    ]
    STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
