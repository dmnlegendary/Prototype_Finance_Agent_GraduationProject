from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
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
        label="Correo electrónico", required=True,
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

    def clean_email(self):
        email = self.cleaned_data["email"]
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email

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
        fields = ["nombre_tienda", "alcaldia", "alcaldia_otra", "anios_operacion", "regimen_resico", "rfc"]
        widgets = {
            "nombre_tienda": forms.TextInput(attrs={"placeholder": "Ej. Abarrotes Don Raúl", "class": INPUT_CLASSES}),
            "alcaldia": forms.Select(attrs={"class": SELECT_CLASSES}),
            "alcaldia_otra": forms.TextInput(attrs={"placeholder": "Ej. Naucalpan, Estado de México", "class": INPUT_CLASSES}),
            "anios_operacion": forms.Select(attrs={"class": SELECT_CLASSES}),
            "regimen_resico": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "rfc": forms.TextInput(attrs={"placeholder": "MARL850312AB3", "class": INPUT_CLASSES}),
        }

    def clean(self):
        datos = super().clean()
        if datos.get("alcaldia") == Negocio.Alcaldia.OTRA:
            if not (datos.get("alcaldia_otra") or "").strip():
                self.add_error("alcaldia_otra", "Escribe el nombre del lugar donde está tu tienda.")
        else:
            datos["alcaldia_otra"] = ""
        return datos


class RecuperarPasswordForm(PasswordResetForm):
    """Mismo PasswordResetForm de Django, solo con el estilo del proyecto."""

    email = forms.EmailField(
        label="Correo electrónico", max_length=254,
        widget=forms.EmailInput(attrs={"placeholder": "correo@ejemplo.com", "class": INPUT_CLASSES, "autofocus": True}),
    )


class NuevaPasswordForm(SetPasswordForm):
    """Mismo SetPasswordForm de Django, solo con el estilo del proyecto."""

    new_password1 = forms.CharField(
        label="Contraseña nueva",
        widget=forms.PasswordInput(attrs={"placeholder": "Mínimo 6 caracteres", "class": INPUT_CLASSES, "autofocus": True}),
    )
    new_password2 = forms.CharField(
        label="Confirma la contraseña nueva",
        widget=forms.PasswordInput(attrs={"placeholder": "Repite la contraseña", "class": INPUT_CLASSES}),
    )


class EliminarCuentaForm(forms.Form):
    """Pide la contraseña de nuevo antes de borrar la cuenta por completo."""

    password = forms.CharField(
        label="Confirma tu contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Tu contraseña actual", "class": INPUT_CLASSES, "autofocus": True}),
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.usuario.check_password(password):
            raise forms.ValidationError("La contraseña no es correcta.")
        return password


class LoginForm(AuthenticationForm):
    """Login, con el mismo estilo que el resto del registro."""

    username = forms.CharField(
        label="Correo o teléfono",
        widget=forms.TextInput(attrs={"placeholder": "correo@ejemplo.com o 55 1234 5678", "class": INPUT_CLASSES, "autofocus": True}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Tu contraseña", "class": INPUT_CLASSES}),
    )
