"""
Datos de las gráficas del agente financiero. Todo sale de la base de datos de la tienda; la
página solo los dibuja (static/finanzas/js/graficas.js). Cada gráfica es un diccionario:

    {"titulo", "tipo": "barras" | "linea", "formato": "dinero" | "porcentaje" | "numero",
     "etiquetas": [...], "series": [{"nombre", "valores": [...]}], "referencia": {...} o None}
"""
from datetime import timedelta
from decimal import Decimal

from django.db.models import DecimalField, F, Sum
from django.db.models.functions import TruncDate

from inventario.models import Producto
from ventas.models import ItemVenta

from . import calculos

MESES_ABREVIADOS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def etiqueta_mes(mes, con_anio=False):
    return MESES_ABREVIADOS[mes.month - 1] + (f" {str(mes.year)[2:]}" if con_anio else "")


def _numero(valor):
    return float(valor) if valor is not None else 0.0


def meses_recientes(hoy, cantidad=6):
    """Los primeros días de los últimos `cantidad` meses, del más viejo al mes actual."""
    mes = calculos.primer_dia_del_mes(hoy)
    meses = [mes]
    for _ in range(cantidad - 1):
        mes = calculos.mes_anterior(mes)
        meses.append(mes)
    return list(reversed(meses))


def _ventas_por_dia(negocio, desde, hasta):
    """{fecha: total vendido} entre dos fechas (el límite 'hasta' no se incluye)."""
    filas = (
        calculos.ventas_cobradas(negocio, desde, hasta)
        .annotate(dia=TruncDate("creado_en")).order_by().values("dia").annotate(total=Sum("total"))
    )
    return {(f["dia"].date() if hasattr(f["dia"], "date") else f["dia"]): f["total"] or Decimal("0") for f in filas}


def grafica_ingresos_y_egresos(datos_meses, etiquetas):
    """Lo que entró contra lo que salió (gastos y compras de mercancía) en cada mes."""
    return {
        "titulo": "Ingresos vs egresos", "tipo": "barras", "formato": "dinero", "etiquetas": etiquetas,
        "series": [
            {"nombre": "Ingresos", "valores": [_numero(m["ingresos"]) for m in datos_meses]},
            {"nombre": "Egresos", "valores": [_numero(m["gastos"] + m["compras"]) for m in datos_meses]},
        ],
        "referencia": None,
    }


def grafica_utilidad(datos_meses, etiquetas):
    return {
        "titulo": "Utilidad neta mensual", "tipo": "linea", "formato": "dinero", "etiquetas": etiquetas,
        "series": [{"nombre": "Utilidad neta", "valores": [_numero(m["utilidad_neta"]) for m in datos_meses]}],
        "referencia": None,
    }


def grafica_ventas_por_dia(por_dia):
    """Para el reporte de ventas: lo vendido cada día del periodo elegido."""
    return {
        "titulo": "Ventas de cada día", "tipo": "barras", "formato": "dinero",
        "etiquetas": [d["dia"].strftime("%d/%m") for d in por_dia],
        "series": [{"nombre": "Vendido", "valores": [_numero(d["total"]) for d in por_dia]}],
        "referencia": None,
    }


def graficas_del_inicio(negocio, hoy, equilibrio):
    """Las cinco gráficas de las tarjetas del inicio, con los datos reales de la tienda."""
    meses = meses_recientes(hoy, 6)
    etiquetas = [etiqueta_mes(m, con_anio=meses[0].year != meses[-1].year) for m in meses]
    tasa = calculos.tasa_isr_del_negocio(negocio, hoy)
    resumen = calculos.resumen_por_meses(negocio, meses, tasa)

    # ventas de las últimas 8 semanas (ventanas de 7 días que terminan hoy): es la base del pronóstico
    semanas = 8
    desde = hoy - timedelta(days=semanas * 7 - 1)
    por_dia = _ventas_por_dia(negocio, desde, hoy + timedelta(days=1))
    ventas_semana, etiquetas_semana = [], []
    for i in range(semanas):
        inicio = desde + timedelta(days=7 * i)
        ventas_semana.append(_numero(sum((por_dia.get(inicio + timedelta(days=d), Decimal("0")) for d in range(7)), Decimal("0"))))
        etiquetas_semana.append(inicio.strftime("%d/%m"))

    # ventas acumuladas del mes contra la meta del punto de equilibrio
    inicio_mes = calculos.primer_dia_del_mes(hoy)
    del_mes = _ventas_por_dia(negocio, inicio_mes, hoy + timedelta(days=1))
    acumulado, acumuladas, dias = Decimal("0"), [], []
    for d in range(hoy.day):
        dia = inicio_mes + timedelta(days=d)
        acumulado += del_mes.get(dia, Decimal("0"))
        acumuladas.append(_numero(acumulado))
        dias.append(str(dia.day))
    referencia = None
    if equilibrio.get("estado") == "ok":
        referencia = {"valor": _numero(equilibrio["pe_total"]), "texto": "Punto de equilibrio"}

    # margen de ganancia de lo que más se vendió en el último mes
    dinero = DecimalField(max_digits=14, decimal_places=2)
    vendidos = (
        ItemVenta.objects.filter(
            venta__in=calculos.ventas_cobradas(negocio, hoy - timedelta(days=29), hoy + timedelta(days=1)),
            producto__activo=True,
        )
        .order_by().values("producto_id").annotate(vendido=Sum(F("cantidad") * F("precio_unitario"), output_field=dinero))
        .order_by("-vendido")[:6]
    )
    productos = {p.pk: p for p in Producto.objects.filter(pk__in=[v["producto_id"] for v in vendidos])}
    nombres, margenes = [], []
    for v in vendidos:
        p = productos.get(v["producto_id"])
        if p and p.precio_venta > 0 and p.costo > 0:
            nombres.append(p.nombre if len(p.nombre) <= 14 else p.nombre[:13] + "…")
            margenes.append(_numero((p.precio_venta - p.costo) / p.precio_venta * 100))

    return {
        "reportes": {
            "titulo": "Utilidad neta de los últimos 6 meses", "tipo": "linea", "formato": "dinero", "etiquetas": etiquetas,
            "series": [{"nombre": "Utilidad neta", "valores": [_numero(m["utilidad_neta"]) for m in resumen]}],
            "referencia": None,
        },
        "pronostico": {
            "titulo": "Tus ventas por semana (la base del pronóstico)", "tipo": "barras", "formato": "dinero",
            "etiquetas": etiquetas_semana, "series": [{"nombre": "Vendido en la semana", "valores": ventas_semana}],
            "referencia": None,
        },
        "gastos": {
            "titulo": "Gastos del negocio por mes", "tipo": "barras", "formato": "dinero", "etiquetas": etiquetas,
            "series": [{"nombre": "Gastos (sin mercancía)", "valores": [_numero(m["gastos"]) for m in resumen]}],
            "referencia": None,
        },
        "equilibrio": {
            "titulo": "Lo que llevas vendido este mes", "tipo": "linea", "formato": "dinero", "etiquetas": dias,
            "series": [{"nombre": "Ventas acumuladas", "valores": acumuladas}], "referencia": referencia,
        },
        "precios": {
            "titulo": "Margen de tus productos más vendidos", "tipo": "barras", "formato": "porcentaje", "etiquetas": nombres,
            "series": [{"nombre": "Margen de ganancia", "valores": margenes}], "referencia": None,
        },
    }
