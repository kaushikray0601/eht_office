import os
import sys
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()

env_file = BASE_DIR / ".env"
if env_file.exists():
    # Let process environment win over .env (e.g. USE_POSTGRES=false for SQLite tests).
    environ.Env.read_env(env_file, overwrite=False)


def env_list(name, default):
    """Read a comma-separated or JSON-ish env list without requiring JSON syntax."""
    raw_value = env(name, default=None)
    if raw_value is None:
        return list(default)
    value = str(raw_value).strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [
        item.strip().strip("\"'")
        for item in value.split(",")
        if item.strip().strip("\"'")
    ]


def env_bool_strict(name, default):
    raw_value = env(name, default=None)
    if raw_value is None:
        return default
    value = str(raw_value).strip().lower()
    if value in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "f", "no", "n", "off"}:
        return False
    return default


def merge_unique(*value_lists):
    merged = []
    seen = set()
    for values in value_lists:
        for value in values:
            if value not in seen:
                merged.append(value)
                seen.add(value)
    return merged


def env_url_path(name, default):
    value = str(env(name, default=default)).strip().strip("/")
    if not value:
        value = str(default).strip().strip("/")
    return f"{value}/"


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
DEFAULT_DEV_SECRET_KEY = "django-insecure-5ms*1c5@!*%6q)ve3&guld-jc$ii_!pbvyvr*g$_lf)f0d*r6a"
SECRET_KEY = env(
    "SECRET_KEY",
    default=DEFAULT_DEV_SECRET_KEY,
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env_bool_strict("DEBUG", default=True)
IS_TESTING = "test" in sys.argv
ADMIN_SITE_PATH = env_url_path("DJANGO_ADMIN_PATH", default="admin/")

DEFAULT_ALLOWED_HOSTS = ["local.enggsense.com", "localhost", "127.0.0.1"]
ALLOWED_HOSTS = merge_unique(
    DEFAULT_ALLOWED_HOSTS,
    env_list("ALLOWED_HOSTS", default=[]),
)

CSRF_TRUSTED_ORIGINS = merge_unique(
    ["https://local.enggsense.com"],
    env_list("CSRF_TRUSTED_ORIGINS", default=[]),
)

if IS_TESTING and "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("testserver")

# Keep baseline review/local hosts present even when `.env` adds more hosts.

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG and not IS_TESTING)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=not DEBUG)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG and not IS_TESTING)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG and not IS_TESTING)



# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'eht',
    'easyaudit',
    "crispy_forms",
    "crispy_bootstrap4",
    "idfviewer",
    "plant3d",
    "raceway",
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'eht.middleware.LoginRequiredMiddleware',
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/base/'
LOGOUT_REDIRECT_URL = '/login/'

ROOT_URLCONF = 'ELECSENSE.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'eht.context_processors.nav_projects',
            ],
        },
    },
]

WSGI_APPLICATION = 'ELECSENSE.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

USE_POSTGRES = env.bool("USE_POSTGRES", default=False)
EHT_TIMING_LOGS = env.bool("EHT_TIMING_LOGS", default=False)
USE_EXISTING_POSTGRES_TEST_DB = env.bool("USE_EXISTING_POSTGRES_TEST_DB", default=False)
EHT_LOGIN_IP_RATE_LIMIT = env("EHT_LOGIN_IP_RATE_LIMIT", default="20/m")
EHT_LOGIN_USERNAME_RATE_LIMIT = env("EHT_LOGIN_USERNAME_RATE_LIMIT", default="5/m")
EHT_UPLOAD_RATE_LIMIT = env("EHT_UPLOAD_RATE_LIMIT", default="20/h")
EHT_CONFIRM_UPLOAD_RATE_LIMIT = env("EHT_CONFIRM_UPLOAD_RATE_LIMIT", default="60/h")
EHT_ERROR_FILE_DOWNLOAD_RATE_LIMIT = env("EHT_ERROR_FILE_DOWNLOAD_RATE_LIMIT", default="60/h")

SQLITE_DB_PATH = BASE_DIR / env("SQLITE_DB_NAME", default="db.sqlite3")
SQLITE_SOURCE_DB_PATH = BASE_DIR / env("SQLITE_SOURCE_DB_NAME", default="db.sqlite3")
SQLITE_BACKUP_DB_PATH = BASE_DIR / env("SQLITE_BACKUP_DB_NAME", default="db.sqlite3.bak")

POSTGRES_USER = env("POSTGRES_USER", default=os.getenv("PGUSER", "sa"))
POSTGRES_NAME = env(
    "POSTGRES_DB",
    default=os.getenv("PGDATABASE", POSTGRES_USER),
)
POSTGRES_TEST_NAME = env("POSTGRES_TEST_DB", default=f"test_{POSTGRES_NAME}")

if USE_POSTGRES:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": POSTGRES_NAME,
            "USER": POSTGRES_USER,
            "PASSWORD": env("POSTGRES_PASSWORD", default=os.getenv("PGPASSWORD", "")),
            "HOST": env("POSTGRES_HOST", default=os.getenv("PGHOST", "127.0.0.1")),
            "PORT": env("POSTGRES_PORT", default=os.getenv("PGPORT", "5432")),
            "CONN_MAX_AGE": env.int("POSTGRES_CONN_MAX_AGE", default=60),
            "CONN_HEALTH_CHECKS": env.bool("POSTGRES_CONN_HEALTH_CHECKS", default=True),
            "OPTIONS": {
                "connect_timeout": env.int("POSTGRES_CONNECT_TIMEOUT", default=10),
            },
            "TEST": {
                "NAME": POSTGRES_TEST_NAME,
            },
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": SQLITE_DB_PATH,
        }
    }

if USE_POSTGRES and USE_EXISTING_POSTGRES_TEST_DB:
    TEST_RUNNER = "ELECSENSE.test_runner.ExistingPostgresTestRunner"

# Convenience aliases used during one-time migration from SQLite to PostgreSQL.
DATABASES["sqlite_source"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": SQLITE_SOURCE_DB_PATH,
}

DATABASES["sqlite_backup"] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": SQLITE_BACKUP_DB_PATH,
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # for production (to serve static files), where 'collectstatic' commd gathers all satic files
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static"),
                    ] # for development 

PLANT3D_VIEWER_EXTENSIONS = [
    {
        "id": "raceway-overlay",
        "owner": "raceway",
        "kind": "consumer-overlay",
        "script": "raceway/js/raceway_overlay.js",
        "version": "20260711_raceway10",
    },
]

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') 

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
