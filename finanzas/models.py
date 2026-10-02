from django.db import models

from core.models import ModeloBase


class CategoriaGasto(ModeloBase):
    """Categoría libre que el tendero crea sobre la marcha (Renta, Luz, Internet…)."""

    negocio = models.ForeignKey("accounts.Negocio", on_delete=models.CASCADE, related_name="categorias_gasto")
    nombre = models.CharField(max_length=60)

    class Meta:
        verbose_name = "Categoría de gasto"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["negocio", "nombre"], name="categoria_gasto_unica_por_negocio"),
        ]

    def __str__(self):
        return self.nombre


class GastoOperativo(ModeloBase):
    """Gasto fijo o variable del negocio (renta, luz, inventario, merma, etc.)."""

    class Tipo(models.TextChoices):
        FIJO = "FIJO", "Fijo"
        VARIABLE = "VARIABLE", "Variable"

    negocio = models.ForeignKey("accounts.Negocio", on_delete=models.CASCADE, related_name="gastos")
    categoria = models.ForeignKey(
        CategoriaGasto, on_delete=models.SET_NULL, null=True, blank=True, related_name="gastos",
    )
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
