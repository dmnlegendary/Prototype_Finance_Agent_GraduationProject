"""
`core` no representa una entidad de negocio propia: es la app de
utilidades compartidas por el resto del monolito (clases base, mixins,
helpers). Aquí solo vive un modelo abstracto reutilizable.
"""
from django.db import models


class ModeloBase(models.Model):
    """
    Clase base abstracta para timestamps de auditoría. Las apps de negocio
    (inventario, ventas, finanzas, ...) heredan de esta clase en lugar de
    repetir `creado_en` / `actualizado_en` en cada modelo.

    Al ser `abstract = True`, Django NO crea una tabla `core_modelobase`;
    los campos simplemente se agregan a cada modelo hijo.
    """

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
