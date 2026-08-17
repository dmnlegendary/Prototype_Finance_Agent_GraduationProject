from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("negocio/", views.datos_negocio, name="datos_negocio"),
    path("productos-iniciales/", views.productos_precargados, name="productos_precargados"),
    path("login/", views.TiendaLoginView.as_view(), name="login"),
    path("logout/", views.TiendaLogoutView.as_view(), name="logout"),
]
