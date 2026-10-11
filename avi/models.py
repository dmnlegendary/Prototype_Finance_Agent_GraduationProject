from django.conf import settings
from django.db import models

from core.models import ModeloBase


class HistorialConversacion(ModeloBase):
    """Un mensaje (del usuario o del asistente) del chat con el AVI."""

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
        indexes = [
            models.Index(fields=["negocio", "creado_en"], name="conversacion_negocio_fecha_idx"),
        ]

    def __str__(self):
        return f"[{self.rol}] {self.mensaje[:40]}"


class ResumenDiario(ModeloBase):
    """El resumen de "cómo te fue ayer" que la IA genera la primera vez que el
    tendero entra al sistema en el día, para no llamarla en cada inicio de sesión."""

    negocio = models.ForeignKey(
        "accounts.Negocio", on_delete=models.CASCADE, related_name="resumenes_avi",
    )
    fecha = models.DateField()
    texto = models.TextField()
    numero_ventas = models.PositiveIntegerField(default=0)
    total_ventas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ganancia = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_gastos = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Resumen diario (AVI)"
        ordering = ["-fecha"]
        constraints = [
            models.UniqueConstraint(fields=["negocio", "fecha"], name="resumen_avi_unico_por_dia"),
        ]

    def __str__(self):
        return f"Resumen {self.fecha} · {self.negocio.nombre_tienda}"


class ExplicacionIA(ModeloBase):
    """La explicación que la IA da del dashboard o de los reportes financieros.

    Se guarda junto con una "huella" de los números que se le mandaron: si el
    tendero vuelve a pedirla y los números no cambiaron, se muestra la misma
    explicación sin gastar otra llamada a la IA."""

    class Tipo(models.TextChoices):
        DASHBOARD = "dashboard", "Dashboard"
        REPORTES = "reportes", "Reportes financieros"

    negocio = models.ForeignKey(
        "accounts.Negocio", on_delete=models.CASCADE, related_name="explicaciones_avi",
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    fecha = models.DateField()
    huella = models.CharField(max_length=64)
    texto = models.TextField()

    class Meta:
        verbose_name = "Explicación de la IA"
        verbose_name_plural = "Explicaciones de la IA"
        ordering = ["-fecha"]
        constraints = [
            models.UniqueConstraint(fields=["negocio", "tipo", "fecha"], name="explicacion_unica_por_dia"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.fecha} · {self.negocio.nombre_tienda}"
