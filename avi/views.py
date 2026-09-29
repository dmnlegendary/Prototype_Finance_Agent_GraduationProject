import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services
from .clients import preguntar_chatgpt, preguntar_gemini
from .models import HistorialConversacion, ResumenDiario


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


@login_required
def resumen_diario(request):
    """Muestra el resumen del día que ya generó el trigger de las 7am.
    Si todavía no existe (primer día, negocio nuevo, etc.) lo genera al vuelo y lo guarda."""
    negocio = getattr(request.user, "negocio", None)
    if negocio is None:
        return JsonResponse({"respuesta": "Primero completa los datos de tu negocio."})

    hoy = timezone.localdate()
    resumen = ResumenDiario.objects.filter(negocio=negocio, fecha=hoy).first()
    if resumen:
        return JsonResponse({
            "respuesta": resumen.texto,
            "numero_ventas": resumen.numero_ventas,
            "total_ventas": float(resumen.total_ventas),
            "ganancia": float(resumen.ganancia),
            "total_gastos": float(resumen.total_gastos),
        })

    modelo = request.GET.get("modelo", "chatgpt")
    datos = services.datos_resumen_diario(negocio)
    mensaje = services.construir_mensaje_resumen(datos)

    try:
        if modelo == "gemini":
            respuesta = preguntar_gemini(mensaje, negocio)
        else:
            respuesta = preguntar_chatgpt(mensaje, negocio)
    except ImportError:
        respuesta = "Falta instalar la librería del modelo (pip install -r requirements.txt)."
    except Exception:
        respuesta = "No pude conectarme con el modelo de lenguaje en este momento."
    else:
        ResumenDiario.objects.update_or_create(
            negocio=negocio, fecha=hoy,
            defaults={
                "texto": respuesta,
                "numero_ventas": datos["numero_ventas"],
                "total_ventas": datos["total_ventas"],
                "ganancia": datos["ganancia"],
                "total_gastos": datos["total_gastos"],
            },
        )

    return JsonResponse({"respuesta": respuesta, **datos})
