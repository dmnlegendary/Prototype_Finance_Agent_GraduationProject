import hashlib
import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import services
from .clients import (
    MENSAJE_SIN_LLAVE, SinLlaveError, generar_texto, modelo_disponible,
    preguntar_chatgpt, preguntar_gemini,
)
from .models import ExplicacionIA, HistorialConversacion, ResumenDiario

registro = logging.getLogger(__name__)

MENSAJE_SIN_LIBRERIA = "Falta instalar la librería del modelo (pip install -r requirements.txt)."
MENSAJE_SIN_CONEXION = "No pude conectarme con el modelo de lenguaje en este momento."


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
    modelo = modelo_disponible(datos.get("modelo", "chatgpt"))
    if not mensaje:
        return JsonResponse({"respuesta": "Escribe algo para que te pueda ayudar."})

    # ojo: el historial se guarda HASTA ABAJO, después de llamar al LLM, para
    # que preguntar_chatgpt/preguntar_gemini no se encuentren este mismo
    # mensaje duplicado al armar el contexto de la conversación.
    try:
        if modelo == "gemini":
            respuesta, funciones = preguntar_gemini(mensaje, negocio)
        else:
            respuesta, funciones = preguntar_chatgpt(mensaje, negocio)
    except ImportError:
        respuesta, funciones = MENSAJE_SIN_LIBRERIA, []
    except Exception:
        registro.exception("Falló la llamada al modelo de lenguaje")
        respuesta, funciones = MENSAJE_SIN_CONEXION, []

    HistorialConversacion.objects.create(
        negocio=negocio, usuario=request.user, rol=HistorialConversacion.Rol.USUARIO, mensaje=mensaje,
    )
    HistorialConversacion.objects.create(
        negocio=negocio, usuario=request.user, rol=HistorialConversacion.Rol.ASISTENTE, mensaje=respuesta,
    )

    refrescar = any(f in services.FUNCIONES_QUE_CAMBIAN_LA_VISTA for f in funciones)
    return JsonResponse({"respuesta": respuesta, "refrescar": refrescar})


@login_required
def resumen_diario(request):
    """El resumen de "cómo te fue ayer". La primera vez que entra el tendero en
    el día se pide a la IA y se guarda; el resto del día se reutiliza ese mismo."""
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
        respuesta = generar_texto(mensaje, modelo)
    except SinLlaveError:
        respuesta = MENSAJE_SIN_LLAVE
    except ImportError:
        respuesta = MENSAJE_SIN_LIBRERIA
    except Exception:
        registro.exception("Falló el resumen diario con la IA")
        respuesta = MENSAJE_SIN_CONEXION
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


@login_required
def explicar(request, tipo):
    """La IA explica el dashboard o los reportes financieros con palabras sencillas.

    Para no gastar llamadas de más: si ya se explicó hoy y los números son los
    mismos (misma "huella"), se muestra la explicación guardada."""
    if tipo not in ExplicacionIA.Tipo.values:
        raise Http404("Ese tipo de explicación no existe.")

    negocio = getattr(request.user, "negocio", None)
    if negocio is None:
        return JsonResponse({"respuesta": "Primero completa los datos de tu negocio."})

    datos = services.datos_para_explicar(negocio, tipo)
    huella = hashlib.sha256(json.dumps(datos, sort_keys=True, default=str).encode()).hexdigest()
    hoy = timezone.localdate()

    guardada = ExplicacionIA.objects.filter(negocio=negocio, tipo=tipo, fecha=hoy).first()
    if guardada and guardada.huella == huella:
        return JsonResponse({"respuesta": guardada.texto, "guardada": True})

    try:
        respuesta = generar_texto(services.construir_mensaje_explicacion(datos), request.GET.get("modelo", "chatgpt"))
    except SinLlaveError:
        return JsonResponse({"respuesta": MENSAJE_SIN_LLAVE})
    except ImportError:
        return JsonResponse({"respuesta": MENSAJE_SIN_LIBRERIA})
    except Exception:
        registro.exception("Falló la explicación con la IA")
        return JsonResponse({"respuesta": MENSAJE_SIN_CONEXION})

    ExplicacionIA.objects.update_or_create(
        negocio=negocio, tipo=tipo, fecha=hoy, defaults={"huella": huella, "texto": respuesta},
    )
    return JsonResponse({"respuesta": respuesta, "guardada": False})
