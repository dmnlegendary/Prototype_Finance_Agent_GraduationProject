# Notas de arquitectura

Cómo está organizado el proyecto de Django, para no perder el hilo entre entregas. El detalle de instalación y configuración está en el manual técnico (`docs/capitulos_tt2/13_anexo_b_manual_tecnico.md`).

## Carpetas

```
config/         configuración del proyecto (settings, urls)
core/           lo compartido: ModeloBase, caché por negocio, sincronización sin internet, llaves cifradas, términos y condiciones, importar_csv
accounts/       usuarios, login/registro (con términos y condiciones), datos del negocio, preferencias
inventario/     productos, proveedores, alertas, kardex, lotes de compra, importación CSV, datos base (catálogo, proveedores, íconos)
ventas/         punto de venta con dos cajas, cobro y regla de oro
finanzas/       gastos con mes, reportes, reporte de ventas, punto de equilibrio, precios, pronóstico y gráficas (calculos.py y graficas.py)
avi/            asistente: chat con Gemini/ChatGPT por function calling, resúmenes y explicaciones con IA, configurar_ia
templates/      base.html, base_auth.html, base_app.html y los parciales (navbar, ayuda, guía de colores)
static/         css/js compartidos y el service worker (sw.js)
```

Cada app tiene su propio `templates/<app>/` y, si aplica, `static/<app>/`.

## Reglas que viven en un solo lugar

- Precio de venta nunca menor al costo: `inventario/compras.py` (`mensaje_si_vende_bajo_el_costo`).
- Toda entrada de mercancía (alta, resurtir, CSV, asistente) pasa por `inventario/compras.py` y deja un gasto de compra.
- Todo cambio de existencias deja un movimiento en el kardex (`inventario/movimientos.py`) y abre o gasta lotes (`inventario/lotes.py`, método PEPS).
- El stock ideal es el promedio de las existencias tras cada carga de mercancía (`inventario/movimientos.py`).
- Regla de oro y cobro único: `ventas/cobro.py`.
- Fórmulas financieras y pronóstico: `finanzas/calculos.py`; datos de las gráficas: `finanzas/graficas.py`.
- Las pantallas y el asistente llaman a las mismas funciones (`avi/services.py` usa los módulos de arriba).

## Estado actual

- Registro en 3 pasos con aceptación de términos, login con correo o teléfono, recuperación de contraseña y eliminar cuenta.
- Guía de colores y video de bienvenida la primera vez que se entra.
- Inventario: alta, edición con motivo, baja, proveedores, alertas por ritmo de venta, kardex, importación CSV y catálogo precargado.
- Ventas: dos cajas, búsqueda tolerante, código de barras, granel, producto no encontrado y trabajo sin internet con sincronización.
- Finanzas: gastos con mes, reportes configurables, reporte de ventas, punto de equilibrio, precios para cubrir gastos, pronóstico progresivo con tres modelos y gráficas reales en rosa con vista ampliada.
- Asistente: 25 funciones, Gemini primero y ChatGPT de respaldo, dictado tipo radio (Chrome y Edge), explicaciones con IA.
- Seguridad: llaves de IA cifradas en la base de datos, HTTPS y correo por variables de entorno.
- Pruebas automáticas: `python manage.py test`.

## Pendiente

- [ ] Despliegue en Azure y servicio de correo real.
- [ ] Prueba de aceptación con tenderos.
- [ ] Caché compartido (Redis) si se ejecutan varios procesos.
- [ ] Registro de errores a archivo.
