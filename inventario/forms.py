from django import forms

from .models import Producto, Proveedor


class ProductoForm(forms.ModelForm):
    """Valida campos de Producto antes de crear o actualizar su fila."""

    class Meta:
        model = Producto
        fields = [
            "nombre", "descripcion", "costo", "precio_venta",
            "cantidad_actual", "cantidad_minima", "categoria", "proveedor",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej: Coca Cola 2lt"}),
            "descripcion": forms.Textarea(attrs={"rows": 3, "placeholder": "Descripción breve del producto…"}),
            "costo": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
            "precio_venta": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
            "cantidad_actual": forms.NumberInput(attrs={"step": "1", "placeholder": "0"}),
            "cantidad_minima": forms.NumberInput(attrs={"step": "1", "placeholder": "0"}),
            "categoria": forms.RadioSelect(),
        }

    def __init__(self, *args, negocio=None, **kwargs):
        """Limita las opciones de proveedor a la tienda que edita el producto."""
        super().__init__(*args, **kwargs)
        if negocio is not None:
            self.fields["proveedor"].queryset = Proveedor.objects.filter(negocio=negocio)
        self.fields["proveedor"].required = False
        self.fields["categoria"].required = False


class ProveedorForm(forms.ModelForm):
    """Valida datos del proveedor; sus categorias se guardan como relacion M2M."""

    class Meta:
        model = Proveedor
        fields = ["nombre", "telefono", "correo", "categorias"]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej: FEMSA / Coca-Cola FEMSA"}),
            "telefono": forms.TextInput(attrs={"placeholder": "55 1234-5678"}),
            "correo": forms.EmailInput(attrs={"placeholder": "ventas@proveedor.com"}),
            "categorias": forms.CheckboxSelectMultiple,
        }
