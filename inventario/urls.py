from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.panel, name="panel"),
    path("filas/", views.panel_filas, name="panel_filas"),
    path("productos/alta/", views.producto_alta, name="producto_alta"),
    path("categorias/alta/", views.categoria_alta, name="categoria_alta"),
    path("productos/<int:pk>/datos/", views.producto_datos, name="producto_datos"),
    path("productos/<int:pk>/editar/", views.producto_editar, name="producto_editar"),
    path("productos/<int:pk>/resurtir/", views.producto_resurtir, name="producto_resurtir"),
    path("productos/<int:pk>/eliminar/", views.producto_eliminar, name="producto_eliminar"),
    path("proveedores/", views.proveedores, name="proveedores"),
    path("proveedores/<int:pk>/editar/", views.proveedor_editar, name="proveedor_editar"),
    path("movimientos/", views.movimientos, name="movimientos"),
    path("movimientos/exportar/", views.movimientos_exportar, name="movimientos_exportar"),
    path("alertas/", views.alertas, name="alertas"),
    path("alertas/filas/", views.alertas_filas, name="alertas_filas"),
    path("buscar/", views.buscar_json, name="buscar_json"),
    path("importar/", views.importar, name="importar"),
    path("importar/revisar/", views.importar_revisar, name="importar_revisar"),
    path("importar/cancelar/", views.importar_cancelar, name="importar_cancelar"),
    path("importar/plantilla/", views.importar_plantilla, name="importar_plantilla"),
]
