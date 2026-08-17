from django.contrib import admin

from .models import GastoOperativo


@admin.register(GastoOperativo)
class GastoOperativoAdmin(admin.ModelAdmin):
    list_display = ("concepto", "negocio", "tipo", "monto", "fecha")
    list_filter = ("negocio", "tipo")
