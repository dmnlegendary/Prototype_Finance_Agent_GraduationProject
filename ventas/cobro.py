"""
Lógica de cobrar una venta. La usan el botón "Cobrar" (ventas/views.py), la
sincronización sin internet (core/sync.py) y el asistente (avi/services.py), para
que todos hagan exactamente lo mismo.
"""
from django.db import transaction

from inventario.compras import texto_numero
from inventario.models import MovimientoInventario, Producto
from inventario.movimientos import registrar_movimiento

from .models import Venta


class VentaYaCobrada(Exception):
    """La venta ya no está en curso: otra petición (por ejemplo, un doble clic con internet lento) la cobró primero."""

    mensaje = "Esa venta ya se cobró. Revisa el historial antes de volver a cobrar."


class SinExistencias(Exception):
    """Se quiso vender más de lo que hay en el inventario (regla de oro: no se vende sin piezas)."""

    def __init__(self, producto, disponible, solicitado):
        self.producto = producto
        self.disponible = disponible
        self.solicitado = solicitado
        super().__init__(f'No hay suficientes existencias de "{producto.nombre}".')

    @property
    def detalle(self):
        """Qué pasó, sin la pregunta final."""
        unidad = self.producto.unidad
        if self.disponible <= 0:
            return f'No hay existencias de "{self.producto.nombre}"'
        return f'De "{self.producto.nombre}" solo hay {texto_numero(self.disponible)} {unidad} y pides {texto_numero(self.solicitado)}'

    @property
    def mensaje(self):
        return f"{self.detalle}. ¿Quieres agregar más al inventario?"


def verificar_existencias(producto, cantidad_total):
    """Lanza SinExistencias si `cantidad_total` es más de lo que hay. Los productos
    "no encontrados" (inactivos y pendientes de validar) no llevan control de existencias."""
    if producto.sin_control_de_stock:
        return
    if cantidad_total > producto.cantidad_actual:
        raise SinExistencias(producto, producto.cantidad_actual, cantidad_total)


def cobrar_venta(venta):
    """Descuenta el inventario y marca la venta como cobrada, todo junto.

    Si algún producto ya no alcanza (por ejemplo, la otra caja vendió la última
    pieza) lanza SinExistencias y no se mueve nada.

    Regresa la lista de productos que con esta venta quedaron en amarillo, naranja o
    rojo (o que empeoraron de color) para poder avisarle al tendero."""
    productos_que_empeoraron = []

    with transaction.atomic():
        # se bloquea la venta para que dos cobros al mismo tiempo no la registren dos veces
        estado_actual = Venta.objects.select_for_update().values_list("estado", flat=True).get(pk=venta.pk)
        if estado_actual != Venta.Estado.EN_CURSO:
            raise VentaYaCobrada()

        items = list(venta.items.select_related("producto"))
        # se bloquean los productos (en bases de datos que lo permiten) para que dos
        # cobros al mismo tiempo no vendan la misma última pieza
        bloqueados = {
            p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=[i.producto_id for i in items])
        }

        # primero se revisa todo y después se descuenta, para no dejar una venta a medias
        for item in items:
            verificar_existencias(bloqueados[item.producto_id], item.cantidad)

        for item in items:
            producto = bloqueados[item.producto_id]
            nivel_antes = producto.nivel_stock
            if not producto.sin_control_de_stock:
                producto.cantidad_actual = producto.cantidad_actual - item.cantidad
                producto.save(update_fields=["cantidad_actual", "actualizado_en"])
                movimiento = registrar_movimiento(
                    producto, -item.cantidad, MovimientoInventario.Tipo.VENTA,
                    motivo=f"Venta folio {venta.folio}", venta=venta, usuario=venta.cajero,
                )
                # el renglón se queda con el costo de las piezas que de verdad salieron (lotes más viejos primero)
                item.costo_unitario = movimiento.costo_unitario
                item.save(update_fields=["costo_unitario", "actualizado_en"])
            if producto.nivel_stock not in ("ok", nivel_antes):
                productos_que_empeoraron.append(producto)

        venta.estado = Venta.Estado.COBRADA
        venta.save(update_fields=["estado"])
        venta.recalcular_total()

    return productos_que_empeoraron


def texto_aviso_stock(producto):
    """El mensaje de aviso según el color en el que quedó el producto."""
    nivel = producto.nivel_stock
    piezas = f"{texto_numero(producto.cantidad_actual)}"
    if nivel == "rojo":
        return f'"{producto.nombre}" llegó a su mínimo ({piezas} {producto.unidad}): hay que resurtir.'
    if nivel == "naranja":
        return f'A "{producto.nombre}" le queda solo un cuarto de su stock ({piezas} {producto.unidad}).'
    return f'"{producto.nombre}" ya va a la mitad de su stock ({piezas} {producto.unidad}).'
