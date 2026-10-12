from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Q, Sum
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from inventario.compras import registrar_compra
from inventario.models import HistorialModificacionProducto, Producto
from ventas.models import ItemVenta, Venta

from . import calculos
from .forms import GastoOperativoForm
from .models import CategoriaGasto, GastoOperativo

MARGEN_DESEADO_POR_DEFECTO = Decimal("30")


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
        "num_gastos_mes": GastoOperativo.objects.filter(negocio=negocio, fecha__gte=inicio_mes).count(),
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
            _, creada = CategoriaGasto.objects.get_or_create(negocio=negocio, nombre=nombre)
            if creada:
                messages.success(request, f'Categoría "{nombre}" agregada.')
            else:
                messages.info(request, f'Ya existía una categoría "{nombre}".')

    return redirect("finanzas:registrar_gastos")


@login_required
def historial_gastos(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    gastos = GastoOperativo.objects.filter(negocio=negocio).order_by("-fecha", "-id")
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

    margen = _leer_margen(request.GET.get("margen", MARGEN_DESEADO_POR_DEFECTO))

    productos = Producto.objects.filter(negocio=negocio, activo=True, costo__gt=0).select_related("categoria")
    filas = []
    for producto in productos:
        sugerido = calculos.precio_sugerido(producto.costo, margen)
        filas.append({"producto": producto, "sugerido": sugerido, "diferencia": sugerido - producto.precio_venta})
    # primero los que más deberían subir de precio
    filas.sort(key=lambda fila: fila["diferencia"], reverse=True)
    pagina = Paginator(filas, 15).get_page(request.GET.get("page"))

    # referencia: qué tanto de cada peso vendido se va en gastos operativos
    hoy = timezone.localdate()
    desde = calculos.primer_dia_del_mes(hoy)
    for _ in range(3):
        desde = calculos.mes_anterior(desde)
    hasta = hoy + timedelta(days=1)
    ingresos = calculos.ingresos_periodo(negocio, desde, hasta)
    gastos_sobre_ventas = None
    if ingresos:
        gastos_sobre_ventas = calculos.redondear(calculos.gastos_periodo(negocio, desde, hasta) / ingresos * 100, calculos.DECIMA)

    return render(request, "finanzas/sugerir_precios.html", {
        "activo": "precios",
        "margen": margen,
        "pagina": pagina,
        "total_productos": len(filas),
        "gastos_sobre_ventas": gastos_sobre_ventas,
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
    destino = f"{reverse('finanzas:sugerir_precios')}?margen={margen}&page={pagina}"

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
        motivo=f"Precio sugerido aceptado: de ${precio_anterior} a ${nuevo_precio} (margen deseado {margen}%)",
    )
    messages.success(request, f'El precio de "{producto.nombre}" ahora es ${nuevo_precio}.')
    return redirect(destino)


@login_required
def pronostico_ventas(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    generar = request.GET.get("generar") == "1"
    datos = calculos.pronostico_ventas_negocio(negocio) if generar else None
    return render(request, "finanzas/pronostico_ventas.html", {
        "activo": "pronostico",
        "pronostico": datos,
    })


MESES_ABREVIADOS = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


@login_required
def reportes_financieros(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    periodo_meses = 3 if request.GET.get("periodo") == "3" else 6

    hoy = timezone.localdate()
    meses = []
    cursor = calculos.primer_dia_del_mes(hoy)
    for _ in range(periodo_meses):
        meses.append(cursor)
        cursor = calculos.mes_anterior(cursor)
    meses.reverse()

    # la misma tasa de ISR para todo el reporte (depende de los ingresos del último año)
    tasa_isr = calculos.tasa_isr_del_negocio(negocio, hoy)

    # todos los meses se calculan juntos (4 consultas en total, no 4 por mes)
    datos_meses = calculos.resumen_por_meses(negocio, meses, tasa_isr)
    for mes, resumen in zip(meses, datos_meses):
        resumen["etiqueta"] = MESES_ABREVIADOS[mes.month - 1]

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
    max_barra = max([m["ingresos"] for m in datos_meses] + [m["gastos"] + m["compras"] for m in datos_meses] + [Decimal("1")])
    max_utilidad = max([abs(m["utilidad_neta"]) for m in datos_meses] + [Decimal("1")])
    for i, m in enumerate(datos_meses):
        centro = paso * i + paso / 2
        m["x_ingresos"] = round(centro - 10)
        m["x_egresos"] = round(centro + 2)
        m["x_texto"] = round(centro)
        m["h_ingresos"] = max(round(float(m["ingresos"] / max_barra) * 100), 2)
        # la barra de egresos incluye lo que se gastó en comprar mercancía (es dinero que salió)
        m["h_egresos"] = max(round(float((m["gastos"] + m["compras"]) / max_barra) * 100), 2)
        m["y_ingresos"] = 135 - m["h_ingresos"]
        m["y_egresos"] = 135 - m["h_egresos"]
        m["y_punto"] = round(90 - float(m["utilidad_neta"] / max_utilidad) * 50)

    puntos_linea = " ".join(f"{m['x_texto']},{m['y_punto']}" for m in datos_meses)

    # el gasto operativo más grande del periodo, si es claramente mayor al promedio
    gastos_del_periodo = GastoOperativo.objects.filter(
        negocio=negocio, fecha__gte=meses[0],
    ).exclude(tipo=GastoOperativo.Tipo.MERCANCIA)
    gasto_inusual = None
    promedio_gasto = gastos_del_periodo.aggregate(promedio=Avg("monto"))["promedio"]
    if promedio_gasto:
        mayor = gastos_del_periodo.order_by("-monto").first()
        if mayor and mayor.monto > promedio_gasto * 2:
            gasto_inusual = mayor

    return render(request, "finanzas/reportes_financieros.html", {
        "activo": "reportes",
        "periodo_meses": periodo_meses,
        "datos_meses": datos_meses,
        "puntos_linea": puntos_linea,
        "total": total,
        "es_resico": negocio.regimen_resico,
        "gasto_inusual": gasto_inusual,
        "renglones_sin_costo": calculos.renglones_sin_costo(negocio, meses[0], hoy + timedelta(days=1)),
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
