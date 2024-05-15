import os
import environ
import datetime
from pathlib import Path
from urllib.parse import urljoin

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
# Take environment variables from .env file
environ.Env.read_env(os.path.join(BASE_DIR, ".venv"))

env = environ.Env(
    # set casting, default value
    DJANGO_DEBUG=(bool, False)
)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-ps#8st!$_(#b$4p4dda9d_z4_h&1@qbs^95xyo%g5(^^je9(j5"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

# DOMAIN_URL = "http://localhost:8000"
DOMAIN_URL = "https://adequate-adequately-husky.ngrok-free.app"


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # INTERNAL APPS
    "common",
    "accounts",
    "agents",
    "integrations",
    "feedbacks",
    # THIRD-PARTY AUTH APPS
    "social_django",
    "drf_yasg",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "django_celery_results",
    "django_celery_beat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # SOCIAL-DJANGO MIDDLEWARE
    "social_django.middleware.SocialAuthExceptionMiddleware",
    # DJANGO-CORS HEADERS
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # SOCIAL-DJANGO CONFIG
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

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

AUTH_USER_MODEL = "accounts.User"

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# EMAIL CONFIG
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = env("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = True


# DJANGO-CORS CONFIGURATIONS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
        "https://adequate-adequately-husky.ngrok-free.app",
    ],
)
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",  # for localhost (REACT Default)
    "http://192.168.0.50:3000",  # for network
    "http://localhost:8080",  # for localhost (Developlemt)
    "http://192.168.0.50:8080",  # for network (Development)
    "https://adequate-adequately-husky.ngrok-free.app",
]


REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "accounts.authentication.JSONWebTokenCookieAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_THROTTLE_RATES": {"anon": "100/day"},
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(
        minutes=env.int("ACCESS_TOKEN_LIFETIME_MINUTES", default=60)
    ),
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(
        days=env.int("REFRESH_TOKEN_LIFETIME_DAYS", default=7)
    ),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
}
ACCESS_TOKEN_COOKIE = "token"
REFRESH_TOKEN_COOKIE = "refresh_token"
REFRESH_TOKEN_LOGOUT_COOKIE = "refresh_token_logout"
COOKIE_MAX_AGE = 3600 * 24 * 14  # 14 days

SOCIAL_AUTH_USER_MODEL = "accounts.User"
SOCIAL_AUTH_USER_FIELDS = ["email", "username"]
SOCIAL_AUTH_STRATEGY = "accounts.strategy.DjangoJWTStrategy"
SOCIAL_AUTH_JSONFIELD_ENABLED = True
SOCIAL_AUTH_REDIRECT_IS_HTTPS = env.bool("SOCIAL_AUTH_REDIRECT_IS_HTTPS", default=True)
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.social_auth.associate_by_email",
    "social_core.pipeline.user.create_user",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
    "social_core.pipeline.user.user_details",
)
SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS = env.list(
    "SOCIAL_AUTH_ALLOWED_REDIRECT_HOSTS", default=[]
)
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = env("SOCIAL_AUTH_GOOGLE_OAUTH2_KEY", default="")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = env("SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET", default="")
SOCIAL_AUTH_FACEBOOK_KEY = env("SOCIAL_AUTH_FACEBOOK_KEY", default="")
SOCIAL_AUTH_FACEBOOK_SECRET = env("SOCIAL_AUTH_FACEBOOK_SECRET", default="")
SOCIAL_AUTH_FACEBOOK_SCOPE = ["email", "public_profile"]
SOCIAL_AUTH_FACEBOOK_PROFILE_EXTRA_PARAMS = {
    "fields": "id, name, email",
}
SOCIAL_AUTH_LOGIN_ERROR_URL = "/"
SOCIAL_AUTH_FIELDS_STORED_IN_SESSION = ["locale"]

SWAGGER_SETTINGS = {
    "DEFAULT_INFO": "core.urls.api_info",
    "SECURITY_DEFINITIONS": {
        "api_key": {"type": "apiKey", "in": "header", "name": "Authorization"}
    },
}

HASHID_FIELD_SALT = env("HASHID_FIELD_SALT", default="haaga82@#*?!")
HASHID_FIELD_ENABLE_HASHID_OBJECT = False

OTP_AUTH_ISSUER_NAME = env("OTP_AUTH_ISSUER_NAME", default="")
OTP_AUTH_TOKEN_COOKIE = "otp_auth_token"
OTP_AUTH_TOKEN_LIFETIME_MINUTES = datetime.timedelta(
    minutes=env.int("OTP_AUTH_TOKEN_LIFETIME_MINUTES", default=5)
)
OTP_VALIDATE_PATH = "/auth/validate-otp"


# SLACK CONFIGURATIONS
SLACK_SCOPES = env(
    "SLACK_SCOPES", default=["chat:write", "channels:history", "app_mentions:read"]
)
SLACK_CLIENT_ID = env("SLACK_CLIENT_ID", default="")
SLACK_CLIENT_SECRET = env("SLACK_CLIENT_SECRET", default="")
SLACK_SIGNING_SECRET = env("SLACK_SIGNING_SECRET", default="")
SLACK_EVENT_URL = urljoin(DOMAIN_URL, "/api/integrations/event")
SLACK_STATE_EXPIRATION_SECONDS = env("SLACK_STATE_EXPIRATION_SECONDS", default=3000)

# GOOGLE CONFIGURATIONS
DISCOVERY_DOC = "https://forms.googleapis.com/$discovery/rest?version=v1"
GOOGLE_GMAIL_SCOPES = ["https://mail.google.com/"]
GOOGLE_DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
GOOGLE_CALENDER_SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
]
GOOGLE_DOCUMENT_SCOPES = []
GOOGLE_DRIVE_SCOPES = []
GOOGLE_SHEET_SCOPES = []
GOOGLE_FORM_SCOPES = []
DEFAULT_CREDS_TOKEN_FILE = BASE_DIR / "token.json"
DEFAULT_CLIENT_SECRETS_FILE = BASE_DIR / "credentials.json"
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")
INTEGRATION_REDIRECT_URI = urljoin(DOMAIN_URL, "/api/integrations/oauth/callback")
GOOGLE_API_KEY = env("GOOGLE_API_KEY", default="")  # For GeminiAPI 


# CELERY CONFIGURATIONS
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_BROKER_URL=env('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0')
# this allows you to schedule items in the Django admin.
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_USE_SSL =True