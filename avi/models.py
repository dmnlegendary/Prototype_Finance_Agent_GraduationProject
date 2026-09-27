from django.conf import settings
from django.db import models

from core.models import ModeloBase


class HistorialConversacion(ModeloBase):
    """Un mensaje (del usuario o del asistente) del chat con el AVI. Aún sin usar."""

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
        verbose_name = "Historial de conversación (AVI)"
        ordering = ["creado_en"]

    def __str__(self):
        return f"[{self.rol}] {self.mensaje[:40]}"
