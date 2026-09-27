from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def inicio(request):
    return render(request, "finanzas/inicio.html", {"activo": "inicio"})


@login_required
def registrar_gastos(request):
    return render(request, "finanzas/registrar_gastos.html", {"activo": "gastos"})


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
def reportes_financieros(request):
    return render(request, "finanzas/reportes_financieros.html", {"activo": "reportes"})
