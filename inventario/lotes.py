"""
Costo por lotes (PEPS: primeras entradas, primeras salidas).

Cada compra de mercancía abre un lote con su propio costo, y cada salida (venta, merma o
ajuste a la baja) se toma de los lotes más viejos. Con eso el costo de lo vendido es el de
las piezas que de verdad salieron, aunque el proveedor haya subido el precio después.
"""
from decimal import Decimal, ROUND_HALF_UP

from .models import LoteInventario

CERO = Decimal("0")
DIEZMILESIMAS = Decimal("0.0001")


def abrir_lote(producto, cantidad, costo):
    return LoteInventario.objects.create(
        negocio_id=producto.negocio_id, producto=producto,
        cantidad_inicial=cantidad, cantidad_restante=cantidad, costo_unitario=costo,
    )


def gastar_lotes(producto, cantidad):
    """Saca `cantidad` de los lotes más viejos y regresa el costo promedio por pieza de lo que salió.
    Si los lotes no alcanzan (productos que ya existían antes de que hubiera lotes), lo que
    falta se cuenta al costo que tiene el producto."""
    cantidad = Decimal(cantidad)
    por_sacar = cantidad
    total = CERO

    lotes = LoteInventario.objects.select_for_update().filter(producto=producto, cantidad_restante__gt=0)
    for lote in lotes.order_by("creado_en", "id"):
        if por_sacar <= 0:
            break
        tomado = min(lote.cantidad_restante, por_sacar)
        lote.cantidad_restante = lote.cantidad_restante - tomado
        lote.save(update_fields=["cantidad_restante", "actualizado_en"])
        total += tomado * lote.costo_unitario
        por_sacar -= tomado

    if por_sacar > 0:
        total += por_sacar * producto.costo
    return (total / cantidad).quantize(DIEZMILESIMAS, rounding=ROUND_HALF_UP)
