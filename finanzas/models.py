from django.db import models
from django.utils import timezone

from core.models import ModeloBase


def mes_actual():
    """Primer día del mes de hoy (el periodo que se propone al registrar un gasto)."""
    return timezone.localdate().replace(day=1)


class CategoriaGasto(ModeloBase):
    """Categoría libre que el tendero crea sobre la marcha (Renta, Luz, Internet…)."""

    negocio = models.ForeignKey("accounts.Negocio", on_delete=models.CASCADE, related_name="categorias_gasto")
    nombre = models.CharField(max_length=60)
    # si es un gasto que normalmente se paga siempre o que cambia según el mes; con esto se propone el tipo al elegirla
    tipo = models.CharField(max_length=10, blank=True, default="")

    class Meta:
        verbose_name = "Categoría de gasto"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["negocio", "nombre"], name="categoria_gasto_unica_por_negocio"),
        ]

    def __str__(self):
        return self.nombre


class GastoOperativo(ModeloBase):
    """Gasto del negocio: fijo (renta, luz), variable (bolsas, flete) o compra de
    mercancía. La compra de mercancía se registra sola cuando se agregan piezas al
    inventario; cuenta para el flujo de efectivo pero NO para la utilidad, porque
    el costo de lo vendido ya se resta al vender (si no, se contaría dos veces)."""

    class Tipo(models.TextChoices):
        FIJO = "FIJO", "Fijo"
        VARIABLE = "VARIABLE", "Variable"
        MERCANCIA = "MERCANCIA", "Compra de mercancía"

    negocio = models.ForeignKey("accounts.Negocio", on_delete=models.CASCADE, related_name="gastos")
    categoria = models.ForeignKey(
        CategoriaGasto, on_delete=models.SET_NULL, null=True, blank=True, related_name="gastos",
    )
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    concepto = models.CharField(max_length=150)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    nota = models.CharField(max_length=255, blank=True)
    fecha = models.DateField(auto_now_add=True)
    # el mes al que pertenece el gasto (por ejemplo, la luz de septiembre que se paga en octubre).
    # Se guarda como el primer día de ese mes y es el que cuentan los reportes.
    periodo = models.DateField("Mes al que corresponde", default=mes_actual)

    class Meta:
        verbose_name = "Gasto operativo"
        ordering = ["-periodo", "-fecha"]
        indexes = [
            models.Index(fields=["negocio", "fecha"], name="gasto_negocio_fecha_idx"),
            models.Index(fields=["negocio", "periodo"], name="gasto_negocio_periodo_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0), name="gasto_monto_positivo",
                violation_error_message="El monto del gasto debe ser mayor a cero.",
            ),
        ]

    def __str__(self):
        return f"{self.concepto} (${self.monto})"


# Pendiente para más adelante: punto de equilibrio, precio sugerido y
# el pronóstico de ventas (todavía no se decide con qué modelo).
