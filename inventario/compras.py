"""
Entradas de mercancía. TODA pieza que se agrega al inventario (alta de un producto,
resurtir, importar un CSV, el asistente…) pasa por aquí, para que la compra quede
registrada como gasto de "Compra de mercancía" y así todo peso que sale se vea
reflejado en las finanzas.

Esa compra cuenta para el flujo de efectivo pero no para la utilidad (el costo de lo
vendido ya se resta al vender); ver finanzas/calculos.py.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from finanzas.models import GastoOperativo

from .models import HistorialModificacionProducto, MovimientoInventario
from .movimientos import registrar_movimiento

CENTAVOS = Decimal("0.01")
MILESIMAS = Decimal("0.001")


class CantidadInvalida(Exception):
    """La cantidad o el costo que se quiso agregar no sirve (negativo, texto, pieza con decimales…)."""


def a_decimal(valor, defecto=None):
    """Convierte lo que llegue (texto, número) a Decimal, o regresa `defecto` si no se puede."""
    if valor is None or str(valor).strip() == "":
        return defecto
    try:
        numero = Decimal(str(valor).replace("$", "").replace(",", "").strip())
    except InvalidOperation:
        return defecto
    return numero if numero.is_finite() else defecto


def validar_cantidad(producto, cantidad):
    """Regresa la cantidad lista para guardar (3 decimales), o lanza CantidadInvalida.
    Los productos por pieza solo aceptan números enteros; los de granel aceptan decimales (kilos)."""
    cantidad = a_decimal(cantidad)
    if cantidad is None or cantidad <= 0:
        raise CantidadInvalida("La cantidad tiene que ser un número mayor a cero.")
    cantidad = cantidad.quantize(MILESIMAS, rounding=ROUND_HALF_UP)
    if not producto.a_granel and cantidad != cantidad.to_integral_value():
        raise CantidadInvalida(f'"{producto.nombre}" se vende por pieza: la cantidad debe ser un número entero.')
    return cantidad


def mensaje_si_vende_bajo_el_costo(costo, precio):
    """Regla de negocio: nunca se vende por debajo de lo que costó. Regresa el aviso, o None si todo está bien."""
    costo, precio = a_decimal(costo), a_decimal(precio)
    if costo is None or precio is None or costo <= 0:
        return None
    if precio < costo:
        return f"El precio de venta (${precio:.2f}) no puede ser menor a lo que te cuesta (${costo:.2f}). Sube el precio de venta o revisa el costo."
    return None


def registrar_compra(negocio, concepto, monto):
    """Registra una compra de mercancía como gasto. Si el monto es 0 (todavía no se
    sabe cuánto costó) no se registra nada. Regresa el gasto o None."""
    monto = Decimal(monto).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    if monto <= 0:
        return None
    return GastoOperativo.objects.create(
        negocio=negocio, tipo=GastoOperativo.Tipo.MERCANCIA, concepto=concepto[:150], monto=monto,
    )


def agregar_existencias(producto, cantidad, costo=None, motivo="Compra de mercancía", registrar_gasto=True, usuario=None,
                        precio_venta=None):
    """Suma piezas (o kilos) a un producto y registra la compra.

    `costo` es el precio de compra de esta entrega; si se da, el producto se queda con
    ese costo (las ventas anteriores no cambian porque guardan su propio costo).
    `precio_venta` es el nuevo precio de venta, por si el costo subió y hay que subirlo también.
    Con registrar_gasto=False no se crea el gasto (quien llama lo registra, por ejemplo
    la importación de un CSV que junta todo en un solo gasto). Regresa el monto de la compra."""
    cantidad = validar_cantidad(producto, cantidad)
    costo = a_decimal(costo)
    if costo is not None and costo < 0:
        raise CantidadInvalida("El precio de compra no puede ser negativo.")

    precio_nuevo = a_decimal(precio_venta)
    if precio_nuevo is not None and precio_nuevo <= 0:
        raise CantidadInvalida("El precio de venta tiene que ser mayor a cero.")
    if costo is not None:
        # con el costo nuevo, el precio (el de ahora o el nuevo) no puede quedar por debajo
        aviso = mensaje_si_vende_bajo_el_costo(costo, precio_nuevo if precio_nuevo is not None else producto.precio_venta)
        if aviso:
            raise CantidadInvalida(aviso)
        producto.costo = costo.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    if precio_nuevo is not None:
        producto.precio_venta = precio_nuevo.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
    producto.cantidad_actual = producto.cantidad_actual + cantidad
    producto.save(update_fields=["cantidad_actual", "costo", "precio_venta", "actualizado_en"])

    HistorialModificacionProducto.objects.create(
        producto=producto, usuario=producto.negocio.usuario,
        motivo=f"{motivo}: +{texto_numero(cantidad)} {producto.unidad}"[:255],
    )
    registrar_movimiento(producto, cantidad, MovimientoInventario.Tipo.ENTRADA, motivo=motivo, usuario=usuario or producto.negocio.usuario)
    monto = cantidad * producto.costo
    if registrar_gasto:
        registrar_compra(producto.negocio, f"Compra de mercancía: {producto.nombre}", monto)
    return monto


def texto_numero(valor):
    """3.000 -> "3", 0.250 -> "0.25", 100 -> "100" (para mostrar cantidades sin ceros de sobra)."""
    return format(Decimal(valor).normalize(), "f")


def registrar_alta(producto, usuario=None):
    """El producto se dio de alta con piezas: entra al kardex y la compra queda en los gastos.
    Regresa el gasto (o None si todavía no se sabe cuánto costó)."""
    registrar_movimiento(
        producto, producto.cantidad_actual, MovimientoInventario.Tipo.ENTRADA, motivo="Alta del producto", usuario=usuario,
    )
    return registrar_compra(producto.negocio, f"Compra de mercancía: {producto.nombre}", producto.cantidad_actual * producto.costo)
