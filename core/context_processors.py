"""
Context processors: funciones que agregan variables a TODAS las plantillas
automáticamente (configuradas en config/settings.py > TEMPLATES > OPTIONS).
"""


def negocio_activo(request):
    """
    Expone `negocio` (el perfil de negocio del usuario en sesión) a todas
    las plantillas, para poder mostrar el nombre de la tienda en el navbar
    (ver templates/partials/navbar.html) sin repetir la consulta en cada
    vista de cada app.

    Devuelve None si no hay usuario autenticado o si aún no completó el
    onboarding (paso "Datos del negocio").
    """
    usuario = getattr(request, "user", None)
    if not usuario or not usuario.is_authenticated:
        return {"negocio": None}

    # Import local para evitar problemas de import circular entre apps.
    negocio = getattr(usuario, "negocio", None)
    return {"negocio": negocio}
