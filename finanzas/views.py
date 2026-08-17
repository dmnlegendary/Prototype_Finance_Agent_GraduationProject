"""
Vista placeholder de `finanzas`, tal como lo pide el alcance de esta
entrega: "sin motor predictivo todavía, solo dejar preparada la
estructura/modelos y una vista placeholder".
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def placeholder(request):
    return render(request, "finanzas/placeholder.html")
