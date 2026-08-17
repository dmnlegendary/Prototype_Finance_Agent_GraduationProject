from django.urls import path

from . import views

app_name = "finanzas"

urlpatterns = [
    path("", views.placeholder, name="placeholder"),
    # TODO (roadmap): path("gastos/", views.gastos, name="gastos")
    # TODO (roadmap): path("equilibrio/", views.punto_de_equilibrio, name="punto_de_equilibrio")
]
