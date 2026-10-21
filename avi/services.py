"""
Funciones que el AVI puede ejecutar (function calling) y sus "herramientas"
en el formato que espera cada proveedor de LLM.

Regla del proyecto: todo lo que el tendero puede hacer a mano en el sistema
también lo puede pedir por el chat. Para agregar una función nueva:
  1. escríbela aquí (el primer parámetro siempre es `negocio`)
  2. descríbela en la lista FUNCIONES (nombre, descripción, parámetros)
  3. regístrala en DESPACHADOR
  4. si modifica datos, agrégala al conjunto ACCIONES
"""
from contextvars import ContextVar
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Count, Sum
from django.utils import timezone

from core import cache_negocio
from finanzas import calculos
from finanzas.models import CategoriaGasto, GastoOperativo
from inventario.alertas import conteo_alertas, productos_con_alerta
from inventario.models import MINIMO_POR_DEFECTO, Categoria, HistorialModificacionProducto, MovimientoInventario, Producto, Proveedor
from inventario.movimientos import registrar_movimiento
from inventario import busqueda
from inventario.compras import (
    CantidadInvalida, agregar_existencias, mensaje_si_vende_bajo_el_costo, registrar_alta, texto_numero,
)
from inventario.datos_base import icono_para
from ventas import carrito
from ventas.cobro import SinExistencias, VentaYaCobrada, cobrar_venta, texto_aviso_stock
from ventas.models import MAXIMO_DE_CARRITOS, ItemVenta, Venta

from .models import HistorialConversacion

CENTAVOS = Decimal("0.01")

# cuánto tiempo se queda guardada la conversación con el asistente
HORAS_DE_HISTORIAL = 24

# Las funciones que MODIFICAN datos. Sirven para dos cosas:
#  - si el asistente solo ejecutó acciones, se contesta con el mensaje de la
#    propia función y se ahorra la segunda llamada a la IA (respuesta casi instantánea)
#  - avisarle a la pantalla que se refresque para mostrar el cambio
ACCIONES = {
    "agregar_al_carrito", "quitar_del_carrito", "cambiar_cantidad_carrito",
    "cobrar_carrito", "cancelar_venta", "agregar_producto_no_encontrado",
    "dar_de_alta_producto", "modificar_producto", "ajustar_existencias",
    "dar_de_baja_producto", "crear_categoria", "alta_proveedor", "modificar_proveedor",
    "registrar_gasto",
}
FUNCIONES_QUE_CAMBIAN_LA_VISTA = ACCIONES


# ------------------------------------------------ descripción para la IA

def _texto(descripcion):
    return {"type": "string", "description": descripcion}


def _numero(descripcion):
    return {"type": "number", "description": descripcion}


def _funcion(nombre, descripcion, propiedades=None, requeridos=None):
    parametros = {"type": "object", "properties": propiedades or {}}
    if requeridos:
        parametros["required"] = requeridos
    return {"name": nombre, "description": descripcion, "parameters": parametros}


