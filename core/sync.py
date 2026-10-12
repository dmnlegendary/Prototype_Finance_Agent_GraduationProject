"""
Sincronización de lo que se hizo SIN INTERNET. El navegador guarda en su cola cada
operación (una venta, un producto dado de alta, mercancía que llegó) y, cuando regresa
la conexión, las manda aquí en el orden en que ocurrieron.

Cada operación trae un identificador único (uuid). Si la conexión se corta a la mitad y
el navegador la manda otra vez, se reconoce y no se guarda dos veces.
"""
import logging
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from inventario.compras import CantidadInvalida, a_decimal, agregar_existencias, registrar_compra, validar_cantidad
from inventario.forms import ProductoForm
from inventario.models import Producto
from ventas import carrito
from ventas.models import ItemVenta, Venta

from .models import OperacionSincronizada

registro = logging.getLogger(__name__)

MAXIMO_RENGLONES_POR_VENTA = 200


class ErrorDeSincronizacion(Exception):
    """La operación no es válida (datos malos, producto que ya no existe…). Reintentarla no sirve de nada."""


def _fecha(texto):
    """La fecha en que ocurrió la operación, o ahora si no viene bien."""
    try:
        fecha = datetime.fromisoformat(str(texto).replace("Z", "+00:00"))
    except ValueError:
        return timezone.now()
    return timezone.make_aware(fecha) if timezone.is_naive(fecha) else fecha


def _venta(negocio, usuario, datos):
    renglones = datos.get("renglones") or []
    if not renglones or len(renglones) > MAXIMO_RENGLONES_POR_VENTA:
        raise ErrorDeSincronizacion("La venta no trae productos.")

    numero = carrito.numero_de_carrito_valido(datos.get("carrito"))
    lineas = []
    for renglon in renglones:
        precio = a_decimal(renglon.get("precio_unitario"))
        if precio is None or precio < 0:
            raise ErrorDeSincronizacion("Un producto de la venta trae un precio inválido.")

        if renglon.get("no_encontrado"):
            nombre = str(renglon.get("nombre", "")).strip()[:150]
            if not nombre or precio <= 0:
                raise ErrorDeSincronizacion("Un producto no encontrado no trae nombre o precio.")
            producto = carrito.crear_no_encontrado(negocio, nombre, precio.quantize(Decimal("0.01")))
        else:
            producto = Producto.objects.filter(pk=renglon.get("producto_id") or 0, negocio=negocio).first()
            if producto is None:
                raise ErrorDeSincronizacion("Un producto de la venta ya no existe en el inventario.")
        try:
            cantidad = validar_cantidad(producto, renglon.get("cantidad"))
        except CantidadInvalida as error:
            raise ErrorDeSincronizacion(str(error))
        lineas.append((producto, cantidad, precio.quantize(Decimal("0.01"))))

    venta = Venta.objects.create(
        negocio=negocio, cajero=usuario, folio=carrito._siguiente_folio(negocio),
        estado=Venta.Estado.COBRADA, carrito=numero,
    )
    faltantes = []
    for producto, cantidad, precio in lineas:
        ItemVenta.objects.create(
            venta=venta, producto=producto, cantidad=cantidad, precio_unitario=precio, costo_unitario=producto.costo,
        )
        if not producto.pendiente_validacion:
            # la venta ya ocurrió: no se puede rechazar, pero el inventario nunca queda en negativo
            if cantidad > producto.cantidad_actual:
                faltantes.append(producto.nombre)
            producto.cantidad_actual = max(producto.cantidad_actual - cantidad, Decimal("0"))
            producto.save(update_fields=["cantidad_actual", "actualizado_en"])
    venta.recalcular_total()
    # la venta se hizo antes, así que se queda con la fecha en que realmente ocurrió
    Venta.objects.filter(pk=venta.pk).update(creado_en=_fecha(datos.get("fecha")))

    # si los productos venían de un carrito que estaba abierto en el servidor, se vacía para no duplicarlos
    if datos.get("limpiar_carrito"):
        abierta = Venta.objects.filter(negocio=negocio, estado=Venta.Estado.EN_CURSO, carrito=numero).first()
        if abierta is not None:
            abierta.items.all().delete()
            abierta.recalcular_total()

    mensaje = f"Venta #{venta.folio:04d} guardada por ${venta.total}."
    if faltantes:
        mensaje += " Ojo: no alcanzaban las existencias de " + ", ".join(faltantes) + "."
    return mensaje


def _alta_producto(negocio, usuario, datos):
    form = ProductoForm(datos, negocio=negocio)
    if not form.is_valid():
        errores = "; ".join(f"{campo}: {', '.join(lista)}" for campo, lista in form.errors.items())
        raise ErrorDeSincronizacion(f'El producto "{datos.get("nombre", "")}" no se pudo dar de alta ({errores}).')
    producto = form.save(commit=False)
    producto.negocio = negocio
    producto.save()
    registrar_compra(negocio, f"Compra de mercancía: {producto.nombre}", producto.cantidad_actual * producto.costo)
    return f'Producto "{producto.nombre}" dado de alta.'


def _resurtir(negocio, usuario, datos):
    producto = Producto.objects.filter(pk=datos.get("producto_id") or 0, negocio=negocio, activo=True).first()
    if producto is None:
        raise ErrorDeSincronizacion("El producto que se quería resurtir ya no existe.")
    try:
        agregar_existencias(producto, datos.get("cantidad"), costo=datos.get("costo"))
    except CantidadInvalida as error:
        raise ErrorDeSincronizacion(str(error))
    return f'Mercancía agregada a "{producto.nombre}".'


APLICADORES = {
    "venta": _venta,
    "alta_producto": _alta_producto,
    "resurtir": _resurtir,
}


def aplicar_operaciones(negocio, usuario, operaciones):
    """Aplica la lista de operaciones en orden. Regresa un resultado por cada una:
    {"uuid", "ok", "mensaje", "definitivo"}. Si `definitivo` es True el navegador ya no la reintenta."""
    resultados = []
    for operacion in operaciones:
        uuid = str(operacion.get("uuid", ""))[:64]
        tipo = operacion.get("tipo")
        datos = operacion.get("datos")
        if not uuid or tipo not in APLICADORES or not isinstance(datos, dict):
            resultados.append({"uuid": uuid, "ok": False, "definitivo": True, "mensaje": "Operación no reconocida."})
            continue

        if OperacionSincronizada.objects.filter(negocio=negocio, uuid=uuid).exists():
            resultados.append({"uuid": uuid, "ok": True, "mensaje": "Ya estaba guardada."})
            continue

        try:
            with transaction.atomic():
                mensaje = APLICADORES[tipo](negocio, usuario, datos)
                OperacionSincronizada.objects.create(negocio=negocio, uuid=uuid, tipo=tipo)
            resultados.append({"uuid": uuid, "ok": True, "mensaje": mensaje})
        except ErrorDeSincronizacion as error:
            resultados.append({"uuid": uuid, "ok": False, "definitivo": True, "mensaje": str(error)})
        except Exception:
            # algo inesperado: se deja en la cola para reintentarla más tarde
            registro.exception("Falló la sincronización de una operación (%s)", tipo)
            resultados.append({"uuid": uuid, "ok": False, "definitivo": False, "mensaje": "Error del servidor."})
    return resultados
