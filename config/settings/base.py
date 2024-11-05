"""
Base settings to build other settings files upon.
"""

from pathlib import Path

import environ

# DMcQ: This is a hack to prevent allauth from sending an email when a user tries to reset their password

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent
APPS_DIR = BASE_DIR / "kinesinlms"
env = environ.Env()

READ_DOT_ENV_FILE = env.bool("DJANGO_READ_DOT_ENV_FILE", default=False)
if READ_DOT_ENV_FILE:
    # OS environment variables take precedence over variables from .env
    env.read_env(str(BASE_DIR / ".env"))

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", False)
# Local time zone. Choices are
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# though not all of them may be available with every OS.
# In Windows, this must be set to your system time zone.
TIME_ZONE = "America/Los_Angeles"
# https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = "en-us"
# https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
# https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True
# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
# https://docs.djangoproject.com/en/dev/ref/settings/#locale-paths
LOCALE_PATHS = [str(BASE_DIR / "locale")]

# DATABASES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres:///kinesinlms"),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# URLS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = "config.urls"
# https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "django_celery_beat",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    # Using django_react_templatetags to add React components to templates...
    "django_react_templatetags",
    # Using MPTT for our course structure (stored in CourseNode)
    "mptt",
    "taggit",
    "django_recaptcha",
    # Using django_bleach for filtering incoming answers
    "django_bleach",
    # Using simple_history for tracking history of course content edits by instructor/admin
    "simple_history",
    # OpenAPI docs generation...
    "drf_spectacular",
    # Manage features and feature flags
    "waffle",
    # Allows rendering markdown in blocks
    "markdownify.apps.MarkdownifyConfig",
    # TinyMCE for wysiwyg editing in Composer
    "tinymce",
]
# noinspection PyUnresolvedReferences
LOCAL_APPS = [
    "kinesinlms.users.apps.UsersAppConfig",
    "kinesinlms.core.apps.CoreConfig",
    "kinesinlms.marketing.apps.MarketingConfig",
    "kinesinlms.dashboard.apps.DashboardConfig",
    "kinesinlms.course.apps.CoursesConfig",
    "kinesinlms.course_analytics.apps.CourseAnalyticsConfig",
    "kinesinlms.tracking.apps.TrackingConfig",
    "kinesinlms.custom_app.apps.CustomAppConfig",
    "kinesinlms.management.apps.ManagementConfig",
    "kinesinlms.learning_library.apps.LearningLibraryConfig",
    "kinesinlms.pathways.apps.PathwaysConfig",
    "kinesinlms.assessments.apps.AssessmentsConfig",
    "kinesinlms.educator_resources.apps.EducatorResourcesConfig",
    "kinesinlms.forum.apps.ForumConfig",
    "kinesinlms.analytics.apps.AnalyticsConfig",
    "kinesinlms.catalog.apps.CatalogConfig",
    "kinesinlms.survey.apps.SurveyConfig",
    "kinesinlms.composer.apps.ComposerConfig",
    "kinesinlms.speakers.apps.SpeakersConfig",
    "kinesinlms.news.apps.NewsConfig",
    "kinesinlms.sits.apps.SimpleInteractiveToolsConfig",
    "kinesinlms.resources.apps.ResourcesConfig",
    "kinesinlms.badges.apps.BadgesConfig",
    "kinesinlms.certificates.apps.CertificatesConfig",
    "kinesinlms.help.apps.HelpConfig",
    "kinesinlms.cohorts.apps.CohortsConfig",
    "kinesinlms.course_admin.apps.CourseAdminConfig",
    "kinesinlms.course_enrollment.apps.CourseEnrollmentConfig",
    "kinesinlms.institutions.apps.InstitutionsConfig",
    "kinesinlms.email_automation.apps.EmailAutomationConfig",
    "kinesinlms.external_tools.apps.ExternalToolConfig",
    "kinesinlms.lti.apps.LTIConfig",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIGRATIONS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#migration-modules
MIGRATION_MODULES = {"sites": "kinesinlms.contrib.sites.migrations"}

# AUTHENTICATION
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#authentication-backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-user-model
AUTH_USER_MODEL = "users.User"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-redirect-url
LOGIN_REDIRECT_URL = "users:redirect"
# https://docs.djangoproject.com/en/dev/ref/settings/#login-url
LOGIN_URL = "account_login"

# PASSWORDS
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#password-hashers
PASSWORD_HASHERS = [
    # https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# MIDDLEWARE
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "waffle.middleware.WaffleMiddleware",
]

# STATIC
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = str(BASE_DIR / "staticfiles")
# https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = "/static/"
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [str(APPS_DIR / "static")]
# https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = str(APPS_DIR / "media")
# https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = "/media/"

# TEMPLATES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        "DIRS": [str(APPS_DIR / "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            # https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "kinesinlms.utils.context_processors.settings_context",
                "kinesinlms.core.context_processors.site_context",
                "django_react_templatetags.context_processors.react_context_processor",
            ],
        },
    },
]