FUNCIONES = [
    # ---- ventas
    _funcion(
        "buscar_producto",
        "Busca productos del inventario por nombre (o parte del nombre, como 'agua' o 'leche') y regresa "
        "cuántos encontró, su precio y cuántas piezas quedan de cada uno. Sirve para contar o listar "
        "productos parecidos.",
        {"nombre": _texto("Nombre o parte del nombre del producto")},
        ["nombre"],
    ),
    _funcion(
        "agregar_al_carrito",
        "Agrega un producto a la caja (el usuario también puede decirle carrito) de la venta que está en curso. En productos a granel la cantidad va "
        "en kilos (250 gramos = 0.25). Si no alcanzan las existencias regresa sin_existencias: entonces "
        "pregunta cuánto quiere agregar al inventario y a qué precio de compra, usa ajustar_existencias "
        "(modo sumar) y vuelve a agregar a la caja.",
        {
            "nombre_producto": _texto("Nombre del producto a agregar"),
            "cantidad": _numero("Cantidad a agregar, por default 1"),
        },
        ["nombre_producto"],
    ),
    _funcion(
        "quitar_del_carrito",
        "Quita un producto de la caja por completo.",
        {"nombre_producto": _texto("Nombre del producto que está en la caja")},
        ["nombre_producto"],
    ),
    _funcion(
        "cambiar_cantidad_carrito",
        "Cambia la cantidad de un producto que ya está en la caja (la deja en ese número exacto).",
        {
            "nombre_producto": _texto("Nombre del producto que está en la caja"),
            "cantidad": _numero("Nueva cantidad total de ese producto"),
        },
        ["nombre_producto", "cantidad"],
    ),
    _funcion("ver_carrito", "Regresa los productos que hay en la caja y el total a cobrar."),
    _funcion(
        "cobrar_carrito",
        "Cobra la venta en curso: descuenta el inventario y genera el ticket. "
        "Úsala cuando pidan cobrar, cerrar la venta o terminar la cuenta.",
    ),
    _funcion(
        "cancelar_venta",
        "Cancela la venta en curso y vacía la caja. Antes de usarla con confirmar=true "
        "hay que preguntarle al usuario si está seguro.",
        {"confirmar": {"type": "boolean", "description": "true solo si el usuario ya confirmó que sí quiere cancelar"}},
    ),
    _funcion(
        "agregar_producto_no_encontrado",
        "Agrega a la caja un producto que no existe en el inventario, solo con nombre y precio, "
        "para poder cobrarlo. Se deja pendiente de validar en el inventario.",
        {
            "nombre": _texto("Nombre del producto"),
            "precio": _numero("Precio de venta en pesos"),
        },
        ["nombre", "precio"],
    ),
    _funcion("consultar_ventas_hoy", "Regresa el total vendido y el número de ventas cobradas el día de hoy."),
    _funcion(
        "ultimas_ventas",
        "Regresa las últimas ventas cobradas (folio, hora y total).",
        {"cantidad": _numero("Cuántas ventas regresar, por default 5")},
    ),
    # ---- inventario
    _funcion(
        "consultar_alertas_stock",
        "Regresa los productos que hay que resurtir, con su color: rojo (llegó al mínimo), "
        "naranja (queda un cuarto del stock ideal) o amarillo (va a la mitad).",
    ),
    _funcion(
        "dar_de_alta_producto",
        "Da de alta un producto nuevo en el inventario.",
        {
            "nombre": _texto("Nombre del producto"),
            "precio_venta": _numero("Precio de venta en pesos"),
            "costo": _numero("Lo que le cuesta al tendero cada pieza (o cada kilo), en pesos"),
            "cantidad_actual": _numero("Piezas que hay ahorita (kilos si es a granel), por default 0"),
            "cantidad_minima": _numero("Piezas mínimas antes de resurtir, por default 5"),
            "stock_ideal": _numero("Piezas que tiene cuando resurte completo, por default 0"),
            "categoria": _texto("Nombre de una categoría que ya exista (obligatoria; si el usuario no la dijo, pregúntasela)"),
            "a_granel": {"type": "boolean", "description": "true si se vende por peso (el precio y las cantidades son por kilo)"},
            "codigo_barras": _texto("Código de barras (opcional)"),
        },
        ["nombre", "precio_venta", "costo", "categoria"],
    ),
    _funcion(
        "modificar_producto",
        "Cambia datos de un producto que ya existe (precio, costo, nombre, mínimo, stock ideal o categoría). "
        "Para cambiar las existencias usa ajustar_existencias.",
        {
            "nombre_producto": _texto("Nombre actual del producto"),
            "nuevo_nombre": _texto("Nuevo nombre (opcional)"),
            "precio_venta": _numero("Nuevo precio de venta (opcional)"),
            "costo": _numero("Nuevo costo (opcional)"),
            "cantidad_minima": _numero("Nueva cantidad mínima (opcional)"),
            "stock_ideal": _numero("Nuevo stock ideal (opcional)"),
            "categoria": _texto("Nombre de la nueva categoría (opcional)"),
            "motivo": _texto("Por qué se hace el cambio, con las palabras del usuario (opcional)"),
        },
        ["nombre_producto"],
    ),
    _funcion(
        "ajustar_existencias",
        "Cambia las piezas que hay de un producto: sumar (llegó mercancía; se registra como compra), restar "
        "(merma, se rompió) o establecer (después de contar el inventario). En productos a granel la "
        "cantidad va en kilos (250 gramos = 0.25).",
        {
            "nombre_producto": _texto("Nombre del producto"),
            "cantidad": _numero("Número de piezas (kilos si es a granel)"),
            "costo": _numero("Precio de compra de cada pieza (o kilo) de esta entrega, solo al sumar (opcional)"),
            "modo": {"type": "string", "enum": ["sumar", "restar", "establecer"], "description": "Qué hacer con la cantidad"},
        },
        ["nombre_producto", "cantidad", "modo"],
    ),
    _funcion(
        "dar_de_baja_producto",
        "Da de baja un producto del catálogo (no se borra su historial de ventas). Antes de usarla "
        "con confirmar=true hay que preguntarle al usuario si está seguro.",
        {
            "nombre_producto": _texto("Nombre del producto"),
            "confirmar": {"type": "boolean", "description": "true solo si el usuario ya confirmó la baja"},
        },
        ["nombre_producto"],
    ),
    _funcion(
        "crear_categoria",
        "Crea una categoría de productos nueva.",
        {"nombre": _texto("Nombre de la categoría"), "icono": _texto("Un emoji (opcional)")},
        ["nombre"],
    ),
    _funcion(
        "alta_proveedor",
        "Registra un proveedor nuevo.",
        {
            "nombre": _texto("Nombre del proveedor"),
            "telefono": _texto("Teléfono (opcional)"),
            "correo": _texto("Correo (opcional)"),
        },
        ["nombre"],
    ),
    _funcion(
        "modificar_proveedor",
        "Cambia el nombre, teléfono o correo de un proveedor que ya está registrado.",
        {
            "nombre_proveedor": _texto("Nombre actual del proveedor"),
            "nuevo_nombre": _texto("Nuevo nombre (opcional)"),
            "telefono": _texto("Teléfono nuevo (opcional)"),
            "correo": _texto("Correo nuevo, con @ (si el usuario dice 'arroba' escríbelo como @) (opcional)"),
        },
        ["nombre_proveedor"],
    ),
    _funcion("consultar_proveedores", "Regresa la lista de proveedores registrados."),
    _funcion(
        "consultar_inventario",
        "Regresa cuántos productos hay en el inventario, cuántos por categoría y la lista de productos "
        "(hasta 30) con sus piezas. Úsala para preguntas como '¿qué productos tengo?'.",
        {"categoria": _texto("Nombre de una categoría para ver solo esos productos (opcional)")},
    ),
    # ---- finanzas
    _funcion(
        "registrar_gasto",
        "Registra un gasto operativo del negocio (fijo o variable).",
        {
            "concepto": _texto("Ej. Renta, Luz, Bolsas"),
            "monto": _numero("Monto del gasto en pesos"),
            "tipo": {"type": "string", "enum": ["FIJO", "VARIABLE"], "description": "Tipo de gasto"},
            "categoria": _texto("Categoría del gasto, como Luz o Internet (opcional)"),
            "mes": _numero("Número del mes al que corresponde el gasto, de 1 a 12 (opcional; por default el mes actual)"),
            "anio": _numero("Año del mes al que corresponde el gasto (opcional; por default el año actual)"),
        },
        ["concepto", "monto", "tipo"],
    ),
    _funcion(
        "consultar_gastos_mes",
        "Regresa cuánto se ha gastado en el mes (fijos y variables) y los últimos gastos registrados.",
    ),
    _funcion(
        "consultar_resumen_financiero",
        "Regresa las finanzas del mes en curso: ingresos, costo de ventas, gastos, flujo de "
        "efectivo, margen operativo (%), ISR RESICO y utilidad neta.",
    ),
    _funcion(
        "consultar_punto_equilibrio",
        "Regresa el punto de equilibrio mensual en pesos (la venta mínima para no perder dinero), "
        "por día y cuánto vender de cada categoría.",
    ),
    _funcion(
        "sugerir_precio",
        "Calcula a cuánto conviene vender un producto para ganar el margen que el usuario quiere.",
        {
            "nombre_producto": _texto("Nombre del producto"),
            "margen_deseado": _numero("Margen de ganancia deseado en porcentaje (si no lo dice, se usa el que ya tiene guardado el usuario o 30)"),
        },
        ["nombre_producto"],
    ),
]


# Para gastar menos en cada mensaje, a la IA solo se le mandan las herramientas de la pantalla
# en la que está el usuario (más unas pocas de consulta que sirven en todas).
# Las consultas (que no modifican nada) están disponibles en todas las pantallas, para poder preguntar por
# cualquier módulo desde donde se esté; las acciones que cambian datos solo vienen las de la pantalla actual.
HERRAMIENTAS_COMUNES = {funcion["name"] for funcion in FUNCIONES if funcion["name"] not in ACCIONES}
HERRAMIENTAS_POR_PANTALLA = {
    "ventas": {
        "agregar_al_carrito", "quitar_del_carrito", "cambiar_cantidad_carrito", "ver_carrito", "cobrar_carrito",
        "cancelar_venta", "agregar_producto_no_encontrado", "ultimas_ventas", "ajustar_existencias",
    },
    "inventario": {
        "consultar_inventario", "consultar_alertas_stock", "dar_de_alta_producto", "modificar_producto",
        "ajustar_existencias", "dar_de_baja_producto", "crear_categoria", "alta_proveedor", "modificar_proveedor",
        "consultar_proveedores",
    },
    "finanzas": {
        "registrar_gasto", "consultar_gastos_mes", "consultar_resumen_financiero", "consultar_punto_equilibrio",
        "sugerir_precio",
    },
}
NOMBRES_DE_PANTALLA = {"ventas": "Módulo de ventas", "inventario": "Auxiliar de inventario", "finanzas": "Agente financiero"}


