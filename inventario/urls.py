from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("productos/alta/", views.producto_alta, name="producto_alta"),
    path("productos/<int:pk>/editar/", views.producto_editar, name="producto_editar"),
    path("productos/<int:pk>/eliminar/", views.producto_eliminar, name="producto_eliminar"),
    path("proveedores/", views.proveedores, name="proveedores"),
    path("proveedores/<int:pk>/editar/", views.proveedor_editar, name="proveedor_editar"),
    path("alertas/", views.alertas, name="alertas"),
]
