"""
Vistas de `accounts`: autenticación + wizard de onboarding de 3 pasos
(Cuenta -> Negocio -> Productos), tal como lo marca el stepper de los
mockups (registro.html, datos_negocio.html, productos_precargados.html).
"""
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from inventario.models import Categoria, Producto, ProductoCatalogo

from .forms import LoginForm, NegocioForm, RegistroForm


def registro(request):
    """Paso 1: Cuenta. Crea el Usuario y arranca la sesión de una vez."""
    if request.user.is_authenticated:
        return redirect("accounts:datos_negocio")

    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            auth_login(request, usuario)
            return redirect("accounts:datos_negocio")
    else:
        form = RegistroForm()
    return render(request, "accounts/registro.html", {"form": form})


@login_required
def datos_negocio(request):
    """Paso 2: Negocio. Crea/edita el perfil de la tienda del usuario en sesión."""
    negocio = getattr(request.user, "negocio", None)

    if request.method == "POST":
        form = NegocioForm(request.POST, instance=negocio)
        if form.is_valid():
            negocio = form.save(commit=False)
            negocio.usuario = request.user
            negocio.save()
            return redirect("accounts:productos_precargados")
    else:
        form = NegocioForm(instance=negocio)
    return render(request, "accounts/datos_negocio.html", {"form": form})


@login_required
def productos_precargados(request):
    """
    Paso 3: Productos. Deja elegir productos del catálogo genérico
    (ProductoCatalogo) para "clonarlos" como Producto del negocio en sesión.

    TODO: reemplazar por datos reales del ORM. Aún no existe una base de
    artículos real, así que `productos_catalogo` puede llegar vacío hasta
    que alguien cargue un catálogo (admin de Django o un fixture).
    """
    negocio = getattr(request.user, "negocio", None)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    if request.method == "POST":
        seleccionados = request.POST.getlist("productos_catalogo")
        catalogo_items = ProductoCatalogo.objects.filter(id__in=seleccionados)
        Producto.objects.bulk_create([
            Producto(
                negocio=negocio,
                nombre=item.nombre,
                categoria=item.categoria,
                icono=item.icono,
                costo=item.precio_sugerido,       # TODO: pedir costo real; el catálogo solo trae precio sugerido.
                precio_venta=item.precio_sugerido,
                catalogo_origen=item,
            )
            for item in catalogo_items
        ])
        return redirect("ventas:punto_de_venta")

    context = {
        "productos_catalogo": ProductoCatalogo.objects.select_related("categoria"),
        "categorias": Categoria.objects.all(),
    }
    return render(request, "accounts/productos_precargados.html", context)


class TiendaLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class TiendaLogoutView(LogoutView):
    next_page = "accounts:login"
