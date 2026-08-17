# Arquitectura del proyecto — Tiendita AI (POS + Inventario + Agente Financiero)

Este documento acompaña la primera entrega de la base funcional del sistema (sin IA ni pronóstico todavía). Explica cómo quedó organizado el proyecto, por qué se tomó cada decisión, qué se asumió al no tener datos de negocio reales, y qué falta para las siguientes iteraciones.

## 1. Dónde quedó cada cosa

El proyecto Django se creó en la **raíz del repositorio**, junto a tus carpetas originales (`agente_financiero/`, `auxiliar_de_inventario/`, `modulo_ventas/`, `sistema_configuracion/`), que **no se tocaron ni se borraron** — quedan como referencia histórica del prototipo. Los HTML que ya tenías se copiaron y adaptaron dentro de las apps de Django correspondientes.

```
Prototype_Finance_Agent_GraduationProject/
├── manage.py
├── requirements.txt
├── ARQUITECTURA.md                 ← este documento
├── .gitignore
├── config/                         ← paquete de configuración de Django (antes "project")
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── core/                           ← utilidades compartidas (sin modelos de negocio)
│   └── models.py (ModeloBase: creado_en/actualizado_en)
│   └── context_processors.py (expone `negocio` a todos los templates)
│
├── accounts/                       ← Usuarios + onboarding (Cuenta → Negocio → Productos)
│   ├── models.py   (Usuario, Negocio)
│   ├── forms.py, views.py, urls.py, admin.py
│   └── templates/accounts/{registro,datos_negocio,productos_precargados,login}.html
│
├── inventario/                     ← Catálogo, proveedores, alertas
│   ├── models.py   (Categoria, Proveedor, ProductoCatalogo, Producto)
│   ├── views.py, urls.py, admin.py
│   └── templates/inventario/panel.html
│   └── static/inventario/{css,js}/inventario.{css,js}
│
├── ventas/                         ← Punto de venta / carrito
│   ├── models.py   (Venta, ItemVenta)
│   ├── views.py, urls.py, admin.py
│   └── templates/ventas/punto_de_venta.html
│   └── static/ventas/{css,js}/ventas.{css,js}
│
├── finanzas/                       ← Gastos operativos (placeholder de punto de equilibrio/reportes)
│   ├── models.py   (GastoOperativo)
│   └── templates/finanzas/placeholder.html
│
├── avi/                            ← Placeholder del futuro Asistente Virtual Inteligente
│   └── models.py   (HistorialConversacion, sin lógica activa)
│
├── templates/                      ← SOLO lo compartido por TODAS las apps
│   ├── base.html                   (shell mínimo: doctype, blocks)
│   ├── base_auth.html              (+ Tailwind CDN, para onboarding/login)
│   ├── base_app.html               (+ navbar, para pantallas ya logueadas)
│   └── partials/navbar.html
│
├── static/
│   ├── css/auth.css                (estilos compartidos de las pantallas Tailwind)
│   └── img/
│
└── media/                          (para futuras fotos de producto)
```

**Regla de `templates/`:** hay una carpeta **global** (`templates/` en la raíz) solo para lo que de verdad comparten todas las apps — `base.html`, las dos variantes de layout y el navbar —, y cada app tiene su **propia** carpeta `templates/<app>/` (namespacing) para sus pantallas específicas. Así se evita que dos apps choquen si algún día ambas tienen, por ejemplo, un `detalle.html`.

**Regla de `static/`:** los estilos/scripts que pertenecen a una sola pantalla (los `<style>`/`<script>` gigantes que traían `inventario.html` y `venta1.html`) se movieron a `static/<app>/css/` y `static/<app>/js/` de esa misma app — se extrajeron **literalmente**, sin cambiar una sola línea de CSS/JS. Lo poco que sí comparten varias pantallas de onboarding (Tailwind + tokens de color) vive en `static/css/auth.css` (global).

## 2. Decisiones que tomamos juntos (resumen de tus respuestas)

1. **CSS:** se conservó Tailwind CDN + CSS propio tal cual venían tus HTML. No se migró nada a Bootstrap 5, aunque la especificación original del proyecto lo mencionaba — quedó anotado como una desviación consciente de esa especificación, a tu pedido.
2. **`finanzas`:** por ahora solo lleva el modelo `GastoOperativo` + una vista placeholder. El React app (`agente_financiero/`) se dejó **intacto y sin integrar**, como referencia de diseño para cuando se aborde esa pantalla en Django.
3. **Ubicación:** el proyecto Django vive en la raíz del repo.

