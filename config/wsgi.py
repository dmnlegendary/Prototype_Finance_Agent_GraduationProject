"""
Configuración WSGI para el proyecto. Expone la variable de módulo
`application`, usada por servidores WSGI (gunicorn, Azure App Service, etc.)
para servir el proyecto en producción.
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
