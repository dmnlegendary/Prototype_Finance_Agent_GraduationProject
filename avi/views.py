import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .clients import preguntar_chatgpt, preguntar_gemini
from .models import HistorialConversacion


@login_required
@require_POST
def chat(request):
    negocio = getattr(request.user, "negocio", None)
    if negocio is None:
        return JsonResponse({"respuesta": "Primero completa los datos de tu negocio."})

    try:
        datos = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"respuesta": "No entendí ese mensaje."}, status=400)

    mensaje = datos.get("mensaje", "").strip()
    modelo = datos.get("modelo", "chatgpt")
    if not mensaje:
        return JsonResponse({"respuesta": "Escribe algo para que te pueda ayudar."})

    HistorialConversacion.objects.create(
        negocio=negocio, usuario=request.user, rol=HistorialConversacion.Rol.USUARIO, mensaje=mensaje,
    )

    try:
        if modelo == "gemini":
            respuesta = preguntar_gemini(mensaje, negocio)
        else:
            respuesta = preguntar_chatgpt(mensaje, negocio)
    except ImportError:
        respuesta = "Falta instalar la librería del modelo (pip install -r requirements.txt)."
    except Exception:
        respuesta = "No pude conectarme con el modelo de lenguaje en este momento."

    HistorialConversacion.objects.create(
        negocio=negocio, usuario=request.user, rol=HistorialConversacion.Rol.ASISTENTE, mensaje=respuesta,
    )

    return JsonResponse({"respuesta": respuesta})
