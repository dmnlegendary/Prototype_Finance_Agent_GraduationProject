def negocio_activo(request):
    """Agrega la variable `negocio` a todas las plantillas (para el navbar)."""
    usuario = getattr(request, "user", None)
    if not usuario or not usuario.is_authenticated:
        return {"negocio": None}

    negocio = getattr(usuario, "negocio", None)
    return {"negocio": negocio}
