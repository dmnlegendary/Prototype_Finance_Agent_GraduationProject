"""
Semáforo de reabastecimiento. Cada producto tiene un nivel según cuántas
piezas le quedan (ver Producto.nivel_stock):

    amarillo -> ya va a la mitad de su stock ideal
    naranja  -> le queda un cuarto de su stock ideal
    rojo     -> llegó a su cantidad mínima (hay que resurtir ya)
"""
from django.db.models import Case, DecimalField, F, Q, When

from core import cache_negocio

from .models import Producto

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
