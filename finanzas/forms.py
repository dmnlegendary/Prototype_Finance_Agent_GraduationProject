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
    fecha_inicio = forms.DateField(
        label="Fecha de inicio",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="La primera fecha en que se cuenta el gasto; las siguientes se calculan con la periodicidad.",
    )
    intervalo_meses = forms.IntegerField(
        label="Cada cuántos meses",
        required=False,
        min_value=2,
        widget=forms.NumberInput(attrs={"min": "2", "step": "1", "placeholder": "Ej. 2"}),
        help_text="Por ejemplo, 2 para cada dos meses o 6 para cada seis meses.",
    )

    class Meta:
        model = GastoOperativo
        fields = [
            "tipo", "categoria", "concepto", "monto", "periodicidad", "intervalo_meses",
            "fecha_inicio", "periodo", "nota",
        ]
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
        self.fields["periodicidad"].required = False
        self.fields["intervalo_meses"].required = False
        self.fields["periodo"].initial = mes_actual()
        self.fields["fecha_inicio"].initial = timezone.localdate()

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

    def clean_periodicidad(self):
        return self.cleaned_data.get("periodicidad") or GastoOperativo.Periodicidad.UNA_VEZ

    def clean_fecha_inicio(self):
        fecha_inicio = self.cleaned_data.get("fecha_inicio")
        if fecha_inicio and fecha_inicio.year < 2000:
            raise forms.ValidationError("Escribe una fecha de inicio válida.")
        return fecha_inicio

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo")
        periodicidad = cleaned_data.get("periodicidad")
        intervalo_meses = cleaned_data.get("intervalo_meses")
        fecha_inicio = cleaned_data.get("fecha_inicio")

        if tipo != GastoOperativo.Tipo.FIJO:
            cleaned_data["periodicidad"] = GastoOperativo.Periodicidad.UNA_VEZ
            cleaned_data["intervalo_meses"] = 1
            cleaned_data["fecha_inicio"] = None
        elif periodicidad == GastoOperativo.Periodicidad.UNA_VEZ:
            cleaned_data["intervalo_meses"] = 1
            cleaned_data["fecha_inicio"] = None
        elif periodicidad == GastoOperativo.Periodicidad.CADA_MESES:
            if intervalo_meses is None:
                self.add_error("intervalo_meses", "Indica cada cuántos meses ocurre el gasto.")
            elif intervalo_meses < 2:
                self.add_error("intervalo_meses", "El intervalo debe ser de al menos 2 meses.")
            if not fecha_inicio:
                self.add_error("fecha_inicio", "Selecciona desde qué fecha comienza el gasto.")
        elif not fecha_inicio:
            cleaned_data["intervalo_meses"] = 1
            self.add_error("fecha_inicio", "Selecciona desde qué fecha comienza el gasto.")
        else:
            cleaned_data["intervalo_meses"] = 1
            cleaned_data["periodo"] = fecha_inicio.replace(day=1)

        if fecha_inicio and periodicidad not in (
            GastoOperativo.Periodicidad.UNA_VEZ,
            None,
        ):
            cleaned_data["periodo"] = fecha_inicio.replace(day=1)

        return cleaned_data
