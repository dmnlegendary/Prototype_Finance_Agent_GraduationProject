"""
Cuando cambia un producto, una venta o un gasto, se borra el cache de ese
negocio (ver cache_negocio.py) para que el asistente y las alertas nunca
contesten con datos viejos.

Nota: bulk_create y los update() masivos NO disparan estas señales. Quien los
use (por ejemplo el comando importar_csv) debe llamar a cache_negocio.invalidar().
"""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from finanzas.models import GastoOperativo
from inventario.models import Producto
from ventas.models import Venta

from . import cache_negocio


@receiver([post_save, post_delete], sender=Producto)
def producto_cambio(sender, instance, **kwargs):
    cache_negocio.invalidar(instance.negocio_id)


@receiver([post_save, post_delete], sender=Venta)
def venta_cambio(sender, instance, **kwargs):
    # la caja siempre termina con venta.recalcular_total(), que guarda la
    # venta, así que con escuchar a Venta también se cubren los ItemVenta
    cache_negocio.invalidar(instance.negocio_id)


@receiver([post_save, post_delete], sender=GastoOperativo)
def gasto_cambio(sender, instance, **kwargs):
    cache_negocio.invalidar(instance.negocio_id)
