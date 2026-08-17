from django.urls import path

from . import views

app_name = "ventas"

urlpatterns = [
    path("", views.punto_de_venta, name="punto_de_venta"),
    # TODO: path("carrito/agregar/", views.agregar_al_carrito, name="agregar_al_carrito")
    # TODO: path("cobrar/", views.cobrar, name="cobrar")
]
