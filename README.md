# Asistente Virtual Inteligente para la gestión financiera y pronóstico de ventas

Proyecto de titulación (Trabajo Terminal 2) para microempresas del sector comercial (abarrotes),
con posible afiliación al régimen RESICO.

Es un sistema de punto de venta (POS) + inventario + un módulo financiero que más adelante
va a pronosticar ventas con Machine Learning, y un asistente conversacional (AVI) para
resolver dudas del negocio.

## Módulos

- **Ventas y caja**: punto de venta, alta a la caja, cobro.
- **Inventario y alertas**: catálogo de productos, proveedores, aviso de stock bajo.
- **Agente financiero**: gastos operativos y (a futuro) pronóstico de ventas.
- **Orquestador AVI**: conecta con el LLM para el chat del asistente. El modelo se elige solo: primero consulta a Gemini y, si no contesta, usa ChatGPT (basta con tener una de las dos llaves).
- **Seguridad y autenticación**: registro, login y datos del negocio.

## Tecnologías

- **Backend**: Python + Django (ORM, vistas y rutas). La lógica de negocio se intenta
  mantener en Python simple, sin abusar de las utilidades más avanzadas de Django.
- **Frontend**: HTML, CSS y JavaScript, con Bootstrap 5 para no maquetar todo a mano.
- **Base de datos**: PostgreSQL (SQLite si no se configura nada). Ver `database/README.md`.
- **Machine Learning**: todavía por definir el modelo de pronóstico (ARIMA, series de
  tiempo o regresión), se va a probar más de uno.
- **Reportes**: Power BI, conectado a la base de datos para los reportes avanzados.

## Cómo correrlo

Crea el entorno virtual (solo la primera vez que clonas el proyecto):

```bash
python -m venv .venv
```

Actívalo. El comando cambia según tu terminal:

```bash
# PowerShell (la terminal integrada de VS Code en Windows usa esta por default)
.venv\Scripts\Activate.ps1

# CMD
.venv\Scripts\activate.bat

# Linux/Mac
source .venv/bin/activate
```

Si PowerShell te marca error de "ejecución de scripts deshabilitada", corre esto una vez y vuelve a activar:

