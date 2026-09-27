from django import forms

from .models import GastoOperativo


class GastoOperativoForm(forms.ModelForm):
    class Meta:
        model = GastoOperativo
        fields = ["tipo", "concepto", "monto", "nota"]
        widgets = {
            "tipo": forms.HiddenInput(),
            "concepto": forms.TextInput(attrs={"placeholder": "Ej. Renta, Luz…"}),
            "monto": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
            "nota": forms.TextInput(attrs={"placeholder": "Descripción breve (opcional)…"}),
        }
