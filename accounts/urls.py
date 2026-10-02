from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import NuevaPasswordForm, RecuperarPasswordForm

app_name = "accounts"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("negocio/", views.datos_negocio, name="datos_negocio"),
    path("productos-iniciales/", views.productos_precargados, name="productos_precargados"),
    path("login/", views.TiendaLoginView.as_view(), name="login"),
    path("logout/", views.TiendaLogoutView.as_view(), name="logout"),
    path("eliminar-cuenta/", views.eliminar_cuenta, name="eliminar_cuenta"),

    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html",
            email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
            form_class=RecuperarPasswordForm,
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/listo/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "password-reset/confirmar/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            form_class=NuevaPasswordForm,
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/completo/",
        auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
]
