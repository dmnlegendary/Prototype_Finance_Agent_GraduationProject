# Vistas de accounts: login/logout + registro en 3 pasos (Cuenta -> Negocio -> Productos)
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from core import cache_negocio
from inventario.compras import a_decimal, registrar_compra
from inventario.models import Categoria, Producto, ProductoCatalogo
from ventas.models import ItemVenta

from .forms import EliminarCuentaForm, LoginForm, NegocioForm, RegistroForm


def registro(request):
    """Paso 1: Cuenta. Crea el Usuario y arranca la sesión de una vez."""
    if request.user.is_authenticated:
        return redirect("accounts:datos_negocio")

    if request.method == "POST":
        form = RegistroForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            # hay más de un backend de autenticación, así que hay que decir con cuál se inicia sesión
            auth_login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
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

    errores = []
    elegidos = []
    if request.method == "POST":
        elegidos = request.POST.getlist("productos_catalogo")
        catalogo_items = list(ProductoCatalogo.objects.filter(id__in=elegidos))

        # de cada producto elegido se piden las piezas y lo que costó y se vende cada una
        nuevos = []
        for item in catalogo_items:
            piezas = a_decimal(request.POST.get(f"piezas_{item.id}"))
            costo = a_decimal(request.POST.get(f"costo_{item.id}"))
            precio = a_decimal(request.POST.get(f"precio_{item.id}"))
            if piezas is None or piezas < 0 or piezas != piezas.to_integral_value():
                errores.append(f'"{item.nombre}": escribe cuántas piezas tienes (un número entero, puede ser 0).')
            elif costo is None or costo < 0:
                errores.append(f'"{item.nombre}": escribe cuánto te costó cada pieza.')
            elif precio is None or precio <= 0:
                errores.append(f'"{item.nombre}": escribe en cuánto lo vendes.')
            else:
                nuevos.append(Producto(
                    negocio=negocio, nombre=item.nombre, categoria=item.categoria, icono=item.icono,
                    costo=costo, precio_venta=precio, cantidad_actual=piezas, catalogo_origen=item,
                ))

        if not errores:
            Producto.objects.bulk_create(nuevos)
            # las piezas con las que arranca cada producto son mercancía que se compró
            registrar_compra(negocio, "Compra de mercancía (inventario inicial)", sum((p.cantidad_actual * p.costo for p in nuevos), Decimal("0")))
            # bulk_create no avisa a las señales, así que se limpia el cache a mano
            cache_negocio.invalidar(negocio.pk)
            return redirect("ventas:punto_de_venta")

    context = {
        "productos_catalogo": ProductoCatalogo.objects.select_related("categoria"),
        "categorias": Categoria.objects.all(),
        "errores": errores,
        "elegidos": elegidos,
    }
    return render(request, "accounts/productos_precargados.html", context)


@login_required
def eliminar_cuenta(request):
    """Borra la cuenta por completo (negocio, productos, ventas, gastos…
    todo cae en cascada porque esos modelos apuntan a Negocio, que apunta
    al Usuario). Se pide la contraseña de nuevo para evitar un borrado
    accidental o por una sesión que alguien más dejó abierta."""
    if request.method == "POST":
        form = EliminarCuentaForm(request.POST, usuario=request.user)
        if form.is_valid():
            usuario = request.user
            negocio = getattr(usuario, "negocio", None)
            auth_logout(request)
            if negocio is not None:
                # ItemVenta.producto es PROTECT (para no perder tickets viejos
                # si solo se da de baja un producto); hay que quitar esas filas
                # antes de que la cascada de abajo intente borrar los productos.
                ItemVenta.objects.filter(venta__negocio=negocio).delete()
            usuario.delete()
            messages.info(request, "Tu cuenta y todos tus datos se eliminaron permanentemente.")
            return redirect("accounts:login")
    else:
        form = EliminarCuentaForm(usuario=request.user)

    return render(request, "accounts/eliminar_cuenta.html", {"form": form})


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
