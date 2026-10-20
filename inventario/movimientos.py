"""
Kardex. Todo lugar que cambia las existencias de un producto llama a `registrar_movimiento`
para dejar el renglón con su origen (regla de negocio: ningún cambio de stock sin evidencia).
"""
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg

from .lotes import abrir_lote, gastar_lotes
from .models import LoteInventario, MovimientoInventario

TIPOS = MovimientoInventario.Tipo


def calcular_stock_ideal(producto):
    """El stock ideal es el promedio de lo que se ha tenido cada vez que se cargó mercancía
    (por ejemplo, si después de resurtir había 24, 26 y 29, el ideal es 26.3). Los productos por
    pieza se redondean a un número entero. Regresa None si todavía no hay cargas."""
    promedio = MovimientoInventario.objects.filter(
        producto=producto, tipo=TIPOS.ENTRADA, cantidad__gt=0,
    ).aggregate(promedio=Avg("existencia_resultante"))["promedio"]
    if promedio is None:
        return None
    promedio = Decimal(promedio)
    return promedio.quantize(Decimal("0.001") if producto.a_granel else Decimal("1"), rounding=ROUND_HALF_UP)


def _actualizar_stock_ideal(producto):
    """Se recalcula con cada carga de mercancía. Con la primera carga (el alta) se respeta lo que
    el tendero haya escrito, si escribió algo; desde la segunda, manda el promedio."""
    cargas = MovimientoInventario.objects.filter(producto=producto, tipo=TIPOS.ENTRADA, cantidad__gt=0).count()
    if cargas <= 1 and producto.stock_ideal > 0:
        return
    ideal = calcular_stock_ideal(producto)
    if ideal is not None and ideal != producto.stock_ideal:
        producto.stock_ideal = ideal
        producto.save(update_fields=["stock_ideal", "actualizado_en"])


def registrar_movimiento(producto, cantidad, tipo, motivo="", venta=None, usuario=None):
    """Anota un cambio de existencias. `cantidad` va con signo (positivo entra, negativo sale)
    y la existencia que queda se toma del producto, que ya debe traer su cantidad nueva."""
    cantidad = Decimal(cantidad)
    if cantidad == 0:
        return None
    # lo que entra abre un lote con el costo actual del producto; lo que sale se toma de los lotes más viejos
    if cantidad > 0:
        costo = producto.costo
        abrir_lote(producto, cantidad, costo)
    else:
        costo = gastar_lotes(producto, -cantidad)
    movimiento = MovimientoInventario.objects.create(
        negocio_id=producto.negocio_id, producto=producto, tipo=tipo, cantidad=cantidad,
        existencia_resultante=producto.cantidad_actual, motivo=motivo[:255], venta=venta, usuario=usuario,
        costo_unitario=costo,
    )
    if cantidad > 0 and tipo == TIPOS.ENTRADA:
        _actualizar_stock_ideal(producto)
    return movimiento


def registrar_entradas_iniciales(productos, motivo):
    """Para varios productos recién creados a la vez (registro, importación): una entrada por cada
    uno que tenga piezas. Se guardan todas juntas."""
    con_piezas = [p for p in productos if p.cantidad_actual > 0]
    movimientos = [
        MovimientoInventario(
            negocio_id=p.negocio_id, producto=p, tipo=TIPOS.ENTRADA, cantidad=p.cantidad_actual,
            existencia_resultante=p.cantidad_actual, motivo=motivo[:255], costo_unitario=p.costo,
        )
        for p in con_piezas
    ]
    MovimientoInventario.objects.bulk_create(movimientos)
    LoteInventario.objects.bulk_create([
        LoteInventario(
            negocio_id=p.negocio_id, producto=p, cantidad_inicial=p.cantidad_actual,
            cantidad_restante=p.cantidad_actual, costo_unitario=p.costo,
        )
        for p in con_piezas
    ])
    # con la primera carga, el stock ideal es lo que se tiene (si no se había escrito uno)
    sin_ideal = [p for p in con_piezas if p.stock_ideal <= 0]
    for p in sin_ideal:
        p.stock_ideal = p.cantidad_actual
    if sin_ideal:
        type(sin_ideal[0]).objects.bulk_update(sin_ideal, ["stock_ideal"])
    return movimientos
