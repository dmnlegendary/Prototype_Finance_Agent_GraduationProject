# Notas de arquitectura

Cómo está organizado el proyecto de Django, para no perder el hilo entre entregas.

## Carpetas

```
config/         configuración del proyecto (settings, urls)
core/           cosas compartidas (ModeloBase, context processor del navbar)
accounts/       usuarios, login/registro, datos del negocio (Seguridad y autenticación)
inventario/     productos, proveedores, alertas de stock (Inventario y alertas)
ventas/         punto de venta y carrito (Ventas y carrito)
finanzas/       gastos operativos, a futuro el pronóstico (Agente financiero)
avi/            placeholder del asistente conversacional (Orquestador AVI)
templates/      base.html, base_auth.html, base_app.html y el navbar
static/         css/js que comparten varias pantallas
```

Cada app tiene su propio `templates/<app>/` y (si aplica) `static/<app>/`.

## Estado actual

- Login/registro/onboarding de 3 pasos: funcionando.
- Inventario (alta, edición, baja, proveedores, alertas): funcionando.
- Ventas (carrito, cobro, ticket): funcionando, con formularios POST + redirect (sin Fetch).
- Finanzas: solo el modelo de gastos y una pantalla placeholder.
- AVI: app vacía, sin conectar todavía a ningún LLM.

## Pendiente

- [ ] Elegir el modelo de pronóstico de ventas (ARIMA / series de tiempo / regresión) y
      dónde se va a correr (¿un script aparte, un management command de Django?).
- [ ] Implementar `avi/views.py` con el endpoint que llama a la API de ChatGPT o Gemini.
- [ ] Pantallas de gastos y punto de equilibrio en `finanzas`.
- [ ] Conectar Power BI a la base de datos para los reportes.
- [ ] Definir si el login termina siendo por teléfono en vez de usuario.
