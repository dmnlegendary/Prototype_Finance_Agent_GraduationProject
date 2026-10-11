# Notas de arquitectura

Cómo está organizado el proyecto de Django, para no perder el hilo entre entregas.

## Carpetas

```
config/         configuración del proyecto (settings, urls)
core/           cosas compartidas (ModeloBase, cache por negocio, importar_csv, context processor del navbar)
accounts/       usuarios, login/registro, datos del negocio (Seguridad y autenticación)
inventario/     productos, proveedores, alertas de stock (Inventario y alertas)
ventas/         punto de venta y carrito (Ventas y carrito)
finanzas/       gastos, reportes, punto de equilibrio, precios sugeridos y fórmulas (calculos.py)
avi/            asistente conversacional: chat con ChatGPT/Gemini, funciones, resúmenes con IA y configurar_ia
templates/      base.html, base_auth.html, base_app.html y el navbar
static/         css/js que comparten varias pantallas
```

Cada app tiene su propio `templates/<app>/` y (si aplica) `static/<app>/`.

## Estado actual

- Cuenta: registro en 3 pasos, login con correo o teléfono, recuperar contraseña (el correo sale en
  la terminal en modo desarrollo) y eliminar cuenta: funcionando.
- Inventario (alta, edición con motivo, baja, proveedores, alertas, productos pendientes de validar): funcionando.
- Ventas (carrito, cobro, ticket, historial): funcionando, con formularios POST + redirect;
  solo la búsqueda y el chat usan fetch.
- Finanzas: gastos con categorías, reportes, punto de equilibrio por categoría y precios sugeridos
  con fórmulas reales (todas en `finanzas/calculos.py`). El pronóstico sigue como maqueta.
- AVI: chat con ChatGPT o Gemini usando function calling, memoria de los últimos 10 mensajes,
  dictado por voz y resumen diario guardado en la base (una llamada a la IA por día).
- Semáforo de reabastecimiento (amarillo / naranja / rojo según el stock ideal), campana de alertas en el navbar y búsqueda instantánea en las alertas.
- Base de datos PostgreSQL con índices y restricciones (ver `database/README.md`) y carga masiva desde CSV.
- Cache por negocio (`core/cache_negocio.py`) para alertas, ventas de hoy, catálogo del asistente y resumen financiero; se invalida con señales (`core/signals.py`).
- Pruebas automáticas: `python manage.py test` (unitarias y de integración en cada app).

## Pendiente

- [ ] Modelo de pronóstico de ventas (fase 2): elegir método (promedio móvil, ARIMA, regresión, etc.).
- [ ] Prueba de aceptación con tenderos.
- [ ] Video introductorio del tutorial.
- [x] Paginación del catálogo, historial de ventas e historial de gastos (25 por página).
- [ ] Servicio de correo real y configuración de producción (DEBUG, SECRET_KEY, servidor).
- [ ] Conectar Power BI a la base de datos para los reportes.
