from django import forms

from .models import Producto, Proveedor


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "nombre", "descripcion", "costo", "precio_venta",
            "cantidad_actual", "cantidad_minima", "stock_ideal", "categoria", "proveedor",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej: Coca Cola 2lt"}),
            "descripcion": forms.Textarea(attrs={"rows": 3, "placeholder": "Descripción breve del producto…"}),
            "costo": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
            "precio_venta": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
            "cantidad_actual": forms.NumberInput(attrs={"step": "1", "placeholder": "0"}),
            "cantidad_minima": forms.NumberInput(attrs={"step": "1", "placeholder": "0"}),
            "stock_ideal": forms.NumberInput(attrs={"step": "1", "placeholder": "0"}),
            "categoria": forms.RadioSelect(),
        }

    def __init__(self, *args, negocio=None, **kwargs):
        super().__init__(*args, **kwargs)
        if negocio is not None:
            self.fields["proveedor"].queryset = Proveedor.objects.filter(negocio=negocio)
        self.fields["proveedor"].required = False
        self.fields["categoria"].required = False
        self.fields["stock_ideal"].required = False

    def clean_stock_ideal(self):
        # si lo dejan vacío se toma como 0 (el sistema usa 4 veces el mínimo)
        return self.cleaned_data.get("stock_ideal") or 0

    def clean(self):
        datos = super().clean()
        minima = datos.get("cantidad_minima")
        ideal = datos.get("stock_ideal")
        if minima is not None and ideal and ideal < minima:
            self.add_error("stock_ideal", "El stock ideal no puede ser menor que la cantidad mínima.")
        return datos


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
