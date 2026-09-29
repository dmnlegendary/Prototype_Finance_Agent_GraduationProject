# El carrito es la Venta en estado EN_CURSO del negocio. Las acciones
# (agregar, +/-, cobrar, cancelar) son formularios POST con redirect,
# no Fetch/JSON. La única excepción es la búsqueda instantánea, que sí
# usa fetch/JSON porque necesita responder mientras el usuario escribe.
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from inventario.models import Producto

from .models import ItemVenta, Venta


def _negocio_o_none(request):
    return getattr(request.user, "negocio", None)


def _siguiente_folio(negocio):
    ultima = Venta.objects.filter(negocio=negocio).order_by("-folio").first()
    return (ultima.folio + 1) if ultima else 1


def _venta_en_curso(negocio):
    """Devuelve el carrito abierto del negocio, o crea uno nuevo."""
    venta = Venta.objects.filter(negocio=negocio, estado=Venta.Estado.EN_CURSO).first()
    if venta is None:
        venta = Venta.objects.create(negocio=negocio, folio=_siguiente_folio(negocio))
    return venta


@login_required
def punto_de_venta(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        messages.warning(request, "Primero completa los datos de tu negocio.")
        return redirect("accounts:datos_negocio")

    venta = _venta_en_curso(negocio)
    items = venta.items.select_related("producto").all()

    ticket_venta = None
    ticket_items = None
    ticket_id = request.GET.get("ticket", "").strip()
    if ticket_id:
        ticket_venta = Venta.objects.filter(pk=ticket_id, negocio=negocio, estado=Venta.Estado.COBRADA).first()
        if ticket_venta:
            ticket_items = ticket_venta.items.select_related("producto")

    context = {
        "venta": venta,
        "items": items,
        "ticket_venta": ticket_venta,
        "ticket_items": ticket_items,
        "mostrar_resumen_avi": request.session.pop("mostrar_resumen_avi", False),
    }
    return render(request, "ventas/punto_de_venta.html", context)


def buscar_productos_json(request):
    """Búsqueda instantánea (sin recargar la página) para la barra de ventas."""
    negocio = _negocio_o_none(request)
    if negocio is None:
        return JsonResponse({"resultados": []})

    q = request.GET.get("q", "").strip()
    if not q:
        return JsonResponse({"resultados": []})

    productos = Producto.objects.filter(negocio=negocio, activo=True, nombre__icontains=q)[:8]
    resultados = [
        {"id": p.pk, "nombre": p.nombre, "icono": p.icono, "precio_venta": str(p.precio_venta)}
        for p in productos
    ]
    return JsonResponse({"resultados": resultados, "q": q})


@login_required
def agregar_item(request, producto_pk):
    negocio = _negocio_o_none(request)
    if negocio is None or request.method != "POST":
        return redirect("ventas:punto_de_venta")

    producto = get_object_or_404(Producto, pk=producto_pk, negocio=negocio, activo=True)
    venta = _venta_en_curso(negocio)

    item, creado = ItemVenta.objects.get_or_create(
        venta=venta, producto=producto,
        defaults={"cantidad": 1, "precio_unitario": producto.precio_venta},
    )
    if not creado:
        item.cantidad += 1
        item.save(update_fields=["cantidad"])

    venta.recalcular_total()
    messages.success(request, f'"{producto.nombre}" agregado al carrito.')
    return redirect("ventas:punto_de_venta")


@login_required
@require_POST
def agregar_no_encontrado(request):
    """Alta rápida de un producto que no está en el catálogo, con lo mínimo
    (nombre y precio), para poder cobrarlo de una vez."""
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("ventas:punto_de_venta")

    nombre = request.POST.get("nombre", "").strip()
    try:
        precio = Decimal(request.POST.get("precio", "0").replace(",", "."))
    except InvalidOperation:
        precio = Decimal("0")

    if not nombre or precio <= 0:
        messages.warning(request, "Escribe un nombre y un precio válido para poder cobrarlo.")
        return redirect("ventas:punto_de_venta")

    producto = Producto.objects.create(
        negocio=negocio, nombre=nombre, costo=0, precio_venta=precio,
        cantidad_actual=0, cantidad_minima=0, activo=False,
    )
    venta = _venta_en_curso(negocio)
    ItemVenta.objects.create(venta=venta, producto=producto, cantidad=1, precio_unitario=precio)
    venta.recalcular_total()

    messages.success(request, f'"{nombre}" agregado al carrito.')
    return redirect("ventas:punto_de_venta")


def _cambiar_cantidad(negocio, item_pk, delta):
    item = get_object_or_404(
        ItemVenta, pk=item_pk, venta__negocio=negocio, venta__estado=Venta.Estado.EN_CURSO,
    )
    venta = item.venta
    nueva_cantidad = item.cantidad + delta
    if nueva_cantidad <= 0:
        item.delete()
    else:
        item.cantidad = nueva_cantidad
        item.save(update_fields=["cantidad"])
    venta.recalcular_total()


@login_required
def item_incrementar(request, item_pk):
    negocio = _negocio_o_none(request)
    if negocio is not None and request.method == "POST":
        _cambiar_cantidad(negocio, item_pk, Decimal("1"))
    return redirect(f"{reverse('ventas:punto_de_venta')}?seleccionado={item_pk}")


@login_required
def item_decrementar(request, item_pk):
    negocio = _negocio_o_none(request)
    if negocio is not None and request.method == "POST":
        _cambiar_cantidad(negocio, item_pk, Decimal("-1"))
    return redirect(f"{reverse('ventas:punto_de_venta')}?seleccionado={item_pk}")


@login_required
def cobrar(request):
    negocio = _negocio_o_none(request)
    if negocio is None or request.method != "POST":
        return redirect("ventas:punto_de_venta")

    venta = _venta_en_curso(negocio)
    if not venta.items.exists():
        messages.warning(request, "El carrito está vacío, no hay nada que cobrar.")
        return redirect("ventas:punto_de_venta")

    with transaction.atomic():
        # descuenta el inventario producto por producto, sin dejarlo en negativo
        for item in venta.items.select_related("producto"):
            producto = item.producto
            producto.cantidad_actual = max(producto.cantidad_actual - item.cantidad, Decimal("0"))
            producto.save(update_fields=["cantidad_actual"])

        venta.estado = Venta.Estado.COBRADA
        venta.save(update_fields=["estado"])
        venta.recalcular_total()

    # el ticket se muestra como notificación + modal en la propia pantalla,
    # no en una página aparte
    return redirect(f"{reverse('ventas:punto_de_venta')}?ticket={venta.pk}")


@login_required
def cancelar_venta(request):
    negocio = _negocio_o_none(request)
    if negocio is None or request.method != "POST":
        return redirect("ventas:punto_de_venta")

    venta = _venta_en_curso(negocio)
    if venta.items.exists():
        venta.estado = Venta.Estado.CANCELADA
        venta.save(update_fields=["estado"])
        messages.info(request, "Venta cancelada.")
    return redirect("ventas:punto_de_venta")


@login_required
def historial(request):
    negocio = _negocio_o_none(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    ventas = Venta.objects.filter(negocio=negocio).exclude(estado=Venta.Estado.EN_CURSO).order_by("-creado_en")
    return render(request, "ventas/historial.html", {"ventas": ventas})


@login_required
def ticket(request, pk):
    negocio = _negocio_o_none(request)
    venta = get_object_or_404(Venta, pk=pk, negocio=negocio)
    items = venta.items.select_related("producto")
    return render(request, "ventas/ticket.html", {"venta": venta, "items": items})