def funciones_de(pantalla=None):
    """Las descripciones de las funciones de esa pantalla (o todas si no se indica una)."""
    if pantalla not in HERRAMIENTAS_POR_PANTALLA:
        return FUNCIONES
    permitidas = HERRAMIENTAS_COMUNES | HERRAMIENTAS_POR_PANTALLA[pantalla]
    return [f for f in FUNCIONES if f["name"] in permitidas]


def tools_openai(pantalla=None):
    """Formato "tools" que espera la API de Chat Completions de OpenAI."""
    return [{"type": "function", "function": f} for f in funciones_de(pantalla)]


def tools_gemini(pantalla=None):
    """Formato que espera la API de Gemini (google-generativeai)."""
    return [{"function_declarations": funciones_de(pantalla)}]


# ------------------------------------------------------------- apoyo

def _decimal(valor, defecto=None):
    """Convierte lo que mande la IA (número o texto) a Decimal, o regresa `defecto`."""
    if valor is None or valor == "":
        return defecto
    try:
        numero = Decimal(str(valor).strip())
    except InvalidOperation:
        return defecto
    return numero if numero.is_finite() else defecto


def _dinero(valor):
    return valor.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


# La búsqueda de productos vive en inventario/busqueda.py (la comparte la caja); aquí
# se dejan los mismos nombres de siempre para el resto del archivo y las pruebas.
_normalizar = busqueda.normalizar
catalogo = busqueda.catalogo
_encontrar = busqueda.encontrar
buscar_en_catalogo = busqueda.buscar
PALABRAS_VACIAS = busqueda.PALABRAS_VACIAS

# Número de la caja (1 o 2) en la que está trabajando la persona. La pantalla lo manda con
# cada mensaje y así el asistente agrega y cobra en la caja que ella está viendo.
CARRITO_ACTIVO = ContextVar("carrito_activo", default=1)


def _buscar_uno(negocio, nombre):
    """(producto, None) si hay uno solo; (None, respuesta_para_la_IA) si no hay o hay varios."""
    encontrados = buscar_en_catalogo(negocio, nombre)
    if not encontrados:
        return None, {"ok": False, "mensaje": f'No encontré ningún producto parecido a "{nombre}".'}
    if len(encontrados) > 1:
        nombres = ", ".join(p["nombre"] for p in encontrados)
        return None, {
            "ok": False,
            "ambiguo": True,
            "mensaje": f'Encontré varios productos parecidos a "{nombre}": {nombres}. ¿Cuál de esos quieres?',
        }
    return Producto.objects.get(pk=encontrados[0]["id"]), None


def _venta_actual(negocio):
    """La venta en curso de la caja activa si ya existe (sin crearla)."""
    return carrito.venta_abierta(negocio, CARRITO_ACTIVO.get())


def _venta_en_curso(negocio):
    return carrito.venta_en_curso(negocio, CARRITO_ACTIVO.get(), negocio.usuario)


def _item_del_carrito(negocio, nombre):
    """(venta, item, None) o (None, None, respuesta_para_la_IA)."""
    venta = _venta_actual(negocio)
    if venta is None or not venta.items.exists():
        return None, None, {"ok": False, "mensaje": "La caja está vacía."}

    palabras = _normalizar(nombre).split()
    items = [
        item for item in venta.items.select_related("producto")
        if all(palabra in _normalizar(item.producto.nombre) for palabra in palabras)
    ]
    if not items:
        return None, None, {"ok": False, "mensaje": f'No tengo "{nombre}" en la caja.'}
    if len(items) > 1:
        nombres = ", ".join(item.producto.nombre for item in items)
        return None, None, {
            "ok": False, "ambiguo": True,
            "mensaje": f'En la caja hay varios parecidos a "{nombre}": {nombres}. ¿Cuál?',
        }
    return venta, items[0], None


def _buscar_categoria(nombre):
    """(categoria, None) o (None, respuesta_para_la_IA)."""
    buscado = _normalizar(nombre)
    categorias = list(Categoria.objects.all())
    for categoria in categorias:
        if _normalizar(categoria.nombre) == buscado:
            return categoria, None
    nombres = ", ".join(c.nombre for c in categorias) or "ninguna todavía"
    return None, {
        "ok": False,
        "mensaje": f'No existe la categoría "{nombre}". Las que hay son: {nombres}. '
                   "Elige una o dime si quieres que cree la nueva.",
    }


def _respuesta_sin_existencias(error):
    """Regla de oro: no se vende lo que no hay. Se le pide al usuario cuánto quiere agregar."""
    producto = error.producto
    unidad = "kilos (puedes decirlo en gramos)" if producto.a_granel else "piezas"
    return {
        "ok": False,
        "sin_existencias": True,
        "producto": producto.nombre,
        "disponible": float(error.disponible),
        "mensaje": (
            f"{error.detalle}. ¿Cuántas {unidad} quieres agregar al inventario y a qué precio de compra "
            "cada una? Así lo agrego y seguimos con la venta."
        ),
    }


# ------------------------------------------------------------ ventas

def buscar_producto(negocio, nombre):
    encontrados = _encontrar(negocio, nombre)
    return {
        "total_encontrados": len(encontrados),
        "resultados": [
            {
                "nombre": p["nombre"], "precio_venta": p["precio"], "stock": p["stock"], "minimo": p["minimo"],
                "unidad": "kg" if p["a_granel"] else "pzas",
            }
            for p in encontrados[:10]
        ],
    }


def agregar_al_carrito(negocio, nombre_producto, cantidad=1):
    cantidad = _decimal(cantidad, Decimal("1"))
    producto, error = _buscar_uno(negocio, nombre_producto)
    if error:
        return error

    venta = _venta_en_curso(negocio)
    try:
        carrito.agregar_producto(venta, producto, cantidad)
    except SinExistencias as sin_existencias:
        return _respuesta_sin_existencias(sin_existencias)
    except CantidadInvalida as invalida:
        return {"ok": False, "mensaje": str(invalida)}

    return {
        "ok": True,
        "mensaje": f'Agregué {texto_numero(cantidad)} {producto.unidad} de "{producto.nombre}" a la caja.',
        "total_carrito": float(venta.total),
    }


def quitar_del_carrito(negocio, nombre_producto):
    venta, item, error = _item_del_carrito(negocio, nombre_producto)
    if error:
        return error

    nombre = item.producto.nombre
    carrito.quitar(item)
    return {"ok": True, "mensaje": f'Quité "{nombre}" de la caja.', "total_carrito": float(venta.total)}


def cambiar_cantidad_carrito(negocio, nombre_producto, cantidad):
    cantidad = _decimal(cantidad)
    if cantidad is None or cantidad < 0:
        return {"ok": False, "mensaje": "Dime una cantidad válida."}

    venta, item, error = _item_del_carrito(negocio, nombre_producto)
    if error:
        return error

    nombre = item.producto.nombre
    unidad = item.producto.unidad
    try:
        carrito.cambiar_cantidad(item, cantidad)
    except SinExistencias as sin_existencias:
        return _respuesta_sin_existencias(sin_existencias)
    except CantidadInvalida as invalida:
        return {"ok": False, "mensaje": str(invalida)}

    venta.refresh_from_db()
    if cantidad == 0:
        mensaje = f'Quité "{nombre}" de la caja.'
    else:
        mensaje = f'Ahora hay {texto_numero(cantidad)} {unidad} de "{nombre}" en la caja.'
    return {"ok": True, "mensaje": mensaje, "total_carrito": float(venta.total)}


