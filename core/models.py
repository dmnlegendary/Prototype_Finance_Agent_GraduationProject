from django.db import models


class ModeloBase(models.Model):
    """Campos de fecha que comparten casi todos los modelos del proyecto."""

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
