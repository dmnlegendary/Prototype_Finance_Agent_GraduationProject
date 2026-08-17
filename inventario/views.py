"""
Vistas de `inventario`. Todo lo que se muestra aquí viene del ORM — nada de
datos de ejemplo. Si una lista sale vacía es porque el negocio en sesión
todavía no tiene ese dato cargado (comportamiento correcto, no un bug).
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductoForm, ProveedorForm
from .models import Categoria, Producto, Proveedor


def _negocio_o_redirect(request):
    """
    Devuelve el Negocio del usuario en sesión, o None si todavía no
    completó el onboarding (paso 2). Las vistas de esta app requieren un
    Negocio para poder filtrar todo por él.
    """
    return getattr(request.user, "negocio", None)


@login_required
def panel(request):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        messages.warning(request, "Primero completa los datos de tu negocio.")
        return redirect("accounts:datos_negocio")

    productos = Producto.objects.filter(negocio=negocio, activo=True).select_related("categoria")

    q = request.GET.get("q", "").strip()
    if q:
        productos = productos.filter(nombre__icontains=q)

    categoria_id = request.GET.get("categoria", "").strip()
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

    # Conteo de productos en estado crítico (cantidad_actual <= cantidad_minima),
    # comparando dos campos del MISMO registro -> requiere F(), no un valor fijo.
    alertas_count = Producto.objects.filter(
        negocio=negocio, activo=True, cantidad_actual__lte=F("cantidad_minima"),
    ).count()

    context = {
        "productos": productos,
        "categorias": Categoria.objects.all(),
        "q": q,
        "categoria_id": categoria_id,
        "alertas_count": alertas_count,
    }
    return render(request, "inventario/panel.html", context)


@login_required
def producto_alta(request):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    if request.method == "POST":
        form = ProductoForm(request.POST, negocio=negocio)
        if form.is_valid():
            producto = form.save(commit=False)
            producto.negocio = negocio
            producto.save()
            messages.success(request, f'"{producto.nombre}" se dio de alta correctamente.')
            return redirect("inventario:panel")
    else:
        form = ProductoForm(negocio=negocio)

    return render(request, "inventario/producto_form.html", {"form": form, "modo": "alta"})


@login_required
def producto_editar(request, pk):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    producto = get_object_or_404(Producto, pk=pk, negocio=negocio)

    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto, negocio=negocio)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{producto.nombre}" se actualizó correctamente.')
            return redirect("inventario:panel")
    else:
        form = ProductoForm(instance=producto, negocio=negocio)

    return render(request, "inventario/producto_form.html", {
        "form": form, "modo": "editar", "producto": producto,
    })


@login_required
def producto_eliminar(request, pk):
    negocio = _negocio_o_redirect(request)
    producto = get_object_or_404(Producto, pk=pk, negocio=negocio)
    if request.method == "POST":
        # Baja lógica: se desactiva en vez de borrarse, para no perder el
        # historial de ventas que ya lo referencian (ItemVenta.producto
        # usa on_delete=PROTECT precisamente por esto).
        producto.activo = False
        producto.save(update_fields=["activo"])
        messages.success(request, f'"{producto.nombre}" se dio de baja.')
    return redirect("inventario:panel")


@login_required
def proveedores(request):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    if request.method == "POST":
        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.negocio = negocio
            proveedor.save()
            form.save_m2m()
            messages.success(request, f'Proveedor "{proveedor.nombre}" agregado.')
            return redirect("inventario:proveedores")
    else:
        form = ProveedorForm()

    return render(request, "inventario/proveedores.html", {
        "form": form,
        "proveedores": Proveedor.objects.filter(negocio=negocio).prefetch_related("categorias"),
    })


@login_required
def proveedor_editar(request, pk):
    negocio = _negocio_o_redirect(request)
    proveedor = get_object_or_404(Proveedor, pk=pk, negocio=negocio)

    if request.method == "POST":
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Proveedor "{proveedor.nombre}" actualizado.')
            return redirect("inventario:proveedores")
    else:
        form = ProveedorForm(instance=proveedor)

    return render(request, "inventario/proveedores.html", {
        "form": form,
        "proveedor_editando": proveedor,
        "proveedores": Proveedor.objects.filter(negocio=negocio).prefetch_related("categorias"),
    })


@login_required
def alertas(request):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    productos = Producto.objects.filter(negocio=negocio, activo=True).select_related("categoria", "proveedor")
    criticos = [p for p in productos if p.stock_critico]
    # "Advertencia": no está crítico todavía, pero ya está a menos del
    # doble de su mínimo (umbral simple, ajustable a futuro).
    advertencia = [
        p for p in productos
        if not p.stock_critico and p.cantidad_minima and p.cantidad_actual <= p.cantidad_minima * 2
    ]
    return render(request, "inventario/alertas.html", {
        "criticos": criticos,
        "advertencia": advertencia,
    })
