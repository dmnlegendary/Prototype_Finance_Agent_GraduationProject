from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models

from core.models import ModeloBase
from inventario.models import Producto

# cuántas cajas pueden estar abiertas al mismo tiempo en una tienda
# (dos personas pueden cobrar a la vez, cada quien en el suyo)
MAXIMO_DE_CARRITOS = 2


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
    # número de la caja en el que se armó la venta (1 o 2)
    carrito = models.PositiveSmallIntegerField(default=1)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-creado_en"]
        constraints = [
            models.UniqueConstraint(fields=["negocio", "folio"], name="folio_unico_por_negocio"),
            models.CheckConstraint(condition=models.Q(total__gte=0), name="venta_total_no_negativo"),
            # solo puede haber una venta abierta por cada caja de la tienda
            models.UniqueConstraint(
                fields=["negocio", "carrito"], condition=models.Q(estado="EN_CURSO"),
                name="un_carrito_abierto_por_numero",
            ),
        ]
        # los reportes siempre piden "las ventas COBRADAS de un negocio en un rango de fechas"
        indexes = [
            models.Index(fields=["negocio", "estado", "creado_en"], name="venta_negocio_estado_fecha_idx"),
        ]

    def __str__(self):
        return f"Venta #{self.folio:04d} ({self.negocio.nombre_tienda})"

    def recalcular_total(self):
        total = sum((item.subtotal for item in self.items.all()), start=Decimal("0"))
        self.total = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        self.save(update_fields=["total"])


class ItemVenta(ModeloBase):
    """Cada renglón de la caja."""

    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="items_venta")
    # decimal para poder vender a granel (ej. 0.250 kg)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    # El precio y el costo se guardan en el renglón al momento de vender, así que si
    # después cambian en el producto, las ventas de antes NO cambian.
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name="item_cantidad_positiva"),
            models.CheckConstraint(condition=models.Q(precio_unitario__gte=0), name="item_precio_no_negativo"),
        ]

    def __str__(self):
        return f"{self.cantidad} x {self.producto.nombre}"

    def save(self, *args, **kwargs):
        # al crear el renglón, si no se dijo el costo se toma el que tiene el producto en este momento
        if self._state.adding and not self.costo_unitario:
            self.costo_unitario = self.producto.costo
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return (self.cantidad * self.precio_unitario).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
