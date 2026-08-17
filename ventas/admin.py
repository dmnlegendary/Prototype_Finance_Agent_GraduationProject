from django.contrib import admin

from .models import ItemVenta, Venta


class ItemVentaInline(admin.TabularInline):
    model = ItemVenta
    extra = 0


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ("folio", "negocio", "cajero", "estado", "total", "creado_en")
    list_filter = ("negocio", "estado")
    inlines = [ItemVentaInline]
