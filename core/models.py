from django.db import models


class ModeloBase(models.Model):
    """Campos persistidos automaticamente para las entidades con historial.

    Al heredar de este modelo abstracto, Django agrega `creado_en` y
    `actualizado_en` a la tabla concreta. La clase abstracta no crea su propia
    tabla; cada modelo hijo almacena ambos campos en su tabla.
    """

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