```bash
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Sabes que ya quedó activado porque el prompt te muestra `(.venv)` al inicio.

Instala las dependencias usando siempre `python -m pip` (no solo `pip`) — si tienes más de un Python instalado en tu PC, un `pip` suelto a veces instala en el Python equivocado aunque el venv esté activado:

```bash
python -m pip install -r requirements.txt
```

Las llaves de la IA (ChatGPT y Gemini) se guardan cifradas en la base de datos con un solo comando. Como usa una tabla, hay que correrlo después de `python manage.py migrate` (más abajo):

```bash
python manage.py configurar_ia
```

Te pide las dos llaves una vez y listo. Otras formas: `python manage.py configurar_ia --openai sk-... --gemini AIza...`, o `python manage.py configurar_ia --archivo claves.txt` con un archivo de texto con líneas `OPENAI_API_KEY=...` y `GEMINI_API_KEY=...` (pásenselo entre ustedes por un medio privado, **no lo suban a git**: si una llave llega a un repositorio, OpenAI y Google la revocan solos). Con `--ver` revisas cuáles están guardadas. Si solo configuras una de las dos, el sistema usa esa aunque el selector del chat diga otra.

Aplica las migraciones, crea tu usuario administrador y levanta el servidor:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Entra a `/cuenta/registro/` para crear una cuenta y seguir el flujo de alta del negocio.

## Base de datos

Por default se usa SQLite para poder probar sin instalar nada. Para usar **PostgreSQL** (lo recomendado con miles de productos y ventas) llena las variables `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST` y `DB_PORT` del `.env` (hay un ejemplo en `.env.example`). La instalación paso a paso, el diagrama de las tablas, los índices y las consultas útiles están en [`database/README.md`](database/README.md).

Para cargar productos y ventas desde un CSV de golpe (en vez de una por una):

```bash
python manage.py importar_csv --usuario correo@tienda.com --productos productos.csv --ventas ventas.csv
```

## Semáforo de reabastecimiento

Cada producto tiene su cantidad mínima y su **stock ideal** (lo que hay cuando se resurte completo). El color se calcula solo:

- 🟡 **Amarillo**: queda la mitad del stock ideal.
- 🟠 **Naranja**: queda un cuarto del stock ideal.
- 🔴 **Rojo**: llegó a la cantidad mínima, hay que resurtir.

Si el stock ideal se deja en 0, el sistema usa 4 veces el mínimo. Las alertas avisan con la campana del navbar (en todas las pantallas), un aviso al entrar si hay productos en rojo, un aviso al cobrar una venta que deja un producto en otro color, y la pantalla de alertas, que tiene búsqueda instantánea y filtro por color.

## Asistente (AVI)

Todo lo que se puede hacer a mano en el sistema se puede pedir por el chat (escrito o con el micrófono): agregar o quitar productos de la caja, cambiar cantidades, cobrar, cancelar la venta, dar de alta o modificar productos, sumar piezas al inventario, dar de baja, crear categorías y proveedores, registrar gastos, ver ventas, alertas, finanzas, punto de equilibrio y precios sugeridos. La lista completa está en `avi/services.py` (`FUNCIONES`).

Para responder rápido:

- Las acciones se contestan con el mensaje de la propia función, sin una segunda llamada a la IA.
- Los datos que más se piden (catálogo, alertas, ventas de hoy, resumen financiero) viven en un **cache por negocio** (`core/cache_negocio.py`) que se borra solo cuando cambia una venta, producto o gasto.
- El resumen de "cómo te fue ayer" (modal al iniciar sesión) y las explicaciones del dashboard y de los reportes se guardan en la base de datos: se pide a la IA solo la primera vez del día, o cuando los números cambian.

## Autores

- Jorge Arif Diaz Jimenez — Ingeniería en Inteligencia Artificial
- Luis Bernardo Delgado Acosta — Ingeniería en Inteligencia Artificial

Escuela Superior de Cómputo (ESCOM) — Instituto Politécnico Nacional.

## Novedades de la versión actual

- **Compras de mercancía automáticas.** Toda pieza que entra al inventario (alta de producto, resurtir, importar CSV, registro inicial, el asistente) se registra sola como gasto de "Compra de mercancía". Cuenta para el flujo de efectivo pero no para la utilidad (el costo de lo vendido ya se resta al vender), así no se duplica.
- **Precio y costo congelados en cada venta.** Si cambias el precio o el costo de un producto, las ventas de antes no cambian.
- **Regla de oro:** no se vende más de lo que hay. Si falta, el sistema pregunta cuántas piezas (o kilos) agregar y a qué precio de compra, y sigue con la venta.
- **Productos a granel:** se venden por gramos (el precio y las existencias son por kilo).
- **Dos cajas** por tienda, cantidad escrita con el teclado y búsqueda tolerante (sin acentos, sin importar el orden, con errores de dedo).
- **Código de barras:** un lector USB o Bluetooth "escribe" el código en el buscador de ventas y da Enter; también se puede capturar en el alta y la edición del producto.
- **Importar CSV desde la pantalla de inventario**, con revisión y confirmación antes de guardar (columnas obligatorias: `producto, cantidad, precio_compra, precio_venta`).
- **Sin internet:** se puede cobrar, dar de alta productos y registrar mercancía. Todo se guarda en el dispositivo y se sincroniza solo al regresar la conexión (ver `static/js/sinconexion.js`, `static/sw.js` y `core/sync.py`).
- **Pantallas ligeras:** inventario y alertas cargan 20 renglones y el resto con "Ver más"; los reportes usan pocas consultas.
- **El asistente solo recibe las herramientas de la pantalla en la que estás**, para gastar menos.
- **Gastos con mes:** cada gasto lleva el mes al que corresponde (la luz de septiembre pagada en octubre cuenta en septiembre).
- **Sugerir precios para cubrir tus gastos:** el margen se puede calcular con lo que se va en gastos sobre ventas más una ganancia extra.
- **Alertas con ritmo de venta:** dentro de cada color va primero lo que se acaba antes, y cada alerta dice cuánto vende el producto por semana.
- **Kardex de inventario:** cada entrada, venta, merma o ajuste deja un movimiento con la existencia que quedó; se consulta en `/inventario/movimientos/` y se exporta a CSV.
- **Reportes financieros configurables:** de 1, 3, 6 o 12 meses o un rango de meses, con sugerencias, más un reporte de ventas por periodo.
- **Pronóstico por partes y con confianza:** carga primero la base y luego cada modelo; con poco historial avisa el nivel de confianza, y el botón "Explícame mi pronóstico" hace otra llamada a la IA.
- **Llaves de la IA cifradas** en la base de datos (usan la `SECRET_KEY`, así que en un servidor hay que fijar `DJANGO_SECRET_KEY` en el `.env`); `python manage.py configurar_ia --ver` muestra cuáles hay, tapadas.
- **Video de bienvenida** la primera vez que entra cada usuario, y preferencias del negocio (como el margen de ganancia) que el asistente recuerda.
- **Listo para publicar:** `DJANGO_DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `USAR_HTTPS` y el correo SMTP se configuran desde el `.env` (ver `.env.example`).
- **Costo por lotes (PEPS):** cada compra abre un lote con su propio costo y las ventas gastan primero el más viejo; si la coca costó 15 ayer y 17 hoy, las de ayer se venden con costo de 15. El kardex guarda el costo de cada movimiento.
- **Cajas en lugar de carritos:** en pantalla y en el asistente se les dice «caja 1» y «caja 2». Si se apaga el wifi con productos en la caja, se conservan y se pueden cobrar sin internet.
- **Listo para vender:** `python manage.py seed_catalogo --negocios` carga 20 categorías de productos, un catálogo de 186 productos con ícono y precio sugerido, y les agrega a las tiendas 24 proveedores comunes y 19 categorías de gastos (fijos o variables). Las tiendas nuevas los reciben solas al registrarse.
- **Reglas de negocio:** el precio de venta nunca puede ser menor al de compra (alta, edición, resurtido, CSV y asistente), y el stock ideal es el promedio de lo que había después de cada carga de mercancía.
- **Íconos de productos:** se eligen de una lista o se asignan solos según el nombre.
- **Dictado como radio:** el micrófono del chat se mantiene presionado mientras se habla y se suelta al terminar.
