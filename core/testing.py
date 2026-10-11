"""Funciones de apoyo para las pruebas automáticas de todas las apps."""
from decimal import Decimal

from django.core.cache import cache

from accounts.models import Negocio, Usuario
from inventario.models import Producto

CLAVE = "clave12345"


def crear_negocio(telefono="5512345678", email="tendero@ejemplo.com", nombre_tienda="Abarrotes Prueba"):
    # el cache vive entre pruebas y los ids de negocio se repiten, así que se limpia
    cache.clear()
    usuario = Usuario.objects.create_user(
        username=telefono, password=CLAVE, email=email,
        telefono=telefono, nombre_completo="Tendero de Prueba",
    )
    negocio = Negocio.objects.create(
        usuario=usuario, nombre_tienda=nombre_tienda, alcaldia=Negocio.Alcaldia.IZTAPALAPA,
    )
    return usuario, negocio


def crear_producto(negocio, nombre="Coca 600", costo="15", precio="25", cantidad="10", minimo="2", ideal="0"):
    return Producto.objects.create(
        negocio=negocio, nombre=nombre, costo=Decimal(costo), precio_venta=Decimal(precio),
        cantidad_actual=Decimal(cantidad), cantidad_minima=Decimal(minimo), stock_ideal=Decimal(ideal),
    )
