"""
Django settings for Obstracts Web project.

For more information on this file, see
https://docs.djangoproject.com/en/stable/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/stable/ref/settings/
"""

import os
import sys
from pathlib import Path

import environ
from django.utils.translation import gettext_lazy

# Build paths inside the project like this: BASE_DIR / "subdir".
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, ".env"))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/stable/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env(
    "SECRET_KEY", default="django-insecure-QYyvoHi8KCmzcnUWACt7EzeLRYi3TuMyTLlzab4S"
)

# SECURITY WARNING: don"t run with debug turned on in production!
DEBUG = env.bool("DJANGO_DEBUG", default=True)
ENABLE_DEBUG_TOOLBAR = (
    env.bool("ENABLE_DEBUG_TOOLBAR", default=False) and "test" not in sys.argv
)

CORS_ORIGIN_ALLOW_ALL = True

# Note: It is not recommended to set ALLOWED_HOSTS to "*" in production
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["http://*, https://*"])
# Application definition


DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.admindocs",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sitemaps",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.forms",
    'django_filters',
]

# Put your third-party apps here
THIRD_PARTY_APPS = [
    "corsheaders",
    "allauth",  # allauth account/registration management
    "allauth.account",
    "allauth.socialaccount",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "allauth.mfa",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_api_key",
    "celery_progress",
    "djstripe",  # stripe integration
    "waffle",
    "health_check",
    "health_check.db",
    "health_check.contrib.celery",
    "health_check.contrib.redis",
    "django_celery_beat",
    "rest_framework.authtoken",
    "dj_rest_auth",
    "dj_rest_auth.registration",
    "allauth.socialaccount.providers.auth0",
]

# Put your project-specific apps here
PROJECT_APPS = [
    "apps.subscriptions.apps.SubscriptionConfig",
    "apps.users.apps.UserConfig",
    "apps.dashboard.apps.DashboardConfig",
    "apps.api.apps.APIConfig",
    "apps.web",
    "apps.teams.apps.TeamConfig",
    "apps.obstracts_api",
    "arango_taxii_server.app",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + PROJECT_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "apps.teams.middleware.TeamsMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "waffle.middleware.WaffleMiddleware",
    "corsheaders.middleware.CorsMiddleware",
]


if ENABLE_DEBUG_TOOLBAR:
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INSTALLED_APPS.append("debug_toolbar")
    INTERNAL_IPS = ["127.0.0.1"]
    try:
        import socket

        # get hostname for Docker environments
        # See https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#configure-internal-ips
        hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
        # add discovered IPs plus some common defaults
        INTERNAL_IPS += [ip[: ip.rfind(".")] + ".1" for ip in ips] + [
            "192.168.65.1",
            "10.0.2.2",
        ]
    except OSError as e:
        print(
            f"{e} while attempting to resolve system hostname. Using INTERNAL_IPS={INTERNAL_IPS}"
        )

ROOT_URLCONF = "obstracts_web.urls"


# used to disable the cache in dev, but turn it on in production.
# more here: https://nickjanetakis.com/blog/django-4-1-html-templates-are-cached-by-default-with-debug-true
_DEFAULT_LOADERS = [
    "django.template.loaders.filesystem.Loader",
    "django.template.loaders.app_directories.Loader",
]

_CACHED_LOADERS = [("django.template.loaders.cached.Loader", _DEFAULT_LOADERS)]


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
        ],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.web.context_processors.project_meta",
                "apps.teams.context_processors.team",
                "apps.teams.context_processors.user_teams",
                # this line can be removed if not using google analytics
                "apps.web.context_processors.google_analytics_id",
            ],
            "loaders": _DEFAULT_LOADERS if DEBUG else _CACHED_LOADERS,
        },
    },
]

WSGI_APPLICATION = "obstracts_web.wsgi.application"

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases

if "DATABASE_URL" in env:
    DATABASES = {"default": env.db()}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": env("POSTGRES_HOST", default="localhost"),
            "PORT": env("POSTGRES_PORT", default="5432"),
            "NAME": env("POSTGRES_DB", default="obstracts_web"),
            "USER": env("POSTGRES_USER", default="postgres"),
            "PASSWORD": env("POSTGRES_PASSWORD", default="***"),
        }
    }


CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': env("REDIS_CACHE_URL", default="redis://localhost:6379"),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Auth / login stuff

# Django recommends overriding the user model even if you don"t think you need to because it makes
# future changes much easier.
AUTH_USER_MODEL = "users.CustomUser"
LOGIN_REDIRECT_URL = "/admin"
LOGOUT_REDIRECT_URL = '/accounts/auth0/login/'
LOGIN_URL = '/accounts/auth0/login/'

# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

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

