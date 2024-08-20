import logging


import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration    # noqa: 262
from sentry_sdk.integrations.django import DjangoIntegration    # noqa: 262
from sentry_sdk.integrations.logging import LoggingIntegration  # noqa: 262
from sentry_sdk.integrations.redis import RedisIntegration      # noqa: 262

from .base import *  # noqa
from .base import env

logger = logging.getLogger(__name__)

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env('DJANGO_SECRET_KEY')
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['kinesinlms.herokuapp.com'])

# DATABASES
# ------------------------------------------------------------------------------
DATABASES['default']['CONN_MAX_AGE'] = env.int('CONN_MAX_AGE', default=60)  # noqa F405

# CACHES
# ------------------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            # Mimicing memcache behavior.
            # https://github.com/jazzband/django-redis#memcached-exceptions-behavior
            "IGNORE_EXCEPTIONS": True
        }
    }

}

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = env.bool('DJANGO_SECURE_SSL_REDIRECT', default=True)
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = True
# https://docs.djangoproject.com/en/dev/topics/security/#ssl-https
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-seconds
# TODO: set this to 60 seconds first and then to 518400 once you prove the former works
SECURE_HSTS_SECONDS = 60
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-include-subdomains
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    'DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True
)
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-hsts-preload
SECURE_HSTS_PRELOAD = env.bool('DJANGO_SECURE_HSTS_PRELOAD', default=True)
# https://docs.djangoproject.com/en/dev/ref/middleware/#x-content-type-options-nosniff
SECURE_CONTENT_TYPE_NOSNIFF = env.bool(
    'DJANGO_SECURE_CONTENT_TYPE_NOSNIFF', default=True
)

# STORAGES
# ------------------------------------------------------------------------------
# https://django-storages.readthedocs.io/en/latest/#installation
INSTALLED_APPS += ['storages']  # noqa F405

# AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are assigned in base.py

# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_STORAGE_BUCKET_NAME = env("DJANGO_AWS_STORAGE_BUCKET_NAME", default=None)
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_QUERYSTRING_AUTH = False

# DO NOT change these unless you know what you're doing.
_AWS_EXPIRY = 60 * 60 * 24 * 7
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': f'max-age={_AWS_EXPIRY}, s-maxage={_AWS_EXPIRY}, must-revalidate',
}
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_S3_MAX_MEMORY_SIZE = env.int(
    "DJANGO_AWS_S3_MAX_MEMORY_SIZE",
    default=100_000_000,  # 100MB
)
#  https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_DEFAULT_ACL = None

# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings
AWS_S3_REGION_NAME = env("DJANGO_AWS_S3_REGION_NAME", default=None)

# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#cloudfront
AWS_S3_CUSTOM_DOMAIN = env("DJANGO_AWS_S3_CUSTOM_DOMAIN", default=None)

aws_s3_domain = AWS_S3_CUSTOM_DOMAIN or f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

# STATIC
# ------------------------
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# MEDIA
# ------------------------------------------------------------------------------
DEFAULT_FILE_STORAGE = "kinesinlms.utils.storages.MediaRootS3Boto3Storage"
MEDIA_URL = f"https://{aws_s3_domain}/media/"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    'DJANGO_DEFAULT_FROM_EMAIL',
    # Update the default below if you're not setting the DJANGO_DEFAULT_FROM_EMAIL env variable
    default='KinesinLMS Site Admin<noreply@example.com>'
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env('DJANGO_SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env('DJANGO_EMAIL_SUBJECT_PREFIX', default='[kinesinlms-webapp]')

# Anymail (Postmark)
# ------------------------------------------------------------------------------
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
INSTALLED_APPS += ['anymail']  # noqa F405
EMAIL_BACKEND = "anymail.backends.postmark.EmailBackend"
# https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
ANYMAIL = {
    "POSTMARK_SERVER_TOKEN": env("POSTMARK_SERVER_TOKEN", default=None),
    "SEND_DEFAULTS": {"track_opens": True},
}

# Collectfast
# ------------------------------------------------------------------------------
# INSTALLED_APPS = ["collectfast"] + INSTALLED_APPS  # noqa F405

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse"
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s '
                      '%(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console"]
    },
    'loggers': {
        "sentry_sdk": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False
        },
        'django.security.DisallowedHost': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        'django.db.backends': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
        'kinesinlms.assessments': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.catalog': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.core': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.course': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.dashboard': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.discourse': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.educator_resources': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.learning_library': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.management': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.sits': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.marketing': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.pathways': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.survey': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.tracking': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.users': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.speakers': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'kinesinlms.badges': {
            'level': 'DEBUG',
            'handlers': ['console']
        }
    }
}

# Sentry
# ------------------------------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default=None)
SENTRY_LOG_LEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", default=logging.WARNING)

if SENTRY_DSN:  
    sentry_logging = LoggingIntegration(
        level=SENTRY_LOG_LEVEL,  # Capture info and above as breadcrumbs
        event_level=logging.WARNING,  # Send errors as events
    )

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[sentry_logging, DjangoIntegration(), CeleryIntegration(), RedisIntegration()]
    )

# django-rest-framework
# -------------------------------------------------------------------------------
# Tools that generate code samples can use SERVERS to point to the correct domain
SPECTACULAR_SETTINGS["SERVERS"] = [  # noqa: F405
    {"url": "https://{{ cookiecutter.domain_name }}", "description": "Production server"},
]

# Your stuff...
# ------------------------------------------------------------------------------

# DRF API
CORS_ORIGIN_ALLOW_ALL = False

# Update this list with the domains you want to allow to access this site.
# Usually that means:
# 1. Your analytics site (e.g. https://kinesinlms-analytics.herokuapp.com)
# 2. Your AWS S3 bucket (e.g. https://kinesinlms.s3.amazonaws.com)
CORS_ORIGIN_WHITELIST = [
    "https://kinesinlms-analytics.herokuapp.com",
    "https://kinesinlms.s3.amazonaws.com",
]

# Recaptcha:
USE_RECAPTCHA = True
