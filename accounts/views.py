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
    """Paso 3: elegir productos del catálogo para crearlos en el negocio."""
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

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        self.request.session["mostrar_resumen_avi"] = True
        return respuesta


class TiendaLogoutView(LogoutView):
    next_page = "accounts:login"
