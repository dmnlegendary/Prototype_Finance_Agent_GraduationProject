from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("cuenta/", include("accounts.urls")),
    path("inventario/", include("inventario.urls")),
    path("ventas/", include("ventas.urls")),
    path("finanzas/", include("finanzas.urls")),
    path("avi/", include("avi.urls")),

    # la raíz del sitio manda directo al punto de venta
    path("", RedirectView.as_view(pattern_name="ventas:punto_de_venta", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
