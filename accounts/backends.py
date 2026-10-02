from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

Usuario = get_user_model()


class TelefonoOCorreoBackend(ModelBackend):
    """Permite iniciar sesión con el teléfono (username) o con el correo."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        candidatos = Usuario.objects.filter(Q(username=username) | Q(email__iexact=username))
        usuario = candidatos.order_by("pk").first()
        if usuario is None:
            return None

        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
