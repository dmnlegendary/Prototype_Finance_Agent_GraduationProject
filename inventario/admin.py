from django.contrib import admin

from .models import Categoria, Producto, ProductoCatalogo, Proveedor


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "icono")
    search_fields = ("nombre",)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "negocio", "telefono", "correo")
    list_filter = ("categorias",)
    search_fields = ("nombre", "negocio__nombre_tienda")


@admin.register(ProductoCatalogo)
class ProductoCatalogoAdmin(admin.ModelAdmin):
    # TODO: aquí es donde el equipo cargará la base de artículos real
    # (manualmente o vía `loaddata` de un fixture) cuando exista.
    list_display = ("nombre", "categoria", "precio_sugerido")
    list_filter = ("categoria",)
    search_fields = ("nombre",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre", "negocio", "categoria", "costo", "precio_venta",
        "cantidad_actual", "cantidad_minima", "activo",
    )
    list_filter = ("negocio", "categoria", "activo")
    search_fields = ("nombre", "negocio__nombre_tienda")
