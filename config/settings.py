"""
Configuración de Django para el proyecto "Tiendita AI" (POS + Auxiliar de
Inventario + Agente Financiero para microempresas).

Filosofía de esta configuración:
- Debe funcionar "out of the box" en desarrollo con SQLite y sin variables
  de entorno configuradas (cero fricción para clonar y correr el proyecto).
- Ningún valor sensible (SECRET_KEY, credenciales de BD, API keys futuras
  del AVI) queda hardcodeado: todo se lee de variables de entorno con un
  valor por defecto SOLO apto para desarrollo local.
- Está pensada para migrar a PostgreSQL / Azure SQL sin tocar el resto del
  código: basta con definir la variable de entorno DATABASE_URL (ver
  sección DATABASES) e instalar el driver correspondiente.

Generado con Django 5.x (django-admin startproject), luego adaptado a la
arquitectura de monolito modular de este Trabajo Terminal.
"""

import os
from pathlib import Path

# BASE_DIR apunta a la raíz del repositorio (donde vive manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent


# ──────────────────────────────────────────────────────────────────────────
# SEGURIDAD BÁSICA
# ──────────────────────────────────────────────────────────────────────────
# En producción, SECRET_KEY y DEBUG SIEMPRE deben venir de variables de
# entorno (o de un servicio de secretos, ej. Azure Key Vault). El valor por
# defecto de abajo es intencionalmente inseguro y solo sirve para que el
# proyecto arranque en desarrollo sin configuración extra.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-CAMBIA-ESTA-LLAVE-ANTES-DE-DESPLEGAR-A-PRODUCCION",
)

# DEBUG=True habilita páginas de error detalladas y sirve estáticos sin
# `collectstatic`. Debe ser False en producción.
DEBUG = os.environ.get("DJANGO_DEBUG", "True") == "True"

# Lista de hosts/dominios permitidos, separados por coma.
# Ej: DJANGO_ALLOWED_HOSTS="tiendita-ai.azurewebsites.net,miapp.com"
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]


# ──────────────────────────────────────────────────────────────────────────
# APPS INSTALADAS
# ──────────────────────────────────────────────────────────────────────────
# Se separan las apps de Django, apps de terceros y apps propias del
# proyecto para que sea fácil ubicar cada módulo de negocio.
INSTALLED_APPS = [
    # Apps nativas de Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",  # filtros de plantilla para moneda/números (intcomma, etc.)

    # Apps propias del proyecto (monolito modular).
    # Orden: primero las que no dependen de otras (core, accounts), luego
    # las que sí dependen de accounts/inventario (ventas, finanzas).
    "core",            # utilidades compartidas, template base, navegación
    "accounts",        # usuarios, autenticación, onboarding del negocio
    "inventario",      # catálogo de productos, proveedores, alertas
    "ventas",          # punto de venta / carrito
    "finanzas",        # gastos operativos, punto de equilibrio (placeholder)
    "avi",             # placeholder del futuro Asistente Virtual Inteligente
]

# Modelo de usuario personalizado (ver accounts/models.py). Se define desde
# el día 1 del proyecto porque cambiar el modelo de usuario después de tener
# migraciones aplicadas es muy costoso en Django.
AUTH_USER_MODEL = "accounts.Usuario"


# ──────────────────────────────────────────────────────────────────────────
# MIDDLEWARE
# ──────────────────────────────────────────────────────────────────────────
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


