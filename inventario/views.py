from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProductoForm, ProveedorForm
from .models import Categoria, Producto, Proveedor


def _negocio_o_redirect(request):
    """Negocio del usuario en sesión, o None si aún no lo registró."""
    return getattr(request.user, "negocio", None)


def _contexto_panel(request, negocio, form_alta=None, form_proveedor=None):
    productos = Producto.objects.filter(negocio=negocio, activo=True).select_related("categoria")

    q = request.GET.get("q", "").strip()
    if q:
        productos = productos.filter(nombre__icontains=q)

    categoria_id = request.GET.get("categoria", "").strip()
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

    productos = list(productos)
    for p in productos:
        p.form_editar = ProductoForm(instance=p, negocio=negocio, auto_id=f"id_producto_{p.pk}_%s")

    # productos con cantidad_actual <= cantidad_minima (se comparan dos campos, por eso F())
    alertas_count = Producto.objects.filter(
        negocio=negocio, activo=True, cantidad_actual__lte=F("cantidad_minima"),
    ).count()

    proveedores_lista = list(Proveedor.objects.filter(negocio=negocio).prefetch_related("categorias"))
    for prov in proveedores_lista:
        prov.form_editar = ProveedorForm(instance=prov, auto_id=f"id_proveedor_{prov.pk}_%s")

    return {
        "productos": productos,
        "categorias": Categoria.objects.all(),
        "q": q,
        "categoria_id": categoria_id,
        "alertas_count": alertas_count,
        "form_alta": form_alta or ProductoForm(negocio=negocio, auto_id="id_alta_%s"),
        "proveedores_lista": proveedores_lista,
        "form_proveedor": form_proveedor or ProveedorForm(auto_id="id_proveedor_nuevo_%s"),
    }


@login_required
def panel(request):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        messages.warning(request, "Primero completa los datos de tu negocio.")
        return redirect("accounts:datos_negocio")

    return render(request, "inventario/panel.html", _contexto_panel(request, negocio))


@login_required
def producto_alta(request):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    if request.method == "POST":
        form = ProductoForm(request.POST, negocio=negocio, auto_id="id_alta_%s")
        if form.is_valid():
            producto = form.save(commit=False)
            producto.negocio = negocio
            producto.save()
            messages.success(request, f'"{producto.nombre}" se dio de alta correctamente.')
            return redirect("inventario:panel")

        # si el modal tiene errores, se regresa al panel con el modal ya abierto
        context = _contexto_panel(request, negocio, form_alta=form)
        context["abrir_modal_alta"] = True
        return render(request, "inventario/panel.html", context)

    return redirect("inventario:panel")


@login_required
def producto_editar(request, pk):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    producto = get_object_or_404(Producto, pk=pk, negocio=negocio)

    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto, negocio=negocio, auto_id=f"id_producto_{producto.pk}_%s")
        if form.is_valid():
            form.save()
            messages.success(request, f'"{producto.nombre}" se actualizó correctamente.')
            return redirect("inventario:panel")

        context = _contexto_panel(request, negocio)
        for p in context["productos"]:
            if p.pk == producto.pk:
                p.form_editar = form
        context["abrir_modal_editar_pk"] = producto.pk
        return render(request, "inventario/panel.html", context)

    return redirect("inventario:panel")


@login_required
def categoria_alta(request):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        icono = request.POST.get("icono", "").strip() or "📦"
        origen = request.POST.get("origen", "alta")

        if nombre:
            _, creada = Categoria.objects.get_or_create(nombre=nombre, defaults={"icono": icono})
            if creada:
                messages.success(request, f'Categoría "{nombre}" agregada.')
            else:
                messages.info(request, f'Ya existía una categoría "{nombre}".')

        context = _contexto_panel(request, negocio)
        if origen.startswith("editar-"):
            context["abrir_modal_editar_pk"] = origen.split("-", 1)[1]
        else:
            context["abrir_modal_alta"] = True
        return render(request, "inventario/panel.html", context)

    return redirect("inventario:panel")


@login_required
def producto_eliminar(request, pk):
    negocio = _negocio_o_redirect(request)
    producto = get_object_or_404(Producto, pk=pk, negocio=negocio)
    if request.method == "POST":
        # no se borra de verdad, para no perder el historial de ventas que ya lo usan
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
        form = ProveedorForm(request.POST, auto_id="id_proveedor_nuevo_%s")
        if form.is_valid():
            proveedor = form.save(commit=False)
            proveedor.negocio = negocio
            proveedor.save()
            form.save_m2m()
            messages.success(request, f'Proveedor "{proveedor.nombre}" agregado.')
            return redirect("inventario:panel")

        context = _contexto_panel(request, negocio, form_proveedor=form)
        context["abrir_modal_proveedores"] = True
        return render(request, "inventario/panel.html", context)

    return redirect("inventario:panel")


@login_required
def proveedor_editar(request, pk):
    negocio = _negocio_o_redirect(request)
    proveedor = get_object_or_404(Proveedor, pk=pk, negocio=negocio)

    if request.method == "POST":
        form = ProveedorForm(request.POST, instance=proveedor, auto_id=f"id_proveedor_{proveedor.pk}_%s")
        if form.is_valid():
            form.save()
            messages.success(request, f'Proveedor "{proveedor.nombre}" actualizado.')
            return redirect("inventario:panel")

        context = _contexto_panel(request, negocio)
        for prov in context["proveedores_lista"]:
            if prov.pk == proveedor.pk:
                prov.form_editar = form
        context["abrir_modal_proveedor_editar_pk"] = proveedor.pk
        return render(request, "inventario/panel.html", context)

    return redirect("inventario:panel")


@login_required
def alertas(request):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    productos = Producto.objects.filter(negocio=negocio, activo=True).select_related("categoria", "proveedor")
    criticos = [p for p in productos if p.stock_critico]
    # todavía no está crítico, pero ya va por debajo del doble de su mínimo
    advertencia = [
        p for p in productos
        if not p.stock_critico and p.cantidad_minima and p.cantidad_actual <= p.cantidad_minima * 2
    ]
    return render(request, "inventario/alertas.html", {
        "criticos": criticos,
        "advertencia": advertencia,
    })