# Auth0 settings
AUTH0_DOMAIN = env("AUTH0_DOMAIN", default="")
AUTH0_LOGIN_DOMAIN = env("AUTH0_LOGIN_DOMAIN", default=AUTH0_DOMAIN)
AUTH0_URL = f'https://{AUTH0_DOMAIN}'
AUTH0_CLIENT_ID = env("AUTH0_CLIENT_ID", default="")
AUTH0_CLIENT_SECRET = env("AUTH0_CLIENT_SECRET", default="")
AUTH0_WEB_CLIENT_ID = env("AUTH0_WEB_CLIENT_ID", default="")
AUTH0_WEB_CLIENT_SECRET = env("AUTH0_WEB_CLIENT_SECRET", default="")

# Allauth setup

ACCOUNT_ADAPTER = "apps.teams.adapter.AcceptInvitationAdapter"
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_SUBJECT_PREFIX = ""
ACCOUNT_EMAIL_UNKNOWN_ACCOUNTS = (
    False  # don't send "forgot password" emails to unknown accounts
)
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGIN_BY_CODE_ENABLED = True


SOCIALACCOUNT_PROVIDERS = {
    'auth0': {
        'AUTH0_URL': f'https://{AUTH0_LOGIN_DOMAIN}',
        'OAUTH_PKCE_ENABLED': True,
    }
}

ACCOUNT_FORMS = {
    "signup": "apps.teams.forms.TeamSignupForm",
}

# User signup configuration: change to "mandatory" to require users to confirm email before signing in.
# or "optional" to send confirmation emails but not require them
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="none")

AUTHENTICATION_BACKENDS = (
    # Needed to login by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)

# For turnstile captchas
TURNSTILE_KEY = env("TURNSTILE_KEY", default=None)
TURNSTILE_SECRET = env("TURNSTILE_SECRET", default=None)


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = False

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

STATIC_ROOT = BASE_DIR / "static_root"
STATIC_URL = "/dj-static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # swap these to use manifest storage to bust cache when files change
        # note: this may break image references in sass/css files which is why it is not enabled by default
        # "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage",
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

MEDIA_ROOT = BASE_DIR / "media"
MEDIA_URL = "/media/"

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field

# future versions of Django will use BigAutoField as the default, but it can result in unwanted library
# migration files being generated, so we stick with AutoField for now.
# change this to BigAutoField if you"re sure you want to use it and aren"t worried about migrations.
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Removes deprecation warning for future compatibility.
# see https://adamj.eu/tech/2023/12/07/django-fix-urlfield-assume-scheme-warnings/ for details.
FORMS_URLFIELD_ASSUME_HTTPS = True

# Email setup

# default email used by your server
SERVER_EMAIL = env("SERVER_EMAIL", default="noreply@dogesec.com")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@dogesec.com")

# The default value will print emails to the console, but you can change that here
# and in your environment.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

# Most production backends will require further customization. The below example uses Mailgun.
# ANYMAIL = {
#     "MAILGUN_API_KEY": env("MAILGUN_API_KEY", default=None),
#     "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN", default=None),
# }

# use in production
# see https://github.com/anymail/django-anymail for more details/examples
# EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"

EMAIL_SUBJECT_PREFIX = "[Obstracts Web] "

# Django sites

SITE_ID = 1

# DRF config
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": (
        "apps.api.permissions.IsAuthenticatedOrHasUserAPIKey",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}


SPECTACULAR_SETTINGS = {
    "TITLE": "Obstracts Web",
    "DESCRIPTION": "Turn any blog into structured threat intelligence",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "displayOperationId": False,
    },
    "PREPROCESSING_HOOKS": [
        "apps.api.schema.filter_schema_apis",
    ],
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "ApiKeyAuth": {"type": "apiKey", "in": "header", "name": "Authorization"}
        }
    },
    "SECURITY": [
        {
            "ApiKeyAuth": [],
        }
    ],
}

# Celery setup (using redis)
if "REDIS_URL" in env:
    REDIS_URL = env("REDIS_URL")
elif "REDIS_TLS_URL" in env:
    REDIS_URL = env("REDIS_TLS_URL")
else:
    REDIS_HOST = env("REDIS_HOST", default="localhost")
    REDIS_PORT = env("REDIS_PORT", default="6379")
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"

if REDIS_URL.startswith("rediss"):
    REDIS_URL = f"{REDIS_URL}?ssl_cert_reqs=none"

CELERY_BROKER_URL = CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Health Checks
# A list of tokens that can be used to access the health check endpoint
HEALTH_CHECK_TOKENS = env.list("HEALTH_CHECK_TOKENS", default="")

# Waffle config

WAFFLE_FLAG_MODEL = "teams.Flag"

# set this to True in production to have URLs generated with https instead of http
USE_HTTPS_IN_ABSOLUTE_URLS = env.bool("USE_HTTPS_IN_ABSOLUTE_URLS", default=False)

ADMINS = [("DOGESEC", "noreply@dogesec.com")]

# Add your google analytics ID to the environment to connect to Google Analytics
GOOGLE_ANALYTICS_ID = env("GOOGLE_ANALYTICS_ID", default="")