def ver_carrito(negocio):
    venta = _venta_actual(negocio)
    if venta is None or not venta.items.exists():
        return {"productos": [], "total": 0, "mensaje_vacio": "La caja está vacía.", "carrito": CARRITO_ACTIVO.get()}
    return {
        "carrito": CARRITO_ACTIVO.get(),
        "productos": [
            {
                "nombre": item.producto.nombre, "cantidad": float(item.cantidad), "unidad": item.producto.unidad,
                "subtotal": float(item.subtotal),
            }
            for item in venta.items.select_related("producto")
        ],
        "total": float(venta.total),
    }


def cobrar_carrito(negocio):
    venta = _venta_actual(negocio)
    if venta is None or not venta.items.exists():
        return {"ok": False, "mensaje": "La caja está vacía, no hay nada que cobrar."}

    try:
        avisos = [texto_aviso_stock(producto) for producto in cobrar_venta(venta)]
    except SinExistencias as sin_existencias:
        return _respuesta_sin_existencias(sin_existencias)
    except VentaYaCobrada as ya_cobrada:
        return {"ok": False, "mensaje": ya_cobrada.mensaje}

    mensaje = f"Listo, cobré la venta #{venta.folio:04d} por ${venta.total:.2f}."
    if avisos:
        mensaje += " Ojo: " + " ".join(avisos)
    return {"ok": True, "mensaje": mensaje, "folio": venta.folio, "total": float(venta.total)}


def cancelar_venta(negocio, confirmar=False):
    venta = _venta_actual(negocio)
    if venta is None or not venta.items.exists():
        return {"ok": False, "mensaje": "No hay ninguna venta en curso que cancelar."}

    if not confirmar:
        return {
            "ok": False, "requiere_confirmacion": True,
            "mensaje": f"Voy a cancelar la venta actual ({venta.items.count()} productos, ${venta.total:.2f}). ¿Seguro que quieres cancelarla?",
        }

    carrito.cancelar(venta)
    return {"ok": True, "mensaje": "Listo, cancelé la venta."}


def agregar_producto_no_encontrado(negocio, nombre, precio):
    nombre = str(nombre).strip()
    precio = _decimal(precio)
    if not nombre or precio is None or precio <= 0:
        return {"ok": False, "mensaje": "Necesito el nombre del producto y un precio mayor a cero."}

    # si ya había uno igual pendiente de validar, se reutiliza para no duplicarlo
    producto = carrito.crear_no_encontrado(negocio, nombre, _dinero(precio))
    venta = _venta_en_curso(negocio)
    carrito.agregar_producto(venta, producto, 1)
    return {
        "ok": True,
        "mensaje": (
            f'Agregué "{nombre}" a la caja a ${_dinero(precio):.2f}. Quedó pendiente de validar; '
            "en Finanzas > Registrar gastos puedes ponerle su precio de compra."
        ),
        "total_carrito": float(venta.total),
    }


def consultar_ventas_hoy(negocio):
    def armar():
        hoy = timezone.localdate()
        manana = hoy + timedelta(days=1)
        return {
            "total": float(calculos.ingresos_periodo(negocio, hoy, manana)),
            "numero_ventas": calculos.ventas_cobradas(negocio, hoy, manana).count(),
        }
    return cache_negocio.obtener(negocio, "ventas_hoy", armar)


def ultimas_ventas(negocio, cantidad=5):
    cantidad = int(_decimal(cantidad, Decimal("5")))
    cantidad = min(max(cantidad, 1), 20)
    ventas = Venta.objects.filter(negocio=negocio, estado=Venta.Estado.COBRADA).order_by("-creado_en")[:cantidad]
    return {
        "ventas": [
            {
                "folio": venta.folio,
                "fecha": timezone.localtime(venta.creado_en).strftime("%d/%m/%Y %H:%M"),
                "total": float(venta.total),
            }
            for venta in ventas
        ]
    }


# --------------------------------------------------------- inventario

def consultar_alertas_stock(negocio):
    conteo = conteo_alertas(negocio)
    lista = productos_con_alerta(negocio)[:15]
    return {
        "conteo": conteo,
        "productos": [
            {
                "nombre": p.nombre,
                "color": p.nivel_stock,
                "stock": float(p.cantidad_actual),
                "minimo": float(p.cantidad_minima),
                "stock_ideal": float(p.stock_ideal_efectivo),
                "proveedor": p.proveedor.nombre if p.proveedor else "",
            }
            for p in lista
        ],
        "nota": "Solo se muestran los 15 más urgentes." if conteo["total"] > 15 else "",
    }


def dar_de_alta_producto(negocio, nombre, precio_venta, costo, cantidad_actual=0,
                         cantidad_minima=5, stock_ideal=0, categoria="", a_granel=False, codigo_barras=""):
    nombre = str(nombre).strip()
    precio = _decimal(precio_venta)
    costo = _decimal(costo)
    actual = _decimal(cantidad_actual, Decimal("0"))
    minima = _decimal(cantidad_minima, MINIMO_POR_DEFECTO)
    ideal = _decimal(stock_ideal, Decimal("0"))
    codigo = str(codigo_barras or "").strip()
    a_granel = bool(a_granel)

    if not nombre:
        return {"ok": False, "mensaje": "¿Cómo se llama el producto?"}
    if precio is None or precio <= 0:
        return {"ok": False, "mensaje": "¿A qué precio lo vas a vender?" + (" (por kilo)" if a_granel else "")}
    if costo is None or costo < 0:
        return {"ok": False, "mensaje": "¿Cuánto te cuesta a ti cada pieza? Lo necesito para calcular tu ganancia."}
    aviso = mensaje_si_vende_bajo_el_costo(costo, precio)
    if aviso:
        return {"ok": False, "mensaje": aviso}
    if actual < 0 or minima < 0 or ideal < 0:
        return {"ok": False, "mensaje": "Las cantidades no pueden ser negativas."}
    if not a_granel and any(x != x.to_integral_value() for x in (actual, minima, ideal)):
        return {"ok": False, "mensaje": "Ese producto es por pieza: las cantidades deben ser números enteros."}
    if ideal and ideal < minima:
        return {"ok": False, "mensaje": "El stock ideal no puede ser menor que la cantidad mínima."}

    if any(p["buscable"] == _normalizar(nombre) for p in catalogo(negocio)):
        return {"ok": False, "mensaje": f'Ya tienes "{nombre}" en tu catálogo. Si quieres cambiarlo, dime qué modificar.'}
    if codigo and Producto.objects.filter(negocio=negocio, codigo_barras=codigo).exists():
        return {"ok": False, "mensaje": f"Ya hay un producto con el código de barras {codigo}."}

    if not str(categoria or "").strip():
        return {"ok": False, "mensaje": "¿En qué categoría va el producto? Todo producto lleva una (por ejemplo Bebidas o Botanas)."}
    categoria_producto, error = _buscar_categoria(categoria)
    if error:
        return error

    producto = Producto.objects.create(
        negocio=negocio, nombre=nombre, costo=_dinero(costo), precio_venta=_dinero(precio),
        cantidad_actual=actual, cantidad_minima=minima, stock_ideal=ideal, categoria=categoria_producto,
        a_granel=a_granel, codigo_barras=codigo, icono=icono_para(nombre, categoria_producto),
    )
    # las piezas con las que arranca el producto son mercancía que se compró
    registrar_alta(producto, negocio.usuario)
    return {
        "ok": True,
        "mensaje": (
            f'Di de alta "{producto.nombre}": precio ${producto.precio_venta:.2f}'
            f'{" por kilo" if a_granel else ""}, costo ${producto.costo:.2f}, {texto_numero(actual)} {producto.unidad}.'
        ),
    }


