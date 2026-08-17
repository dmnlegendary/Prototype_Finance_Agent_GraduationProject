"""
Configuración ASGI para el proyecto. Se deja lista desde ahora porque el
futuro AVI (chat en tiempo real / streaming de respuestas del LLM) puede
beneficiarse de un servidor ASGI (ej. Daphne/Uvicorn) en vez de WSGI puro.
Por ahora el proyecto puede correr perfectamente sobre WSGI.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
