# La pantalla de ventas habla con el servidor por JSON (fetch) para que agregar productos,
# cambiar cantidades o cobrar no recargue la página. Las reglas (existencias, granel,
# dos cajas) viven en ventas/carrito.py y ventas/cobro.py.
import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from inventario import busqueda
from inventario.compras import CantidadInvalida, a_decimal, texto_numero
from inventario.models import Producto

from . import carrito
from .cobro import SinExistencias, VentaYaCobrada, cobrar_venta, texto_aviso_stock
from .models import MAXIMO_DE_CARRITOS, ItemVenta, Venta


def _negocio_o_none(request):
    return getattr(request.user, "negocio", None)


def _datos_json(request):
    try:
        datos = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return {}
    return datos if isinstance(datos, dict) else {}


def _error(mensaje, estado=400, **extra):
    return JsonResponse({"ok": False, "mensaje": mensaje, **extra}, status=estado)


def _sin_existencias(error):
    """409: la regla de oro. La pantalla pregunta cuánto agregar al inventario."""
    producto = error.producto
    return _error(
        error.mensaje, 409, error="sin_existencias", disponible=texto_numero(error.disponible),
        producto={
            "id": producto.pk, "nombre": producto.nombre, "a_granel": producto.a_granel,
            "unidad": producto.unidad, "costo": str(producto.costo), "precio_venta": str(producto.precio_venta),
        },
    )


def _estado(negocio, numero):
    return {"ok": True, **carrito.estado_del_carrito(negocio, numero)}


