"""
Lógica de cobrar una venta. La usan el botón "Cobrar" (ventas/views.py) y
el asistente (avi/services.py), para que los dos hagan exactamente lo mismo.
"""
from decimal import Decimal

from django.db import transaction

from .models import Venta


def cobrar_venta(venta):
    """Descuenta el inventario y marca la venta como cobrada, todo junto.

    Regresa la lista de productos que con esta venta quedaron en amarillo,
    naranja o rojo (o que empeoraron de color) para poder avisarle al tendero."""
    productos_que_empeoraron = []

    with transaction.atomic():
        # descuenta el inventario producto por producto, sin dejarlo en negativo
        for item in venta.items.select_related("producto"):
            producto = item.producto
            nivel_antes = producto.nivel_stock
            producto.cantidad_actual = max(producto.cantidad_actual - item.cantidad, Decimal("0"))
            producto.save(update_fields=["cantidad_actual"])
            if producto.nivel_stock not in ("ok", nivel_antes):
                productos_que_empeoraron.append(producto)

        venta.estado = Venta.Estado.COBRADA
        venta.save(update_fields=["estado"])
        venta.recalcular_total()

    return productos_que_empeoraron


def texto_aviso_stock(producto):
    """El mensaje de aviso según el color en el que quedó el producto."""
    nivel = producto.nivel_stock
    piezas = f"{producto.cantidad_actual:g}"
    if nivel == "rojo":
        return f'"{producto.nombre}" llegó a su mínimo ({piezas} pzas): hay que resurtir.'
    if nivel == "naranja":
        return f'A "{producto.nombre}" le queda solo un cuarto de su stock ({piezas} pzas).'
    return f'"{producto.nombre}" ya va a la mitad de su stock ({piezas} pzas).'
