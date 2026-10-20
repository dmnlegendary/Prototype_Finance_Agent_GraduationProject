from datetime import date

from django import forms
from django.utils import timezone

from .models import CategoriaGasto, GastoOperativo, mes_actual


def _mes_siguiente(primer_dia):
    if primer_dia.month == 12:
        return date(primer_dia.year + 1, 1, 1)
    return date(primer_dia.year, primer_dia.month + 1, 1)


class MesInput(forms.DateInput):
    """Selector de mes del navegador. Escribe el valor como AAAA-MM sin depender del sistema operativo."""
    input_type = "month"

    def format_value(self, value):
        if isinstance(value, date):
            return f"{value.year:04d}-{value.month:02d}"
        return value


class GastoOperativoForm(forms.ModelForm):
    # el mes se escoge con un selector de mes (AAAA-MM); se guarda el primer día de ese mes
    periodo = forms.DateField(
        label="Mes al que corresponde",
        required=False,
        input_formats=["%Y-%m"],
        widget=MesInput(),
        help_text="Por ejemplo, la luz de septiembre que pagas en octubre.",
    )

    class Meta:
        model = GastoOperativo
        fields = ["tipo", "categoria", "concepto", "monto", "periodo", "nota"]
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
        self.fields["periodo"].initial = mes_actual()

    def clean_tipo(self):
        # la compra de mercancía no se captura a mano: se registra sola al agregar piezas al inventario
        tipo = self.cleaned_data["tipo"]
        if tipo == GastoOperativo.Tipo.MERCANCIA:
            raise forms.ValidationError("La compra de mercancía se registra sola al agregar piezas al inventario.")
        return tipo

    def clean_periodo(self):
        periodo = self.cleaned_data["periodo"]
        if not periodo:
            return mes_actual()  # si no se escoge mes, es el mes de hoy
        periodo = periodo.replace(day=1)
        # se puede capturar un mes pasado (la luz que apenas llegó), pero no meses lejanos hacia adelante
        if periodo > _mes_siguiente(timezone.localdate().replace(day=1)):
            raise forms.ValidationError("El mes no puede ser posterior al mes que viene.")
        if periodo.year < 2000:
            raise forms.ValidationError("Escribe un mes válido.")
        return periodo