@login_required
def punto_de_venta(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        messages.warning(request, "Primero completa los datos de tu negocio.")
        return redirect("accounts:datos_negocio")

    numero = carrito.numero_de_carrito_valido(request.GET.get("carrito"))
    recientes = list(
        Producto.objects.filter(negocio=negocio, pendiente_validacion=True)
        .order_by("-actualizado_en").values("nombre", "precio_venta")[:8]
    )
    context = {
        "estado_inicial": carrito.estado_del_carrito(negocio, numero),
        "recientes": [{"nombre": r["nombre"], "precio": str(r["precio_venta"])} for r in recientes],
        "cajas": range(1, MAXIMO_DE_CARRITOS + 1),
        "mostrar_resumen_avi": request.session.pop("mostrar_resumen_avi", False),
    }
    return render(request, "ventas/punto_de_venta.html", context)


def _datos_de_resultado(p):
    """Un producto del catálogo (cache) en el formato que usa la pantalla."""
    return {
        "id": p["id"], "nombre": p["nombre"], "icono": p["icono"], "precio_venta": f"{p['precio']:.2f}",
        "a_granel": p["a_granel"], "unidad": "kg" if p["a_granel"] else "pzas", "stock": f"{p['stock']:g}",
    }


@login_required
@require_GET
def buscar_productos_json(request):
    """Búsqueda instantánea (sin recargar la página) para la barra de ventas.
    Ignora acentos y tolera palabras en otro orden y errores de dedo."""
    negocio = _negocio_o_none(request)
    q = request.GET.get("q", "").strip()
    if negocio is None or not q:
        return JsonResponse({"resultados": []})

    resultados = [_datos_de_resultado(p) for p in busqueda.buscar(negocio, q, limite=8)]
    return JsonResponse({"resultados": resultados, "q": q})


@login_required
@require_GET
def api_codigo(request):
    """Busca un producto por su código de barras (el lector de códigos 'escribe' el código y da Enter)."""
    negocio = _negocio_o_none(request)
    p = busqueda.por_codigo(negocio, request.GET.get("c", "")) if negocio else None
    if p is None:
        return JsonResponse({"encontrado": False})
    return JsonResponse({"encontrado": True, "producto": _datos_de_resultado(p)})


@login_required
@require_GET
def api_catalogo(request):
    """Todo el catálogo activo (liviano) para poder vender sin internet."""
    negocio = _negocio_o_none(request)
    if negocio is None:
        return JsonResponse({"productos": []})
    productos = [
        {**_datos_de_resultado(p), "buscable": p["buscable"], "codigo": p["codigo"]}
        for p in busqueda.catalogo(negocio)
    ]
    return JsonResponse({"productos": productos, "generado": timezone.now().isoformat()})


@login_required
@require_GET
def api_carrito(request, numero):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return _error("Primero completa los datos de tu negocio.")
    return JsonResponse(_estado(negocio, numero))


@login_required
@require_POST
def api_agregar(request, numero):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return _error("Primero completa los datos de tu negocio.")

    datos = _datos_json(request)
    producto = get_object_or_404(Producto, pk=datos.get("producto_id") or 0, negocio=negocio, activo=True)
    venta = carrito.venta_en_curso(negocio, numero, request.user)
    try:
        carrito.agregar_producto(venta, producto, datos.get("cantidad", 1))
    except SinExistencias as error:
        return _sin_existencias(error)
    except CantidadInvalida as error:
        return _error(str(error))
    return JsonResponse(_estado(negocio, numero))


def _item_abierto(request, pk):
    negocio = _negocio_o_none(request)
    return get_object_or_404(
        ItemVenta, pk=pk, venta__negocio=negocio, venta__estado=Venta.Estado.EN_CURSO,
    )


@login_required
@require_POST
def api_cantidad(request, pk):
    """Deja el renglón en la cantidad que se escribió (0 lo quita)."""
    item = _item_abierto(request, pk)
    negocio, numero = item.venta.negocio, item.venta.carrito
    try:
        carrito.cambiar_cantidad(item, _datos_json(request).get("cantidad"))
    except SinExistencias as error:
        return _sin_existencias(error)
    except CantidadInvalida as error:
        return _error(str(error))
    return JsonResponse(_estado(negocio, numero))


@login_required
@require_POST
def api_quitar(request, pk):
    item = _item_abierto(request, pk)
    negocio, numero = item.venta.negocio, item.venta.carrito
    carrito.quitar(item)
    return JsonResponse(_estado(negocio, numero))


@login_required
@require_POST
def api_cobrar(request, numero):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return _error("Primero completa los datos de tu negocio.")

    venta = carrito.venta_en_curso(negocio, numero, request.user)
    if not venta.items.exists():
        return _error("La caja está vacía, no hay nada que cobrar.")

    try:
        productos_que_empeoraron = cobrar_venta(venta)
    except SinExistencias as error:
        return _sin_existencias(error)
    except VentaYaCobrada as error:
        return _error(error.mensaje, estado=409, error="ya_cobrada")

    ahora = timezone.localtime()
    renglones = venta.items.select_related("producto")
    return JsonResponse({
        "ok": True,
        "ticket": {
            "folio": venta.folio,
            "fecha": ahora.strftime("%d/%m/%Y"),
            "hora": ahora.strftime("%H:%M"),
            "total": str(venta.total),
            "tienda": negocio.nombre_tienda,
            "ubicacion": negocio.ubicacion,
            "renglones": [
                {"nombre": r.producto.nombre, "cantidad": texto_numero(r.cantidad), "unidad": r.producto.unidad, "subtotal": str(r.subtotal)}
                for r in renglones
            ],
        },
        "avisos": [{"texto": texto_aviso_stock(p), "nivel": p.nivel_stock} for p in productos_que_empeoraron],
        **carrito.estado_del_carrito(negocio, numero),
    })


@login_required
@require_POST
def api_cancelar(request, numero):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return _error("Primero completa los datos de tu negocio.")
    carrito.cancelar(carrito.venta_en_curso(negocio, numero, request.user))
    return JsonResponse(_estado(negocio, numero))


@login_required
@require_POST
def api_no_encontrado(request, numero):
    """Alta rápida de un producto que no está en el catálogo, con lo mínimo (nombre y
    precio), para poder cobrarlo de una vez. Si ya se había vendido antes, se reutiliza."""
    negocio = _negocio_o_none(request)
    if negocio is None:
        return _error("Primero completa los datos de tu negocio.")

    datos = _datos_json(request)
    nombre = str(datos.get("nombre", "")).strip()
    precio = a_decimal(datos.get("precio"), Decimal("0"))
    if not nombre or precio <= 0:
        return _error("Escribe un nombre y un precio válido para poder cobrarlo.")

    producto = carrito.crear_no_encontrado(negocio, nombre[:150], precio.quantize(Decimal("0.01")))
    carrito.agregar_producto(carrito.venta_en_curso(negocio, numero, request.user), producto, 1)
    return JsonResponse(_estado(negocio, numero))


@login_required
def historial(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    ventas = Venta.objects.filter(negocio=negocio).exclude(estado=Venta.Estado.EN_CURSO).order_by("-creado_en")
    # por páginas, porque un negocio con años de historia tiene miles de ventas
    pagina = Paginator(ventas, 25).get_page(request.GET.get("page"))
    return render(request, "ventas/historial.html", {"ventas": pagina, "pagina": pagina})


@login_required
def ticket(request, pk):
    negocio = _negocio_o_none(request)
    venta = get_object_or_404(Venta, pk=pk, negocio=negocio)
    items = venta.items.select_related("producto")
    return render(request, "ventas/ticket.html", {"venta": venta, "items": items})
