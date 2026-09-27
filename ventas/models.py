from django.conf import settings
from django.db import models

from core.models import ModeloBase
from inventario.models import Producto


class Venta(ModeloBase):
    """Un ticket de venta."""

    class Estado(models.TextChoices):
        EN_CURSO = "EN_CURSO", "En curso"
        COBRADA = "COBRADA", "Cobrada"
        CANCELADA = "CANCELADA", "Cancelada"

    negocio = models.ForeignKey("accounts.Negocio", on_delete=models.CASCADE, related_name="ventas")
    cajero = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="ventas_realizadas",
    )
    folio = models.PositiveIntegerField()
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.EN_CURSO)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-creado_en"]
        constraints = [
            models.UniqueConstraint(fields=["negocio", "folio"], name="folio_unico_por_negocio"),
        ]

    def __str__(self):
        return f"Venta #{self.folio:04d} ({self.negocio.nombre_tienda})"

    def recalcular_total(self):
        self.total = sum((item.subtotal for item in self.items.all()), start=0)
        self.save(update_fields=["total"])


class ItemVenta(ModeloBase):
    """Cada renglón del carrito."""

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="items_venta")
    # decimal para poder vender a granel (ej. 1.5 kg)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario
