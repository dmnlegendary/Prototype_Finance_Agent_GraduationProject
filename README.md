# Asistente Virtual Inteligente para la gestión financiera y pronóstico de ventas

Proyecto de titulación (Trabajo Terminal 2) para microempresas del sector comercial (abarrotes),
con posible afiliación al régimen RESICO.

Es un sistema de punto de venta (POS) + inventario + un módulo financiero que más adelante
va a pronosticar ventas con Machine Learning, y un asistente conversacional (AVI) para
resolver dudas del negocio.

## Módulos

- **Ventas y carrito**: punto de venta, alta al carrito, cobro.
- **Inventario y alertas**: catálogo de productos, proveedores, aviso de stock bajo.
- **Agente financiero**: gastos operativos y (a futuro) pronóstico de ventas.
- **Orquestador AVI**: conecta con el LLM (ChatGPT o Gemini) para el chat del asistente.
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

Guarda las llaves de la IA (ChatGPT y Gemini) con un solo comando. Las escribe en el archivo `.env`, que nunca se sube a git:

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

Todo lo que se puede hacer a mano en el sistema se puede pedir por el chat (escrito o con el micrófono): agregar o quitar productos del carrito, cambiar cantidades, cobrar, cancelar la venta, dar de alta o modificar productos, sumar piezas al inventario, dar de baja, crear categorías y proveedores, registrar gastos, ver ventas, alertas, finanzas, punto de equilibrio y precios sugeridos. La lista completa está en `avi/services.py` (`FUNCIONES`).

Para responder rápido:

- Las acciones se contestan con el mensaje de la propia función, sin una segunda llamada a la IA.
- Los datos que más se piden (catálogo, alertas, ventas de hoy, resumen financiero) viven en un **cache por negocio** (`core/cache_negocio.py`) que se borra solo cuando cambia una venta, producto o gasto.
- El resumen de "cómo te fue ayer" (modal al iniciar sesión) y las explicaciones del dashboard y de los reportes se guardan en la base de datos: se pide a la IA solo la primera vez del día, o cuando los números cambian.

## Autores

- Jorge Arif Diaz Jimenez — Ingeniería en Inteligencia Artificial
- Luis Bernardo Delgado Acosta — Ingeniería en Inteligencia Artificial

Escuela Superior de Cómputo (ESCOM) — Instituto Politécnico Nacional.
