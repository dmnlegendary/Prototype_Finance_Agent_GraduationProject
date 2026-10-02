from django.contrib import admin

from .models import CategoriaGasto, GastoOperativo


@admin.register(CategoriaGasto)
class CategoriaGastoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "negocio")
    list_filter = ("negocio",)


@admin.register(GastoOperativo)
class GastoOperativoAdmin(admin.ModelAdmin):
    list_display = ("concepto", "negocio", "categoria", "tipo", "monto", "fecha")
    list_filter = ("negocio", "tipo", "categoria")
