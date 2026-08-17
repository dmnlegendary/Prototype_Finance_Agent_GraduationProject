"""
App PLACEHOLDER para el futuro Asistente Virtual Inteligente (AVI).

Instrucción explícita del alcance actual: "vacío/placeholder, sin lógica,
para no tener que reestructurar todo el proyecto después". Por eso esta
app:
  - SÍ está en INSTALLED_APPS y en config/urls.py (con un urls.py vacío),
    para que el día que se implemente el AVI baste con escribir
    views.py/urls.py aquí adentro, sin tocar el resto del proyecto.
  - NO tiene vistas activas, NO llama a ningún LLM externo, NO tiene
    prompts ni lógica de negocio todavía.

El único modelo que existe es un placeholder de historial de conversación,
para que el esquema de base de datos ya contemple dónde vivirán los
mensajes cuando se conecte la API del LLM (ChatGPT/Gemini). Se deja
comentado en avi/admin.py para no exponerlo en el admin todavía.
"""
from django.conf import settings
from django.db import models

from core.models import ModeloBase


class HistorialConversacion(ModeloBase):
    """
    Placeholder. Un renglón por mensaje (del usuario o del asistente) en
    una conversación con el AVI. Sin lógica activa: nada en el proyecto
    escribe ni lee este modelo todavía.
    """

    class Rol(models.TextChoices):
        USUARIO = "USUARIO", "Usuario"
        ASISTENTE = "ASISTENTE", "Asistente"

    negocio = models.ForeignKey(
        "accounts.Negocio", on_delete=models.CASCADE, related_name="conversaciones_avi",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+",
    )
    rol = models.CharField(max_length=10, choices=Rol.choices)
    mensaje = models.TextField()

    class Meta:
        verbose_name = "Historial de conversación (AVI, placeholder)"
        ordering = ["creado_en"]

    def __str__(self):
        return f"[{self.rol}] {self.mensaje[:40]}"
