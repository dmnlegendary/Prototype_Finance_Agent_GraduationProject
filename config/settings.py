# Configuración de Django del proyecto (marIA).
# Corre en local con SQLite o con PostgreSQL (ver DATABASES más abajo).

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga las llaves del archivo .env (en la raíz del proyecto, junto a manage.py)
load_dotenv(BASE_DIR / ".env")

# En producción la llave y el modo debug se ponen en el .env (ver .env.example)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-cambiar-esta-llave-antes-de-subir-a-produccion")

DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

# Direcciones desde las que se puede abrir el sistema (separadas por comas en el .env)
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if host.strip()]
CSRF_TRUSTED_ORIGINS = [origen.strip() for origen in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if origen.strip()]

# HTTPS: con USAR_HTTPS=True en el .env todo viaja cifrado (la contraseña y la sesión nunca van en claro).
# Se activa cuando el sistema se publica detrás de un certificado (por ejemplo, el de Cloudflare cuando se usa un túnel).
USAR_HTTPS = os.environ.get("USAR_HTTPS", "False") == "True"
if USAR_HTTPS:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Apps del proyecto
    "core",
    "accounts",
    "inventario",
    "ventas",
    "finanzas",
    "avi",
]

# Modelo de usuario propio, definido en accounts/models.py
AUTH_USER_MODEL = "accounts.Usuario"

# Permite iniciar sesión con teléfono o con correo (ver accounts/backends.py)
AUTHENTICATION_BACKENDS = [
    "accounts.backends.TelefonoOCorreoBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Modo desarrollo: el correo de recuperación de contraseña se imprime en la
# terminal en vez de mandarse de verdad. Cambiar por un backend SMTP real
# antes de producción.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "marIA <no-reply@mariamiga.local>"


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
        # carpeta de templates compartidos por todas las apps
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # agrega la variable `negocio` a todas las plantillas
                "core.context_processors.negocio_activo",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Base de datos. Si en el .env se define DB_NAME se usa PostgreSQL (lo
# recomendado, sobre todo con miles de productos y ventas). Si no, se usa
# SQLite para poder probar el proyecto sin instalar nada. Ver database/README.md
if os.environ.get("DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DB_NAME"],
            "USER": os.environ.get("DB_USER", "postgres"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# Cache en memoria para los datos que más se piden (ver core/cache_negocio.py).
# Ojo: vive dentro de cada proceso de Python; si algún día se corren varios
# procesos hay que cambiarlo por Redis.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "marIA",
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# A dónde mandar al usuario al iniciar/cerrar sesión
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "ventas:punto_de_venta"
LOGOUT_REDIRECT_URL = "accounts:login"


# API keys del AVI (nunca hardcodeadas). Se definen como variables de entorno:
#   Lo más fácil: python manage.py configurar_ia (las guarda en el archivo .env)
#   Windows:  set OPENAI_API_KEY=sk-...
#   Linux/Mac: export OPENAI_API_KEY=sk-...
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")


# Video de presentación que se muestra la primera vez que alguien entra (puede ser un enlace de YouTube,
# de Vimeo o un archivo de video). Si se deja vacío, no se muestra nada.
VIDEO_INTRODUCTORIO_URL = os.environ.get("VIDEO_INTRODUCTORIO_URL", "")

# Días de historia que necesita un producto para poder pronosticar sus ventas
PRONOSTICO_MINIMO_DIAS = int(os.environ.get("PRONOSTICO_MINIMO_DIAS", "30"))
