"""
Django settings for SecurWork e-commerce platform.
"""
from datetime import timedelta
from pathlib import Path

from decouple import Config, Csv, RepositoryEnv

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent
_env_file = ROOT_DIR / ".env"
config = Config(RepositoryEnv(str(_env_file))) if _env_file.exists() else Config(RepositoryEnv())

SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# Public storefront URL — required in production (emails, redirects). Set in .env per environment.
FRONTEND_URL = config("FRONTEND_URL", default="")

# Django admin path — React owns /admin/ for the product panel.
DJANGO_ADMIN_PATH = config("DJANGO_ADMIN_PATH", default="django-admin")


def _csv_env(key: str) -> list[str]:
    """Parse a comma-separated env var, ignoring empty values."""
    return [v.strip() for v in config(key, default="", cast=Csv()) if v.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "parler",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "store",
    "orders",
    "accounts",
    "cms",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.DevFrontendRedirectMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if config("USE_SQLITE", default=False, cast=bool):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("DB_NAME", default="securwork"),
            "USER": config("DB_USER", default="securwork"),
            "PASSWORD": config("DB_PASSWORD", default="securwork"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "it"
LANGUAGES = [
    ("it", "Italiano"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = "Europe/Rome"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Parler — bilingual content
PARLER_LANGUAGES = {
    None: (
        {"code": "it"},
        {"code": "en"},
    ),
    "default": {
        "fallbacks": ["it"],
        "hide_untranslated": False,
    },
}

# CORS / CSRF — set per environment in .env (local dev needs origins; production same-origin usually does not).
CORS_ALLOWED_ORIGINS = _csv_env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = _csv_env("CSRF_TRUSTED_ORIGINS")

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "config.authentication.OptionalJWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.AllowAny",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_THROTTLE_RATES": {
        "contact": "10/hour",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# SecurWork store defaults
SECURWORK_CURRENCY = "EUR"
SECURWORK_VAT_RATE = config("VAT_RATE", default="22.00", cast=str)
SECURWORK_LOW_STOCK_THRESHOLD = config("LOW_STOCK_THRESHOLD", default=5, cast=int)

# Email (contact form)
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@securwork.it")
CONTACT_EMAIL = config("CONTACT_EMAIL", default="info@securwork.it")
ORDER_ADMIN_EMAIL = config("ORDER_ADMIN_EMAIL", default=CONTACT_EMAIL)

# Shipping
SECURWORK_SHIPPING_FLAT_RATE = config("SHIPPING_FLAT_RATE", default="5.99")
SECURWORK_FREE_SHIPPING_THRESHOLD = config("FREE_SHIPPING_THRESHOLD", default="100.00")

# Stripe payments
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")

# Bank transfer (displayed at checkout)
SECURWORK_BANK_IBAN = config("SECURWORK_BANK_IBAN", default="[PLACEHOLDER-IBAN]")
SECURWORK_BANK_BIC = config("SECURWORK_BANK_BIC", default="[PLACEHOLDER-BIC]")
SECURWORK_BANK_ACCOUNT_NAME = config("SECURWORK_BANK_ACCOUNT_NAME", default="SecurWork S.r.l.")

# Company / contact info (public site config)
SECURWORK_COMPANY_NAME = config("SECURWORK_COMPANY_NAME", default="SecurWork S.r.l.")
SECURWORK_COMPANY_VAT = config("SECURWORK_COMPANY_VAT", default="[PLACEHOLDER] P.IVA")
SECURWORK_COMPANY_ADDRESS = config("SECURWORK_COMPANY_ADDRESS", default="[PLACEHOLDER] Via Esempio 1")
SECURWORK_COMPANY_CITY = config("SECURWORK_COMPANY_CITY", default="[PLACEHOLDER] Milano, Italia")
SECURWORK_COMPANY_PHONE = config("SECURWORK_COMPANY_PHONE", default="+39 [PLACEHOLDER]")
SECURWORK_MAP_LAT = config("SECURWORK_MAP_LAT", default="45.4642")
SECURWORK_MAP_LNG = config("SECURWORK_MAP_LNG", default="9.1900")

# Security (production)
if not DEBUG:
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
