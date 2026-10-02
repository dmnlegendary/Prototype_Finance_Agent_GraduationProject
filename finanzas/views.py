from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.shortcuts import redirect, render
from django.utils import timezone

from inventario.models import Producto
from ventas.models import ItemVenta, Venta

from .forms import GastoOperativoForm
from .models import CategoriaGasto, GastoOperativo


@login_required
def inicio(request):
    return render(request, "finanzas/inicio.html", {"activo": "inicio"})


@login_required
def registrar_gastos(request):
    negocio = getattr(request.user, "negocio", None)
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
    gastos_mes = GastoOperativo.objects.filter(negocio=negocio, fecha__year=hoy.year, fecha__month=hoy.month)
    total_fijos = sum((g.monto for g in gastos_mes if g.tipo == GastoOperativo.Tipo.FIJO), start=Decimal("0"))
    total_variables = sum((g.monto for g in gastos_mes if g.tipo == GastoOperativo.Tipo.VARIABLE), start=Decimal("0"))

    return render(request, "finanzas/registrar_gastos.html", {
        "activo": "gastos",
        "form": form,
        "total_fijos": total_fijos,
        "total_variables": total_variables,
        "total_general": total_fijos + total_variables,
    })


@login_required
def categoria_gasto_alta(request):
    negocio = getattr(request.user, "negocio", None)
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
    negocio = getattr(request.user, "negocio", None)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    gastos = GastoOperativo.objects.filter(negocio=negocio).order_by("-fecha", "-id")
    return render(request, "finanzas/historial_gastos.html", {"activo": "gastos", "gastos": gastos})


@login_required
def punto_equilibrio(request):
    return render(request, "finanzas/punto_equilibrio.html", {"activo": "equilibrio"})


@login_required
def sugerir_precios(request):
    return render(request, "finanzas/sugerir_precios.html", {"activo": "precios"})


@login_required
def pronostico_ventas(request):
    return render(request, "finanzas/pronostico_ventas.html", {"activo": "pronostico"})


MESES_ABREVIADOS = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


def _primer_dia_del_mes(fecha):
    return fecha.replace(day=1)


def _mes_siguiente(primer_dia):
    return (primer_dia.replace(day=28) + timedelta(days=4)).replace(day=1)


@login_required
def reportes_financieros(request):
    negocio = getattr(request.user, "negocio", None)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    periodo_meses = 3 if request.GET.get("periodo") == "3" else 6

    hoy = timezone.localdate()
    meses = []
    cursor = _primer_dia_del_mes(hoy)
    for _ in range(periodo_meses):
        meses.append(cursor)
        cursor = _primer_dia_del_mes(cursor - timedelta(days=1))
    meses.reverse()

    datos_meses = []
    for mes in meses:
        siguiente = _mes_siguiente(mes)
        ingresos = sum((
            v.total for v in Venta.objects.filter(
                negocio=negocio, estado=Venta.Estado.COBRADA,
                creado_en__date__gte=mes, creado_en__date__lt=siguiente,
            )
        ), start=Decimal("0"))
        egresos = sum((
            g.monto for g in GastoOperativo.objects.filter(negocio=negocio, fecha__gte=mes, fecha__lt=siguiente)
        ), start=Decimal("0"))
        datos_meses.append({
            "etiqueta": MESES_ABREVIADOS[mes.month - 1],
            "ingresos": ingresos,
            "egresos": egresos,
            "utilidad": ingresos - egresos,
        })

    ingresos_totales = sum((m["ingresos"] for m in datos_meses), start=Decimal("0"))
    egresos_totales = sum((m["egresos"] for m in datos_meses), start=Decimal("0"))
    utilidad_neta = ingresos_totales - egresos_totales
    margen_promedio = round(utilidad_neta / ingresos_totales * 100, 1) if ingresos_totales else Decimal("0")

    # coordenadas de las barras/puntos dentro de un viewBox fijo de 320x160,
    # normalizadas contra el valor más alto del periodo
    n = len(datos_meses)
    paso = 320 / n
    max_barra = max([m["ingresos"] for m in datos_meses] + [m["egresos"] for m in datos_meses] + [Decimal("1")])
    max_utilidad = max([abs(m["utilidad"]) for m in datos_meses] + [Decimal("1")])
    for i, m in enumerate(datos_meses):
        centro = paso * i + paso / 2
        m["x_ingresos"] = round(centro - 10)
        m["x_egresos"] = round(centro + 2)
        m["x_texto"] = round(centro)
        h_ingresos = round(float(m["ingresos"] / max_barra) * 100)
        h_egresos = round(float(m["egresos"] / max_barra) * 100)
        m["h_ingresos"] = max(h_ingresos, 2)
        m["h_egresos"] = max(h_egresos, 2)
        m["y_ingresos"] = 135 - m["h_ingresos"]
        m["y_egresos"] = 135 - m["h_egresos"]
        m["y_punto"] = round(90 - float(m["utilidad"] / max_utilidad) * 50)

    puntos_linea = " ".join(f"{m['x_texto']},{m['y_punto']}" for m in datos_meses)

    # productos activos sin ninguna venta cobrada en el periodo (baja rotación)
    productos_vendidos_ids = ItemVenta.objects.filter(
        venta__negocio=negocio, venta__estado=Venta.Estado.COBRADA, venta__creado_en__date__gte=meses[0],
    ).values_list("producto_id", flat=True).distinct()
    baja_rotacion = Producto.objects.filter(negocio=negocio, activo=True).exclude(pk__in=productos_vendidos_ids)[:5]

    # el gasto más grande del periodo, si es claramente mayor al promedio
    gastos_periodo = GastoOperativo.objects.filter(negocio=negocio, fecha__gte=meses[0])
    gasto_inusual = None
    promedio_gasto = gastos_periodo.aggregate(promedio=Avg("monto"))["promedio"]
    if promedio_gasto:
        mayor = gastos_periodo.order_by("-monto").first()
        if mayor and mayor.monto > promedio_gasto * 2:
            gasto_inusual = mayor

    return render(request, "finanzas/reportes_financieros.html", {
        "activo": "reportes",
        "periodo_meses": periodo_meses,
        "datos_meses": datos_meses,
        "puntos_linea": puntos_linea,
        "ingresos_totales": ingresos_totales,
        "egresos_totales": egresos_totales,
        "utilidad_neta": utilidad_neta,
        "margen_promedio": margen_promedio,
        "baja_rotacion": baja_rotacion,
        "gasto_inusual": gasto_inusual,
    })
