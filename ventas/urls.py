from django.urls import path

from . import views

app_name = "ventas"

urlpatterns = [
    path("", views.punto_de_venta, name="punto_de_venta"),
    path("buscar/", views.buscar_productos_json, name="buscar_productos_json"),
    path("carrito/agregar/<int:producto_pk>/", views.agregar_item, name="agregar_item"),
    path("carrito/agregar-no-encontrado/", views.agregar_no_encontrado, name="agregar_no_encontrado"),
    path("carrito/item/<int:item_pk>/mas/", views.item_incrementar, name="item_incrementar"),
    path("carrito/item/<int:item_pk>/menos/", views.item_decrementar, name="item_decrementar"),
    path("cobrar/", views.cobrar, name="cobrar"),
    path("cancelar/", views.cancelar_venta, name="cancelar_venta"),
    path("ticket/<int:pk>/", views.ticket, name="ticket"),
]
