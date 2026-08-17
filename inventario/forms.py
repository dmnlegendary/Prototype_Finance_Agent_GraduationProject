"""
Formularios de `inventario`. A diferencia de `accounts`, aquí ya no hace
falta reusar clases de Tailwind (inventario.html usa CSS propio con
selectores por tipo de elemento, ej. `.form-group input`), así que los
widgets casi no necesitan `attrs` extra.
"""
from django import forms

from .models import Producto, Proveedor


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "nombre", "descripcion", "icono", "costo", "precio_venta",
            "cantidad_actual", "cantidad_minima", "categoria", "proveedor",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej: Coca Cola 2lt"}),
            "descripcion": forms.Textarea(attrs={"rows": 3, "placeholder": "Descripción breve del producto…"}),
            "icono": forms.TextInput(attrs={"placeholder": "📦 (emoji opcional)"}),
            "costo": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
            "precio_venta": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
            "cantidad_actual": forms.NumberInput(attrs={"step": "1", "placeholder": "0"}),
            "cantidad_minima": forms.NumberInput(attrs={"step": "1", "placeholder": "0"}),
        }

    def __init__(self, *args, negocio=None, **kwargs):
        super().__init__(*args, **kwargs)
        # El proveedor a elegir solo debe listar los proveedores de ESTE
        # negocio, no los de todas las tiendas del sistema.
        if negocio is not None:
            self.fields["proveedor"].queryset = Proveedor.objects.filter(negocio=negocio)
        self.fields["proveedor"].required = False
        self.fields["categoria"].required = False


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ["nombre", "telefono", "correo", "categorias"]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej: FEMSA / Coca-Cola FEMSA"}),
            "telefono": forms.TextInput(attrs={"placeholder": "55 1234-5678"}),
            "correo": forms.EmailInput(attrs={"placeholder": "ventas@proveedor.com"}),
            "categorias": forms.CheckboxSelectMultiple,
        }
