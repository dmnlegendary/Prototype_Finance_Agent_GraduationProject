from django.urls import path

from . import views

app_name = "finanzas"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("gastos/", views.registrar_gastos, name="registrar_gastos"),
    path("gastos/historial/", views.historial_gastos, name="historial_gastos"),
    path("equilibrio/", views.punto_equilibrio, name="punto_equilibrio"),
    path("precios/", views.sugerir_precios, name="sugerir_precios"),
    path("pronostico/", views.pronostico_ventas, name="pronostico_ventas"),
    path("pronostico/api/", views.pronostico_ventas_api, name="pronostico_ventas_api"),
    path("reportes/", views.reportes_financieros, name="reportes_financieros"),
]
