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
import unicodedata
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db.models import Sum
from django.utils import timezone

from core import cache_negocio
from finanzas import calculos
from finanzas.models import CategoriaGasto, GastoOperativo
from inventario.alertas import conteo_alertas, productos_con_alerta
from inventario.models import Categoria, HistorialModificacionProducto, Producto, Proveedor
from ventas.cobro import cobrar_venta, texto_aviso_stock
from ventas.models import ItemVenta, Venta
from ventas.views import _venta_en_curso

from .models import HistorialConversacion

CENTAVOS = Decimal("0.01")

# Las funciones que MODIFICAN datos. Sirven para dos cosas:
#  - si el asistente solo ejecutó acciones, se contesta con el mensaje de la
#    propia función y se ahorra la segunda llamada a la IA (respuesta casi instantánea)
#  - avisarle a la pantalla que se refresque para mostrar el cambio
ACCIONES = {
    "agregar_al_carrito", "quitar_del_carrito", "cambiar_cantidad_carrito",
    "cobrar_carrito", "cancelar_venta", "agregar_producto_no_encontrado",
    "dar_de_alta_producto", "modificar_producto", "ajustar_existencias",
    "dar_de_baja_producto", "crear_categoria", "alta_proveedor", "registrar_gasto",
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
        "Busca productos del inventario por nombre y regresa su precio y cuántas piezas quedan.",
        {"nombre": _texto("Nombre o parte del nombre del producto")},
        ["nombre"],
    ),
    _funcion(
        "agregar_al_carrito",
        "Agrega un producto al carrito de la venta que está en curso.",
        {
            "nombre_producto": _texto("Nombre del producto a agregar"),
            "cantidad": _numero("Cantidad a agregar, por default 1"),
        },
        ["nombre_producto"],
    ),
    _funcion(
        "quitar_del_carrito",
        "Quita un producto del carrito por completo.",
        {"nombre_producto": _texto("Nombre del producto que está en el carrito")},
        ["nombre_producto"],
    ),
    _funcion(
        "cambiar_cantidad_carrito",
        "Cambia la cantidad de un producto que ya está en el carrito (la deja en ese número exacto).",
        {
            "nombre_producto": _texto("Nombre del producto que está en el carrito"),
            "cantidad": _numero("Nueva cantidad total de ese producto"),
        },
        ["nombre_producto", "cantidad"],
    ),
    _funcion("ver_carrito", "Regresa los productos que hay en el carrito y el total a cobrar."),
    _funcion(
        "cobrar_carrito",
        "Cobra la venta en curso: descuenta el inventario y genera el ticket. "
        "Úsala cuando pidan cobrar, cerrar la venta o terminar la cuenta.",
    ),
    _funcion(
        "cancelar_venta",
        "Cancela la venta en curso y vacía el carrito. Antes de usarla con confirmar=true "
        "hay que preguntarle al usuario si está seguro.",
        {"confirmar": {"type": "boolean", "description": "true solo si el usuario ya confirmó que sí quiere cancelar"}},
    ),
    _funcion(
        "agregar_producto_no_encontrado",
        "Agrega al carrito un producto que no existe en el inventario, solo con nombre y precio, "
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
            "costo": _numero("Lo que le cuesta al tendero cada pieza, en pesos"),
            "cantidad_actual": _numero("Piezas que hay ahorita, por default 0"),
            "cantidad_minima": _numero("Piezas mínimas antes de resurtir, por default 0"),
            "stock_ideal": _numero("Piezas que tiene cuando resurte completo, por default 0"),
            "categoria": _texto("Nombre de una categoría que ya exista (opcional)"),
        },
        ["nombre", "precio_venta", "costo"],
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
        "Cambia las piezas que hay de un producto: sumar (llegó mercancía), restar (merma, se rompió) "
        "o establecer (después de contar el inventario).",
        {
            "nombre_producto": _texto("Nombre del producto"),
            "cantidad": _numero("Número de piezas"),
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
    _funcion("consultar_proveedores", "Regresa la lista de proveedores registrados."),
    # ---- finanzas
    _funcion(
        "registrar_gasto",
        "Registra un gasto operativo del negocio (fijo o variable).",
        {
            "concepto": _texto("Ej. Renta, Luz, Inventario"),
            "monto": _numero("Monto del gasto en pesos"),
            "tipo": {"type": "string", "enum": ["FIJO", "VARIABLE"], "description": "Tipo de gasto"},
            "categoria": _texto("Categoría del gasto, como Luz o Internet (opcional)"),
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
            "margen_deseado": _numero("Margen de ganancia deseado en porcentaje, por default 30"),
        },
        ["nombre_producto"],
    ),
]


