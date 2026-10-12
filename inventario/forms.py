from decimal import Decimal

from django import forms

from .models import Producto, Proveedor


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            "nombre", "descripcion", "costo", "precio_venta",
            "cantidad_actual", "cantidad_minima", "stock_ideal", "categoria", "proveedor",
            "a_granel", "codigo_barras",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Ej: Coca Cola 2lt"}),
            "descripcion": forms.Textarea(attrs={"rows": 3, "placeholder": "Descripción breve del producto…"}),
            "costo": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
            "precio_venta": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
            "cantidad_actual": forms.NumberInput(attrs={"step": "any", "placeholder": "0"}),
            "cantidad_minima": forms.NumberInput(attrs={"step": "any", "placeholder": "0"}),
            "stock_ideal": forms.NumberInput(attrs={"step": "any", "placeholder": "0"}),
            "categoria": forms.RadioSelect(),
            "codigo_barras": forms.TextInput(attrs={"placeholder": "Escanéalo con tu lector o escríbelo", "autocomplete": "off"}),
        }

    def __init__(self, *args, negocio=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.negocio = negocio
        if negocio is not None:
            self.fields["proveedor"].queryset = Proveedor.objects.filter(negocio=negocio)
        self.fields["proveedor"].required = False
        self.fields["categoria"].required = False
        self.fields["stock_ideal"].required = False
        self.fields["codigo_barras"].required = False

    def clean_stock_ideal(self):
        # si lo dejan vacío se toma como 0 (el sistema usa 4 veces el mínimo)
        return self.cleaned_data.get("stock_ideal") or Decimal("0")

    def clean_codigo_barras(self):
        codigo = (self.cleaned_data.get("codigo_barras") or "").strip()
        if codigo and self.negocio is not None:
            repetidos = Producto.objects.filter(negocio=self.negocio, codigo_barras=codigo)
            if self.instance.pk:
                repetidos = repetidos.exclude(pk=self.instance.pk)
            if repetidos.exists():
                raise forms.ValidationError(f"Ese código de barras ya lo tiene {repetidos.first().nombre}.")
        return codigo

    def clean(self):
        datos = super().clean()
        minima = datos.get("cantidad_minima")
        ideal = datos.get("stock_ideal")
        if minima is not None and ideal and ideal < minima:
            self.add_error("stock_ideal", "El stock ideal no puede ser menor que la cantidad mínima.")

        # los productos por pieza llevan cantidades enteras; solo los de granel aceptan decimales
        if not datos.get("a_granel"):
            for campo in ("cantidad_actual", "cantidad_minima", "stock_ideal"):
                valor = datos.get(campo)
                if valor is not None and Decimal(valor) != Decimal(valor).to_integral_value():
                    self.add_error(campo, "Este producto es por pieza: usa un número entero (o márcalo como a granel).")
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
