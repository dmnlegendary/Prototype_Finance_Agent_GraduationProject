from django.urls import path

from . import views

app_name = "ventas"

urlpatterns = [
    path("", views.punto_de_venta, name="punto_de_venta"),
    path("buscar/", views.buscar_productos_json, name="buscar_productos_json"),
    path("api/codigo/", views.api_codigo, name="api_codigo"),
    path("api/catalogo/", views.api_catalogo, name="api_catalogo"),
    path("api/carrito/<int:numero>/", views.api_carrito, name="api_carrito"),
    path("api/carrito/<int:numero>/agregar/", views.api_agregar, name="api_agregar"),
    path("api/carrito/<int:numero>/cobrar/", views.api_cobrar, name="api_cobrar"),
    path("api/carrito/<int:numero>/cancelar/", views.api_cancelar, name="api_cancelar"),
    path("api/carrito/<int:numero>/no-encontrado/", views.api_no_encontrado, name="api_no_encontrado"),
    path("api/item/<int:pk>/cantidad/", views.api_cantidad, name="api_cantidad"),
    path("api/item/<int:pk>/quitar/", views.api_quitar, name="api_quitar"),
    path("historial/", views.historial, name="historial"),
    path("ticket/<int:pk>/", views.ticket, name="ticket"),
]
