"""
Vistas de `inventario`. Por ahora solo la vista de panel principal, que
alimenta la tabla del estado "normal" (ver templates/inventario/panel.html)
con el inventario real del negocio en sesión.

TODO (roadmap, no en esta entrega): vistas para procesar el alta/edición de
producto y de proveedor (los formularios ya están maquetados en los paneles
laterales de panel.html: #panel-alta, #panel-modificar, #panel-proveedores),
y una vista de alertas de reabastecimiento basada en `Producto.stock_critico`.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Producto


@login_required
def panel(request):
    negocio = getattr(request.user, "negocio", None)
    productos = (
        Producto.objects.filter(negocio=negocio, activo=True).select_related("categoria")
        if negocio else Producto.objects.none()
    )
    return render(request, "inventario/panel.html", {"productos": productos})
