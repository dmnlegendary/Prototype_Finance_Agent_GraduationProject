from django.urls import path

from . import views

app_name = "ventas"

urlpatterns = [
    path("", views.punto_de_venta, name="punto_de_venta"),
    path("carrito/agregar/<int:producto_pk>/", views.agregar_item, name="agregar_item"),
    path("carrito/item/<int:item_pk>/mas/", views.item_incrementar, name="item_incrementar"),
    path("carrito/item/<int:item_pk>/menos/", views.item_decrementar, name="item_decrementar"),
    path("cobrar/", views.cobrar, name="cobrar"),
    path("cancelar/", views.cancelar_venta, name="cancelar_venta"),
    path("ticket/<int:pk>/", views.ticket, name="ticket"),
]
