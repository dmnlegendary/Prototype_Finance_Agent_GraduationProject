# Notas de arquitectura

Cómo está organizado el proyecto de Django, para no perder el hilo entre entregas.

## Carpetas

```
config/         configuración del proyecto (settings, urls)
core/           cosas compartidas (ModeloBase, context processor del navbar)
accounts/       usuarios, login/registro, datos del negocio (Seguridad y autenticación)
inventario/     productos, proveedores, alertas de stock (Inventario y alertas)
ventas/         punto de venta y carrito (Ventas y carrito)
finanzas/       gastos operativos, equilibrio y pronóstico semanal de ventas
avi/            placeholder del asistente conversacional (Orquestador AVI)
templates/      base.html, base_auth.html, base_app.html y el navbar
static/         css/js que comparten varias pantallas
```

Cada app tiene su propio `templates/<app>/` y (si aplica) `static/<app>/`.

## Estado actual

- Login/registro/onboarding de 3 pasos: funcionando.
- Inventario (alta, edición, baja, proveedores, alertas): funcionando.
- Ventas (carrito, cobro, ticket): funcionando, con formularios POST + redirect (sin Fetch).
- Finanzas: registro e historial de gastos; pronóstico semanal de unidades implementado.
- AVI: app vacía, sin conectar todavía a ningún LLM.

## Pendiente

- [ ] Implementar `avi/views.py` con el endpoint que llama a la API de ChatGPT o Gemini.
- [ ] Pantallas de gastos y punto de equilibrio en `finanzas`.
- [ ] Conectar Power BI a la base de datos para los reportes.
- [ ] Definir si el login termina siendo por teléfono en vez de usuario.

## Pronóstico de ventas

La pantalla está en `/finanzas/pronostico/` y requiere iniciar sesión. Al pulsar **Generar pronóstico**, el navegador consulta `GET /finanzas/pronostico/api/`. La vista obtiene el negocio del usuario autenticado y llama a `finanzas.forecasting.forecast_sales`; el cálculo se ejecuta localmente en el servidor y no requiere una API externa.

### Datos de entrada

- Se consideran únicamente ventas del negocio actual con estado `COBRADA`.
- La serie representa **unidades**, calculadas como la suma de `items__cantidad` por semana; no pronostica ingresos ni resultados por producto.
- Las semanas comienzan el lunes. Se descartan la primera o la última semana si están incompletas, y las semanas sin ventas entre ambas se rellenan con cero.
- Se necesita al menos una semana completa con ventas para generar cualquier resultado.

### Comparación y selección

Con al menos 8 semanas, el sistema evalúa tres candidatos: regresión lineal, ARIMA(1,1,0) y Holt-Winters con tendencia aditiva. Holt-Winters incorpora estacionalidad aditiva de periodo 4 a partir de 12 semanas. Cada modelo genera pronósticos de prueba siguiendo el orden temporal: reserva las últimas 2 a 4 semanas, predice cada una usando solo los datos anteriores y calcula el error absoluto medio (MAE). Se selecciona el modelo con menor MAE y luego se ajusta con toda la serie para pronosticar la semana siguiente.

Los pronósticos negativos se limitan a cero. Si no hay suficientes semanas para comparar candidatos, o ninguno puede evaluarse, se usa como línea base el total de la última semana completa. En ese caso el MAE es 0 y la lista de modelos comparados queda vacía.

### Respuesta y lectura

La API devuelve `forecast_units`, `next_week`, `weeks`, `model`, `mae`, `confidence`, `message` y `candidates`. La pantalla muestra las unidades estimadas, modelo, semanas analizadas y MAE, además de una lista de modelos comparados cuando existe.

`confidence` es un indicador heurístico derivado del MAE relativo al promedio de la serie, limitado al rango de 35% a 95%; **no es una probabilidad estadística de que el pronóstico sea correcto**. El resultado es una estimación para orientar decisiones, no una garantía de ventas futuras.