## 3. Qué se asumió (y qué falta confirmar)

Como todavía no existe una base de artículos/negocio real, varios catálogos se tomaron **literalmente** de las opciones que ya existían en tus `<select>`, sin inventar nada nuevo:

- `Negocio.Alcaldia`: Iztapalapa, Gustavo A. Madero, Álvaro Obregón, Tlalpan, Coyoacán, Xochimilco, Otra (de `datos_negocio.html`). **Pendiente de confirmar:** el label dice "Alcaldía / Colonia" pero el `<select>` solo trae alcaldías — ¿falta un campo de texto libre para Colonia?
- `Negocio.AniosOperacion`: Menos de 1 año / 1 a 3 / 3 a 10 / Más de 10 (de `datos_negocio.html`).
- Categorías de producto (Bebidas, Lácteos, Abarrotes, Verduras, Botanas, Limpieza, Dulcería...) recopiladas de `inventario.html` y `productos_precargados.html`.
- **Login:** no había mockup. Se construyó `accounts/templates/accounts/login.html` reutilizando el mismo lenguaje visual de `registro.html`. Si ya tienes un diseño para esta pantalla, se reemplaza sin tocar `views.py`/`urls.py`.
- **Contraseña con un solo campo:** `registro.html` solo maqueta un input de contraseña (sin confirmación). Se respetó así — el formulario no pide confirmar contraseña. Si prefieren pedirla, hay que ampliar el mockup.
- **Login por username, no por teléfono:** se guarda el teléfono como dato de perfil (`Usuario.telefono`, único) pero el login sigue autenticando por `username` (heredado de `AbstractUser`), inicializado igual al teléfono al registrarse. Cambiarlo a un login 100% por teléfono es sencillo pero se dejó como TODO explícito en `accounts/models.py` para no tomar esa decisión por ustedes.
- **`ProductoCatalogo` (productos precargados) está vacío.** No se inventaron productos de ejemplo en la base de datos: la pantalla de onboarding ya está conectada al modelo real y muestra un mensaje de "aún no hay catálogo" hasta que alguien cargue artículos (vía admin de Django o un fixture).

## 4. Cómo se integraron tus HTML (Paso 2)

- **`registro.html`, `datos_negocio.html`, `productos_precargados.html`:** se reescribieron como templates de Django que extienden `base_auth.html`. Cada `<input>`/`<select>` se reemplazó por `{{ form.campo }}`, reutilizando **las mismas clases de Tailwind** que ya traía el HTML (se movieron a `accounts/forms.py` como atributos del widget). El resultado visual no cambia.
- **`inventario.html` y `venta1.html`:** son mucho más grandes (1400 y 1050 líneas), así que se procesaron de forma **mecánica y verificable** en vez de reescribirse a mano: se extrajo el `<style>` completo a su `.css`, el `<script>` completo a su `.js`, y el contenido de `<body>` se volvió el `{% block app_content %}` del template — carácter por carácter, sin recrear nada. Se verificó automáticamente que todos los `id` que el JS busca (`getElementById`) siguen existiendo en el HTML resultante.
- **Actualización posterior a esta entrega:** las barras "Estado: 1·2·3..." (`demo-bar`/`showState()`) y las tablas duplicadas con datos de ejemplo fijos (estados "alta", "modificar", "proveedores", "alertas" en `inventario.html`; estados "carrito", "búsqueda", "AVI agrega", "ticket" en `venta1.html`) **ya se quitaron por completo**. Cada pantalla que antes era una copia estática ahora es una vista real de Django conectada al ORM (ver punto 7 de la sección 7, ya resuelto). Lo que sigue en este documento describe el estado ANTES de ese cambio, para que quede constancia del proceso; el estado actual del código es el que se explica en la sección 7.

## 5. Verificación hecha en esta entrega

- Los **~40 archivos Python** se verificaron con `python -m py_compile` (sin errores de sintaxis).
- Se revisaron a mano las referencias cruzadas: nombres de `{% url %}` en templates contra `urls.py`, nombres de variables de contexto entre `views.py` y sus templates, y nombres de campos de modelo usados en templates contra `models.py`.
- Se verificó que **todos los `id` del DOM** que usan `inventario.js` y `ventas.js` (`getElementById`) siguen presentes en sus templates.
- Se contó el balance de `{% block %}/{% endblock %}`, `{% if %}/{% endif %}` y `{% for %}/{% endfor %}` en las 11 plantillas nuevas: todas cierran correctamente.
- **Limitación de este entorno:** el sandbox donde se generó este proyecto no tiene salida a internet para instalar Django, así que **no se pudo correr** `python manage.py check` / `makemigrations` / `runserver` de verdad. Es el primer paso que deberían correr ustedes al recibir esto (ver sección 6). Si algo truena, probablemente sea un detalle menor (un import, un nombre de campo) — avísenme y lo corregimos.