# https://docs.djangoproject.com/en/dev/ref/settings/#form-renderer
FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = "bootstrap5"
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

# FIXTURES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#fixture-dirs
FIXTURE_DIRS = (str(APPS_DIR / "fixtures"),)

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-httponly
SESSION_COOKIE_HTTPONLY = True
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-httponly
# KinesinLMS: Setting to false so React/Axios calls work
# KinesinLMS: Per Django docs, no reason to set this to True:
# https://docs.djangoproject.com/en/4.2/ref/settings/#csrf-cookie-httponly
CSRF_COOKIE_HTTPONLY = False
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-browser-xss-filter
SECURE_BROWSER_XSS_FILTER = True
# https://docs.djangoproject.com/en/dev/ref/settings/#x-frame-options

# TODO: Remove X_FRAME_OPTIONS and only use Content-Security-Policy header instead.
# In the meantime, setting X_FRAME_OPTIONS to SAMEORIGIN rather than DENY to support LTI launches.
# We need to do this because of the LTI launch process. In this process, KinesinLMS will be generating
# pages that appear *inside* the iframe. Therefore we need SAMEORIGIN to make sure it doesn't freak
# out about KinesinLMS pages being rendered inside an iframe.
X_FRAME_OPTIONS = "SAMEORIGIN"

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
)
ADMIN_EMAIL = env("DJANGO_ADMIN_EMAIL", default="kinesinlms-admin@example.com")

# https://docs.djangoproject.com/en/dev/ref/settings/#email-timeout
EMAIL_TIMEOUT = 5

# ADMIN
# ------------------------------------------------------------------------------
# Django Admin URL regex.
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

# https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [
    ("""Site Admin""", ADMIN_EMAIL),
]
# https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

DJANGO_ADMIN_FORCE_ALLAUTH = env.bool("DJANGO_ADMIN_FORCE_ALLAUTH", default=False)

# LOGGING
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#logging
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s "
            "%(process)d %(thread)d %(message)s"
        }
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console"],
    },
}

# CACHES
# ------------------------------------------------------------------------------

REDIS_URL = env("REDIS_TLS_URL", default=None)
if not REDIS_URL:
    REDIS_URL = env("REDIS_URL", default=None)
if not REDIS_URL:
    raise Exception(
        "Cannot find REDIS url in environment. Please set REDIS_TLS_URL or REDIS_URL."
    )

# Celery
# ------------------------------------------------------------------------------
if USE_TZ:
    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-timezone
    CELERY_TIMEZONE = TIME_ZONE
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-broker_url
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=None)

# If we don't have a CELERY_BROKER_URL, use REDIS_URL.
if not CELERY_BROKER_URL:
    CELERY_BROKER_URL = REDIS_URL

# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_backend
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-extended
CELERY_RESULT_EXTENDED = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-always-retry
# https://github.com/celery/celery/pull/6122
CELERY_RESULT_BACKEND_ALWAYS_RETRY = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#result-backend-max-retries
CELERY_RESULT_BACKEND_MAX_RETRIES = 10
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-accept_content
CELERY_ACCEPT_CONTENT = ["json"]
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_serializer
CELERY_TASK_SERIALIZER = "json"
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_serializer
CELERY_RESULT_SERIALIZER = "json"
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-time-limit
CELERYD_TASK_TIME_LIMIT = 5 * 60
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#task-soft-time-limit
CELERYD_TASK_SOFT_TIME_LIMIT = 60
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#beat-scheduler
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#worker-send-task-events
CELERY_WORKER_SEND_TASK_EVENTS = True
# https://docs.celeryq.dev/en/stable/userguide/configuration.html#std-setting-task_send_sent_event
CELERY_TASK_SEND_SENT_EVENT = True

# django-allauth
# ------------------------------------------------------------------------------
ACCOUNT_ALLOW_REGISTRATION = env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_AUTHENTICATION_METHOD = "username_email"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_REQUIRED = True
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_EMAIL_VERIFICATION = "mandatory"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
ACCOUNT_ADAPTER = "kinesinlms.users.adapters.AccountAdapter"
# https://django-allauth.readthedocs.io/en/latest/configuration.html
SOCIALACCOUNT_ADAPTER = "kinesinlms.users.adapters.SocialAccountAdapter"

# DJANGO REST FRAMEWORK
# ------------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "100/day", "user": "1000/day"},
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# Convention for limiting the size of incoming json for json fields.
# We use these fields in a number of api endpoints.
# Max bytes size of json data incoming into our serializers.
# Size is determined using sys.getsizeof()
# Default to approx 100KB.
MAX_JSON_CONTENT_BYTES_ALLOWED = env(
    "DJANGO_MAX_JSON_CONTENT_BYTES_ALLOWED", default=100000
)

