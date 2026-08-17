"""
Enrutamiento raíz del proyecto.

Regla del monolito modular: este archivo NO conoce el detalle de cada app,
solo las "conecta" con un prefijo e importa su propio `urls.py`. Cada app es
responsable de sus propias rutas internas (ver <app>/urls.py).
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Cada app expone su propio namespace de URLs (app_name en <app>/urls.py),
    # así se puede usar {% url 'ventas:punto_de_venta' %} en templates sin
    # ambigüedad, incluso si dos apps reutilizan nombres de vista.
    path("cuenta/", include("accounts.urls")),
    path("inventario/", include("inventario.urls")),
    path("ventas/", include("ventas.urls")),
    path("finanzas/", include("finanzas.urls")),

    # AVI: placeholder. El módulo ya está "enchufado" al proyecto (app +
    # urls.py vacío) para que, cuando se implemente el asistente virtual,
    # NO sea necesario tocar este archivo ni reestructurar el proyecto:
    # solo se agregan paths dentro de avi/urls.py.
    path("avi/", include("avi.urls")),

    # Redirige la raíz del sitio al punto de venta (pantalla principal del
    # día a día de la tienda). TODO: si prefieren un dashboard/home distinto,
    # cambien esto por una vista propia en `core`.
    path("", RedirectView.as_view(pattern_name="ventas:punto_de_venta", permanent=False)),
]

# Sirve archivos de MEDIA (ej. fotos de producto) en desarrollo. En
# producción esto lo debe servir el servidor web / Azure Blob Storage, no Django.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
