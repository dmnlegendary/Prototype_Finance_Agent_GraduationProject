from django.urls import path

from . import views

app_name = "avi"

urlpatterns = [
    path("chat/", views.chat, name="chat"),
    path("resumen/", views.resumen_diario, name="resumen_diario"),
]