# Stripe config
# modeled to be the same as https://github.com/dj-stripe/dj-stripe
# Note: don"t edit these values here - edit them in your .env file or environment variables!
# The defaults are provided to prevent crashes if your keys don"t match the expected format.
STRIPE_PUBLIC_KEY = env("STRIPE_PUBLIC_KEY", default="pk_test_***")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="sk_test_***")

# Change to True in production
STRIPE_LIVE_MODE = env.bool("STRIPE_LIVE_MODE", False)

if STRIPE_LIVE_MODE:
    STRIPE_LIVE_PUBLIC_KEY = STRIPE_PUBLIC_KEY
    STRIPE_LIVE_PUBLIC_KEY = STRIPE_SECRET_KEY
else:
    STRIPE_TEST_PUBLIC_KEY = STRIPE_PUBLIC_KEY
    STRIPE_TEST_SECRET_KEY = STRIPE_SECRET_KEY

API_KEY_CUSTOM_HEADER = "HTTP_API_KEY"
# djstripe settings
# Get it from the section in the Stripe dashboard where you added the webhook endpoint
# or from the stripe CLI when testing
DJSTRIPE_WEBHOOK_SECRET = env("DJSTRIPE_WEBHOOK_SECRET", default="whsec_***")

DJSTRIPE_FOREIGN_KEY_TO_FIELD = (
    "id"  # change to "djstripe_id" if not a new installation
)
DJSTRIPE_SUBSCRIBER_MODEL = "teams.Team"
DJSTRIPE_SUBSCRIBER_MODEL_REQUEST_CALLBACK = lambda request: request.team  # noqa E731

SILENCED_SYSTEM_CHECKS = [
    "djstripe.I002",
]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": '[{asctime}] {levelname} "{name}" {message}',
            "style": "{",
            "datefmt": "%d/%b/%Y %H:%M:%S",  # match Django server time format
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": env("DJANGO_LOG_LEVEL", default="INFO"),
        },
        "obstracts_web": {
            "handlers": ["console"],
            "level": env("OBSTRACTS_WEB_LOG_LEVEL", default="INFO"),
        },
    },
}

FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", default="")
INVITATION_URL = FRONTEND_BASE_URL + "/teams/invitation/"

OBSTRACT_SERVICE_BASE_URL = env("OBSTRACT_SERVICE_BASE_URL", default="")
OBSTRACT_SERVICE_API = OBSTRACT_SERVICE_BASE_URL + "/api/v1"

BREVO_KEY = env("BREVO_KEY", default="")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("SMTP_SERVER")
EMAIL_PORT = env("SMTP_PORT")
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("SMTP_USERNAME")
EMAIL_HOST_PASSWORD = env("SMTP_PASSWORD")

PROJECT_METADATA = {
    "NAME": gettext_lazy("Obstracts Web"),
    "URL": FRONTEND_BASE_URL,
    "DESCRIPTION": gettext_lazy(
        "The most amazing SaaS application the world has ever seen"
    ),
    "IMAGE": "https://upload.wikimedia.org/wikipedia/commons/2/20/PEO-pegasus_black.svg",
    "KEYWORDS": "SaaS, django",
    "CONTACT_EMAIL": "noreply@dogesec.com",
}


USE_SSL = env.bool("USE_SSL", False)
if USE_SSL:
    # fix ssl mixed content issues
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # Django security checklist settings.
    # More details here: https://docs.djangoproject.com/en/stable/howto/deployment/checklist/
    # SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    USE_X_FORWARDED_HOST = True
    # HTTP Strict Transport Security settings
    # Without uncommenting the lines below, you will get security warnings when running ./manage.py check --deploy
    # https://docs.djangoproject.com/en/stable/ref/middleware/#http-strict-transport-security

    # # Increase this number once you're confident everything works https://stackoverflow.com/a/49168623/8207
    # SECURE_HSTS_SECONDS = 60
    # # Uncomment these two lines if you are sure that you don't host any subdomains over HTTP.
    # # You will get security warnings if you don't do this.
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_HSTS_PRELOAD = True

    USE_HTTPS_IN_ABSOLUTE_URLS = True


### Arango Taxii Server settings
ARANGODB_HOST_URL = env('ARANGODB_HOST_URL')
ARANGODB_USERNAME = env('ARANGODB_USERNAME')
ARANGODB_PASSWORD = env('ARANGODB_PASSWORD')
ARANGO_TAXII_SETTINGS = {
    'FILTER_COLLECTIONS': 'apps.utils.arango_taxii_server.filter_collections',
    'FILTER_API_ROOTS': 'apps.utils.arango_taxii_server.filter_api_roots',
    'PERMISSION_CLASSES': ('apps.utils.arango_taxii_server.Authenticated',),
    'ARANGO_AUTH_FUNCTION': 'apps.utils.arango_taxii_server.get_arango_auth',
    'ARANGODB_HOST_URL': ARANGODB_HOST_URL,
    'SUPPORT_WRITE_OPERATIONS': False,
}