from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .alertas import conteo_alertas, productos_con_alerta
from .forms import ProductoForm, ProveedorForm
from .models import Categoria, HistorialModificacionProducto, Producto, Proveedor

PRODUCTOS_POR_PAGINA = 25


def _negocio_o_redirect(request):
    """Negocio del usuario en sesión, o None si aún no lo registró."""
    return getattr(request.user, "negocio", None)


def _contexto_panel(request, negocio, form_alta=None, form_proveedor=None, solo_pk=None):
    # incluye tanto los productos activos como los "no encontrados" que
    # todavía no se validan (ver Producto.pendiente_validacion)
    productos = Producto.objects.filter(
        negocio=negocio,
    ).filter(Q(activo=True) | Q(pendiente_validacion=True)).select_related("categoria")

    # "abrir" viene del buscador de "Modificar productos": muestra solo ese producto
    abrir = request.GET.get("abrir", "").strip()
    if solo_pk is None and abrir.isdigit():
        solo_pk = int(abrir)
    if solo_pk is not None:
        productos = productos.filter(pk=solo_pk)

    q = request.GET.get("q", "").strip()
    if q:
        productos = productos.filter(nombre__icontains=q)

    categoria_id = request.GET.get("categoria", "").strip()
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

    # los más críticos (más por debajo de su mínimo) primero, ordenados desde la base de datos
    productos = productos.annotate(holgura=F("cantidad_actual") - F("cantidad_minima")).order_by("holgura", "nombre")

    # se muestran por páginas: con miles de productos no se puede dibujar todo junto
    pagina = Paginator(productos, PRODUCTOS_POR_PAGINA).get_page(request.GET.get("page"))
    lista_productos = list(pagina.object_list)
    for p in lista_productos:
        p.form_editar = ProductoForm(instance=p, negocio=negocio, auto_id=f"id_producto_{p.pk}_%s")

    # para que los links de "anterior / siguiente" conserven la búsqueda y el filtro
    filtros = {nombre: valor for nombre, valor in (("q", q), ("categoria", categoria_id)) if valor}

    proveedores_lista = list(Proveedor.objects.filter(negocio=negocio).prefetch_related("categorias"))
    for prov in proveedores_lista:
        prov.form_editar = ProveedorForm(instance=prov, auto_id=f"id_proveedor_{prov.pk}_%s")

    contexto = {
        "productos": lista_productos,
        "pagina": pagina,
        "querystring": urlencode(filtros),
        "categorias": Categoria.objects.all(),
        "q": q,
        "categoria_id": categoria_id,
        "conteo": conteo_alertas(negocio),
        "form_alta": form_alta or ProductoForm(negocio=negocio, auto_id="id_alta_%s"),
        "proveedores_lista": proveedores_lista,
        "form_proveedor": form_proveedor or ProveedorForm(auto_id="id_proveedor_nuevo_%s"),
    }
    if solo_pk is not None and lista_productos:
        contexto["abrir_modal_editar_pk"] = solo_pk
    return contexto


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
        motivo = request.POST.get("motivo", "").strip()

        if form.is_valid() and motivo:
            era_pendiente = producto.pendiente_validacion
            producto = form.save(commit=False)
            if era_pendiente:
                producto.activo = True
                producto.pendiente_validacion = False
            producto.save()
            form.save_m2m()
            HistorialModificacionProducto.objects.create(
                producto=producto, usuario=request.user, motivo=motivo,
            )
            if era_pendiente:
                messages.success(request, f'"{producto.nombre}" se validó y ya aparece en tu catálogo.')
            else:
                messages.success(request, f'"{producto.nombre}" se actualizó correctamente.')
            return redirect("inventario:panel")

        if not motivo:
            form.add_error(None, "Indica el motivo del cambio.")

        # se muestra solo este producto (no se sabe en qué página estaba) con su modal abierto
        context = _contexto_panel(request, negocio, solo_pk=producto.pk)
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

        if origen.startswith("editar-") and origen.split("-", 1)[1].isdigit():
            context = _contexto_panel(request, negocio, solo_pk=int(origen.split("-", 1)[1]))
        else:
            context = _contexto_panel(request, negocio)
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

    # ya vienen ordenadas: primero las rojas, luego naranjas y amarillas
    lista = productos_con_alerta(negocio)
    conteo = {"rojo": 0, "naranja": 0, "amarillo": 0}
    for producto in lista:
        conteo[producto.nivel_stock] += 1
    conteo["total"] = len(lista)

    return render(request, "inventario/alertas.html", {
        "alertas": lista,
        "conteo": conteo,
    })


@login_required
def buscar_json(request):
    """Búsqueda instantánea para el cuadro de 'Modificar productos'."""
    negocio = _negocio_o_redirect(request)
    q = request.GET.get("q", "").strip()
    if negocio is None or not q:
        return JsonResponse({"resultados": []})

    productos = Producto.objects.filter(
        negocio=negocio, nombre__icontains=q,
    ).filter(Q(activo=True) | Q(pendiente_validacion=True))[:10]
    resultados = [
        {
            "id": p.pk, "nombre": p.nombre, "icono": p.icono,
            "precio_venta": str(p.precio_venta), "stock": str(p.cantidad_actual),
        }
        for p in productos
    ]
    return JsonResponse({"resultados": resultados})