def modificar_producto(negocio, nombre_producto, nuevo_nombre=None, precio_venta=None, costo=None,
                       cantidad_minima=None, stock_ideal=None, categoria=None, motivo=None):
    producto, error = _buscar_uno(negocio, nombre_producto)
    if error:
        return error

    cambios = []

    if nuevo_nombre and str(nuevo_nombre).strip():
        cambios.append(f'nombre: "{producto.nombre}" → "{str(nuevo_nombre).strip()}"')
        producto.nombre = str(nuevo_nombre).strip()

    # (campo, valor nuevo, texto para el mensaje)
    campos_numericos = [
        ("precio_venta", precio_venta, "precio de venta"),
        ("costo", costo, "costo"),
        ("cantidad_minima", cantidad_minima, "cantidad mínima"),
        ("stock_ideal", stock_ideal, "stock ideal"),
    ]
    for campo, valor, etiqueta in campos_numericos:
        if valor is None or valor == "":
            continue
        numero = _decimal(valor)
        if numero is None or numero < 0 or (campo == "precio_venta" and numero == 0):
            return {"ok": False, "mensaje": f"El valor de {etiqueta} no es válido."}
        anterior = getattr(producto, campo)
        setattr(producto, campo, _dinero(numero) if campo in ("precio_venta", "costo") else numero)
        cambios.append(f"{etiqueta}: {texto_numero(anterior)} → {texto_numero(numero)}")

    if categoria:
        categoria_nueva, error = _buscar_categoria(categoria)
        if error:
            return error
        producto.categoria = categoria_nueva
        cambios.append(f"categoría: {categoria_nueva.nombre}")

    if not cambios:
        return {"ok": False, "mensaje": "No me dijiste qué quieres cambiar de ese producto."}
    if precio_venta is not None or costo is not None:
        aviso = mensaje_si_vende_bajo_el_costo(producto.costo, producto.precio_venta)
        if aviso:
            return {"ok": False, "mensaje": aviso}
    if producto.stock_ideal and producto.stock_ideal < producto.cantidad_minima:
        return {"ok": False, "mensaje": "El stock ideal no puede ser menor que la cantidad mínima."}

    producto.save()
    HistorialModificacionProducto.objects.create(
        producto=producto, usuario=negocio.usuario,
        motivo=(str(motivo).strip() if motivo else "Cambio hecho con el asistente")[:255],
    )
    return {"ok": True, "mensaje": f'Listo, actualicé "{producto.nombre}" ({"; ".join(cambios)}).'}


def ajustar_existencias(negocio, nombre_producto, cantidad, modo, costo=None):
    cantidad = _decimal(cantidad)
    if cantidad is None or cantidad < 0:
        return {"ok": False, "mensaje": "Dime cuántas piezas son (un número mayor o igual a cero)."}
    if modo not in ("sumar", "restar", "establecer"):
        return {"ok": False, "mensaje": "No entendí si quieres sumar, restar o dejar una cantidad exacta."}

    producto, error = _buscar_uno(negocio, nombre_producto)
    if error:
        return error

    anterior = producto.cantidad_actual
    if modo == "sumar":
        # llegó mercancía: se suma y la compra queda registrada como gasto
        try:
            agregar_existencias(producto, cantidad, costo=costo, motivo="Compra de mercancía con el asistente")
        except CantidadInvalida as invalida:
            return {"ok": False, "mensaje": str(invalida)}
        nueva = producto.cantidad_actual
    else:
        nueva = anterior - cantidad if modo == "restar" else cantidad
        if nueva < 0:
            return {
                "ok": False,
                "mensaje": f'De "{producto.nombre}" solo hay {texto_numero(anterior)}, no se pueden quitar {texto_numero(cantidad)}.',
            }
        if not producto.a_granel and nueva != nueva.to_integral_value():
            return {"ok": False, "mensaje": f'"{producto.nombre}" se vende por pieza: la cantidad debe ser un número entero.'}
        producto.cantidad_actual = nueva
        producto.save(update_fields=["cantidad_actual", "actualizado_en"])
        registrar_movimiento(
            producto, nueva - anterior, MovimientoInventario.Tipo.AJUSTE,
            motivo=f"Ajuste de existencias con el asistente ({modo} {texto_numero(cantidad)})", usuario=negocio.usuario,
        )
        HistorialModificacionProducto.objects.create(
            producto=producto, usuario=negocio.usuario,
            motivo=f"Ajuste de existencias con el asistente ({modo} {texto_numero(cantidad)})",
        )

    mensaje = f'Ahora hay {texto_numero(nueva)} {producto.unidad} de "{producto.nombre}" (antes {texto_numero(anterior)}).'
    if modo == "sumar" and costo is None and producto.costo == 0:
        mensaje += " No tiene precio de compra, así que no pude registrar el gasto de esa compra."
    if producto.nivel_stock != "ok":
        mensaje += " " + texto_aviso_stock(producto)
    return {"ok": True, "mensaje": mensaje}


def dar_de_baja_producto(negocio, nombre_producto, confirmar=False):
    producto, error = _buscar_uno(negocio, nombre_producto)
    if error:
        return error

    if not confirmar:
        extra = " Ya tiene ventas, pero su historial no se pierde." if producto.tiene_ventas else ""
        return {
            "ok": False, "requiere_confirmacion": True,
            "mensaje": f'Voy a dar de baja "{producto.nombre}".{extra} ¿Seguro?',
        }

    producto.activo = False
    producto.save(update_fields=["activo", "actualizado_en"])
    return {"ok": True, "mensaje": f'Listo, di de baja "{producto.nombre}".'}


def crear_categoria(negocio, nombre, icono=""):
    nombre = str(nombre).strip()
    if not nombre:
        return {"ok": False, "mensaje": "¿Cómo se llama la categoría?"}

    _, creada = Categoria.objects.get_or_create(nombre=nombre, defaults={"icono": str(icono).strip() or "📦"})
    if creada:
        return {"ok": True, "mensaje": f'Creé la categoría "{nombre}".'}
    return {"ok": True, "mensaje": f'La categoría "{nombre}" ya existía.'}


