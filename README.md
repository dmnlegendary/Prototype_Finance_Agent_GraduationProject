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
- **Base de datos**: SQL (SQLite en desarrollo).
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

Crea un archivo `.env` en la raíz del proyecto (junto a `manage.py`) con tus llaves de API. Nunca se sube a git:

```
OPENAI_API_KEY=sk-tu-clave-aqui
GEMINI_API_KEY=tu-clave-de-gemini-aqui
```

Aplica las migraciones, crea tu usuario administrador y levanta el servidor:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Entra a `/cuenta/registro/` para crear una cuenta y seguir el flujo de alta del negocio.

## Autores

- Jorge Arif Diaz Jimenez — Ingeniería en Inteligencia Artificial
- Luis Bernardo Delgado Acosta — Ingeniería en Inteligencia Artificial

Escuela Superior de Cómputo (ESCOM) — Instituto Politécnico Nacional.