def tools_openai():
    """Formato "tools" que espera la API de Chat Completions de OpenAI."""
    return [{"type": "function", "function": f} for f in FUNCIONES]


def tools_gemini():
    """Formato que espera la API de Gemini (google-generativeai)."""
    return [{"function_declarations": FUNCIONES}]


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


def _normalizar(texto):
    """Minúsculas y sin acentos, para que 'jabon' encuentre 'Jabón'."""
    descompuesto = unicodedata.normalize("NFD", str(texto))
    sin_acentos = "".join(letra for letra in descompuesto if unicodedata.category(letra) != "Mn")
    return sin_acentos.lower().strip()


def catalogo(negocio):
    """Lista de productos activos del negocio, guardada en el cache. Así el
    asistente encuentra productos sin pegarle a la base de datos en cada mensaje."""
    def armar():
        productos = Producto.objects.filter(negocio=negocio, activo=True).values(
            "id", "nombre", "precio_venta", "cantidad_actual", "cantidad_minima",
        )
        return [
            {
                "id": p["id"],
                "nombre": p["nombre"],
                "buscable": _normalizar(p["nombre"]),
                "precio": float(p["precio_venta"]),
                "stock": float(p["cantidad_actual"]),
                "minimo": float(p["cantidad_minima"]),
            }
            for p in productos
        ]
    return cache_negocio.obtener(negocio, "catalogo", armar)


def _coincidencias(productos, palabras):
    return [p for p in productos if all(palabra in p["buscable"] for palabra in palabras)]


def buscar_en_catalogo(negocio, texto, limite=5):
    """Productos cuyo nombre contiene todas las palabras de `texto`, sin importar
    el orden ni los acentos. Si hay uno con el nombre exacto, ese va primero."""
    palabras = _normalizar(texto).split()
    if not palabras:
        return []

    productos = catalogo(negocio)
    encontrados = _coincidencias(productos, palabras)

    # "cocas" -> "coca": si no salió nada, se prueba con las palabras en singular
    if not encontrados:
        singulares = [p[:-1] if len(p) > 3 and p.endswith("s") else p for p in palabras]
        encontrados = _coincidencias(productos, singulares)

    exactos = [p for p in encontrados if p["buscable"] == " ".join(palabras)]
    return (exactos or encontrados)[:limite]


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
    """La venta en curso si ya existe (sin crearla)."""
    return Venta.objects.filter(negocio=negocio, estado=Venta.Estado.EN_CURSO).first()