def _limpiar_correo(texto):
    """Arregla un correo dictado por voz: 'ventas arroba coca-cola punto com' -> ventas@coca-cola.com.
    Regresa (correo, True) si es válido, o (texto, False) si no lo es."""
    correo = str(texto or "").strip().lower()
    correo = correo.replace(" arroba ", "@").replace(" punto ", ".").replace(" ", "")
    try:
        validate_email(correo)
    except ValidationError:
        return str(texto), False
    return correo, True


def alta_proveedor(negocio, nombre, telefono="", correo=""):
    nombre = str(nombre).strip()
    if not nombre:
        return {"ok": False, "mensaje": "¿Cómo se llama el proveedor?"}
    if Proveedor.objects.filter(negocio=negocio, nombre__iexact=nombre).exists():
        return {
            "ok": False,
            "mensaje": f'Ya tienes registrado a "{nombre}". Si quieres cambiarle el teléfono o el correo, dime los datos nuevos.',
        }

    correo_limpio = ""
    if correo:
        correo_limpio, es_valido = _limpiar_correo(correo)
        if not es_valido:
            return {"ok": False, "mensaje": f'El correo "{correo}" no parece válido. ¿Me lo repites?'}

    Proveedor.objects.create(negocio=negocio, nombre=nombre, telefono=str(telefono or "")[:30], correo=correo_limpio)
    return {"ok": True, "mensaje": f'Registré al proveedor "{nombre}".'}


def modificar_proveedor(negocio, nombre_proveedor, nuevo_nombre=None, telefono=None, correo=None):
    palabras = _normalizar(nombre_proveedor).split()
    proveedores = [
        p for p in Proveedor.objects.filter(negocio=negocio)
        if all(palabra in _normalizar(p.nombre) for palabra in palabras)
    ]
    if not proveedores:
        return {"ok": False, "mensaje": f'No encontré ningún proveedor parecido a "{nombre_proveedor}".'}
    if len(proveedores) > 1:
        nombres = ", ".join(p.nombre for p in proveedores)
        return {"ok": False, "ambiguo": True, "mensaje": f'Hay varios proveedores parecidos: {nombres}. ¿Cuál?'}
    proveedor = proveedores[0]

    cambios = []
    if nuevo_nombre and str(nuevo_nombre).strip():
        proveedor.nombre = str(nuevo_nombre).strip()
        cambios.append(f"nombre: {proveedor.nombre}")
    if telefono and str(telefono).strip():
        proveedor.telefono = str(telefono).strip()[:30]
        cambios.append(f"teléfono: {proveedor.telefono}")
    if correo and str(correo).strip():
        correo_limpio, es_valido = _limpiar_correo(correo)
        if not es_valido:
            return {"ok": False, "mensaje": f'El correo "{correo}" no parece válido. ¿Me lo repites?'}
        proveedor.correo = correo_limpio
        cambios.append(f"correo: {correo_limpio}")

    if not cambios:
        return {"ok": False, "mensaje": "No me dijiste qué quieres cambiar del proveedor (nombre, teléfono o correo)."}

    proveedor.save()
    return {"ok": True, "mensaje": f'Listo, actualicé a "{proveedor.nombre}" ({"; ".join(cambios)}).'}


def consultar_inventario(negocio, categoria=None):
    productos = Producto.objects.filter(negocio=negocio, activo=True)
    if categoria and str(categoria).strip():
        categoria_buscada, error = _buscar_categoria(categoria)
        if error:
            return error
        productos = productos.filter(categoria=categoria_buscada)

    por_categoria = productos.order_by().values("categoria__nombre").annotate(cuantos=Count("id")).order_by("categoria__nombre")
    total = productos.count()
    return {
        "total_productos": total,
        "por_categoria": [
            {"categoria": fila["categoria__nombre"] or "Sin categoría", "productos": fila["cuantos"]}
            for fila in por_categoria
        ],
        "productos": [
            {"nombre": p.nombre, "piezas": float(p.cantidad_actual), "precio_venta": float(p.precio_venta)}
            for p in productos.order_by("nombre")[:30]
        ],
        "nota": "Solo se muestran los primeros 30 productos." if total > 30 else "",
    }


def consultar_proveedores(negocio):
    proveedores = Proveedor.objects.filter(negocio=negocio)
    return {
        "proveedores": [
            {"nombre": p.nombre, "telefono": p.telefono, "correo": p.correo}
            for p in proveedores
        ]
    }


# ----------------------------------------------------------- finanzas

def registrar_gasto(negocio, concepto, monto, tipo, categoria=None, mes=None, anio=None):
    concepto = str(concepto).strip()
    monto = _decimal(monto)
    tipo = str(tipo).upper()
    if not concepto:
        return {"ok": False, "mensaje": "¿En qué fue el gasto?"}
    if monto is None or monto <= 0:
        return {"ok": False, "mensaje": "¿De cuánto fue el gasto? Necesito un monto mayor a cero."}
    if tipo not in ("FIJO", "VARIABLE"):
        return {"ok": False, "mensaje": "¿El gasto es fijo (como la renta) o variable (como las bolsas)?"}

    categoria_gasto = None
    if categoria and str(categoria).strip():
        nombre_categoria = str(categoria).strip()
        # si ya existe con otras mayúsculas (por ejemplo "luz" y "Luz") se usa esa y no se duplica
        categoria_gasto = CategoriaGasto.objects.filter(negocio=negocio, nombre__iexact=nombre_categoria).first()
        if categoria_gasto is None:
            categoria_gasto = CategoriaGasto.objects.create(negocio=negocio, nombre=nombre_categoria[:60], tipo=tipo)

    periodo = calculos.primer_dia_del_mes(timezone.localdate())
    if mes not in (None, ""):
        try:
            numero_mes = int(float(mes))
            numero_anio = int(float(anio)) if anio not in (None, "") else periodo.year
            periodo = date(numero_anio, numero_mes, 1)
        except (ValueError, TypeError, OverflowError):
            return {"ok": False, "mensaje": "No entendí a qué mes corresponde el gasto. Dime el mes y el año, por ejemplo septiembre de 2026."}

    gasto = GastoOperativo.objects.create(
        negocio=negocio, concepto=concepto, monto=_dinero(monto), tipo=tipo, categoria=categoria_gasto, periodo=periodo,
    )
    return {"ok": True, "mensaje": f'Registré el gasto "{gasto.concepto}" por ${gasto.monto:.2f} (mes: {periodo.strftime("%m/%Y")}).'}


