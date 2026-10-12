import json
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Exists, F, OuterRef, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from ventas.models import ItemVenta

from . import busqueda, importacion
from .alertas import conteo_alertas, productos_con_alerta
from .compras import CantidadInvalida, agregar_existencias, registrar_compra, texto_numero
from .forms import ProductoForm, ProveedorForm
from .models import Categoria, HistorialModificacionProducto, Producto, Proveedor

# cuántos renglones se piden cada vez: pocos al abrir la pantalla y más con "Ver más"
# (así carga rápido aunque haya miles de productos y la conexión sea lenta)
PRODUCTOS_POR_LOTE = 20
ALERTAS_POR_LOTE = 20


def _negocio_o_redirect(request):
    """Negocio del usuario en sesión, o None si aún no lo registró."""
    return getattr(request.user, "negocio", None)


def _productos_del_panel(negocio, q="", categoria_id=""):
    """Los productos que se ven en el catálogo, los más críticos (menos piezas sobre su
    mínimo) primero. Incluye los "no encontrados" que todavía no se validan."""
    productos = Producto.objects.filter(negocio=negocio).filter(
        Q(activo=True) | Q(pendiente_validacion=True),
    ).select_related("categoria")

    if q:
        # búsqueda que ignora acentos y tolera errores de dedo (ver inventario/busqueda.py)
        ids = [p["id"] for p in busqueda.encontrar(negocio, q)]
        pendientes = Producto.objects.filter(
            negocio=negocio, pendiente_validacion=True, nombre__icontains=q,
        ).values_list("pk", flat=True)
        productos = productos.filter(pk__in=ids + list(pendientes))
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

    # "con_ventas" se calcula aquí (una sola consulta) para no preguntarlo producto por producto en la tabla
    return productos.annotate(
        holgura=F("cantidad_actual") - F("cantidad_minima"),
        con_ventas=Exists(ItemVenta.objects.filter(producto=OuterRef("pk"))),
    ).order_by("holgura", "nombre")


