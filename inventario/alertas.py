"""
Semáforo de reabastecimiento. Cada producto tiene un nivel según cuántas
piezas le quedan (ver Producto.nivel_stock):

    amarillo -> ya va a la mitad de su stock ideal
    naranja  -> le queda un cuarto de su stock ideal
    rojo     -> llegó a su cantidad mínima (hay que resurtir ya)
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Case, DecimalField, F, Q, Sum, When
from django.utils import timezone

from core import cache_negocio
from ventas.models import ItemVenta, Venta

from .models import Producto

DIAS_DE_RITMO = 28  # para saber qué tan rápido se vende un producto se miran las últimas 4 semanas

ORDEN_NIVELES = {"rojo": 0, "naranja": 1, "amarillo": 2}

TEXTO_NIVELES = {
    "rojo": "Resurtir ya",
    "naranja": "Queda un cuarto",
    "amarillo": "Va a la mitad",
}


def productos_con_alerta(negocio):
    """Productos activos que no están en verde, del más urgente al menos urgente.

    Primero la base de datos descarta los que están bien (así no se traen los
    miles de productos a Python) y luego se calcula el color de los que quedan."""
    ideal = Case(
        When(stock_ideal__gt=F("cantidad_minima"), then=F("stock_ideal")),
        default=F("cantidad_minima") * 4,
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    candidatos = (
        Producto.objects.filter(negocio=negocio, activo=True)
        .annotate(ideal_calculado=ideal)
        .filter(Q(cantidad_actual__lte=F("cantidad_minima")) | Q(cantidad_actual__lte=F("ideal_calculado") / 2))
        .select_related("categoria", "proveedor")
    )

    alertas = [p for p in candidatos if p.nivel_stock != "ok"]
    alertas.sort(key=lambda p: (ORDEN_NIVELES[p.nivel_stock], p.cantidad_actual - p.cantidad_minima))
    return alertas


def ritmo_de_venta(negocio, productos, dias=DIAS_DE_RITMO):
    """Cuántas unidades se vendieron de cada producto en los últimos `dias` días,
    como {producto_id: unidades}. Se hace en una sola consulta para toda la lista."""
    ids = [producto.pk for producto in productos]
    if not ids:
        return {}
    desde = timezone.now() - timedelta(days=dias)
    filas = (
        ItemVenta.objects.filter(
            venta__negocio=negocio, venta__estado=Venta.Estado.COBRADA,
            venta__creado_en__gte=desde, producto_id__in=ids,
        )
        .order_by().values("producto_id").annotate(total=Sum("cantidad"))
    )
    return {fila["producto_id"]: fila["total"] for fila in filas}


def ordenar_por_urgencia(negocio, productos, dias=DIAS_DE_RITMO):
    """Pone en cada producto cuánto vende por semana y para cuántos días le alcanza lo que
    queda, y lo ordena: primero por color y, dentro de cada color, el que se acaba antes.
    Los que no se han vendido en esas semanas van al final de su color."""
    ritmo = ritmo_de_venta(negocio, productos, dias)
    for producto in productos:
        vendidas = ritmo.get(producto.pk) or Decimal("0")
        producto.vendidas_por_semana = vendidas / dias * 7
        producto.dias_de_cobertura = None
        if vendidas > 0:
            producto.dias_de_cobertura = int(producto.cantidad_actual / (vendidas / dias))

    def clave(producto):
        sin_ventas = producto.dias_de_cobertura is None
        return (
            ORDEN_NIVELES[producto.nivel_stock],
            sin_ventas,
            producto.dias_de_cobertura or 0,
            producto.cantidad_actual - producto.cantidad_minima,
        )

    return sorted(productos, key=clave)


def _contar(negocio):
    conteo = {"rojo": 0, "naranja": 0, "amarillo": 0}
    for producto in productos_con_alerta(negocio):
        conteo[producto.nivel_stock] += 1
    conteo["total"] = conteo["rojo"] + conteo["naranja"] + conteo["amarillo"]
    return conteo


def conteo_alertas(negocio):
    """{"rojo": n, "naranja": n, "amarillo": n, "total": n}. Se guarda en el
    cache del negocio, porque el navbar lo pide en todas las pantallas."""
    return cache_negocio.obtener(negocio, "alertas_conteo", lambda: _contar(negocio))


def nivel_mas_urgente(conteo):
    """El color más fuerte que hay en el conteo (para pintar la campana)."""
    for nivel in ("rojo", "naranja", "amarillo"):
        if conteo[nivel]:
            return nivel
    return ""
