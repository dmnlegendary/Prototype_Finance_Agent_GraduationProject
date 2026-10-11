from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Núcleo / utilidades compartidas"

    def ready(self):
        # se importa aquí para que Django registre las señales del cache
        from . import signals  # noqa: F401
