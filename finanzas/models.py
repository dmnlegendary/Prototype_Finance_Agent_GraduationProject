from django.db import models

from core.models import ModeloBase


class GastoOperativo(ModeloBase):
    """Gasto fijo o variable del negocio (renta, luz, inventario, merma, etc.)."""

    class Tipo(models.TextChoices):
        FIJO = "FIJO", "Fijo"
        VARIABLE = "VARIABLE", "Variable"

    negocio = models.ForeignKey("accounts.Negocio", on_delete=models.CASCADE, related_name="gastos")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    concepto = models.CharField(max_length=150)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    nota = models.CharField(max_length=255, blank=True)
    fecha = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = "Gasto operativo"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.concepto} (${self.monto})"


# Pendiente para más adelante: punto de equilibrio, precio sugerido y
# el pronóstico de ventas (todavía no se decide con qué modelo).
