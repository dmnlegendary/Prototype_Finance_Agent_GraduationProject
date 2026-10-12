from django.urls import path

from . import views

app_name = "finanzas"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("gastos/", views.registrar_gastos, name="registrar_gastos"),
    path("gastos/categoria-alta/", views.categoria_gasto_alta, name="categoria_gasto_alta"),
    path("gastos/historial/", views.historial_gastos, name="historial_gastos"),
    path("gastos/<int:pk>/precio-compra/", views.completar_no_encontrado, name="completar_no_encontrado"),
    path("equilibrio/", views.punto_equilibrio, name="punto_equilibrio"),
    path("precios/", views.sugerir_precios, name="sugerir_precios"),
    path("precios/<int:pk>/aceptar/", views.aceptar_precio_sugerido, name="aceptar_precio_sugerido"),
    path("pronostico/", views.pronostico_ventas, name="pronostico_ventas"),
    path("reportes/", views.reportes_financieros, name="reportes_financieros"),
    path("reportes/baja-rotacion/", views.baja_rotacion, name="baja_rotacion"),
]
