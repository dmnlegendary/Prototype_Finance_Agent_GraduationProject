from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("sincronizar/", views.sincronizar, name="sincronizar"),
    path("sincronizar/estado/", views.estado_de_la_conexion, name="estado_de_la_conexion"),
    path("sw.js", views.service_worker, name="service_worker"),
    path("terminos/", views.terminos, name="terminos"),
]
