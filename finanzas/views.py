from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import GastoOperativoForm
from .forecasting import forecast_sales
from .models import GastoOperativo


@login_required
def inicio(request):
    return render(request, "finanzas/inicio.html", {"activo": "inicio"})


@login_required
def registrar_gastos(request):
    negocio = getattr(request.user, "negocio", None)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    if request.method == "POST":
        form = GastoOperativoForm(request.POST)
        if form.is_valid():
            gasto = form.save(commit=False)
            gasto.negocio = negocio
            gasto.save()
            messages.success(request, f'Gasto "{gasto.concepto}" registrado.')
            return redirect("finanzas:registrar_gastos")
    else:
        form = GastoOperativoForm(initial={"tipo": GastoOperativo.Tipo.FIJO})

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


@login_required
def pronostico_ventas_api(request):
    negocio = getattr(request.user, "negocio", None)
    if negocio is None:
        return JsonResponse({"ok": False, "message": "Completa los datos de tu negocio primero."}, status=400)
    return JsonResponse(forecast_sales(negocio))


@login_required
def reportes_financieros(request):
    return render(request, "finanzas/reportes_financieros.html", {"activo": "reportes"})
