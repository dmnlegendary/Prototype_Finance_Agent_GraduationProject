from django.db import models

from core.models import ModeloBase


class GastoOperativo(ModeloBase):
    """Gasto persistido y aislado por negocio, clasificado como fijo o variable.

    La fecha se asigna al crear el registro. Las vistas consultan los gastos
    usando la tienda de la sesion y no comparten filas entre negocios.
    """

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


# Pendiente para más adelante: punto de equilibrio y precio sugerido.