def _contexto_panel(request, negocio, form_alta=None, form_proveedor=None, form_edicion=None):
    q = request.GET.get("q", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()

    pagina = Paginator(_productos_del_panel(negocio, q, categoria_id), PRODUCTOS_POR_LOTE).get_page(1)
    filtros = {nombre: valor for nombre, valor in (("q", q), ("categoria", categoria_id)) if valor}

    proveedores_lista = list(Proveedor.objects.filter(negocio=negocio).prefetch_related("categorias"))
    for prov in proveedores_lista:
        prov.form_editar = ProveedorForm(instance=prov, auto_id=f"id_proveedor_{prov.pk}_%s")

    form_alta = form_alta or ProductoForm(
        negocio=negocio, auto_id="id_alta_%s",
        initial={"codigo_barras": request.GET.get("nuevo_codigo", "")},
    )
    contexto = {
        "productos": list(pagina.object_list),
        "hay_mas": pagina.has_next(),
        "total_productos": pagina.paginator.count,
        "querystring": urlencode(filtros),
        "categorias": Categoria.objects.all(),
        "q": q,
        "categoria_id": categoria_id,
        "conteo": conteo_alertas(negocio),
        "form_alta": form_alta,
        # el único formulario de edición: se llena con JS al tocar "Editar" (no hay uno por producto)
        "form_edicion": form_edicion or ProductoForm(negocio=negocio, auto_id="id_editar_%s"),
        "proveedores_lista": proveedores_lista,
        "form_proveedor": form_proveedor or ProveedorForm(auto_id="id_proveedor_nuevo_%s"),
    }
    if request.GET.get("nuevo_codigo"):
        contexto["abrir_modal_alta"] = True
    if request.GET.get("abrir", "").isdigit():
        contexto["abrir_edicion_pk"] = int(request.GET["abrir"])
    return contexto


@login_required
def panel(request):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        messages.warning(request, "Primero completa los datos de tu negocio.")
        return redirect("accounts:datos_negocio")

    return render(request, "inventario/panel.html", _contexto_panel(request, negocio))


@login_required
@require_GET
def panel_filas(request):
    """"Ver más": el siguiente lote de renglones del catálogo, ya armados, para agregarlos a la tabla."""
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return JsonResponse({"html": "", "hay_mas": False})

    pagina_pedida = request.GET.get("page", "2")
    pagina = Paginator(
        _productos_del_panel(negocio, request.GET.get("q", "").strip(), request.GET.get("categoria", "").strip()),
        PRODUCTOS_POR_LOTE,
    ).get_page(pagina_pedida if pagina_pedida.isdigit() else 2)
    html = render_to_string("inventario/_filas_productos.html", {"productos": list(pagina.object_list)}, request)
    return JsonResponse({"html": html, "hay_mas": pagina.has_next(), "siguiente": pagina.number + 1})


@login_required
@require_GET
def producto_datos(request, pk):
    """Los datos de un producto, para llenar el formulario de edición."""
    negocio = _negocio_o_redirect(request)
    producto = get_object_or_404(Producto, pk=pk, negocio=negocio)
    return JsonResponse({
        "id": producto.pk,
        "nombre": producto.nombre,
        "descripcion": producto.descripcion,
        "costo": str(producto.costo),
        "precio_venta": str(producto.precio_venta),
        "cantidad_actual": texto_numero(producto.cantidad_actual),
        "cantidad_minima": texto_numero(producto.cantidad_minima),
        "stock_ideal": texto_numero(producto.stock_ideal),
        "categoria": producto.categoria_id,
        "proveedor": producto.proveedor_id,
        "a_granel": producto.a_granel,
        "codigo_barras": producto.codigo_barras,
        "pendiente_validacion": producto.pendiente_validacion,
    })


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
            # las piezas con las que arranca el producto son mercancía que se compró
            compra = registrar_compra(negocio, f"Compra de mercancía: {producto.nombre}", producto.cantidad_actual * producto.costo)
            texto = f'"{producto.nombre}" se dio de alta correctamente.'
            if compra:
                texto += f" Se registró la compra de mercancía por ${compra.monto}."
            messages.success(request, texto)
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
        form = ProductoForm(request.POST, instance=producto, negocio=negocio, auto_id="id_editar_%s")
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

        # se regresa al panel con el modal de edición abierto y lo que el usuario había escrito
        context = _contexto_panel(request, negocio, form_edicion=form)
        context["abrir_edicion_pk"] = producto.pk
        context["edicion_con_errores"] = True
        return render(request, "inventario/panel.html", context)

    return redirect("inventario:panel")


@login_required
@require_POST
def producto_resurtir(request, pk):
    """Llegó mercancía: suma las piezas (o kilos) y registra la compra como gasto.
    También la usa la caja cuando se quiere vender algo que ya no hay."""
    negocio = _negocio_o_redirect(request)
    producto = get_object_or_404(Producto, pk=pk, negocio=negocio, activo=True)

    try:
        datos = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        datos = {}
    if not isinstance(datos, dict):
        datos = {}

    try:
        monto = agregar_existencias(producto, datos.get("cantidad"), costo=datos.get("costo"))
    except CantidadInvalida as error:
        return JsonResponse({"ok": False, "mensaje": str(error)}, status=400)

    return JsonResponse({
        "ok": True,
        "mensaje": f'Agregué la mercancía a "{producto.nombre}": ahora hay {texto_numero(producto.cantidad_actual)} {producto.unidad}.',
        "compra": str(monto),
        "stock": texto_numero(producto.cantidad_actual),
    })


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
        if origen == "editar":
            context["abrir_edicion_sin_datos"] = True
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


def _alertas_filtradas(negocio, q, nivel):
    lista = productos_con_alerta(negocio)
    if nivel in ("rojo", "naranja", "amarillo"):
        lista = [p for p in lista if p.nivel_stock == nivel]
    if q:
        permitidos = {p["id"] for p in busqueda.encontrar(negocio, q)}
        lista = [p for p in lista if p.pk in permitidos]
    return lista


@login_required
def alertas(request):
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    # primero se cargan pocas alertas; el resto con "Ver más" (ver alertas_filas)
    lista = productos_con_alerta(negocio)
    conteo = {"rojo": 0, "naranja": 0, "amarillo": 0}
    for producto in lista:
        conteo[producto.nivel_stock] += 1
    conteo["total"] = len(lista)

    return render(request, "inventario/alertas.html", {
        "alertas": lista[:ALERTAS_POR_LOTE],
        "hay_mas": len(lista) > ALERTAS_POR_LOTE,
        "conteo": conteo,
    })


@login_required
@require_GET
def alertas_filas(request):
    """Alertas por lotes y con búsqueda instantánea: el servidor filtra y regresa solo un lote."""
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return JsonResponse({"html": "", "hay_mas": False})

    lista = _alertas_filtradas(negocio, request.GET.get("q", "").strip(), request.GET.get("nivel", ""))
    pagina_pedida = request.GET.get("page", "1")
    pagina = Paginator(lista, ALERTAS_POR_LOTE).get_page(pagina_pedida if pagina_pedida.isdigit() else 1)
    html = render_to_string("inventario/_alertas_items.html", {"alertas": list(pagina.object_list)}, request)
    return JsonResponse({
        "html": html, "hay_mas": pagina.has_next(), "siguiente": pagina.number + 1, "total": pagina.paginator.count,
    })


@login_required
@require_GET
def buscar_json(request):
    """Búsqueda instantánea para el cuadro de 'Modificar productos'."""
    negocio = _negocio_o_redirect(request)
    q = request.GET.get("q", "").strip()
    if negocio is None or not q:
        return JsonResponse({"resultados": []})

    ids = [p["id"] for p in busqueda.buscar(negocio, q, limite=10)]
    pendientes = list(
        Producto.objects.filter(negocio=negocio, pendiente_validacion=True, nombre__icontains=q).values_list("pk", flat=True)[:5]
    )
    productos = {p.pk: p for p in Producto.objects.filter(pk__in=ids + pendientes)}
    resultados = [
        {
            "id": p.pk, "nombre": p.nombre, "icono": p.icono,
            "precio_venta": str(p.precio_venta), "stock": texto_numero(p.cantidad_actual), "unidad": p.unidad,
        }
        for p in (productos[pk] for pk in ids + pendientes if pk in productos)
    ]
    return JsonResponse({"resultados": resultados})


# ------------------------------------------------------- importar productos (CSV)

@login_required
def importar(request):
    """Paso 1: subir el archivo. Se revisa completo y, si algo está mal, no se carga nada."""
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    errores = []
    if request.method == "POST":
        archivo = request.FILES.get("archivo")
        if archivo is None:
            errores = ["Elige un archivo CSV para importar."]
        elif archivo.size > 3 * 1024 * 1024:
            errores = ["El archivo pesa más de 3 MB. Divídelo en varios."]
        else:
            filas, errores = importacion.leer_csv(archivo.read())
            if not errores:
                request.session["importacion_csv"] = {"archivo": archivo.name, "filas": importacion.clasificar(negocio, filas)}
                return redirect("inventario:importar_revisar")

    return render(request, "inventario/importar.html", {
        "errores": errores[:25],
        "mas_errores": max(len(errores) - 25, 0),
        "obligatorias": importacion.COLUMNAS_OBLIGATORIAS,
        "opcionales": importacion.COLUMNAS_OPCIONALES,
    })


@login_required
def importar_revisar(request):
    """Paso 2: el usuario ve qué pasaría con cada renglón y confirma antes de guardar."""
    negocio = _negocio_o_redirect(request)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    pendiente = request.session.get("importacion_csv")
    if not pendiente:
        messages.info(request, "No hay ninguna importación en proceso. Sube un archivo.")
        return redirect("inventario:importar")
    filas = pendiente["filas"]

    if request.method == "POST":
        decisiones = {}
        for fila in filas:
            # lo que ya existe se actualiza; lo demás solo si el usuario lo confirmó
            eleccion = request.POST.get(f"accion_{fila['fila']}", "")
            if fila["tipo"] in ("existente", "pendiente"):
                decisiones[fila["fila"]] = "actualizar" if eleccion != "omitir" else "omitir"
            elif eleccion == "agregar" or eleccion.startswith("usar:"):
                decisiones[fila["fila"]] = eleccion
        resumen = importacion.aplicar(negocio, filas, decisiones)
        request.session.pop("importacion_csv", None)

        partes = []
        if resumen["agregados"]:
            partes.append(f"{resumen['agregados']} productos nuevos")
        if resumen["actualizados"]:
            partes.append(f"{resumen['actualizados']} actualizados")
        if resumen["activados"]:
            partes.append(f"{resumen['activados']} validados")
        texto = "Importación lista: " + (", ".join(partes) if partes else "no se agregó nada")
        if resumen["compra_total"]:
            texto += f". Compra de mercancía registrada: ${resumen['compra_total']:.2f}"
        messages.success(request, texto + ".")
        for error in resumen["errores"][:5]:
            messages.warning(request, error)
        return redirect("inventario:panel")

    grupos = {tipo: [f for f in filas if f["tipo"] == tipo] for tipo in ("existente", "pendiente", "parecido", "nuevo")}
    return render(request, "inventario/importar_revisar.html", {
        "archivo": pendiente["archivo"], "filas": filas, "grupos": grupos,
        "n_ya_estan": len(grupos["existente"]) + len(grupos["pendiente"]),
    })


@login_required
def importar_cancelar(request):
    request.session.pop("importacion_csv", None)
    return redirect("inventario:panel")


@login_required
def importar_plantilla(request):
    """Un archivo de ejemplo con las columnas correctas."""
    respuesta = HttpResponse(importacion.PLANTILLA, content_type="text/csv; charset=utf-8")
    respuesta["Content-Disposition"] = 'attachment; filename="plantilla_productos.csv"'
    return respuesta
