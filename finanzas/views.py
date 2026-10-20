from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Q, Sum
from django.http import Http404, JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from inventario.compras import mensaje_si_vende_bajo_el_costo, registrar_compra
from inventario.models import HistorialModificacionProducto, Producto
from ventas.models import ItemVenta, Venta

from . import calculos
from .forms import GastoOperativoForm
from .models import CategoriaGasto, GastoOperativo

MARGEN_DESEADO_POR_DEFECTO = Decimal("30")
UTILIDAD_DESEADA_POR_DEFECTO = Decimal("10")


def _negocio_o_none(request):
    return getattr(request.user, "negocio", None)


def _cambio_porcentual(actual, anterior, mas_es_bueno=True, referencia="mes ant."):
    """Texto y color para la flechita de comparación de las tarjetas."""
    if not anterior:
        return {"texto": f"sin datos de {referencia}", "clase": "neutral"}
    cambio = (actual - anterior) / abs(anterior) * 100
    if round(cambio) == 0:
        return {"texto": f"igual que {referencia}", "clase": "neutral"}
    signo = "+" if cambio > 0 else ""
    es_bueno = (cambio > 0) == mas_es_bueno
    return {"texto": f"{signo}{round(cambio)}% vs {referencia}", "clase": "up" if es_bueno else "down"}


