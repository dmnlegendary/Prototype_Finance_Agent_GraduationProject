from django.conf import settings

from inventario.alertas import conteo_alertas, nivel_mas_urgente


def negocio_activo(request):
    """Agrega a todas las plantillas la variable `negocio` y el conteo de
    alertas de reabastecimiento (para la campana del navbar)."""
    usuario = getattr(request, "user", None)
    if not usuario or not usuario.is_authenticated:
        return {"negocio": None}

    negocio = getattr(usuario, "negocio", None)
    if negocio is None:
        return {"negocio": None}

    conteo = conteo_alertas(negocio)
    return {
        "negocio": negocio,
        "alertas_conteo": conteo,
        "alertas_nivel": nivel_mas_urgente(conteo),
        # el video de presentación se muestra solo la primera vez que entra, y solo si ya hay un enlace
        "video_bienvenida": settings.VIDEO_INTRODUCTORIO_URL if not usuario.video_visto else "",
        # la guía de los colores también se muestra solo la primera vez
        "guia_colores": not usuario.guia_colores_vista,
    }
