"""
With these settings, tests run faster.
"""

import environ

from .base import *  # noqa

env = environ.Env()

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env("DJANGO_SECRET_KEY", default="sRrfgivMISjKGtwZ2zXjSM77NGN5z3msXMfKord7dzcSbX6Z5CW4H7CYhS5plC89")
ALLOWED_HOSTS = [
    "localhost",
    "0.0.0.0",
    "127.0.0.1",
]

# https://docs.djangoproject.com/en/dev/ref/settings/#test-runner
TEST_RUNNER = "django.test.runner.DiscoverRunner"

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        "LOCATION": ""
    }
}

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG  # noqa F405

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = "localhost"
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = 1025

# Your stuff...
# ------------------------------------------------------------------------------

# Recaptcha:
USE_RECAPTCHA = False

# Celery
# ------------------------------------------------------------------------------
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-always-eager
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER", default=True)

# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-eager-propagates
CELERY_TASK_EAGER_PROPAGATES = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s '
                      '%(process)d %(thread)d %(message)s'
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'fmt': '%(levelname)s %(asctime)s %(message)s',
        },
        'only_message_json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'tracking_console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'only_message_json'
        }
    },
    'loggers': {
        'kinesinlms': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'assessments': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'catalog': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'course': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'dashboard': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'educator_resources': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'core': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'learning_library': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'management': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'marketing': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'users': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'pathways': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'tracking': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
    },
}

# CUSTOM ENV VARIABLES FOR TEST ENV
# ------------------------------------------------------------------------------

# When you're running locally, you may want to set up quick integrations to
# external test accounts via things like management commands. You can define
# env variables to help you do that, then use them in things like factories or
# init management commands.
# Otherwise, you need to use the "management" user interface to manually set
# the providers up with the same information.
# These variables are prefixed with TEST_ to remind you they're not for production.

# Used by factories...
TEST_BADGE_PROVIDER_ISSUER_ID = env("TEST_BADGE_PROVIDER_ISSUER_ID", default=None)
TEST_BADGE_PROVIDER_COURSE_BADGE_CLASS_ID = env("TEST_BADGE_PROVIDER_COURSE_BADGE_CLASS_ID", default=None)

TEST_EMAIL_AUTOMATION_PROVIDER_URL = env("TEST_EMAIL_AUTOMATION_PROVIDER_URL", default=None)

TEST_SURVEY_PROVIDER_DATA_CENTER_ID = env("TEST_SURVEY_PROVIDER_DATA_CENTER_ID", default=None)
TEST_SURVEY_PROVIDER_CALLBACK_SECRET = env('TEST_SURVEY_PROVIDER_CALLBACK_SECRET', default=None)