@login_required
def inicio(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    hoy = timezone.localdate()
    manana = hoy + timedelta(days=1)
    inicio_mes = calculos.primer_dia_del_mes(hoy)
    inicio_mes_ant = calculos.mes_anterior(inicio_mes)
    # se compara contra los mismos días del mes anterior, no contra el mes completo
    hasta_mes_ant = min(inicio_mes_ant + timedelta(days=hoy.day), inicio_mes)
    tasa_isr = calculos.tasa_isr_del_negocio(negocio, hoy)

    ventas_hoy = calculos.ingresos_periodo(negocio, hoy, manana)
    ventas_ayer = calculos.ingresos_periodo(negocio, hoy - timedelta(days=1), hoy)
    mes = calculos.resumen_financiero(negocio, inicio_mes, manana, tasa_isr)
    mes_ant = calculos.resumen_financiero(negocio, inicio_mes_ant, hasta_mes_ant, tasa_isr)
    equilibrio = calculos.punto_equilibrio_negocio(negocio, hoy)

    if equilibrio["estado"] == "ok":
        equilibrio_texto = calculos.redondear(equilibrio["pe_total"])
        equilibrio_nota = "meta mensual"
    else:
        equilibrio_texto = None
        equilibrio_nota = "registra tus gastos fijos y vende para calcularlo"

    return render(request, "finanzas/inicio.html", {
        "activo": "inicio",
        "ventas_hoy": ventas_hoy,
        "ventas_hoy_cambio": _cambio_porcentual(ventas_hoy, ventas_ayer, referencia="ayer"),
        "gastos_mes": mes["gastos"],
        "gastos_mes_cambio": _cambio_porcentual(mes["gastos"], mes_ant["gastos"], mas_es_bueno=False),
        "utilidad_mes": mes["utilidad_neta"],
        "utilidad_mes_cambio": _cambio_porcentual(mes["utilidad_neta"], mes_ant["utilidad_neta"]),
        "equilibrio": equilibrio_texto,
        "equilibrio_nota": equilibrio_nota,
        "compras_mes": mes["compras"],
        # ventas sin precio de compra: mientras existan, la utilidad se ve más alta de lo real
        "renglones_sin_costo": calculos.renglones_sin_costo(negocio, inicio_mes, manana),
        "num_gastos_mes": GastoOperativo.objects.filter(negocio=negocio, periodo__gte=inicio_mes).count(),
        "num_productos_precios": Producto.objects.filter(negocio=negocio, activo=True, costo__gt=0).count(),
    })


@login_required
def registrar_gastos(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    if request.method == "POST":
        form = GastoOperativoForm(request.POST, negocio=negocio)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.negocio = negocio
            gasto.save()
            messages.success(request, f'Gasto "{gasto.concepto}" registrado.')
            return redirect("finanzas:registrar_gastos")
    else:
        form = GastoOperativoForm(initial={"tipo": GastoOperativo.Tipo.FIJO}, negocio=negocio)

    hoy = timezone.localdate()
    inicio_mes = calculos.primer_dia_del_mes(hoy)
    fin_mes = calculos.mes_siguiente(inicio_mes)
    total_fijos = calculos.gastos_periodo(negocio, inicio_mes, fin_mes, tipo=GastoOperativo.Tipo.FIJO)
    total_variables = calculos.gastos_periodo(negocio, inicio_mes, fin_mes, tipo=GastoOperativo.Tipo.VARIABLE)

    # productos "no encontrados" que ya se vendieron pero todavía no tienen precio de compra
    sin_precio_de_compra = Producto.objects.filter(
        negocio=negocio, pendiente_validacion=True, costo=0,
    ).annotate(
        vendidas=Sum("items_venta__cantidad", filter=Q(items_venta__venta__estado=Venta.Estado.COBRADA)),
    ).filter(vendidas__gt=0).order_by("nombre")

    return render(request, "finanzas/registrar_gastos.html", {
        "activo": "gastos",
        "form": form,
        "total_fijos": total_fijos,
        "total_variables": total_variables,
        "total_general": total_fijos + total_variables,
        "total_compras": calculos.compras_periodo(negocio, inicio_mes, fin_mes),
        "productos_sin_precio": list(sin_precio_de_compra),
    })


@login_required
@require_POST
def completar_no_encontrado(request, pk):
    """El tendero le pone precio de compra a un producto "no encontrado" que ya vendió.

    Así el costo de esas ventas queda completo (la utilidad deja de verse inflada) y lo
    que se compró para venderlo se registra como compra de mercancía."""
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    producto = get_object_or_404(Producto, pk=pk, negocio=negocio, pendiente_validacion=True, costo=0)
    try:
        costo = Decimal(request.POST.get("precio_compra", "").replace(",", "."))
        if not costo.is_finite() or costo <= 0 or costo >= Decimal("100000000"):
            raise InvalidOperation
        costo = calculos.redondear(costo)
    except InvalidOperation:
        messages.warning(request, "Escribe un precio de compra válido (mayor a cero).")
        return redirect("finanzas:registrar_gastos")

    aviso = mensaje_si_vende_bajo_el_costo(costo, producto.precio_venta)
    if aviso:
        messages.warning(request, f'"{producto.nombre}": ' + aviso)
        return redirect("finanzas:registrar_gastos")

    producto.costo = costo
    producto.save(update_fields=["costo", "actualizado_en"])
    # las ventas que se hicieron sin saber el costo se completan con este precio de compra
    producto.items_venta.filter(costo_unitario=0).update(costo_unitario=costo)

    vendidas = producto.items_venta.filter(venta__estado=Venta.Estado.COBRADA).aggregate(total=Sum("cantidad"))["total"] or 0
    compra = registrar_compra(negocio, f"Compra de mercancía: {producto.nombre} (producto no encontrado)", vendidas * costo)

    texto = f'Guardé el precio de compra de "{producto.nombre}": ${costo}.'
    if compra:
        texto += f" Se registró la compra de mercancía por ${compra.monto}."
    messages.success(request, texto)
    return redirect("finanzas:registrar_gastos")


@login_required
def categoria_gasto_alta(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if nombre:
            tipo = request.POST.get("tipo", "")
            tipo = tipo if tipo in (GastoOperativo.Tipo.FIJO, GastoOperativo.Tipo.VARIABLE) else ""
            creada = not CategoriaGasto.objects.filter(negocio=negocio, nombre__iexact=nombre).exists()
            if creada:
                CategoriaGasto.objects.create(negocio=negocio, nombre=nombre[:60], tipo=tipo)
                messages.success(request, f'Categoría "{nombre}" agregada.')
            else:
                messages.info(request, f'Ya existía una categoría "{nombre}".')

    return redirect("finanzas:registrar_gastos")


@login_required
def historial_gastos(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    gastos = GastoOperativo.objects.filter(negocio=negocio).order_by("-periodo", "-fecha", "-id")
    pagina = Paginator(gastos, 25).get_page(request.GET.get("page"))
    return render(request, "finanzas/historial_gastos.html", {"activo": "gastos", "gastos": pagina, "pagina": pagina})


@login_required
def punto_equilibrio(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    hoy = timezone.localdate()
    datos = calculos.punto_equilibrio_negocio(negocio, hoy)

    contexto = {
        "activo": "equilibrio",
        "estado": datos["estado"],
        "fijos": datos["fijos"],
        "meses_historial": datos["meses_historial"],
        "categorias": datos["filas"],
    }

    if datos["estado"] == "ok":
        pe_total = datos["pe_total"]
        inicio_mes = calculos.primer_dia_del_mes(hoy)
        ventas_mes = calculos.ingresos_periodo(negocio, inicio_mes, hoy + timedelta(days=1))
        contexto.update({
            "pe_total": calculos.redondear(pe_total),
            "pe_diario": calculos.redondear(pe_total / calculos.dias_del_mes(hoy)),
            "ventas_mes": ventas_mes,
            "porcentaje": min(100, int(ventas_mes / pe_total * 100)),
        })

    return render(request, "finanzas/punto_equilibrio.html", contexto)


def _leer_utilidad(valor):
    """Utilidad deseada en % (entre 0 y 50); si viene mal, la de por defecto."""
    try:
        utilidad = Decimal(str(valor).replace(",", "."))
        if not utilidad.is_finite() or utilidad < 0 or utilidad > 50:
            return UTILIDAD_DESEADA_POR_DEFECTO
        return utilidad.quantize(Decimal("0.1"))
    except InvalidOperation:
        return UTILIDAD_DESEADA_POR_DEFECTO


def _leer_margen(valor):
    """Margen deseado en % (entre 1 y 90); si viene mal, el de por defecto."""
    try:
        margen = Decimal(str(valor).replace(",", "."))
        if not margen.is_finite() or margen < 1 or margen > 90:
            return MARGEN_DESEADO_POR_DEFECTO
        return margen.quantize(Decimal("0.1"))
    except InvalidOperation:
        return MARGEN_DESEADO_POR_DEFECTO


@login_required
def sugerir_precios(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    hoy = timezone.localdate()
    gastos = calculos.gastos_sobre_ventas(negocio, hoy)

    # dos formas de escoger el margen: el tendero lo escribe, o se calcula para cubrir sus gastos
    # lo que el tendero escogió la última vez se recuerda: aparece ya puesto cuando regresa
    modo = request.GET.get("modo") or negocio.preferencia("modo_precios", "manual")
    modo = modo if modo in ("manual", "gastos") else "manual"
    utilidad = _leer_utilidad(request.GET.get("utilidad", negocio.preferencia("utilidad_extra", UTILIDAD_DESEADA_POR_DEFECTO)))
    margen_escrito = _leer_margen(request.GET.get("margen", negocio.preferencia("margen_deseado", MARGEN_DESEADO_POR_DEFECTO)))
    if modo == "gastos" and gastos["porcentaje"] is None:
        # sin ventas no hay forma de saber qué parte se va en gastos
        modo = "manual"
        messages.info(request, "Todavía no hay ventas para calcular tus gastos sobre ventas; escribe el margen a mano.")

    if modo == "gastos":
        margen = calculos.margen_que_cubre_gastos(gastos["porcentaje"], utilidad)
    else:
        margen = margen_escrito
    if "modo" in request.GET:  # el tendero apretó "Calcular": se guarda lo que escogió
        negocio.guardar_preferencias(modo_precios=modo, margen_deseado=str(margen_escrito), utilidad_extra=str(utilidad))

    productos = Producto.objects.filter(negocio=negocio, activo=True, costo__gt=0).select_related("categoria")
    filas = []
    for producto in productos:
        sugerido = calculos.precio_sugerido(producto.costo, margen)
        filas.append({
            "producto": producto, "sugerido": sugerido, "diferencia": sugerido - producto.precio_venta,
            "ganancia": sugerido - producto.costo,
        })
    # primero los que más deberían subir de precio
    filas.sort(key=lambda fila: fila["diferencia"], reverse=True)
    pagina = Paginator(filas, 15).get_page(request.GET.get("page"))

    return render(request, "finanzas/sugerir_precios.html", {
        "activo": "precios",
        "modo": modo,
        "margen": margen,
        "utilidad": utilidad,
        "pagina": pagina,
        "total_productos": len(filas),
        "gastos": gastos,
        "gastos_sobre_ventas": gastos["porcentaje"],
        "margen_ya_cubre": gastos["porcentaje"] is not None and margen < gastos["porcentaje"],
    })


@login_required
@require_POST
def aceptar_precio_sugerido(request, pk):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    producto = get_object_or_404(Producto, pk=pk, negocio=negocio, activo=True)
    margen = _leer_margen(request.POST.get("margen", MARGEN_DESEADO_POR_DEFECTO))
    pagina = request.POST.get("page", "1")
    pagina = pagina if pagina.isdigit() else "1"
    modo = "gastos" if request.POST.get("modo") == "gastos" else "manual"
    utilidad = _leer_utilidad(request.POST.get("utilidad", UTILIDAD_DESEADA_POR_DEFECTO))
    destino = f"{reverse('finanzas:sugerir_precios')}?modo={modo}&margen={margen}&utilidad={utilidad}&page={pagina}"

    try:
        nuevo_precio = Decimal(request.POST.get("precio", "").replace(",", "."))
        if not nuevo_precio.is_finite() or nuevo_precio <= 0 or nuevo_precio >= Decimal("100000000"):
            raise InvalidOperation
        nuevo_precio = calculos.redondear(nuevo_precio)
    except InvalidOperation:
        messages.warning(request, "Escribe un precio válido para poder guardarlo.")
        return redirect(destino)

    precio_anterior = producto.precio_venta
    producto.precio_venta = nuevo_precio
    producto.save(update_fields=["precio_venta", "actualizado_en"])
    HistorialModificacionProducto.objects.create(
        producto=producto, usuario=request.user,
        motivo=(
            f"Precio sugerido aceptado: de ${precio_anterior} a ${nuevo_precio} "
            f"({'margen para cubrir gastos' if modo == 'gastos' else 'margen deseado'} {margen}%)"
        ),
    )
    messages.success(request, f'El precio de "{producto.nombre}" ahora es ${nuevo_precio}.')
    return redirect(destino)


@login_required
def pronostico_ventas(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    # el cálculo se pide por partes desde la pantalla (ver pronostico_base y pronostico_modelo)
    return render(request, "finanzas/pronostico_ventas.html", {"activo": "pronostico"})


@login_required
@require_GET
def pronostico_base(request):
    """Los productos y sus ventas, sin correr ningún modelo todavía (sale en un instante)."""
    negocio = _negocio_o_none(request)
    if negocio is None:
        return JsonResponse({"estado": "sin_ventas"}, status=404)

    base = calculos.series_de_los_mas_vendidos(negocio)
    if base["estado"] == "sin_ventas":
        return JsonResponse({"estado": "sin_ventas"})
    return JsonResponse({
        "estado": "ok",
        "ultima_semana": base["ultima_semana"].strftime("%d/%m/%Y"),
        "semana_pronostico": base["semana_pronostico"].strftime("%d/%m/%Y"),
        "minimo_de_dias": base["minimo_de_dias"],
        "umbrales": {nivel: float(limite) for limite, nivel in calculos.NIVELES_DE_CONFIANZA},
        "productos": [
            {clave: producto[clave] for clave in (
                "producto_id", "nombre", "unidades_historicas", "ultima_semana_real", "promedio_semanal",
                "suficiente", "dias_de_historia", "atipico_corregido",
            )}
            for producto in base["productos"]
        ],
    })


@login_required
@require_GET
def pronostico_modelo(request, clave):
    """Lo que dice un solo modelo (lineal, holt_winters o arima) de cada producto."""
    negocio = _negocio_o_none(request)
    if negocio is None or clave not in {modelo["clave"] for modelo in calculos.MODELOS_PRONOSTICO}:
        raise Http404("Ese modelo no existe.")
    return JsonResponse({"clave": clave, "resultados": calculos.pronostico_de_un_modelo(negocio, clave)})


MESES_ABREVIADOS = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


def _mes_del_filtro(texto):
    """'2026-09' -> primer día de ese mes; None si no es un mes válido."""
    try:
        anio, mes = texto.split("-")
        return date(int(anio), int(mes), 1)
    except (ValueError, AttributeError):
        return None


MAXIMO_DE_MESES_EN_REPORTE = 24


def _meses_del_reporte(request, negocio, hoy):
    """Los meses del reporte, del más viejo al más nuevo: un rango escrito por el tendero (desde y hasta),
    o los últimos 1, 3, 6 o 12 meses. Lo último que escogió se recuerda para la próxima vez."""
    mes_actual = calculos.primer_dia_del_mes(hoy)
    desde = _mes_del_filtro(request.GET.get("desde", ""))
    hasta = _mes_del_filtro(request.GET.get("hasta", ""))

    if desde and hasta:
        if desde > hasta:
            desde, hasta = hasta, desde
        hasta = min(hasta, mes_actual)
        desde = min(desde, hasta)
        meses = []
        cursor = hasta
        while cursor >= desde and len(meses) < MAXIMO_DE_MESES_EN_REPORTE:
            meses.append(cursor)
            cursor = calculos.mes_anterior(cursor)
        meses.reverse()
        return meses, None

    pedido = request.GET.get("periodo", "")
    if pedido in ("1", "3", "6", "12"):
        periodo = int(pedido)
        negocio.guardar_preferencias(meses_reportes=periodo)
    else:
        periodo = negocio.preferencia("meses_reportes", 6)
        if periodo not in (1, 3, 6, 12):
            periodo = 6

    meses = []
    cursor = mes_actual
    for _ in range(periodo):
        meses.append(cursor)
        cursor = calculos.mes_anterior(cursor)
    meses.reverse()
    return meses, periodo


def _sugerencias_del_reporte(datos_meses, meses, total, gasto_inusual):
    """Alertas y sugerencias concretas a partir de los números del periodo."""
    sugerencias = []
    nombre = lambda mes: f"{MESES_ABREVIADOS[mes.month - 1]} {mes.year}"

    if gasto_inusual:
        sugerencias.append({
            "icono": "bi-lightbulb-fill",
            "texto": f'El gasto "{gasto_inusual.concepto}" de ${gasto_inusual.monto} fue mucho más alto de lo normal en este periodo. Vale la pena revisarlo.',
        })

    perdidas = [nombre(mes) for mes, m in zip(meses, datos_meses) if m["ingresos"] and m["utilidad_neta"] < 0]
    if perdidas:
        sugerencias.append({
            "icono": "bi-exclamation-triangle-fill", "alerta": True,
            "texto": "En " + ", ".join(perdidas) + " tus gastos y el costo de lo vendido fueron mayores que lo que vendiste: ese mes perdiste dinero.",
            "enlace": ("finanzas:sugerir_precios", "Revisar mis precios"),
        })

    if len(datos_meses) >= 2:
        anterior, ultimo = datos_meses[-2]["gastos"], datos_meses[-1]["gastos"]
        if anterior > 0 and ultimo > anterior * Decimal("1.2"):
            subio = round((ultimo - anterior) / anterior * 100)
            sugerencias.append({
                "icono": "bi-graph-up-arrow",
                "texto": f"Tus gastos de {nombre(meses[-1])} subieron {subio}% contra {nombre(meses[-2])} (de ${anterior} a ${ultimo}).",
                "enlace": ("finanzas:historial_gastos", "Ver mis gastos"),
            })

    if total["margen_operativo"] is not None and total["margen_operativo"] < Decimal("10") and total["ingresos"]:
        sugerencias.append({
            "icono": "bi-tag-fill",
            "texto": f"Tu margen operativo es de {total['margen_operativo']}%: de cada $100 que vendes te quedan menos de $10 antes de impuestos.",
            "enlace": ("finanzas:sugerir_precios", "Sugerir precios para cubrir mis gastos"),
        })
    return sugerencias


@login_required
def reportes_financieros(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    hoy = timezone.localdate()
    meses, periodo_meses = _meses_del_reporte(request, negocio, hoy)

    # la misma tasa de ISR para todo el reporte (depende de los ingresos del último año)
    tasa_isr = calculos.tasa_isr_del_negocio(negocio, hoy)

    # todos los meses se calculan juntos (4 consultas en total, no 4 por mes)
    datos_meses = calculos.resumen_por_meses(negocio, meses, tasa_isr)
    muchos_anios = meses[0].year != meses[-1].year
    for mes, resumen in zip(meses, datos_meses):
        resumen["etiqueta"] = MESES_ABREVIADOS[mes.month - 1] + (f" {str(mes.year)[2:]}" if muchos_anios else "")

    total = calculos.resumen_desde_sumas(
        sum((m["ingresos"] for m in datos_meses), Decimal("0")),
        sum((m["costo_ventas"] for m in datos_meses), Decimal("0")),
        sum((m["gastos"] for m in datos_meses), Decimal("0")),
        tasa_isr,
        compras=sum((m["compras"] for m in datos_meses), Decimal("0")),
    )

    # coordenadas de las barras/puntos dentro de un viewBox fijo de 320x160,
    # normalizadas contra el valor más alto del periodo
    n = len(datos_meses)
    paso = 320 / n
    ancho_barra = max(min(round(paso / 2 - 1), 10), 3)
    max_barra = max([m["ingresos"] for m in datos_meses] + [m["gastos"] + m["compras"] for m in datos_meses] + [Decimal("1")])
    max_utilidad = max([abs(m["utilidad_neta"]) for m in datos_meses] + [Decimal("1")])
    for i, m in enumerate(datos_meses):
        centro = paso * i + paso / 2
        m["ancho"] = ancho_barra
        m["x_ingresos"] = round(centro - ancho_barra)
        m["x_egresos"] = round(centro + 1)
        m["x_texto"] = round(centro)
        m["h_ingresos"] = max(round(float(m["ingresos"] / max_barra) * 100), 2)
        # la barra de egresos incluye lo que se gastó en comprar mercancía (es dinero que salió)
        m["h_egresos"] = max(round(float((m["gastos"] + m["compras"]) / max_barra) * 100), 2)
        m["y_ingresos"] = 135 - m["h_ingresos"]
        m["y_egresos"] = 135 - m["h_egresos"]
        m["y_punto"] = round(90 - float(m["utilidad_neta"] / max_utilidad) * 50)
        m["con_etiqueta"] = n <= 12 or i % 2 == 0  # con muchos meses se muestra una etiqueta sí y otra no

    puntos_linea = " ".join(f"{m['x_texto']},{m['y_punto']}" for m in datos_meses)

    # el gasto operativo más grande del periodo, si es claramente mayor al promedio
    gastos_del_periodo = GastoOperativo.objects.filter(
        negocio=negocio, periodo__gte=meses[0], periodo__lt=calculos.mes_siguiente(meses[-1]),
    ).exclude(tipo=GastoOperativo.Tipo.MERCANCIA)
    gasto_inusual = None
    promedio_gasto = gastos_del_periodo.aggregate(promedio=Avg("monto"))["promedio"]
    if promedio_gasto:
        mayor = gastos_del_periodo.order_by("-monto").first()
        if mayor and mayor.monto > promedio_gasto * 2:
            gasto_inusual = mayor

    hasta_fecha = min(hoy + timedelta(days=1), calculos.mes_siguiente(meses[-1]))
    return render(request, "finanzas/reportes_financieros.html", {
        "activo": "reportes",
        "periodo_meses": periodo_meses,
        "opciones_de_periodo": (1, 3, 6, 12),
        "desde_mes": meses[0].strftime("%Y-%m"),
        "hasta_mes": meses[-1].strftime("%Y-%m"),
        "mes_actual": calculos.primer_dia_del_mes(hoy).strftime("%Y-%m"),
        "datos_meses": datos_meses,
        "puntos_linea": puntos_linea,
        "total": total,
        "es_resico": negocio.regimen_resico,
        "gasto_inusual": gasto_inusual,
        "sugerencias": _sugerencias_del_reporte(datos_meses, meses, total, gasto_inusual),
        "renglones_sin_costo": calculos.renglones_sin_costo(negocio, meses[0], hasta_fecha),
        "desde_baja_rotacion": meses[0].isoformat(),
    })


@login_required
@require_GET
def baja_rotacion(request):
    """Productos que no se han vendido en el periodo, por lotes ("Ver más"). Se pide aparte
    porque es la parte más pesada del reporte y no todos la necesitan."""
    negocio = _negocio_o_none(request)
    if negocio is None:
        return JsonResponse({"html": "", "hay_mas": False})

    try:
        desde = timezone.datetime.fromisoformat(request.GET.get("desde", "")).date()
    except ValueError:
        desde = calculos.primer_dia_del_mes(timezone.localdate())

    vendidos = ItemVenta.objects.filter(
        venta__negocio=negocio, venta__estado=Venta.Estado.COBRADA, venta__creado_en__date__gte=desde,
    ).values("producto_id")
    sin_ventas = Producto.objects.filter(negocio=negocio, activo=True).exclude(pk__in=vendidos).order_by("-cantidad_actual")
    pagina_pedida = request.GET.get("page", "1")
    pagina = Paginator(sin_ventas, 10).get_page(pagina_pedida if pagina_pedida.isdigit() else 1)
    html = render_to_string("finanzas/_baja_rotacion.html", {"productos": list(pagina.object_list)}, request)
    return JsonResponse({"html": html, "hay_mas": pagina.has_next(), "siguiente": pagina.number + 1, "total": pagina.paginator.count})


def _fecha_o_none(texto):
    try:
        return date.fromisoformat(texto)
    except (ValueError, TypeError):
        return None


@login_required
def reporte_ventas(request):
    """Reporte de ventas con filtro por fechas: lo vendido, lo ganado y los productos que más se mueven."""
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    hoy = timezone.localdate()
    dias = request.GET.get("dias", "")
    desde = _fecha_o_none(request.GET.get("desde", ""))
    hasta = _fecha_o_none(request.GET.get("hasta", ""))
    if dias in ("7", "30", "90"):
        desde, hasta = hoy - timedelta(days=int(dias) - 1), hoy
    if not desde or not hasta:
        desde, hasta, dias = hoy - timedelta(days=29), hoy, "30"
    if desde > hasta:
        desde, hasta = hasta, desde
    hasta = min(hasta, hoy)
    desde = min(desde, hasta)

    reporte = calculos.reporte_de_ventas(negocio, desde, hasta)

    # barras de las ventas de cada día dentro de un viewBox de 320x160
    por_dia = reporte["por_dia"]
    if por_dia:
        maximo = max(dia["total"] for dia in por_dia) or Decimal("1")
        paso = 320 / len(por_dia)
        ancho = max(min(round(paso - 2), 24), 2)
        for i, dia in enumerate(por_dia):
            altura = max(round(float(dia["total"] / maximo) * 110), 2)
            dia.update(x=round(paso * i + (paso - ancho) / 2), alto=altura, y=135 - altura, ancho=ancho)
            dia["etiqueta"] = dia["dia"].strftime("%d/%m")
            dia["con_etiqueta"] = len(por_dia) <= 10 or i % max(len(por_dia) // 8, 1) == 0

    return render(request, "finanzas/reporte_ventas.html", {
        "activo": "reporte_ventas",
        "reporte": reporte,
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "hoy": hoy.isoformat(),
        "dias": dias,
    })