def consultar_gastos_mes(negocio):
    hoy = timezone.localdate()
    inicio = calculos.primer_dia_del_mes(hoy)
    fin = calculos.mes_siguiente(inicio)
    ultimos = GastoOperativo.objects.filter(negocio=negocio, periodo__gte=inicio, periodo__lt=fin).order_by("-fecha", "-id")[:5]
    return {
        "total_fijos": float(calculos.gastos_periodo(negocio, inicio, fin, tipo=GastoOperativo.Tipo.FIJO)),
        "total_variables": float(calculos.gastos_periodo(negocio, inicio, fin, tipo=GastoOperativo.Tipo.VARIABLE)),
        "ultimos_gastos": [
            {"concepto": g.concepto, "monto": float(g.monto), "tipo": g.tipo, "fecha": g.fecha.strftime("%d/%m/%Y")}
            for g in ultimos
        ],
    }


def consultar_resumen_financiero(negocio):
    def armar():
        hoy = timezone.localdate()
        tasa_isr = calculos.tasa_isr_del_negocio(negocio, hoy)
        resumen = calculos.resumen_financiero(
            negocio, calculos.primer_dia_del_mes(hoy), hoy + timedelta(days=1), tasa_isr,
        )
        return {clave: (float(valor) if valor is not None else None) for clave, valor in resumen.items()}
    return cache_negocio.obtener(negocio, "resumen_financiero", armar)


def consultar_punto_equilibrio(negocio):
    def armar():
        hoy = timezone.localdate()
        datos = calculos.punto_equilibrio_negocio(negocio, hoy)
        if datos["estado"] == "sin_fijos":
            return {"disponible": False, "motivo": "Todavía no hay gastos fijos registrados este mes."}
        if datos["estado"] == "sin_ventas":
            return {"disponible": False, "motivo": "Todavía no hay ventas cobradas suficientes para calcularlo."}
        if datos["estado"] == "sin_margen":
            return {"disponible": False, "motivo": "Los productos se venden al costo o más barato, no alcanza para cubrir gastos fijos."}

        pe_total = datos["pe_total"]
        return {
            "disponible": True,
            "gastos_fijos_del_mes": float(datos["fijos"]),
            "punto_equilibrio_mensual": float(calculos.redondear(pe_total)),
            "punto_equilibrio_por_dia": float(calculos.redondear(pe_total / calculos.dias_del_mes(hoy))),
            "por_categoria": [
                {
                    "categoria": fila["nombre"],
                    "vender_en_pesos": float(fila["ventas_objetivo"]),
                    "vender_en_unidades": fila["unidades_objetivo"],
                }
                for fila in datos["filas"]
            ],
        }
    return cache_negocio.obtener(negocio, "punto_equilibrio", armar)


def sugerir_precio(negocio, nombre_producto, margen_deseado=None):
    producto, error = _buscar_uno(negocio, nombre_producto)
    if error:
        return error

    # si el usuario no dice el margen, se usa el que escogió la última vez en la pantalla de precios (o 30)
    margen = _decimal(margen_deseado, _decimal(negocio.preferencia("margen_deseado"), Decimal("30")))
    if margen < 0 or margen >= 100:
        return {"ok": False, "mensaje": "El margen tiene que estar entre 0 y 99 por ciento."}
    if producto.costo <= 0:
        return {"ok": False, "mensaje": f'"{producto.nombre}" no tiene costo registrado, así que no puedo calcular su precio.'}

    return {
        "producto": producto.nombre,
        "costo": float(producto.costo),
        "precio_actual": float(producto.precio_venta),
        "margen_deseado": float(margen),
        "precio_sugerido": float(calculos.precio_sugerido(producto.costo, margen)),
    }


DESPACHADOR = {
    "buscar_producto": buscar_producto,
    "agregar_al_carrito": agregar_al_carrito,
    "quitar_del_carrito": quitar_del_carrito,
    "cambiar_cantidad_carrito": cambiar_cantidad_carrito,
    "ver_carrito": ver_carrito,
    "cobrar_carrito": cobrar_carrito,
    "cancelar_venta": cancelar_venta,
    "agregar_producto_no_encontrado": agregar_producto_no_encontrado,
    "consultar_ventas_hoy": consultar_ventas_hoy,
    "ultimas_ventas": ultimas_ventas,
    "consultar_alertas_stock": consultar_alertas_stock,
    "dar_de_alta_producto": dar_de_alta_producto,
    "modificar_producto": modificar_producto,
    "ajustar_existencias": ajustar_existencias,
    "dar_de_baja_producto": dar_de_baja_producto,
    "crear_categoria": crear_categoria,
    "alta_proveedor": alta_proveedor,
    "modificar_proveedor": modificar_proveedor,
    "consultar_proveedores": consultar_proveedores,
    "consultar_inventario": consultar_inventario,
    "registrar_gasto": registrar_gasto,
    "consultar_gastos_mes": consultar_gastos_mes,
    "consultar_resumen_financiero": consultar_resumen_financiero,
    "consultar_punto_equilibrio": consultar_punto_equilibrio,
    "sugerir_precio": sugerir_precio,
}


def ejecutar_funcion(nombre, argumentos, negocio):
    funcion = DESPACHADOR.get(nombre)
    if funcion is None:
        return {"error": f'No existe la función "{nombre}".'}
    try:
        return funcion(negocio, **argumentos)
    except TypeError:
        # la IA mandó argumentos de más o de menos
        return {"error": f'Los datos para "{nombre}" no estaban completos.'}


def respuesta_directa(ejecuciones):
    """Si lo único que se hizo fueron acciones, el texto final es el mensaje de
    cada función y no hace falta volver a llamar a la IA (se responde al instante).

    `ejecuciones` es una lista de (nombre_de_la_funcion, resultado)."""
    if not ejecuciones:
        return None
    mensajes = []
    for nombre, resultado in ejecuciones:
        if nombre not in ACCIONES or "mensaje" not in resultado:
            return None
        mensajes.append(resultado["mensaje"])
    return " ".join(mensajes)


# -------------------------------------------- contexto y memoria del chat

def contexto_negocio(negocio):
    """Un resumen corto de cómo va la tienda ahorita, que se le pega a las
    instrucciones de la IA para que conteste lo básico sin ejecutar funciones.
    Se guarda en el cache y se renueva cuando cambia una venta, producto o gasto."""
    def armar():
        ventas = consultar_ventas_hoy(negocio)
        conteo = conteo_alertas(negocio)

        lineas = [
            f"Tienda: {negocio.nombre_tienda}. Fecha de hoy: {timezone.localdate().strftime('%d/%m/%Y')}.",
            f"Ventas cobradas hoy: ${ventas['total']:.2f} en {ventas['numero_ventas']} ventas.",
        ]
        for numero in range(1, MAXIMO_DE_CARRITOS + 1):
            venta = carrito.venta_abierta(negocio, numero)
            renglones = list(venta.items.select_related("producto")[:8]) if venta else []
            if renglones:
                detalle = ", ".join(f"{texto_numero(r.cantidad)} {r.producto.nombre}" for r in renglones)
                lineas.append(f"Caja {numero}: {detalle}. Total: ${venta.total:.2f}.")
            else:
                lineas.append(f"Caja {numero}: vacía.")
        lineas.append(
            f"Productos por resurtir: {conteo['rojo']} en rojo, {conteo['naranja']} en naranja, "
            f"{conteo['amarillo']} en amarillo."
        )
        return "\n".join(lineas)
    return cache_negocio.obtener(negocio, "contexto_ia", armar)


