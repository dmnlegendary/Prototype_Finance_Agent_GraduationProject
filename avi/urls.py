from django.urls import path

from . import views

app_name = "avi"

urlpatterns = [
    path("chat/", views.chat, name="chat"),
]
