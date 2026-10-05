# Vistas de accounts: login/logout + registro en 3 pasos (Cuenta -> Negocio -> Productos)
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
    """Crea o actualiza el negocio asociado uno-a-uno al usuario en sesion.

    El `instance` del formulario es el negocio existente, si lo hay; por eso
    `save()` inserta en el primer registro y actualiza en visitas posteriores.
    La vista asigna el propietario desde la sesion, nunca desde el formulario.
    """
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
    """Copia al inventario de la tienda los productos de catalogo elegidos.

    El catalogo es global y solo se lee aqui; `bulk_create` genera productos
    nuevos vinculados al negocio actual en una sola operacion masiva.
    """
    negocio = getattr(request.user, "negocio", None)
    if negocio is None:
        return redirect("accounts:datos_negocio")

    if request.method == "POST":
        seleccionados = request.POST.getlist("productos_catalogo")
        catalogo_items = ProductoCatalogo.objects.filter(id__in=seleccionados)
        # Cada seleccion se vuelve una fila propia; no se modifica el catalogo compartido.
        Producto.objects.bulk_create([
            Producto(
                negocio=negocio,
                nombre=item.nombre,
                categoria=item.categoria,
                icono=item.icono,
                costo=item.precio_sugerido,
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
