from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Negocio, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # Se agregan los campos propios del negocio a la vista de administración
    # de usuarios, además de los que ya trae UserAdmin por defecto.
    fieldsets = UserAdmin.fieldsets + (
        ("Datos de la tienda", {"fields": ("nombre_completo", "telefono")}),
    )
    list_display = ("username", "nombre_completo", "telefono", "email", "is_staff")
    search_fields = ("username", "nombre_completo", "telefono", "email")


@admin.register(Negocio)
class NegocioAdmin(admin.ModelAdmin):
    list_display = ("nombre_tienda", "usuario", "alcaldia", "regimen_resico")
    list_filter = ("alcaldia", "regimen_resico", "anios_operacion")
    search_fields = ("nombre_tienda", "usuario__username", "usuario__nombre_completo")