# django-cors-headers - https://github.com/adamchainz/django-cors-headers#setup
CORS_URLS_REGEX = r"^/api/.*$"

# By Default swagger ui is available only to admin user(s). You can change permission classes to change that
# See more configuration options at https://drf-spectacular.readthedocs.io/en/latest/settings.html#settings
SPECTACULAR_SETTINGS = {
    "TITLE": "KinesinLMS API",
    "DESCRIPTION": "Documentation of API endpoints of KinesinLMS",
    "VERSION": "1.0.0",
    "SERVE_PERMISSIONS": ["rest_framework.permissions.IsAdminUser"],
}

#  OTHER...
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# For react-django-templates
REACT_COMPONENT_PREFIX = "kinesinlmsComponents."
REACT_RENDER_TAG_MANAGER = "kinesinlms.core.react.KinesinLMSReactTagManager"

# Moving AWS setting out of production.py storages section and into base.py
# since we use boto for other things (like Lambda calls)
AWS_ACCESS_KEY_ID = env("DJANGO_AWS_ACCESS_KEY_ID", default=None)
AWS_SECRET_ACCESS_KEY = env("DJANGO_AWS_SECRET_ACCESS_KEY", default=None)

# Lambda for handling and storing events
AWS_KINESINLMS_EVENTS_LAMBDA = env("DJANGO_AWS_KINESINLMS_EVENTS_LAMBDA", default=None)

#  For our slack messaging
SLACK_TOKEN = env("DJANGO_SLACK_TOKEN", default=None)

# Configure recaptcha.
USE_RECAPTCHA = env("RECAPTCHA_USE_RECAPTCHA", default=True)
RECAPTCHA_REQUIRED_SCORE = env("RECAPTCHA_REQUIRED_SCORE", default=0.75)
RECAPTCHA_USE_SSL = env("RECAPTCHA_USE_SSL", default=True)  # Defaults to False
if env("RECAPTCHA_PUBLIC_KEY", default=None):
    # Don't even assign the settings value if there isn't a
    # value in the env ... in that case recaptcha will use test keys.
    RECAPTCHA_PUBLIC_KEY = env("RECAPTCHA_PUBLIC_KEY")
else:
    SILENCED_SYSTEM_CHECKS = ["django_recaptcha.recaptcha_test_key_error"]
if env("RECAPTCHA_PRIVATE_KEY", default=None):
    # Don't even assign the settings value if there isn't a
    # value in the env ... in that case recaptcha will use test keys.
    RECAPTCHA_PRIVATE_KEY = env("RECAPTCHA_PRIVATE_KEY")

MARKDOWNIFY = {
    "default": {
        "WHITELIST_TAGS": [
            "a",
            "abbr",
            "acronym",
            "b",
            "blockquote",
            "em",
            "i",
            "li",
            "ol",
            "p",
            "strong",
            "ul",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "img",
        ],
        "WHITELIST_ATTRS": [
            "src",
        ],
    }
}

# Sign up form
ACCOUNT_SIGNUP_FORM_CLASS = "kinesinlms.users.forms.UserSignupForm"

# Bleach config
BLEACH_STRIP_TAGS = False

# Know within Django which pipeline we're in...e.g. LOCAL, STAGING, PRODUCTION, etc.
DJANGO_PIPELINE = env("DJANGO_PIPELINE", default=None)

# Explicit flag for tests. Set this to True in your test settings.
# When you want a simple way of knowing you're in tests.
TEST_RUN = env("TEST_RUN", default=False)

# Custom username validator for allauth to use during signups
ACCOUNT_USERNAME_VALIDATORS = "kinesinlms.users.validators.custom_username_validators"

# Config TinyMCE for use in Composer.
TINYMCE_DEFAULT_CONFIG = {
    "theme": "silver",
    "height": 500,
    "menubar": False,
    "plugins": [
        "advlist",
        "autolink",
        "lists",
        "link",
        "image",
        "charmap",
        "anchor",
        "pagebreak",
        "preview",
        "searchreplace",
        "wordcount",
        "visualblocks",
        "visualchars",
        "fullscreen",
        "insertdatetime",
        "media",
        "table",
        "emoticons",
        "help",
        # "paste",
        # "hr",
        # "code",
    ],
    "paste_block_drop": False,
    "toolbar": "undo redo | formatselect |  bold italic forecolor backcolor emoticons | alignleft aligncenter alignright alignjustify | bullist numlist outdent indent |  removeformat | link image uploadimage | help",
    "convert_urls": False,
    "extended_valid_elements": "span[class|style],i[class|style],img[class|src|border=0|alt|title|hspace|vspace|width|height|align|onmouseover|onmouseout|name]",
    "setup": """
        function(editor) { 
        
            editor.on("dragenter", window.klmsHTMLContentOnDragEnter, false);
            editor.on("dragover", window.klmsHTMLContentOnDragOver, false);
            editor.on("dragleave", window.klmsHTMLContentOnDragLeave, false);
            editor.on("drop", window.klmsHTMLContentOnDrop, false);

            editor.on("change", (e) => {
                // When the content changes, we need to manually trigger a change event on the
                // hidden textarea to get the onPanelFormChange function to fire.
                const rawTextArea = document.getElementById("id_html_content");
                const changeEvent = new CustomEvent('wysiwyg_change', { detail: e } );
                e.target.formElement.dispatchEvent(changeEvent);
            });
        }
    """,
}

