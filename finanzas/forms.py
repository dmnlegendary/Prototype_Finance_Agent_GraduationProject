from django import forms

from .models import CategoriaGasto, GastoOperativo


class GastoOperativoForm(forms.ModelForm):
    class Meta:
        model = GastoOperativo
        fields = ["tipo", "categoria", "concepto", "monto", "nota"]
        widgets = {
            "tipo": forms.HiddenInput(),
            "categoria": forms.RadioSelect(),
            "concepto": forms.TextInput(attrs={"placeholder": "Ej. Renta, Luz…"}),
            "monto": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
            "nota": forms.TextInput(attrs={"placeholder": "Descripción breve (opcional)…"}),
        }

    def __init__(self, *args, negocio=None, **kwargs):
        super().__init__(*args, **kwargs)
        if negocio is not None:
            self.fields["categoria"].queryset = CategoriaGasto.objects.filter(negocio=negocio)
        self.fields["categoria"].required = False

    def clean_tipo(self):
        # la compra de mercancía no se captura a mano: se registra sola al agregar piezas al inventario
        tipo = self.cleaned_data["tipo"]
        if tipo == GastoOperativo.Tipo.MERCANCIA:
            raise forms.ValidationError("La compra de mercancía se registra sola al agregar piezas al inventario.")
        return tipo
