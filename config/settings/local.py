from .base import *  # noqa
from .base import env

DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000000

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env('DJANGO_SECRET_KEY',
                 default='1QAd6Jv4aUmjgBGI6VkyugigxGznpko46VtKscll03DcRLKY6Ne74EJGoa8mxMLy')
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    "localhost",
    "0.0.0.0",
    "127.0.0.1",
]

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': ''
    }
}

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG  # noqa F405

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env('DJANGO_EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
# https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = 'localhost'
# https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = 1025

# WhiteNoise
# ------------------------------------------------------------------------------
# http://whitenoise.evans.io/en/latest/django.html#using-whitenoise-in-development
INSTALLED_APPS = ["whitenoise.runserver_nostatic"] + INSTALLED_APPS  # noqa: F405

# django-debug-toolbar
# ------------------------------------------------------------------------------
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
INSTALLED_APPS += ['debug_toolbar']  # noqa F405
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']  # noqa F405
# https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
DEBUG_TOOLBAR_CONFIG = {
    'DISABLE_PANELS': [
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ],
    'SHOW_TEMPLATE_CONTEXT': True,
    # DMcQ: use this to temporarily disble
    'SHOW_TOOLBAR_CALLBACK': lambda r: False,  # disables it
}
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ['127.0.0.1', '10.0.2.2']

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ['django_extensions']  # noqa F405

# Celery
# ------------------------------------------------------------------------------
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-always-eager
CELERY_TASK_ALWAYS_EAGER = env("CELERY_TASK_ALWAYS_EAGER", default=True)
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-eager-propagates
CELERY_TASK_EAGER_PROPAGATES = True

# Your stuff...
# ------------------------------------------------------------------------------

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s [%(module)s] :  %(message)s'
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
        'composer': {
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
        'speakers': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
        'tracking': {
            'level': 'DEBUG',
            'handlers': ['console']
        },
    },
}

# DRF API
CORS_ORIGIN_ALLOW_ALL = True

# Sanity when manually creating users in signup...
AUTH_PASSWORD_VALIDATORS = [
]

# Recaptcha:
USE_RECAPTCHA = False
SILENCED_SYSTEM_CHECKS = ['django_recaptcha.recaptcha_test_key_error']

# CUSTOM ENV VARIABLES FOR LOCAL ENV
# ------------------------------------------------------------------------------

# When you're running locally, you may want to set up quick integrations to
# external test accounts via things like management commands. You can define
# env variables to help you do that, then use them in things like factories or
# init management commands.
# Otherwise, you need to use the "management" user interface to manually set
# the providers up with the same information.
# These variables are prefixed with TEST_ to remind you they're not for production.

TEST_BADGE_PROVIDER_ISSUER_ID = env('TEST_BADGE_PROVIDER_ISSUER_ID', default=None)
TEST_BADGE_PROVIDER_COURSE_BADGE_CLASS_ID = env('TEST_BADGE_PROVIDER_COURSE_BADGE_CLASS_ID', default=None)

TEST_EMAIL_AUTOMATION_PROVIDER_URL = env('TEST_EMAIL_AUTOMATION_PROVIDER_URL', default=None)

TEST_SURVEY_PROVIDER_DATA_CENTER_ID = env('TEST_SURVEY_PROVIDER_DATA_CENTER_ID', default=None)
TEST_SURVEY_PROVIDER_CALLBACK_SECRET = env('TEST_SURVEY_PROVIDER_CALLBACK_SECRET', default=None)
