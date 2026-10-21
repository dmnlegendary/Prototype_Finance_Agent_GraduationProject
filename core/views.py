import json
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .sync import aplicar_operaciones

MAXIMO_OPERACIONES_POR_ENVIO = 100


@login_required
@require_POST
def sincronizar(request):
    """Recibe las operaciones que se hicieron sin internet y las guarda (ver core/sync.py)."""
    negocio = getattr(request.user, "negocio", None)
    if negocio is None:
        return JsonResponse({"resultados": [], "mensaje": "Primero completa los datos de tu negocio."}, status=400)

    try:
        datos = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"resultados": []}, status=400)
    operaciones = datos.get("operaciones") if isinstance(datos, dict) else None
    if not isinstance(operaciones, list):
        return JsonResponse({"resultados": []}, status=400)

    resultados = aplicar_operaciones(
        negocio, request.user, [o for o in operaciones[:MAXIMO_OPERACIONES_POR_ENVIO] if isinstance(o, dict)],
    )
    return JsonResponse({"resultados": resultados})


@require_GET
def estado_de_la_conexion(request):
    """El navegador la pide de vez en cuando para saber si ya regresó el internet."""
    return JsonResponse({"ok": True})


@require_GET
def service_worker(request):
    """El service worker tiene que servirse desde la raíz del sitio para poder controlar todas las pantallas."""
    ruta = Path(settings.BASE_DIR) / "static" / "sw.js"
    respuesta = HttpResponse(ruta.read_text(encoding="utf-8"), content_type="text/javascript; charset=utf-8")
    respuesta["Service-Worker-Allowed"] = "/"
    respuesta["Cache-Control"] = "no-cache"
    return respuesta


@require_GET
def terminos(request):
    """Términos y condiciones y aviso de protección de datos (se puede leer sin iniciar sesión)."""
    return render(request, "core/terminos.html")
