from django.contrib.auth.decorators import login_required
from django.shortcuts import render


# Todavía sin pronóstico ni cálculo de punto de equilibrio, solo la pantalla base.
@login_required
def placeholder(request):
    return render(request, "finanzas/placeholder.html")
