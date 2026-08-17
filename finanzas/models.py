"""
Modelos de `finanzas`.

Alcance de ESTA entrega (a propósito acotado, según lo solicitado):
solo el modelo de Gastos Operativos, que es lo mínimo para que
"punto de equilibrio" y "reportes financieros" tengan de dónde leer datos
más adelante. NO se modela todavía ningún cálculo de punto de equilibrio
ni pronóstico: eso es lógica de servicio (se calculará en tiempo real a
partir de estos gastos + las ventas), no un dato que deba persistirse hoy.

Referencia de diseño (NO implementada aún): agente_financiero/agente_financiero.jsx
ya maqueta en React cómo se verían "Gastos", "Punto de equilibrio" y
"Precios sugeridos". Se deja como insumo de diseño para cuando se aborde
esa pantalla en Django; por ahora esta app solo expone el placeholder.
"""
from django.db import models

from core.models import ModeloBase


class GastoOperativo(ModeloBase):
    """
    Gasto fijo o variable del negocio (ver agente_financiero.jsx:
    GastosView -> "Gastos fijos: renta, luz, internet" / "Gastos
    variables: inventario, merma, bolsas").
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


# TODO (roadmap, explícitamente FUERA de esta entrega):
#   - Modelo/servicio de "Punto de equilibrio" (calculado, no persistido,
#     a partir de GastoOperativo + Venta).
#   - Modelo de "Precio sugerido" por producto (regla simple costo/margen,
#     SIN machine learning todavía).
#   - Motor predictivo de ventas (ML) y su integración con el AVI: eso
#     vive en una futura app/servicio aparte, no en `finanzas`.