## 6. Cómo arrancarlo

```bash
python -m venv .venv
source .venv/bin/activate          # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser   # para entrar a /admin/ y cargar categorías/catálogo
python manage.py runserver
```

Flujo para probarlo: entra a `/cuenta/registro/` → completa el negocio → paso 3 (te dirá que aún no hay catálogo, es esperado) → caes en `/ventas/` (punto de venta, carrito vacío) → usa el navbar para ir a `/inventario/` (tabla vacía hasta que des de alta productos desde el admin) y `/finanzas/` (placeholder).

## 7. Orden sugerido para seguir construyendo (Paso 3)

1. Correr y arreglar lo que truene al primer `migrate` (ver limitación de la sección 5).
2. Cargar un catálogo real: `Categoria` y `ProductoCatalogo` vía admin de Django.
3. Autenticación: decidir si el login final es por teléfono (ver TODO en `accounts/models.py`) y si se pide confirmación de contraseña.
4. ✅ **Hecho.** Inventario: `inventario/views.py` implementa alta/edición/baja de producto (`producto_alta`, `producto_editar`, `producto_eliminar`) y gestión de proveedores (`proveedores`, `proveedor_editar`) con formularios reales (`inventario/forms.py`) en páginas propias (`producto_form.html`, `proveedores.html`), además de una vista de alertas de stock (`alertas.html`) calculada con `F()` sobre `cantidad_actual`/`cantidad_minima`.
5. ✅ **Hecho.** Ventas: el carrito vive en un modelo `Venta` real en estado `EN_CURSO` (no en sesión). `ventas/views.py` implementa buscar/agregar producto (`agregar_item`), cambiar cantidad (`item_incrementar`/`item_decrementar`, que borra el renglón si llega a 0), cobrar (`cobrar`: descuenta inventario, marca `COBRADA` y genera un ticket real) y cancelar (`cancelar_venta`). Todo por formularios POST + redirect, no por Fetch API (ver el docstring de `ventas/views.py` para la justificación de esa decisión).
6. Finanzas: pantallas reales de registro de gastos y punto de equilibrio (usar `agente_financiero.jsx` como referencia de diseño, reconstruido con templates de Django).
7. ✅ **Hecho.** Se reemplazaron las "vistas de demo" duplicadas de `inventario.html`/`venta1.html` (barras "Estado: 1·2·3...", tablas con datos de ejemplo fijos, y el toast/drawer de ticket con folio y montos hardcodeados) por vistas reales conectadas al ORM. Sigue pendiente, como mejora futura opcional y sin urgencia, migrar las acciones del carrito de "POST + redirect" a Fetch/JSON si se quiere una experiencia sin recargas de página — los modelos ya lo soportan sin cambios.

## 8. Hoja de ruta futura — AVI y motor predictivo (NO implementado, checklist para después)

- [ ] Definir el proveedor del LLM (ChatGPT/Gemini) y dar de alta la API key como variable de entorno (nunca hardcodeada).
- [ ] Implementar `avi/views.py` + `avi/urls.py` (hoy vacíos a propósito) con el endpoint que recibe el mensaje del usuario, arma el prompt con contexto acotado (ventas/inventario recientes) y llama al LLM.
- [ ] Activar `avi.HistorialConversacion` (hoy sin lógica) para persistir cada mensaje.
- [ ] Sanitización de prompts y permisos de solo lectura sobre la base de datos para el AVI (como marca el `README.md` original del proyecto).
- [ ] Conectar el chat AVI que ya está maquetado (pero inerte) en `inventario/panel.html` y `ventas/punto_de_venta.html` al endpoint real, vía Fetch API.
- [ ] Diseñar y entrenar el motor predictivo de ventas (scikit-learn/keras) por fuera de Django (notebook/servicio aparte) y decidir cómo se sirve (job periódico, endpoint propio, etc.).
- [ ] Construir la pantalla de "Pronóstico de ventas" (hay una referencia de diseño ya hecha en React dentro de `agente_financiero.jsx`, función `ForecastView`).
- [ ] Definir dónde vive el resultado del pronóstico (¿un modelo `Pronostico` en `finanzas`? ¿en una app nueva?) — a propósito no se decidió en esta entrega para no comprometerse antes de tener el motor real.
