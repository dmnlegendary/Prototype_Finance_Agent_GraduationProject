from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .models import Negocio, Usuario

INPUT_CLASSES = "form-control"
SELECT_CLASSES = "form-select"


class RegistroForm(forms.ModelForm):
    """Paso 1 del registro: crear la cuenta."""

    nombre_completo = forms.CharField(
        label="Nombre completo", max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "Ej. Raúl Martínez López", "class": INPUT_CLASSES}),
    )
    telefono = forms.CharField(
        label="Teléfono celular", max_length=20,
        widget=forms.TextInput(attrs={"placeholder": "55 1234 5678", "class": INPUT_CLASSES}),
    )
    email = forms.EmailField(
        label="Correo electrónico", required=False,
        widget=forms.EmailInput(attrs={"placeholder": "correo@ejemplo.com", "class": INPUT_CLASSES}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Mínimo 6 caracteres", "class": INPUT_CLASSES}),
    )

    class Meta:
        model = Usuario
        fields = ("nombre_completo", "telefono", "email")

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

    def clean_telefono(self):
        telefono = self.cleaned_data["telefono"]
        if Usuario.objects.filter(telefono=telefono).exists():
            raise forms.ValidationError("Ya existe una cuenta con este teléfono.")
        return telefono

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.nombre_completo = self.cleaned_data["nombre_completo"]
        usuario.telefono = self.cleaned_data["telefono"]
        usuario.email = self.cleaned_data.get("email", "")
        # se usa el teléfono como username mientras no se decida el login por teléfono
        usuario.username = self.cleaned_data["telefono"]
        usuario.set_password(self.cleaned_data["password"])
        if commit:
            usuario.save()
        return usuario


class NegocioForm(forms.ModelForm):
    """Paso 2 del registro: datos de la tienda."""

    class Meta:
        model = Negocio
        fields = ["nombre_tienda", "alcaldia", "anios_operacion", "regimen_resico", "rfc"]
        widgets = {
            "nombre_tienda": forms.TextInput(attrs={"placeholder": "Ej. Abarrotes Don Raúl", "class": INPUT_CLASSES}),
            "alcaldia": forms.Select(attrs={"class": SELECT_CLASSES}),
            "anios_operacion": forms.Select(attrs={"class": SELECT_CLASSES}),
            "regimen_resico": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "rfc": forms.TextInput(attrs={"placeholder": "MARL850312AB3", "class": INPUT_CLASSES}),
        }


class LoginForm(AuthenticationForm):
    """Login, con el mismo estilo que el resto del registro."""

    username = forms.CharField(
        label="Teléfono / usuario",
        widget=forms.TextInput(attrs={"placeholder": "55 1234 5678", "class": INPUT_CLASSES, "autofocus": True}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Tu contraseña", "class": INPUT_CLASSES}),
    )