# ──────────────────────────────────────────────────────────────────────────
# TEMPLATES
# ──────────────────────────────────────────────────────────────────────────
# Estrategia híbrida (recomendada para monolitos modulares en Django):
#   - `DIRS` apunta a una carpeta GLOBAL `templates/` en la raíz del repo,
#     usada solo para lo que comparten TODAS las apps: base.html,
#     base_app.html y partials/ (navbar, footer). Así evitamos duplicar el
#     layout en cada app.
#   - `APP_DIRS = True` habilita que cada app tenga su propia carpeta
#     `templates/<nombre_app>/` (namespacing) para sus vistas específicas.
#     El namespacing (carpeta con el nombre de la app dentro de templates/)
#     evita colisiones de nombres entre apps (ej. dos apps con "detalle.html").
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
                # Context processor propio: expone el negocio del usuario
                # autenticado (Negocio) a TODAS las plantillas, para poder
                # mostrar el nombre de la tienda en el navbar sin repetir
                # la consulta en cada vista. Ver core/context_processors.py.
                "core.context_processors.negocio_activo",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ──────────────────────────────────────────────────────────────────────────
# BASE DE DATOS
# ──────────────────────────────────────────────────────────────────────────
# Desarrollo: SQLite (cero configuración, ideal para prototipar el TT).
# Producción futura: define la variable de entorno DATABASE_URL y este
# proyecto usará esa base sin cambiar una sola línea de código de las apps,
# porque TODO el acceso a datos pasa por el ORM de Django (nunca SQL crudo).
#
# Ejemplos de DATABASE_URL cuando migren:
#   PostgreSQL:  postgres://usuario:password@host:5432/nombre_bd
#   Azure SQL:   mssql://usuario:password@servidor.database.windows.net/bd
#
# Para activar esto en el futuro basta con:
#   pip install dj-database-url psycopg2-binary   # (o mssql-django para Azure SQL)
# y descomentar el bloque de abajo.
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # TODO (fase de despliegue): instalar `dj-database-url` y descomentar:
    # import dj_database_url
    # DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
    raise NotImplementedError(
        "DATABASE_URL fue definida pero el soporte para PostgreSQL/Azure SQL "
        "todavía no está activado. Instala dj-database-url (y el driver que "
        "corresponda) y descomenta el bloque indicado en config/settings.py."
    )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ──────────────────────────────────────────────────────────────────────────
# VALIDACIÓN DE CONTRASEÑAS
# ──────────────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# NOTA: MinimumLengthValidator se fijó en 6 para calzar con el placeholder
# "Mínimo 6 caracteres" del formulario de registro.html. Ajusten este valor
# si el equipo decide exigir contraseñas más largas.


# ──────────────────────────────────────────────────────────────────────────
# INTERNACIONALIZACIÓN
# ──────────────────────────────────────────────────────────────────────────
LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True


# ──────────────────────────────────────────────────────────────────────────
# ARCHIVOS ESTÁTICOS (CSS/JS/imágenes) Y ARCHIVOS DE MEDIA (subidos por el usuario)
# ──────────────────────────────────────────────────────────────────────────
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]          # estáticos globales del proyecto
STATIC_ROOT = BASE_DIR / "staticfiles"             # destino de `collectstatic` (producción)

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"                     # ej. fotos de productos subidas por el dueño

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ──────────────────────────────────────────────────────────────────────────
# AUTENTICACIÓN / SESIONES
# ──────────────────────────────────────────────────────────────────────────
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "ventas:punto_de_venta"
LOGOUT_REDIRECT_URL = "accounts:login"

# Sesiones basadas en base de datos (backend por defecto de Django). Es la
# opción más simple y funciona igual en SQLite/PostgreSQL/Azure SQL sin
# infraestructura adicional (a diferencia de sesiones basadas en cache/Redis).
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 horas: duración típica de un turno de caja
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True  # renueva el tiempo de vida en cada request activo

# Seguridad de cookies/CSRF. En desarrollo (DEBUG=True) se mantienen laxas
# para poder probar en http://127.0.0.1. En producción, con DEBUG=False,
# se activan automáticamente los flags "Secure" (requieren HTTPS, que es
# el estándar en Azure App Service).
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# TODO (fase de despliegue en Azure): agregar SECURE_SSL_REDIRECT = True,
# SECURE_HSTS_SECONDS, y CSRF_TRUSTED_ORIGINS con el dominio final.
