"""
Fórmulas financieras de la tienda. Todas las pantallas (dashboard, reportes,
punto de equilibrio y precios sugeridos) usan estas funciones para que los
números siempre coincidan.
"""
import calendar
import logging
import math
import warnings
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import TruncDate, TruncMonth

from core import cache_negocio
from inventario.models import Producto
from ventas.models import ItemVenta, Venta

from .models import GastoOperativo

CERO = Decimal("0")
CENTAVOS = Decimal("0.01")
DECIMA = Decimal("0.1")
registro = logging.getLogger(__name__)

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


def _contar_ocurrencias(gasto, desde, hasta):
    """Cuenta las fechas de cobro del gasto dentro de [desde, hasta)."""
    inicio = gasto.fecha_inicio
    if not inicio or desde >= hasta or inicio >= hasta:
        return 0

    primera_fecha = max(inicio, desde)
    if gasto.periodicidad == GastoOperativo.Periodicidad.DIARIA:
        return (hasta - primera_fecha).days

    if gasto.periodicidad == GastoOperativo.Periodicidad.SEMANAL:
        dias = (primera_fecha - inicio).days
        primera_fecha += timedelta(days=(-dias) % 7)
        if primera_fecha >= hasta:
            return 0
        return ((hasta - primera_fecha - timedelta(days=1)).days // 7) + 1

    ultimo_dia = hasta - timedelta(days=1)
    if gasto.periodicidad in (
        GastoOperativo.Periodicidad.MENSUAL,
        GastoOperativo.Periodicidad.CADA_MESES,
    ):
        intervalo_meses = (
            gasto.intervalo_meses
            if gasto.periodicidad == GastoOperativo.Periodicidad.CADA_MESES
            else 1
        )
        cursor = primer_dia_del_mes(primera_fecha)
        meses_desde_inicio = (cursor.year - inicio.year) * 12 + cursor.month - inicio.month
        primer_intervalo = (
            (meses_desde_inicio + intervalo_meses - 1) // intervalo_meses
        ) * intervalo_meses
        ocurrencias = 0
        mes_indice = (inicio.year - 1) * 12 + inicio.month - 1 + primer_intervalo
        ultimo_indice = (ultimo_dia.year - 1) * 12 + ultimo_dia.month - 1
        while mes_indice <= ultimo_indice:
            anio, mes = divmod(mes_indice, 12)
            cursor = date(anio + 1, mes + 1, 1)
            dia = min(inicio.day, calendar.monthrange(cursor.year, cursor.month)[1])
            fecha = cursor.replace(day=dia)
            if inicio <= fecha and desde <= fecha < hasta:
                ocurrencias += 1
            mes_indice += intervalo_meses
        return ocurrencias

    if gasto.periodicidad == GastoOperativo.Periodicidad.ANUAL:
        ocurrencias = 0
        for anio in range(primera_fecha.year, ultimo_dia.year + 1):
            dia = min(inicio.day, calendar.monthrange(anio, inicio.month)[1])
            fecha = inicio.replace(year=anio, day=dia)
            if inicio <= fecha and desde <= fecha < hasta:
                ocurrencias += 1
        return ocurrencias

    return 0


def _gastos_recurrentes(negocio, hasta, tipo=None):
    gastos = GastoOperativo.objects.filter(
        negocio=negocio,
        tipo=GastoOperativo.Tipo.FIJO,
        periodicidad__in=[
            GastoOperativo.Periodicidad.DIARIA,
            GastoOperativo.Periodicidad.SEMANAL,
            GastoOperativo.Periodicidad.MENSUAL,
            GastoOperativo.Periodicidad.CADA_MESES,
            GastoOperativo.Periodicidad.ANUAL,
        ],
        fecha_inicio__lt=hasta,
    )
    if tipo not in (None, GastoOperativo.Tipo.FIJO):
        return gastos.none()
    return gastos


def ventas_cobradas(negocio, desde, hasta):
    """Ventas cobradas entre dos fechas (el límite 'hasta' no se incluye)."""
    return Venta.objects.filter(
        negocio=negocio, estado=Venta.Estado.COBRADA,
        creado_en__date__gte=desde, creado_en__date__lt=hasta,
    )


def ingresos_periodo(negocio, desde, hasta):
    return redondear(_suma(ventas_cobradas(negocio, desde, hasta), "total"))


def gastos_periodo(negocio, desde, hasta, tipo=None):
    """Gastos operativos del periodo. Los no recurrentes usan el mes asignado; los
    fijos recurrentes se cuentan por cada fecha de ocurrencia desde su fecha de inicio.
    La compra de mercancía se cuenta aparte porque su costo ya se resta al vender."""
    gastos = GastoOperativo.objects.filter(
        negocio=negocio,
        periodo__gte=desde,
        periodo__lt=hasta,
        periodicidad=GastoOperativo.Periodicidad.UNA_VEZ,
    )
    if tipo:
        gastos = gastos.filter(tipo=tipo)
    else:
        gastos = gastos.exclude(tipo=GastoOperativo.Tipo.MERCANCIA)
    total = _suma(gastos, "monto")
    recurrentes = _gastos_recurrentes(negocio, hasta, tipo)
    total += sum(
        (gasto.monto * _contar_ocurrencias(gasto, desde, hasta) for gasto in recurrentes),
        CERO,
    )
    return redondear(total)


def cantidad_gastos_periodo(negocio, desde, hasta):
    """Cuenta registros puntuales y ocurrencias fijas dentro del periodo."""
    puntuales = GastoOperativo.objects.filter(
        negocio=negocio,
        periodo__gte=desde,
        periodo__lt=hasta,
        periodicidad=GastoOperativo.Periodicidad.UNA_VEZ,
    ).exclude(tipo=GastoOperativo.Tipo.MERCANCIA)
    cantidad = puntuales.count()
    cantidad += sum(
        _contar_ocurrencias(gasto, desde, hasta)
        for gasto in _gastos_recurrentes(negocio, hasta)
    )
    return cantidad


def gastos_capturados(negocio, desde, hasta):
    """Gastos ocurridos entre dos fechas. Para un registro no recurrente se usa
    la fecha de captura; para uno recurrente, la fecha de cada ocurrencia."""
    gastos = GastoOperativo.objects.filter(
        negocio=negocio,
        fecha__gte=desde,
        fecha__lt=hasta,
        periodicidad=GastoOperativo.Periodicidad.UNA_VEZ,
    ).exclude(tipo=GastoOperativo.Tipo.MERCANCIA)
    total = _suma(gastos, "monto")
    recurrentes = _gastos_recurrentes(negocio, hasta)
    total += sum(
        (gasto.monto * _contar_ocurrencias(gasto, desde, hasta) for gasto in recurrentes),
        CERO,
    )
    return redondear(total)


def gasto_mas_inusual(negocio, desde, hasta):
    """Devuelve el mayor gasto individual si supera dos veces el promedio del periodo."""
    puntuales = GastoOperativo.objects.filter(
        negocio=negocio,
        periodo__gte=desde,
        periodo__lt=hasta,
        periodicidad=GastoOperativo.Periodicidad.UNA_VEZ,
    ).exclude(tipo=GastoOperativo.Tipo.MERCANCIA)
    totales = puntuales.aggregate(total=Sum("monto"), cantidad=Count("pk"))
    suma = totales["total"] or CERO
    cantidad = totales["cantidad"]
    mayor = puntuales.order_by("-monto").first()

    for gasto in _gastos_recurrentes(negocio, hasta):
        ocurrencias = _contar_ocurrencias(gasto, desde, hasta)
        if ocurrencias:
            suma += gasto.monto * ocurrencias
            cantidad += ocurrencias
            if mayor is None or gasto.monto > mayor.monto:
                mayor = gasto

    if cantidad and mayor and mayor.monto > suma / cantidad * 2:
        return mayor
    return None


def compras_periodo(negocio, desde, hasta):
    """Lo que se gastó en comprar mercancía (se registra sola al agregar piezas al inventario)."""
    compras = GastoOperativo.objects.filter(
        negocio=negocio, periodo__gte=desde, periodo__lt=hasta, tipo=GastoOperativo.Tipo.MERCANCIA,
    )
    return redondear(_suma(compras, "monto"))


def costo_de_ventas_periodo(negocio, desde, hasta):
    """Lo que costó (costo de adquisición) la mercancía que se vendió. Usa el costo
    guardado en cada renglón de venta, no el costo actual del producto."""
    items = ItemVenta.objects.filter(venta__in=ventas_cobradas(negocio, desde, hasta))
    return redondear(_suma(items, F("cantidad") * F("costo_unitario")))


def renglones_sin_costo(negocio, desde, hasta):
    """Cuántos renglones vendidos no tienen precio de compra. Mientras existan, la
    utilidad se ve más alta de lo que es en realidad."""
    return ItemVenta.objects.filter(
        venta__in=ventas_cobradas(negocio, desde, hasta), costo_unitario=0,
    ).count()


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

def resumen_desde_sumas(ingresos, costo_ventas, gastos, tasa_isr, compras=CERO):
    """
    Flujo de efectivo  = ingresos - egresos (gastos operativos + compras de mercancía)
    Margen operativo   = (ingresos - costo de ventas - gastos operativos) / ingresos * 100
    Utilidad neta      = ingresos - costo de ventas - gastos operativos - ISR RESICO

    Las compras de mercancía solo cuentan para el flujo de efectivo (es dinero que
    salió); para la utilidad no, porque el costo de lo vendido ya se resta en
    "costo de ventas" y se contaría dos veces.
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
        "compras": compras,
        "flujo_efectivo": ingresos - gastos - compras,
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
        compras=compras_periodo(negocio, desde, hasta),
    )


def resumen_por_meses(negocio, meses, tasa_isr):
    """El resumen de varios meses seguidos con consultas agrupadas, no una por mes.
    `meses` es la lista de primeros días de mes, del más viejo al más nuevo."""
    desde = meses[0]
    hasta = mes_siguiente(meses[-1])
    dinero = DecimalField(max_digits=14, decimal_places=2)

    def por_mes(consulta, campo_fecha, expresion):
        filas = (
            consulta.annotate(mes=TruncMonth(campo_fecha)).order_by().values("mes")
            .annotate(suma=Sum(expresion, output_field=dinero))
        )
        resultado = {}
        for fila in filas:
            mes = fila["mes"]
            resultado[mes.date() if hasattr(mes, "date") else mes] = fila["suma"] or CERO
        return resultado

    ventas = ventas_cobradas(negocio, desde, hasta)
    ingresos = por_mes(ventas, "creado_en", "total")
    costos = por_mes(
        ItemVenta.objects.filter(venta__in=ventas), "venta__creado_en", F("cantidad") * F("costo_unitario"),
    )
    gastos_todos = GastoOperativo.objects.filter(
        negocio=negocio,
        periodo__gte=desde,
        periodo__lt=hasta,
        periodicidad=GastoOperativo.Periodicidad.UNA_VEZ,
    )
    gastos = por_mes(gastos_todos.exclude(tipo=GastoOperativo.Tipo.MERCANCIA), "periodo", "monto")
    compras = por_mes(gastos_todos.filter(tipo=GastoOperativo.Tipo.MERCANCIA), "periodo", "monto")
    for gasto in _gastos_recurrentes(negocio, hasta):
        for mes in meses:
            gastos[mes] = gastos.get(mes, CERO) + gasto.monto * _contar_ocurrencias(
                gasto, mes, mes_siguiente(mes),
            )

    return [
        resumen_desde_sumas(
            redondear(ingresos.get(mes, CERO)), redondear(costos.get(mes, CERO)),
            redondear(gastos.get(mes, CERO)), tasa_isr, compras=redondear(compras.get(mes, CERO)),
        )
        for mes in meses
    ]


# ------------------------------------------------------- precio sugerido

def precio_sugerido(costo, margen_deseado):
    """Precio = costo de adquisición / (1 - margen deseado %)."""
    divisor = 1 - Decimal(margen_deseado) / 100
    sugerido = redondear(Decimal(costo) / divisor)
    return max(sugerido, redondear(costo))  # nunca se sugiere vender por debajo de lo que cuesta


def gastos_sobre_ventas(negocio, hoy, meses=3):
    """Qué parte de lo vendido se fue en gastos operativos (fijos y variables) en los
    últimos `meses` meses y lo que va del mes actual. Dice cuánto margen se necesita
    solo para cubrir los gastos."""
    desde = primer_dia_del_mes(hoy)
    for _ in range(meses):
        desde = mes_anterior(desde)
    hasta = hoy + timedelta(days=1)
    ingresos = ingresos_periodo(negocio, desde, hasta)
    gastos = gastos_periodo(negocio, desde, hasta)
    porcentaje = None
    if ingresos:
        porcentaje = redondear(gastos / ingresos * 100, DECIMA)
    return {"ingresos": ingresos, "gastos": gastos, "porcentaje": porcentaje, "meses": meses}


def margen_que_cubre_gastos(porcentaje_gastos, utilidad_deseada):
    """Margen (en % del precio) con el que de cada $100 vendidos alcanza para los gastos
    y todavía queda la utilidad que quiere el tendero. Nunca pasa de 90 %."""
    margen = Decimal(porcentaje_gastos) + Decimal(utilidad_deseada)
    return min(redondear(margen, DECIMA), Decimal("90"))


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
        costo=Sum(F("cantidad") * F("costo_unitario"), output_field=dinero),
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
    # para calcularlo se necesita al menos un gasto fijo y el precio de compra de los productos
    tiene_costos = Producto.objects.filter(negocio=negocio, activo=True, costo__gt=0).exists()
    if fijos <= 0:
        estado = "sin_fijos"
    elif not tiene_costos:
        estado = "sin_costos"
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


# ---------------------------------------------------------- pronóstico

MODELOS_PRONOSTICO = (
    {"clave": "arima", "nombre": "ARIMA"},
)
MINIMO_SEMANAS_MODELO = 8
SEMANAS_PRUEBA = 4


def _pronosticar_arima(valores, pasos):
    if len(valores) < MINIMO_SEMANAS_MODELO:
        raise ValueError("Se requieren al menos 8 semanas para ajustar el modelo.")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from statsmodels.tsa.arima.model import ARIMA

        ajustado = ARIMA(
            valores, order=(1, 1, 1),
            enforce_stationarity=False, enforce_invertibility=False,
        ).fit()
        return [float(valor) for valor in ajustado.forecast(pasos)]


def _evaluar_arima(valores):
    semanas_prueba = min(SEMANAS_PRUEBA, len(valores) - MINIMO_SEMANAS_MODELO)
    if semanas_prueba <= 0:
        return None

    entrenamiento = valores[:-semanas_prueba]
    reales = valores[-semanas_prueba:]
    estimados = [max(0, estimado) for estimado in _pronosticar_arima(entrenamiento, semanas_prueba)]
    return round(sum(abs(real - estimado) for real, estimado in zip(reales, estimados)) / semanas_prueba, 2)


NIVELES_DE_CONFIANZA = (
    # (error relativo máximo, nivel): el error del modelo contra lo que vende el producto por semana
    (Decimal("0.25"), "alta"),
    (Decimal("0.50"), "media"),
)


def nivel_de_confianza(mae, promedio_semanal):
    """Qué tanta confianza darle al pronóstico: compara el error del modelo (MAE) con lo que el
    producto vende en una semana normal. Si se equivoca poco frente a lo que vende, la confianza
    es alta. Estos umbrales son una propuesta y se pueden ajustar."""
    if mae is None or not promedio_semanal:
        return "sin datos"
    error_relativo = Decimal(str(mae)) / Decimal(str(promedio_semanal))
    for limite, nivel in NIVELES_DE_CONFIANZA:
        if error_relativo <= limite:
            return nivel
    return "baja"


def _minimo_de_dias():
    """Cuántos días de historia tiene que tener un producto para pronosticarlo (configurable)."""
    return int(getattr(settings, "PRONOSTICO_MINIMO_DIAS", 30))


def limpiar_dia_atipico(ventas_por_dia):
    """Quita una venta muy inflada y muy rara: si un solo día se vendió la mitad (o más) de todo lo que
    se vendió del producto en el historial, ese día se cambia por el siguiente día más alto, para que no
    engañe al modelo. Solo se hace si hay al menos 5 días con ventas. Regresa (ventas limpias, si se corrigió algo)."""
    total = sum(ventas_por_dia.values())
    if len(ventas_por_dia) < 5 or total <= 0:
        return ventas_por_dia, False
    dia_mayor, mayor = max(ventas_por_dia.items(), key=lambda dia: dia[1])
    if mayor < total * 0.5:
        return ventas_por_dia, False
    limpias = dict(ventas_por_dia)
    limpias[dia_mayor] = max(valor for dia, valor in ventas_por_dia.items() if dia != dia_mayor)
    return limpias, True


def series_de_los_mas_vendidos(negocio, limite=10, semanas_historial=26):
    """Las series semanales (unidades vendidas por semana) de los productos más vendidos, ya
    limpias de ventas atípicas, y qué productos tienen historia suficiente para pronosticarse."""
    filtro = ItemVenta.objects.filter(
        venta__negocio=negocio,
        venta__estado=Venta.Estado.COBRADA,
        producto__negocio=negocio,
        producto__activo=True,
    )
    populares = list(
        filtro.order_by().values("producto_id", "producto__nombre")
        .annotate(unidades=Sum("cantidad"))
        .order_by("-unidades", "producto_id")[:limite]
    )
    if not populares:
        return {"estado": "sin_ventas", "productos": []}

    ids = [producto["producto_id"] for producto in populares]
    dias = list(
        filtro.filter(producto_id__in=ids)
        .order_by().values("producto_id")
        .annotate(dia=TruncDate("venta__creado_en"))
        .values("producto_id", "dia")
        .annotate(unidades=Sum("cantidad"))
    )
    ultimo_dia = max(fila["dia"].date() if hasattr(fila["dia"], "date") else fila["dia"] for fila in dias)
    ultima_semana = ultimo_dia - timedelta(days=ultimo_dia.weekday())
    primera_semana = ultima_semana - timedelta(weeks=semanas_historial - 1)

    por_producto = {producto_id: {} for producto_id in ids}
    for fila in dias:
        dia = fila["dia"].date() if hasattr(fila["dia"], "date") else fila["dia"]
        if primera_semana <= dia <= ultimo_dia:
            por_producto[fila["producto_id"]][dia] = float(fila["unidades"])

    productos = []
    for popular in populares:
        ventas_por_dia, corregido = limpiar_dia_atipico(por_producto[popular["producto_id"]])
        por_semana = {}
        for dia, unidades in ventas_por_dia.items():
            semana = dia - timedelta(days=dia.weekday())
            por_semana[semana] = por_semana.get(semana, 0.0) + unidades
        serie = [por_semana.get(primera_semana + timedelta(weeks=indice), 0.0) for indice in range(semanas_historial)]

        dias_de_historia = (ultimo_dia - min(ventas_por_dia)).days + 1 if ventas_por_dia else 0
        recientes = serie[-MINIMO_SEMANAS_MODELO:]
        productos.append({
            "producto_id": popular["producto_id"],
            "nombre": popular["producto__nombre"],
            "unidades_historicas": round(float(popular["unidades"]), 2),
            "serie": serie,
            "semanas_con_venta": sum(valor > 0 for valor in serie),
            "dias_de_historia": dias_de_historia,
            "suficiente": dias_de_historia >= _minimo_de_dias(),
            "atipico_corregido": corregido,
            "ultima_semana_real": round(serie[-1], 2),
            "promedio_semanal": round(sum(recientes) / len(recientes), 2),
        })

    return {
        "estado": "ok",
        "productos": productos,
        "ultima_semana": ultima_semana,
        "semana_pronostico": ultima_semana + timedelta(weeks=1),
        "semanas_historial": semanas_historial,
        "minimo_de_dias": _minimo_de_dias(),
    }


def pronostico_de_un_modelo(negocio, clave, limite=10, base=None):
    """Pronostico ARIMA y MAE de prueba para cada producto elegible."""
    if clave != "arima":
        raise ValueError(f"Modelo desconocido: {clave}")

    base = base or series_de_los_mas_vendidos(negocio, limite)
    resultados = []
    for producto in base["productos"]:
        dato = {"producto_id": producto["producto_id"], "pronostico": None, "mae": None, "disponible": False}
        if producto["suficiente"]:
            try:
                prediccion = max(0, _pronosticar_arima(producto["serie"], 1)[0])
                dato.update(
                    pronostico=int(round(prediccion)), mae=_evaluar_arima(producto["serie"]), disponible=True,
                )
            except Exception:
                registro.exception(
                    "No se pudo calcular ARIMA para el producto %s del negocio %s",
                    producto["producto_id"],
                    negocio.pk,
                )
        resultados.append(dato)
    return resultados


def _cambio_porcentual_semanal(pronostico, ultima_semana_real):
    if pronostico is None or not ultima_semana_real:
        return None
    return round((pronostico - ultima_semana_real) / ultima_semana_real * 100)


def pronostico_ventas_negocio(negocio, limite=10, semanas_historial=26):
    """Pronostico ARIMA para los productos más vendidos, con su error MAE y confianza."""
    base = series_de_los_mas_vendidos(negocio, limite, semanas_historial)
    if base["estado"] == "sin_ventas":
        return {"estado": "sin_ventas", "productos": [], "modelos": MODELOS_PRONOSTICO}

    por_modelo = pronostico_de_un_modelo(negocio, "arima", base=base)
    productos = []
    for posicion, producto in enumerate(base["productos"]):
        arima = por_modelo[posicion]
        pronostico = arima["pronostico"] if arima["disponible"] else None
        productos.append({
            "nombre": producto["nombre"],
            "unidades_historicas": producto["unidades_historicas"],
            "semanas_con_venta": producto["semanas_con_venta"],
            "dias_de_historia": producto["dias_de_historia"],
            "datos_suficientes": producto["suficiente"],
            "atipico_corregido": producto["atipico_corregido"],
            "ultima_semana_real": producto["ultima_semana_real"],
            "promedio_semanal": producto["promedio_semanal"],
            "modelos": {
                "arima": {
                    "pronostico": arima["pronostico"],
                    "mae": arima["mae"],
                    "disponible": arima["disponible"],
                },
            },
            "mejor_modelo": "ARIMA" if pronostico is not None else None,
            "mejor_pronostico": pronostico,
            "cambio_porcentual": _cambio_porcentual_semanal(pronostico, producto["ultima_semana_real"]),
            "confianza": nivel_de_confianza(arima["mae"], producto["promedio_semanal"]),
        })

    return {
        "estado": "ok",
        "productos": productos,
        "modelos": MODELOS_PRONOSTICO,
        "ultima_semana": base["ultima_semana"],
        "semana_pronostico": base["semana_pronostico"],
        "semanas_historial": base["semanas_historial"],
        "minimo_de_dias": base["minimo_de_dias"],
    }


def pronostico_cacheado(negocio):
    """El pronóstico ARIMA guardado unos minutos para reutilizarlo en la explicación con IA."""
    return cache_negocio.obtener(negocio, "pronostico", lambda: pronostico_ventas_negocio(negocio))


# ------------------------------------------------------ reporte de ventas

def reporte_de_ventas(negocio, desde, hasta, limite=10):
    """Lo vendido entre dos fechas (las dos se incluyen): cuánto se vendió y se ganó, los productos
    que más se vendieron y los que más ganancia dejaron, y las ventas de cada día.
    La ganancia es lo vendido menos lo que costó la mercancía (el costo que tenía al venderse)."""
    ventas = ventas_cobradas(negocio, desde, hasta + timedelta(days=1))
    items = ItemVenta.objects.filter(venta__in=ventas)
    dinero = DecimalField(max_digits=14, decimal_places=2)

    ingresos = redondear(_suma(ventas, "total"))
    costo = redondear(_suma(items, F("cantidad") * F("costo_unitario")))
    tickets = ventas.count()

    agregados = {
        "unidades": Sum("cantidad"),
        "ventas": Sum(F("cantidad") * F("precio_unitario"), output_field=dinero),
        "ganancia": Sum(F("cantidad") * (F("precio_unitario") - F("costo_unitario")), output_field=dinero),
    }

    def por_producto(orden):
        filas = (
            items.order_by().values("producto_id", "producto__nombre").annotate(**agregados).order_by(orden, "producto_id")[:limite]
        )
        return [
            {"nombre": f["producto__nombre"], "unidades": f["unidades"], "ventas": redondear(f["ventas"]), "ganancia": redondear(f["ganancia"])}
            for f in filas
        ]

    por_categoria = [
        {
            "nombre": f["producto__categoria__nombre"] or "Sin categoría",
            "ventas": redondear(f["ventas"]), "ganancia": redondear(f["ganancia"]),
        }
        for f in items.order_by().values("producto__categoria__nombre").annotate(**agregados).order_by("-ventas")
    ]

    por_dia = [
        {"dia": f["dia"].date() if hasattr(f["dia"], "date") else f["dia"], "total": f["total"] or CERO}
        for f in ventas.annotate(dia=TruncDate("creado_en")).order_by().values("dia").annotate(total=Sum("total")).order_by("dia")
    ]

    ganancia = ingresos - costo
    return {
        "ingresos": ingresos,
        "costo": costo,
        "ganancia": ganancia,
        "margen_bruto": redondear(ganancia / ingresos * 100, DECIMA) if ingresos else None,
        "tickets": tickets,
        "ticket_promedio": redondear(ingresos / tickets) if tickets else None,
        "mas_vendidos": por_producto("-unidades"),
        "mas_ganancia": por_producto("-ganancia"),
        "por_categoria": por_categoria,
        "por_dia": por_dia,
        "renglones_sin_costo": renglones_sin_costo(negocio, desde, hasta + timedelta(days=1)),
    }