def _item_del_carrito(negocio, nombre):
    """(venta, item, None) o (None, None, respuesta_para_la_IA)."""
    venta = _venta_actual(negocio)
    if venta is None or not venta.items.exists():
        return None, None, {"ok": False, "mensaje": "El carrito está vacío."}

    palabras = _normalizar(nombre).split()
    items = [
        item for item in venta.items.select_related("producto")
        if all(palabra in _normalizar(item.producto.nombre) for palabra in palabras)
    ]
    if not items:
        return None, None, {"ok": False, "mensaje": f'No tengo "{nombre}" en el carrito.'}
    if len(items) > 1:
        nombres = ", ".join(item.producto.nombre for item in items)
        return None, None, {
            "ok": False, "ambiguo": True,
            "mensaje": f'En el carrito hay varios parecidos a "{nombre}": {nombres}. ¿Cuál?',
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


# ------------------------------------------------------------ ventas

def buscar_producto(negocio, nombre):
    return {
        "resultados": [
            {"nombre": p["nombre"], "precio_venta": p["precio"], "stock": p["stock"], "minimo": p["minimo"]}
            for p in buscar_en_catalogo(negocio, nombre)
        ]
    }


def agregar_al_carrito(negocio, nombre_producto, cantidad=1):
    cantidad = _decimal(cantidad, Decimal("1"))
    if cantidad <= 0:
        return {"ok": False, "mensaje": "La cantidad tiene que ser mayor a cero."}

    producto, error = _buscar_uno(negocio, nombre_producto)
    if error:
        return error

    venta = _venta_en_curso(negocio)
    item, creado = ItemVenta.objects.get_or_create(
        venta=venta, producto=producto,
        defaults={"cantidad": cantidad, "precio_unitario": producto.precio_venta},
    )
    if not creado:
        item.cantidad += cantidad
        item.save(update_fields=["cantidad"])
    venta.recalcular_total()

    mensaje = f'Agregué {cantidad:g} de "{producto.nombre}" al carrito.'
    if item.cantidad > producto.cantidad_actual:
        mensaje += f" Ojo: en el inventario solo hay {producto.cantidad_actual:g}."
    return {"ok": True, "mensaje": mensaje, "total_carrito": float(venta.total)}


def quitar_del_carrito(negocio, nombre_producto):
    venta, item, error = _item_del_carrito(negocio, nombre_producto)
    if error:
        return error

    nombre = item.producto.nombre
    item.delete()
    venta.recalcular_total()
    return {"ok": True, "mensaje": f'Quité "{nombre}" del carrito.', "total_carrito": float(venta.total)}


def cambiar_cantidad_carrito(negocio, nombre_producto, cantidad):
    cantidad = _decimal(cantidad)
    if cantidad is None or cantidad < 0:
        return {"ok": False, "mensaje": "Dime una cantidad válida."}

    venta, item, error = _item_del_carrito(negocio, nombre_producto)
    if error:
        return error

    nombre = item.producto.nombre
    if cantidad == 0:
        item.delete()
        mensaje = f'Quité "{nombre}" del carrito.'
    else:
        item.cantidad = cantidad
        item.save(update_fields=["cantidad"])
        mensaje = f'Ahora hay {cantidad:g} de "{nombre}" en el carrito.'
    venta.recalcular_total()
    return {"ok": True, "mensaje": mensaje, "total_carrito": float(venta.total)}


def ver_carrito(negocio):
    venta = _venta_actual(negocio)
    if venta is None or not venta.items.exists():
        return {"productos": [], "total": 0, "mensaje_vacio": "El carrito está vacío."}
    return {
        "productos": [
            {"nombre": item.producto.nombre, "cantidad": float(item.cantidad), "subtotal": float(item.subtotal)}
            for item in venta.items.select_related("producto")
        ],
        "total": float(venta.total),
    }


def cobrar_carrito(negocio):
    venta = _venta_actual(negocio)
    if venta is None or not venta.items.exists():
        return {"ok": False, "mensaje": "El carrito está vacío, no hay nada que cobrar."}

    avisos = [texto_aviso_stock(producto) for producto in cobrar_venta(venta)]
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

    venta.estado = Venta.Estado.CANCELADA
    venta.save(update_fields=["estado"])
    return {"ok": True, "mensaje": "Listo, cancelé la venta."}


def agregar_producto_no_encontrado(negocio, nombre, precio):
    nombre = str(nombre).strip()
    precio = _decimal(precio)
    if not nombre or precio is None or precio <= 0:
        return {"ok": False, "mensaje": "Necesito el nombre del producto y un precio mayor a cero."}

    # si ya había uno igual pendiente de validar, se reutiliza para no duplicarlo
    producto = Producto.objects.filter(negocio=negocio, pendiente_validacion=True, nombre__iexact=nombre).first()
    if producto is None:
        producto = Producto.objects.create(
            negocio=negocio, nombre=nombre, costo=0, precio_venta=_dinero(precio),
            cantidad_actual=0, cantidad_minima=0, activo=False, pendiente_validacion=True,
        )

    venta = _venta_en_curso(negocio)
    item, creado = ItemVenta.objects.get_or_create(
        venta=venta, producto=producto,
        defaults={"cantidad": 1, "precio_unitario": _dinero(precio)},
    )
    if not creado:
        item.cantidad += 1
        item.save(update_fields=["cantidad"])
    venta.recalcular_total()
    return {
        "ok": True,
        "mensaje": f'Agregué "{nombre}" al carrito a ${_dinero(precio):.2f}. Quedó pendiente de validar en tu inventario.',
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
                         cantidad_minima=0, stock_ideal=0, categoria=""):
    nombre = str(nombre).strip()
    precio = _decimal(precio_venta)
    costo = _decimal(costo)
    actual = _decimal(cantidad_actual, Decimal("0"))
    minima = _decimal(cantidad_minima, Decimal("0"))
    ideal = _decimal(stock_ideal, Decimal("0"))

    if not nombre:
        return {"ok": False, "mensaje": "¿Cómo se llama el producto?"}
    if precio is None or precio <= 0:
        return {"ok": False, "mensaje": "¿A qué precio lo vas a vender?"}
    if costo is None or costo < 0:
        return {"ok": False, "mensaje": "¿Cuánto te cuesta a ti cada pieza? Lo necesito para calcular tu ganancia."}
    if actual < 0 or minima < 0 or ideal < 0:
        return {"ok": False, "mensaje": "Las cantidades no pueden ser negativas."}
    if ideal and ideal < minima:
        return {"ok": False, "mensaje": "El stock ideal no puede ser menor que la cantidad mínima."}

    if any(p["buscable"] == _normalizar(nombre) for p in catalogo(negocio)):
        return {"ok": False, "mensaje": f'Ya tienes "{nombre}" en tu catálogo. Si quieres cambiarlo, dime qué modificar.'}

    categoria_producto = None
    if categoria:
        categoria_producto, error = _buscar_categoria(categoria)
        if error:
            return error

    producto = Producto.objects.create(
        negocio=negocio, nombre=nombre, costo=_dinero(costo), precio_venta=_dinero(precio),
        cantidad_actual=actual, cantidad_minima=minima, stock_ideal=ideal, categoria=categoria_producto,
    )
    return {
        "ok": True,
        "mensaje": f'Di de alta "{producto.nombre}": precio ${producto.precio_venta:.2f}, costo ${producto.costo:.2f}, {actual:g} piezas.',
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
        cambios.append(f"{etiqueta}: {anterior:g} → {numero:g}")

    if categoria:
        categoria_nueva, error = _buscar_categoria(categoria)
        if error:
            return error
        producto.categoria = categoria_nueva
        cambios.append(f"categoría: {categoria_nueva.nombre}")

    if not cambios:
        return {"ok": False, "mensaje": "No me dijiste qué quieres cambiar de ese producto."}
    if producto.stock_ideal and producto.stock_ideal < producto.cantidad_minima:
        return {"ok": False, "mensaje": "El stock ideal no puede ser menor que la cantidad mínima."}

    producto.save()
    HistorialModificacionProducto.objects.create(
        producto=producto, usuario=negocio.usuario,
        motivo=(str(motivo).strip() if motivo else "Cambio hecho con el asistente")[:255],
    )
    return {"ok": True, "mensaje": f'Listo, actualicé "{producto.nombre}" ({"; ".join(cambios)}).'}


def ajustar_existencias(negocio, nombre_producto, cantidad, modo):
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
        nueva = anterior + cantidad
    elif modo == "restar":
        nueva = anterior - cantidad
    else:
        nueva = cantidad
    if nueva < 0:
        return {"ok": False, "mensaje": f'De "{producto.nombre}" solo hay {anterior:g}, no se pueden quitar {cantidad:g}.'}

    producto.cantidad_actual = nueva
    producto.save(update_fields=["cantidad_actual", "actualizado_en"])
    HistorialModificacionProducto.objects.create(
        producto=producto, usuario=negocio.usuario,
        motivo=f"Ajuste de existencias con el asistente ({modo} {cantidad:g})",
    )

    mensaje = f'Ahora hay {nueva:g} de "{producto.nombre}" (antes {anterior:g}).'
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


def alta_proveedor(negocio, nombre, telefono="", correo=""):
    nombre = str(nombre).strip()
    if not nombre:
        return {"ok": False, "mensaje": "¿Cómo se llama el proveedor?"}
    if Proveedor.objects.filter(negocio=negocio, nombre__iexact=nombre).exists():
        return {"ok": False, "mensaje": f'Ya tienes registrado a "{nombre}".'}

    Proveedor.objects.create(negocio=negocio, nombre=nombre, telefono=str(telefono or "")[:30], correo=str(correo or ""))
    return {"ok": True, "mensaje": f'Registré al proveedor "{nombre}".'}


def consultar_proveedores(negocio):
    proveedores = Proveedor.objects.filter(negocio=negocio)
    return {
        "proveedores": [
            {"nombre": p.nombre, "telefono": p.telefono, "correo": p.correo}
            for p in proveedores
        ]
    }


# ----------------------------------------------------------- finanzas

def registrar_gasto(negocio, concepto, monto, tipo, categoria=None):
    concepto = str(concepto).strip()
    monto = _decimal(monto)
    tipo = str(tipo).upper()
    if not concepto:
        return {"ok": False, "mensaje": "¿En qué fue el gasto?"}
    if monto is None or monto <= 0:
        return {"ok": False, "mensaje": "¿De cuánto fue el gasto? Necesito un monto mayor a cero."}
    if tipo not in ("FIJO", "VARIABLE"):
        return {"ok": False, "mensaje": "¿El gasto es fijo (como la renta) o variable (como el inventario)?"}

    categoria_gasto = None
    if categoria and str(categoria).strip():
        categoria_gasto, _ = CategoriaGasto.objects.get_or_create(negocio=negocio, nombre=str(categoria).strip())

    gasto = GastoOperativo.objects.create(
        negocio=negocio, concepto=concepto, monto=_dinero(monto), tipo=tipo, categoria=categoria_gasto,
    )
    return {"ok": True, "mensaje": f'Registré el gasto "{gasto.concepto}" por ${gasto.monto:.2f}.'}


def consultar_gastos_mes(negocio):
    hoy = timezone.localdate()
    inicio = calculos.primer_dia_del_mes(hoy)
    fin = calculos.mes_siguiente(inicio)
    ultimos = GastoOperativo.objects.filter(negocio=negocio, fecha__gte=inicio, fecha__lt=fin).order_by("-fecha", "-id")[:5]
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


def sugerir_precio(negocio, nombre_producto, margen_deseado=30):
    producto, error = _buscar_uno(negocio, nombre_producto)
    if error:
        return error

    margen = _decimal(margen_deseado, Decimal("30"))
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
    "consultar_proveedores": consultar_proveedores,
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
        carrito = ver_carrito(negocio)

        lineas = [
            f"Tienda: {negocio.nombre_tienda}. Fecha de hoy: {timezone.localdate().strftime('%d/%m/%Y')}.",
            f"Ventas cobradas hoy: ${ventas['total']:.2f} en {ventas['numero_ventas']} ventas.",
        ]
        if carrito["productos"]:
            detalle = ", ".join(f"{p['cantidad']:g} {p['nombre']}" for p in carrito["productos"][:8])
            lineas.append(f"Carrito actual: {detalle}. Total: ${carrito['total']:.2f}.")
        else:
            lineas.append("Carrito actual: vacío.")
        lineas.append(
            f"Productos por resurtir: {conteo['rojo']} en rojo, {conteo['naranja']} en naranja, "
            f"{conteo['amarillo']} en amarillo."
        )
        return "\n".join(lineas)
    return cache_negocio.obtener(negocio, "contexto_ia", armar)


def historial_reciente(negocio, limite=10):
    """Los últimos mensajes de la conversación, del más viejo al más nuevo,
    para que el AVI pueda resolver referencias como '¿cuánto cuesta?'."""
    mensajes = HistorialConversacion.objects.filter(negocio=negocio).order_by("-creado_en", "-id")[:limite]
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
        "total_gastos": float(calculos.gastos_periodo(negocio, ayer, hoy)),
        "total_antier": float(calculos.ingresos_periodo(negocio, antier, ayer)),
        "mas_vendidos": [f"{fila['producto__nombre']} ({fila['piezas']:g} pzas)" for fila in mas_vendidos],
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


def datos_para_explicar(negocio, tipo):
    """Los números que se le mandan a la IA para que explique el dashboard o los reportes."""
    hoy = timezone.localdate()
    tasa_isr = calculos.tasa_isr_del_negocio(negocio, hoy)
    inicio_mes = calculos.primer_dia_del_mes(hoy)

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
    if datos["tipo"] == "reportes":
        pantalla = "los reportes financieros de mis últimos 3 meses"
    else:
        pantalla = "el resumen de mis finanzas (este mes contra el mes pasado)"
    return (
        f"Explícame {pantalla}. Estos son los números: {datos}. "
        "Dime en 4 o 5 frases cortas qué significan, qué va bien, qué va mal, y dame dos consejos "
        "prácticos para mejorar. Usa palabras de todos los días, sin fórmulas."
    )
