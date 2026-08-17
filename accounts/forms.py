"""
Formularios de la app `accounts`. Se usan Django Forms/ModelForms "puros"
(sin django-crispy-forms) porque el diseño visual de los inputs ya viene
maquetado a mano con Tailwind en los HTML originales: en las plantillas se
renderiza cada campo manualmente (`{{ form.campo }}`) dentro del markup
existente, en vez de dejar que Django dibuje el `<input>` completo, para no
perder las clases de Tailwind ni los íconos de Font Awesome del mockup.
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from .models import Negocio, Usuario

# Clases de Tailwind reutilizadas TAL CUAL como estaban en los <input> de
# los HTML originales, para que los campos de Django se vean idénticos al
# mockup una vez renderizados con {{ form.campo }}.
INPUT_CLASSES = "input-field w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm outline-none transition bg-gray-50"
PASSWORD_INPUT_CLASSES = "input-field w-full pl-9 pr-10 py-2.5 border border-gray-200 rounded-xl text-sm outline-none transition bg-gray-50"
SELECT_CLASSES = "input-field w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm outline-none transition bg-gray-50 appearance-none"
RFC_INPUT_CLASSES = "w-full px-3 py-2 border border-indigo-200 rounded-lg text-xs outline-none bg-white focus:border-indigo-400"


class RegistroForm(forms.ModelForm):
    """
    Paso 1 del onboarding: registro.html ("Crea tu cuenta").

    OJO: NO se hereda de `UserCreationForm` a propósito. UserCreationForm
    de Django pide 2 campos de contraseña (confirmación), pero
    registro.html solo maqueta UN input de contraseña ("Mínimo 6
    caracteres"). Para no alterar el diseño (restricción del proyecto) se
    usa un solo campo de contraseña, validado con las mismas reglas de
    Django (`validate_password`, ver AUTH_PASSWORD_VALIDATORS en settings).
    TODO: si el equipo prefiere pedir confirmación de contraseña, hay que
    actualizar el mockup para agregar un segundo input.
    """

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
        widget=forms.PasswordInput(attrs={"placeholder": "Mínimo 6 caracteres", "class": PASSWORD_INPUT_CLASSES}),
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
        # TODO: mientras no se defina login por teléfono (ver models.py),
        # se usa el teléfono también como `username` para no pedirle al
        # dueño un dato adicional que el mockup no contempla.
        usuario.username = self.cleaned_data["telefono"]
        usuario.set_password(self.cleaned_data["password"])
        if commit:
            usuario.save()
        return usuario


class NegocioForm(forms.ModelForm):
    """Paso 2 del onboarding: datos_negocio.html ("Cuéntanos de tu tienda")."""

    class Meta:
        model = Negocio
        fields = ["nombre_tienda", "alcaldia", "anios_operacion", "regimen_resico", "rfc"]
        widgets = {
            "nombre_tienda": forms.TextInput(attrs={"placeholder": "Ej. Abarrotes Don Raúl", "class": INPUT_CLASSES}),
            "alcaldia": forms.Select(attrs={"class": SELECT_CLASSES}),
            "anios_operacion": forms.Select(attrs={"class": SELECT_CLASSES}),
            "regimen_resico": forms.CheckboxInput(),
            "rfc": forms.TextInput(attrs={"placeholder": "MARL850312AB3", "class": RFC_INPUT_CLASSES}),
        }


class LoginForm(AuthenticationForm):
    """
    Login con el mismo lenguaje visual del resto del onboarding. No hay un
    mockup de login provisto (ver templates/accounts/login.html), así que
    solo se restilizan los campos que Django ya trae en AuthenticationForm.
    """

    username = forms.CharField(
        label="Teléfono / usuario",
        widget=forms.TextInput(attrs={"placeholder": "55 1234 5678", "class": INPUT_CLASSES, "autofocus": True}),
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"placeholder": "Tu contraseña", "class": INPUT_CLASSES}),
    )
