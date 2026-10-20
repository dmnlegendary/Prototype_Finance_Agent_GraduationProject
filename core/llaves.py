"""
Llaves de acceso a la IA (OpenAI y Google). Ni las llaves ni las contraseñas se guardan en texto
plano: las contraseñas las cifra Django (PBKDF2) y las llaves de la IA se guardan CIFRADAS en la base
de datos local, con una clave que sale de la SECRET_KEY del proyecto.

Si en la base de datos no hay llave, se usa la del archivo .env (así sigue funcionando en un
servidor donde las llaves se pongan como variables de entorno).
"""
import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from .models import LlaveIA

registro = logging.getLogger(__name__)

# a qué variable de entorno corresponde cada proveedor
VARIABLES = {LlaveIA.OPENAI: "OPENAI_API_KEY", LlaveIA.GEMINI: "GEMINI_API_KEY"}


def _cifrador():
    clave = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest())
    return Fernet(clave)


def cifrar(texto):
    return _cifrador().encrypt(texto.encode("utf-8")).decode("ascii")


def descifrar(cifrado):
    return _cifrador().decrypt(cifrado.encode("ascii")).decode("utf-8")


def guardar(proveedor, llave):
    """Guarda la llave cifrada (si ya había una de ese proveedor, la reemplaza)."""
    if proveedor not in VARIABLES:
        raise ValueError(f"Proveedor desconocido: {proveedor}")
    LlaveIA.objects.update_or_create(proveedor=proveedor, defaults={"valor_cifrado": cifrar(llave.strip())})


def obtener(proveedor):
    """La llave del proveedor, ya descifrada; si no hay en la base de datos, la del .env; si no, ''."""
    try:
        guardada = LlaveIA.objects.filter(proveedor=proveedor).first()
        if guardada:
            return descifrar(guardada.valor_cifrado)
    except InvalidToken:
        registro.warning("No se pudo descifrar la llave de %s (¿cambió la SECRET_KEY?).", proveedor)
    except Exception:  # por ejemplo, la tabla todavía no existe porque faltan migraciones
        registro.debug("No se pudo leer la llave de %s de la base de datos.", proveedor, exc_info=True)
    return getattr(settings, VARIABLES[proveedor], "") or ""


def origen(proveedor):
    """De dónde sale la llave: 'base de datos (cifrada)', '.env' o 'sin configurar'. Para el comando --ver."""
    try:
        if LlaveIA.objects.filter(proveedor=proveedor).exists():
            return "base de datos (cifrada)"
    except Exception:
        pass
    return ".env" if getattr(settings, VARIABLES[proveedor], "") else "sin configurar"
