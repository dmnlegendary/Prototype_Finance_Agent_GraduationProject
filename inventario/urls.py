from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.panel, name="panel"),
    # TODO: path("productos/alta/", views.producto_alta, name="producto_alta")
    # TODO: path("productos/<int:pk>/editar/", views.producto_editar, name="producto_editar")
    # TODO: path("proveedores/", views.proveedores, name="proveedores")
    # TODO: path("alertas/", views.alertas, name="alertas")
]