# Javascript version flag used to bust client browser cache when required. Ugly but works.
KINESINLMS_JAVASCRIPT_VERSION = env(
    "DJANGO_KINESINLMS_JAVASCRIPT_VERSION", default="2023.1.1"
)

# Cookie for remembering if user has accepted or rejected analytics cookies.
ACCEPT_ANALYTICS_COOKIE_NAME = env(
    "DJANGO_ACCEPT_ANALYTICS_COOKIE_NAME", default="kinesinlms_accept_analytics_cookie"
)

EDUCATORS_NEWSLETTER_SIGNUP_URL = env(
    "DJANGO_EDUCATORS_NEWSLETTER_SIGNUP_URL", default=None
)
NEWSLETTER_SIGNUP_URL = env("DJANGO_NEWSLETTER_SIGNUP_URL", default=None)

# Contact email should be defined in SiteProfile, but
# if it's not defined there, this variable should be set.
CONTACT_EMAIL = env("CONTACT_EMAIL", default=None)

# LTI and OAUTH
# =====================================================

# LTI and External Tools
LTI_PLATFORM_PUBLIC_KEY = env("LTI_PLATFORM_PUBLIC_KEY", default=None)
if LTI_PLATFORM_PUBLIC_KEY:
    LTI_PLATFORM_PUBLIC_KEY = LTI_PLATFORM_PUBLIC_KEY.replace("\\n", "\n")
LTI_PLATFORM_PRIVATE_KEY = env("LTI_PLATFORM_PRIVATE_KEY", default=None)
if LTI_PLATFORM_PRIVATE_KEY:
    LTI_PLATFORM_PRIVATE_KEY = LTI_PLATFORM_PRIVATE_KEY.replace("\\n", "\n")
LTI_PLATFORM_JWKS_MAX_AGE_SECONDS = env(
    "LTI_PLATFORM_JWKS_MAX_AGE_SECONDS", default=604800
)
# This is the Key "ID" used in the LTI1.3 platform's JWKS. It has to match
# the "kid" value set in the header of the OpenID Connect token sent during an LTI connection.
LTI_PLATFORM_KID = env("LTI_PLATFORM_KID", default="lti1.3-key")

# THIRD-PARTY INTEGRATIONS
# =====================================================

# Email service
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Email automation provider
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
EMAIL_AUTOMATION_PROVIDER_API_KEY = env(
    "EMAIL_AUTOMATION_PROVIDER_API_KEY", default=None
)

# Survey provider
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
SURVEY_PROVIDER_API_KEY = env("SURVEY_PROVIDER_API_KEY", default=None)

# Badge provider
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
BADGE_PROVIDER_USERNAME = env("BADGE_PROVIDER_USERNAME", default=None)
BADGE_PROVIDER_PASSWORD = env("BADGE_PROVIDER_PASSWORD", default=None)

# Forum provider
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
FORUM_API_KEY = env("FORUM_API_KEY", default=None)
FORUM_SSO_SECRET = env("FORUM_SSO_SECRET", default=None)
FORUM_WEBHOOK_SECRET = env("FORUM_WEBHOOK_SECRET", default=None)

# Features controlled by Waffle
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
WAFFLE_SWITCH_DEFAULT = True
WAFFLE_CREATE_MISSING_SWITCHES = True

# FOR TESTING...
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# These are included in the base settings so that they can be used in automated tests.
# They are used by factories in the integration tests.
# Otherwise, they are not used in the application (the values are assigned by the site admin in
# the management panel )
BADGE_PROVIDER_ISSUER_ID = env("BADGE_PROVIDER_ISSUER_ID", default=None)
BADGE_PROVIDER_COURSE_BADGE_CLASS_ID = env(
    "BADGE_PROVIDER_COURSE_BADGE_CLASS_ID", default=None
)


MODAL_TOKEN_ID = env("MODAL_TOKEN_ID", default=None)
MODAL_TOKEN_SECRET = env("MODAL_TOKEN_SECRET", default=None)