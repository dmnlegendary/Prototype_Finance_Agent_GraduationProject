"""
Cache por negocio. Guarda en memoria los resultados que más se piden (alertas
de stock, ventas de hoy, catálogo para el asistente, resumen financiero) para
no volver a consultar la base de datos en cada mensaje o cada pantalla.

Cada vez que se guarda o se borra un producto, una venta o un gasto, las
señales de core/signals.py borran lo que ya no sirve de ese negocio.

Ojo: el cache por default (LocMemCache) vive dentro de cada proceso de Python.
Con un solo servidor de desarrollo funciona perfecto; si algún día se corren
varios procesos hay que cambiarlo en settings.CACHES (Redis, por ejemplo).
"""
from django.core.cache import cache
from django.utils import timezone

SEGUNDOS = 300  # 5 minutos como máximo, aunque nada lo invalide antes

NOMBRES = [
    "alertas_conteo",
    "catalogo",
    "ventas_hoy",
    "resumen_financiero",
    "punto_equilibrio",
    "contexto_ia",
]


def _clave(negocio_id, nombre):
    # la fecha va en la clave para que, al cambiar de día, nada de ayer se reuse
    return f"negocio_{negocio_id}_{nombre}_{timezone.localdate().isoformat()}"


def obtener(negocio, nombre, calcular, segundos=SEGUNDOS):
    """Regresa el valor guardado; si no hay, lo calcula con `calcular()` y lo guarda."""
    clave = _clave(negocio.pk, nombre)
    valor = cache.get(clave)
    if valor is None:
        valor = calcular()
        cache.set(clave, valor, segundos)
    return valor


def invalidar(negocio_id, *nombres):
    """Borra del cache lo indicado (o todo lo del negocio si no se indica nada)."""
    nombres = nombres or NOMBRES
    cache.delete_many([_clave(negocio_id, nombre) for nombre in nombres])
