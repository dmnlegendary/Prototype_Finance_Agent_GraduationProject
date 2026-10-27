"""
Las operaciones de la caja (agregar, cambiar cantidad, quitar, cobrar, cancelar).
Las usan la pantalla de ventas (ventas/views.py), el asistente (avi/services.py) y la
sincronización sin internet (core/sync.py), así todos aplican las mismas reglas:

  * Regla de oro: no se puede vender más de lo que hay en el inventario.
  * Los productos por pieza solo se venden en cantidades enteras; los de granel
    aceptan decimales (kilos, por ejemplo 0.250).
  * El precio y el costo se guardan en el renglón al momento de agregarlo.
  * Hay dos cajas por tienda, para que dos personas cobren a la vez sin chocar.
"""
from decimal import Decimal

from django.db import IntegrityError, transaction

from inventario.compras import CantidadInvalida, a_decimal, texto_numero, validar_cantidad
from inventario.models import Producto

from .cobro import SinExistencias, verificar_existencias
from .models import MAXIMO_DE_CARRITOS, ItemVenta, Venta


def numero_de_carrito_valido(valor):
    """Regresa 1 o 2 (o el número que sea) si el valor es una caja que existe; si no, 1."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return 1
    return numero if 1 <= numero <= MAXIMO_DE_CARRITOS else 1


def _siguiente_folio(negocio):
    ultima = Venta.objects.filter(negocio=negocio).order_by("-folio").first()
    return (ultima.folio + 1) if ultima else 1


def venta_en_curso(negocio, carrito=1, usuario=None):
    """El carrito abierto (carrito 1 o 2) de la tienda; si no hay uno, lo crea."""
    carrito = numero_de_carrito_valido(carrito)
    venta = Venta.objects.filter(negocio=negocio, estado=Venta.Estado.EN_CURSO, carrito=carrito).first()
    if venta is None:
        for _ in range(3):
            try:
                with transaction.atomic():
                    venta = Venta.objects.create(
                        negocio=negocio, folio=_siguiente_folio(negocio), carrito=carrito, cajero=usuario,
                    )
                break
            except IntegrityError:
                # otro dispositivo creó la caja o tomó el mismo folio al mismo tiempo
                venta = Venta.objects.filter(negocio=negocio, estado=Venta.Estado.EN_CURSO, carrito=carrito).first()
                if venta is not None:
                    break
    return venta


def venta_abierta(negocio, carrito=1):
    """El carrito abierto si ya existe (sin crearlo)."""
    return Venta.objects.filter(
        negocio=negocio, estado=Venta.Estado.EN_CURSO, carrito=numero_de_carrito_valido(carrito),
    ).first()


def agregar_producto(venta, producto, cantidad=1):
    """Agrega `cantidad` del producto a la caja (si ya estaba, se suma).
    Lanza SinExistencias o CantidadInvalida. Regresa el renglón."""
    cantidad = validar_cantidad(producto, cantidad)

    with transaction.atomic():
        item = ItemVenta.objects.filter(venta=venta, producto=producto).first()
        total = cantidad + (item.cantidad if item else Decimal("0"))
        # se lee el producto fresco: las existencias pudieron cambiar desde que se buscó
        producto.refresh_from_db()
        verificar_existencias(producto, total)

        if item is None:
            item = ItemVenta.objects.create(
                venta=venta, producto=producto, cantidad=cantidad,
                precio_unitario=producto.precio_venta, costo_unitario=producto.costo,
            )
        else:
            item.cantidad = total
            item.save(update_fields=["cantidad", "actualizado_en"])
        venta.recalcular_total()
    return item


def cambiar_cantidad(item, cantidad):
    """Deja el renglón en `cantidad` exacta. Con 0 el renglón se quita. Regresa el renglón o None."""
    if a_decimal(cantidad) == 0:
        quitar(item)
        return None

    cantidad = validar_cantidad(item.producto, cantidad)
    item.producto.refresh_from_db()
    verificar_existencias(item.producto, cantidad)
    item.cantidad = cantidad
    item.save(update_fields=["cantidad", "actualizado_en"])
    item.venta.recalcular_total()
    return item


def quitar(item):
    venta = item.venta
    item.delete()
    venta.recalcular_total()


def cancelar(venta):
    """Cancela la venta abierta (si tiene renglones). Regresa True si se canceló."""
    if not venta.items.exists():
        return False
    venta.estado = Venta.Estado.CANCELADA
    venta.save(update_fields=["estado"])
    return True


def estado_del_carrito(negocio, carrito=1):
    """El carrito en un diccionario listo para mandarse como JSON a la pantalla."""
    carrito = numero_de_carrito_valido(carrito)
    venta = venta_en_curso(negocio, carrito)
    renglones = []
    for item in venta.items.select_related("producto"):
        producto = item.producto
        renglones.append({
            "id": item.pk,
            "producto_id": producto.pk,
            "nombre": producto.nombre,
            "icono": producto.icono,
            "a_granel": producto.a_granel,
            "unidad": producto.unidad,
            "cantidad": texto_numero(item.cantidad),
            "precio_unitario": str(item.precio_unitario),
            "subtotal": str(item.subtotal),
            "disponible": None if producto.sin_control_de_stock else texto_numero(producto.cantidad_actual),
        })
    contadores = {
        n: ItemVenta.objects.filter(
            venta__negocio=negocio, venta__estado=Venta.Estado.EN_CURSO, venta__carrito=n,
        ).count()
        for n in range(1, MAXIMO_DE_CARRITOS + 1)
    }
    return {
        "carrito": carrito,
        "folio": venta.folio,
        "total": str(venta.total),
        "renglones": renglones,
        "contadores": contadores,
    }


def datos_de_producto(producto):
    """Lo mínimo de un producto que necesita la pantalla (búsqueda, código de barras, catálogo sin internet)."""
    return {
        "id": producto.pk,
        "nombre": producto.nombre,
        "icono": producto.icono,
        "precio_venta": str(producto.precio_venta),
        "a_granel": producto.a_granel,
        "unidad": producto.unidad,
        "stock": texto_numero(producto.cantidad_actual),
        "codigo_barras": producto.codigo_barras,
    }


def crear_no_encontrado(negocio, nombre, precio):
    """El producto "no encontrado": se crea (o se reutiliza si ya había uno con ese nombre
    pendiente de validar) con lo mínimo: nombre y precio. No lleva control de existencias."""
    existente = Producto.objects.filter(
        negocio=negocio, pendiente_validacion=True, activo=False, nombre__iexact=nombre,
    ).first()
    if existente is not None:
        if existente.precio_venta != precio:
            existente.precio_venta = precio
            existente.save(update_fields=["precio_venta", "actualizado_en"])
        return existente
    return Producto.objects.create(
        negocio=negocio, nombre=nombre, costo=0, precio_venta=precio,
        cantidad_actual=0, cantidad_minima=0, activo=False, pendiente_validacion=True,
    )


__all__ = [
    "CantidadInvalida", "SinExistencias", "agregar_producto", "cambiar_cantidad", "cancelar", "crear_no_encontrado",
    "datos_de_producto", "estado_del_carrito", "numero_de_carrito_valido", "quitar", "venta_abierta", "venta_en_curso",
]
