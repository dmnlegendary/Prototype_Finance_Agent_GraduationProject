"""
Funciones que el AVI puede ejecutar (function calling) y sus "herramientas"
en el formato que espera cada proveedor de LLM. Para agregar una función
nueva: escribe la función en FUNCIONES_DISPONIBLES y descríbela en
FUNCIONES (nombre, descripción, parámetros).
"""
from django.utils import timezone

from finanzas.models import GastoOperativo
from inventario.models import Producto
from ventas.models import ItemVenta, Venta


FUNCIONES = [
    {
        "name": "buscar_producto",
        "description": "Busca productos del inventario de la tienda por nombre.",
        "parameters": {
            "type": "object",
            "properties": {
                "nombre": {"type": "string", "description": "Nombre o parte del nombre del producto"},
            },
            "required": ["nombre"],
        },
    },
    {
        "name": "agregar_al_carrito",
        "description": "Agrega un producto al carrito de la venta que está en curso.",
        "parameters": {
            "type": "object",
            "properties": {
                "nombre_producto": {"type": "string", "description": "Nombre del producto a agregar"},
                "cantidad": {"type": "number", "description": "Cantidad a agregar, por default 1"},
            },
            "required": ["nombre_producto"],
        },
    },
    {
        "name": "consultar_ventas_hoy",
        "description": "Regresa el total vendido y el número de ventas cobradas el día de hoy.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "consultar_alertas_stock",
        "description": "Regresa los productos cuyo stock está en el mínimo o por debajo.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "registrar_gasto",
        "description": "Registra un gasto operativo del negocio (fijo o variable).",
        "parameters": {
            "type": "object",
            "properties": {
                "concepto": {"type": "string", "description": "Ej. Renta, Luz, Inventario"},
                "monto": {"type": "number", "description": "Monto del gasto en pesos"},
                "tipo": {"type": "string", "enum": ["FIJO", "VARIABLE"], "description": "Tipo de gasto"},
            },
            "required": ["concepto", "monto", "tipo"],
        },
    },
]


def tools_openai():
    """Formato "tools" que espera la API de Chat Completions de OpenAI."""
    return [{"type": "function", "function": f} for f in FUNCIONES]


def tools_gemini():
    """Formato que espera la API de Gemini (google-generativeai)."""
    return [{"function_declarations": FUNCIONES}]


def _venta_en_curso(negocio):
    """Consulta el carrito existente; esta funcion no crea una venta."""
    return Venta.objects.filter(negocio=negocio, estado=Venta.Estado.EN_CURSO).first()


def buscar_producto(negocio, nombre):
    """Lee hasta cinco productos activos, limitados al negocio indicado."""
    productos = Producto.objects.filter(negocio=negocio, activo=True, nombre__icontains=nombre)[:5]
    return {
        "resultados": [
            {"nombre": p.nombre, "precio_venta": float(p.precio_venta), "stock": float(p.cantidad_actual)}
            for p in productos
        ]
    }


def agregar_al_carrito(negocio, nombre_producto, cantidad=1):
    """Lee inventario/carrito y persiste el renglon y total resultantes."""
    producto = Producto.objects.filter(negocio=negocio, activo=True, nombre__icontains=nombre_producto).first()
    if producto is None:
        return {"ok": False, "mensaje": f'No encontré ningún producto parecido a "{nombre_producto}".'}

    venta = _venta_en_curso(negocio)
    if venta is None:
        return {"ok": False, "mensaje": "No hay una venta en curso todavía."}

    item, creado = ItemVenta.objects.get_or_create(
        venta=venta, producto=producto,
        defaults={"cantidad": cantidad, "precio_unitario": producto.precio_venta},
    )
    if not creado:
        item.cantidad += cantidad
        item.save(update_fields=["cantidad"])
    venta.recalcular_total()

    return {"ok": True, "mensaje": f'Agregué {cantidad} de "{producto.nombre}" al carrito.'}


def consultar_ventas_hoy(negocio):
    """Agrega en memoria totales de ventas cobradas hoy para esta tienda."""
    hoy = timezone.localdate()
    ventas = Venta.objects.filter(negocio=negocio, estado=Venta.Estado.COBRADA, creado_en__date=hoy)
    total = sum((v.total for v in ventas), start=0)
    return {"total": float(total), "numero_ventas": ventas.count()}


def consultar_alertas_stock(negocio):
    """Lee el inventario activo del negocio y filtra productos criticos."""
    productos = Producto.objects.filter(negocio=negocio, activo=True)
    criticos = [p for p in productos if p.stock_critico]
    return {
        "productos_criticos": [
            {"nombre": p.nombre, "stock": float(p.cantidad_actual), "minimo": float(p.cantidad_minima)}
            for p in criticos
        ]
    }


def registrar_gasto(negocio, concepto, monto, tipo):
    """Inserta un gasto operativo asociado al negocio recibido."""
    gasto = GastoOperativo.objects.create(negocio=negocio, concepto=concepto, monto=monto, tipo=tipo)
    return {"ok": True, "mensaje": f'Registré el gasto "{gasto.concepto}" por ${gasto.monto}.'}


DESPACHADOR = {
    "buscar_producto": buscar_producto,
    "agregar_al_carrito": agregar_al_carrito,
    "consultar_ventas_hoy": consultar_ventas_hoy,
    "consultar_alertas_stock": consultar_alertas_stock,
    "registrar_gasto": registrar_gasto,
}


def ejecutar_funcion(nombre, argumentos, negocio):
    """Despacha una herramienta del AVI con el negocio como limite de datos."""
    funcion = DESPACHADOR.get(nombre)
    if funcion is None:
        return {"error": f'No existe la función "{nombre}".'}
    return funcion(negocio, **argumentos)
