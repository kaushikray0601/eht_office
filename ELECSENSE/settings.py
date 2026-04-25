import os
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(env_file, overwrite=True)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "SECRET_KEY",
    default="django-insecure-5ms*1c5@!*%6q)ve3&guld-jc$ii_!pbvyvr*g$_lf)f0d*r6a",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=True)

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["local.enggsense.com", "localhost", "127.0.0.1"])

ALLOWED_HOSTS = ["*"]

# Allow CSRF validation to pass for the Cloudflare Tunnel HTTPS origin
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["https://local.enggsense.com"])



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
]

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
            ],
        },
    },
]

WSGI_APPLICATION = 'ELECSENSE.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

USE_POSTGRES = env.bool("USE_POSTGRES", default=False)
EHT_TIMING_LOGS = env.bool("EHT_TIMING_LOGS", default=False)

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
            "HOST": env("POSTGRES_HOST", default=os.getenv("PGHOST", "129.151.129.146")),
            "PORT": env("POSTGRES_PORT", default=os.getenv("PGPORT", "5432")),
            "CONN_MAX_AGE": env.int("POSTGRES_CONN_MAX_AGE", default=60),
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

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') 

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
