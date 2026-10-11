"""
Fórmulas financieras de la tienda. Todas las pantallas (dashboard, reportes,
punto de equilibrio y precios sugeridos) usan estas funciones para que los
números siempre coincidan.
"""
import calendar
import math
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import DecimalField, F, Sum

from ventas.models import ItemVenta, Venta

from .models import GastoOperativo

CERO = Decimal("0")
CENTAVOS = Decimal("0.01")
DECIMA = Decimal("0.1")

# ISR RESICO: (ingresos anuales hasta, tasa en %)
TABLA_ISR_RESICO = [
    (Decimal("300000"), Decimal("1.00")),
    (Decimal("600000"), Decimal("1.10")),
    (Decimal("1000000"), Decimal("1.50")),
    (Decimal("2500000"), Decimal("2.00")),
    (Decimal("3500000"), Decimal("2.50")),
]


def redondear(valor, exponente=CENTAVOS):
    return Decimal(valor).quantize(exponente, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------- fechas

def primer_dia_del_mes(fecha):
    return fecha.replace(day=1)


def mes_siguiente(primer_dia):
    return (primer_dia.replace(day=28) + timedelta(days=4)).replace(day=1)


def mes_anterior(primer_dia):
    return primer_dia_del_mes(primer_dia - timedelta(days=1))


def dias_del_mes(fecha):
    return calendar.monthrange(fecha.year, fecha.month)[1]


# ---------------------------------------------------- consultas de apoyo

def _suma(queryset, expresion):
    total = queryset.aggregate(
        total=Sum(expresion, output_field=DecimalField(max_digits=14, decimal_places=2)),
    )["total"]
    return total or CERO


def ventas_cobradas(negocio, desde, hasta):
    """Ventas cobradas entre dos fechas (el límite 'hasta' no se incluye)."""
    return Venta.objects.filter(
        negocio=negocio, estado=Venta.Estado.COBRADA,
        creado_en__date__gte=desde, creado_en__date__lt=hasta,
    )


def ingresos_periodo(negocio, desde, hasta):
    return redondear(_suma(ventas_cobradas(negocio, desde, hasta), "total"))


def gastos_periodo(negocio, desde, hasta, tipo=None):
    gastos = GastoOperativo.objects.filter(negocio=negocio, fecha__gte=desde, fecha__lt=hasta)
    if tipo:
        gastos = gastos.filter(tipo=tipo)
    return redondear(_suma(gastos, "monto"))


def costo_de_ventas_periodo(negocio, desde, hasta):
    """Lo que costó (costo de adquisición) la mercancía que se vendió."""
    items = ItemVenta.objects.filter(venta__in=ventas_cobradas(negocio, desde, hasta))
    return redondear(_suma(items, F("cantidad") * F("producto__costo")))


# ------------------------------------------------------------------- ISR

def tasa_isr_resico(ingresos_anuales):
    """Tasa (en %) que le toca según sus ingresos anuales."""
    for limite, tasa in TABLA_ISR_RESICO:
        if ingresos_anuales <= limite:
            return tasa
    return TABLA_ISR_RESICO[-1][1]


def ingresos_anuales(negocio, hoy):
    """Ingresos cobrados en los últimos 365 días."""
    return ingresos_periodo(negocio, hoy - timedelta(days=365), hoy + timedelta(days=1))


def tasa_isr_del_negocio(negocio, hoy):
    if not negocio.regimen_resico:
        return CERO
    return tasa_isr_resico(ingresos_anuales(negocio, hoy))


# ------------------------------------------- flujo, margen y utilidad neta

def resumen_desde_sumas(ingresos, costo_ventas, gastos, tasa_isr):
    """
    Flujo de efectivo  = ingresos - egresos (gastos registrados)
    Margen operativo   = (ingresos - costo de ventas - gastos operativos) / ingresos * 100
    Utilidad neta      = ingresos - costo de ventas - gastos operativos - ISR RESICO
    """
    isr = redondear(ingresos * tasa_isr / 100)
    utilidad_operativa = ingresos - costo_ventas - gastos
    margen_operativo = None
    if ingresos:
        margen_operativo = redondear(utilidad_operativa / ingresos * 100, DECIMA)
    return {
        "ingresos": ingresos,
        "costo_ventas": costo_ventas,
        "gastos": gastos,
        "flujo_efectivo": ingresos - gastos,
        "margen_operativo": margen_operativo,
        "tasa_isr": tasa_isr,
        "isr": isr,
        "utilidad_neta": utilidad_operativa - isr,
    }


def resumen_financiero(negocio, desde, hasta, tasa_isr):
    return resumen_desde_sumas(
        ingresos_periodo(negocio, desde, hasta),
        costo_de_ventas_periodo(negocio, desde, hasta),
        gastos_periodo(negocio, desde, hasta),
        tasa_isr,
    )


# ------------------------------------------------------- precio sugerido

def precio_sugerido(costo, margen_deseado):
    """Precio = costo de adquisición / (1 - margen deseado %)."""
    divisor = 1 - Decimal(margen_deseado) / 100
    return redondear(Decimal(costo) / divisor)


# --------------------------------------- punto de equilibrio por categoría

def calcular_punto_equilibrio(fijos, categorias):
    """
    F    = gastos fijos del periodo
    w_i  = proporción de ventas (en pesos) de la categoría i
    p_i  = precio promedio por unidad de la categoría i
    cv_i = costo variable promedio por unidad de la categoría i
    r_i  = (p_i - cv_i) / p_i
    PE$  = F / suma(w_i * r_i)
    V_i  = w_i * PE$          (pesos a vender de la categoría i)
    Q_i  = V_i / p_i          (unidades a vender de la categoría i)

    'categorias' es una lista de diccionarios con nombre, ventas, costo y
    unidades vendidas de cada categoría.
    """
    validas = [c for c in categorias if c["ventas"] > 0 and c["unidades"] > 0]
    if not validas:
        return None

    total_ventas = sum((c["ventas"] for c in validas), CERO)
    filas = []
    suma_wr = CERO
    for c in validas:
        w = c["ventas"] / total_ventas
        p = c["ventas"] / c["unidades"]
        cv = c["costo"] / c["unidades"]
        r = (p - cv) / p
        suma_wr += w * r
        filas.append({
            "nombre": c["nombre"],
            "w": w,
            "p": p,
            "cv": cv,
            "r": r,
            "mezcla_pct": redondear(w * 100, DECIMA),
            "precio_promedio": redondear(p),
            "costo_promedio": redondear(cv),
            "margen_pct": redondear(r * 100, DECIMA),
        })

    if suma_wr <= 0:
        return {"filas": filas, "suma_wr": suma_wr, "pe_total": None}

    pe_total = fijos / suma_wr
    for fila in filas:
        fila["ventas_objetivo"] = redondear(fila["w"] * pe_total)
        fila["unidades_objetivo"] = math.ceil(fila["w"] * pe_total / fila["p"])
    return {"filas": filas, "suma_wr": suma_wr, "pe_total": pe_total}


def punto_equilibrio_negocio(negocio, hoy, meses_historial=3):
    """
    Gastos fijos = los registrados en el mes actual. La mezcla de ventas y
    los promedios por categoría salen del histórico de los últimos meses.
    """
    inicio_mes = primer_dia_del_mes(hoy)
    fijos = gastos_periodo(
        negocio, inicio_mes, mes_siguiente(inicio_mes), tipo=GastoOperativo.Tipo.FIJO,
    )

    desde = inicio_mes
    for _ in range(meses_historial):
        desde = mes_anterior(desde)

    items = ItemVenta.objects.filter(
        venta__in=ventas_cobradas(negocio, desde, hoy + timedelta(days=1)),
    )
    dinero = DecimalField(max_digits=14, decimal_places=2)
    por_categoria = items.order_by().values("producto__categoria__nombre").annotate(
        ventas=Sum(F("cantidad") * F("precio_unitario"), output_field=dinero),
        costo=Sum(F("cantidad") * F("producto__costo"), output_field=dinero),
        unidades=Sum("cantidad"),
    )
    categorias = [
        {
            "nombre": fila["producto__categoria__nombre"] or "Sin categoría",
            "ventas": fila["ventas"] or CERO,
            "costo": fila["costo"] or CERO,
            "unidades": fila["unidades"] or CERO,
        }
        for fila in por_categoria
    ]

    resultado = calcular_punto_equilibrio(fijos, categorias)
    if fijos <= 0:
        estado = "sin_fijos"
    elif resultado is None:
        estado = "sin_ventas"
    elif resultado["pe_total"] is None:
        estado = "sin_margen"
    else:
        estado = "ok"

    return {
        "estado": estado,
        "fijos": fijos,
        "meses_historial": meses_historial,
        "filas": resultado["filas"] if resultado else [],
        "pe_total": resultado["pe_total"] if resultado else None,
    }
