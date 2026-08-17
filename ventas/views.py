"""
Vista de `ventas`. Por ahora arma el contexto del carrito con datos de
ejemplo (mock), porque todavía no hay lógica de "agregar producto al
carrito" (eso depende de decidir dónde vive el carrito en curso: sesión vs.
un modelo `Venta` en estado EN_CURSO). Se deja el TODO explícito abajo.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def punto_de_venta(request):
    # TODO: reemplazar por datos reales del ORM. La idea es que este
    # `carrito_items` venga de una `Venta` en estado EN_CURSO (o de
    # `request.session`) en vez de estar vacío por defecto. Con la lista
    # vacía, el template ya cae en su bloque {% empty %} ("Carrito vacío"),
    # así que la pantalla funciona igual sin necesidad de datos falsos.
    carrito_items = []
    return render(request, "ventas/punto_de_venta.html", {"carrito_items": carrito_items})