def historial_reciente(negocio, limite=10):
    """Los últimos mensajes de la conversación, del más viejo al más nuevo,
    para que el AVI pueda resolver referencias como '¿cuánto cuesta?'.
    Solo cuenta lo que se habló en las últimas 24 horas (igual que el chat que se ve en pantalla)."""
    desde = timezone.now() - timedelta(hours=HORAS_DE_HISTORIAL)
    mensajes = HistorialConversacion.objects.filter(
        negocio=negocio, creado_en__gte=desde,
    ).order_by("-creado_en", "-id")[:limite]
    return list(reversed(mensajes))


# --------------------------------------- datos para los resúmenes con IA

def datos_resumen_diario(negocio):
    """Junta los números de ayer (ventas, ganancia, gastos) para que el AVI los explique."""
    hoy = timezone.localdate()
    ayer = hoy - timedelta(days=1)
    antier = ayer - timedelta(days=1)

    total_ventas = calculos.ingresos_periodo(negocio, ayer, hoy)
    costo = calculos.costo_de_ventas_periodo(negocio, ayer, hoy)
    ventas_ayer = calculos.ventas_cobradas(negocio, ayer, hoy)

    mas_vendidos = (
        ItemVenta.objects.filter(venta__in=ventas_ayer)
        .order_by().values("producto__nombre").annotate(piezas=Sum("cantidad")).order_by("-piezas")[:3]
    )

    return {
        "numero_ventas": ventas_ayer.count(),
        "total_ventas": float(total_ventas),
        "ganancia": float(total_ventas - costo),
        "total_gastos": float(calculos.gastos_capturados(negocio, ayer, hoy)),
        "total_antier": float(calculos.ingresos_periodo(negocio, antier, ayer)),
        "mas_vendidos": [f"{fila['producto__nombre']} ({texto_numero(fila['piezas'])} pzas)" for fila in mas_vendidos],
        "alertas": conteo_alertas(negocio),
    }


def construir_mensaje_resumen(datos):
    """Convierte los números de datos_resumen_diario en el prompt que se le manda a la IA."""
    texto = (
        "Dame un resumen breve de cómo le fue ayer a mi tienda. "
        f"Ventas de ayer: ${datos['total_ventas']:.2f} en {datos['numero_ventas']} ventas "
        f"(antier fueron ${datos.get('total_antier', 0):.2f}). "
        f"Ganancia estimada: ${datos['ganancia']:.2f}. Gastos pagados: ${datos['total_gastos']:.2f}. "
    )
    if datos.get("mas_vendidos"):
        texto += "Lo más vendido: " + ", ".join(datos["mas_vendidos"]) + ". "

    alertas = datos.get("alertas")
    if alertas and alertas["total"]:
        texto += (
            f"Productos por resurtir: {alertas['rojo']} en rojo (ya llegaron al mínimo), "
            f"{alertas['naranja']} en naranja y {alertas['amarillo']} en amarillo. "
        )
    texto += (
        "Dime en 3 o 4 frases cortas cómo estuvo y dame dos consejos prácticos, concretos y fáciles, "
        "para mejorar mi negocio hoy."
    )
    return texto


def datos_para_explicar(negocio, tipo, desde=None, hasta=None):
    """Los números que se le mandan a la IA para que explique el dashboard o los reportes."""
    hoy = timezone.localdate()
    tasa_isr = calculos.tasa_isr_del_negocio(negocio, hoy)
    inicio_mes = calculos.primer_dia_del_mes(hoy)

    if tipo == "pronostico":
        pronostico = (
            calculos.pronostico_ventas_negocio(negocio, desde=desde, hasta=hasta)
            if desde is not None and hasta is not None
            else calculos.pronostico_cacheado(negocio)
        )
        productos = [
            {
                "producto": p["nombre"],
                "vendio_la_ultima_semana": p["ultima_semana_real"],
                "se_espera_la_proxima_semana": p["mejor_pronostico"],
                "cambio_porcentual": p["cambio_porcentual"],
                "confianza": p["confianza"],
                "tiene_historia_suficiente": p["datos_suficientes"],
            }
            for p in pronostico["productos"]
        ] if pronostico["estado"] == "ok" else []
        return {"tipo": "pronostico", "semana_pronosticada": str(pronostico.get("semana_pronostico", "")), "productos": productos}

    if tipo == "reportes":
        meses = []
        desde = inicio_mes
        for _ in range(3):
            hasta = calculos.mes_siguiente(desde)
            resumen = calculos.resumen_financiero(negocio, desde, hasta, tasa_isr)
            meses.append({
                "mes": desde.strftime("%m/%Y"),
                "ingresos": float(resumen["ingresos"]),
                "gastos": float(resumen["gastos"]),
                "utilidad_neta": float(resumen["utilidad_neta"]),
                "margen_operativo": float(resumen["margen_operativo"]) if resumen["margen_operativo"] is not None else None,
            })
            desde = calculos.mes_anterior(desde)
        return {"tipo": "reportes", "meses_del_mas_nuevo_al_mas_viejo": meses}

    actual = calculos.resumen_financiero(negocio, inicio_mes, hoy + timedelta(days=1), tasa_isr)
    anterior_inicio = calculos.mes_anterior(inicio_mes)
    anterior = calculos.resumen_financiero(negocio, anterior_inicio, inicio_mes, tasa_isr)
    equilibrio = consultar_punto_equilibrio(negocio)
    return {
        "tipo": "dashboard",
        "ventas_hoy": consultar_ventas_hoy(negocio),
        "este_mes": {clave: (float(v) if v is not None else None) for clave, v in actual.items()},
        "mes_pasado": {clave: (float(v) if v is not None else None) for clave, v in anterior.items()},
        "punto_equilibrio_mensual": equilibrio.get("punto_equilibrio_mensual"),
    }


def construir_mensaje_explicacion(datos):
    """El prompt para que la IA explique los números de la pantalla."""
    if datos["tipo"] == "pronostico":
        return (
            f"Explícame mi pronóstico de ventas de la próxima semana. Estos son los datos: {datos}. "
            "Dime en 4 o 5 frases cortas qué productos conviene surtir más, cuáles voy a vender menos y en cuáles "
            "el pronóstico es poco confiable (confianza baja) o no se pudo calcular por falta de historia. "
            "Recuérdame que es una estimación de apoyo y que la decisión de cuánto comprar es mía. "
            "Usa palabras de todos los días, sin fórmulas ni términos técnicos."
        )
    if datos["tipo"] == "reportes":
        pantalla = "los reportes financieros de mis últimos 3 meses"
    else:
        pantalla = "el resumen de mis finanzas (este mes contra el mes pasado)"
    return (
        f"Explícame {pantalla}. Estos son los números: {datos}. "
        "Dime en 4 o 5 frases cortas qué significan, qué va bien, qué va mal, y dame dos consejos "
        "prácticos para mejorar. Usa palabras de todos los días, sin fórmulas."
    )
