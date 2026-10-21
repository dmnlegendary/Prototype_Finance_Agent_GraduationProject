# Capítulo 7. Documentación del código y problemas del desarrollo

## 7.1 Documentación del código

El código se organizó siguiendo la forma en que Django propone dividir un proyecto: una aplicación por cada parte del sistema, cada una con sus modelos, sus vistas y sus plantillas. Esto nos ayudó a trabajar los dos al mismo tiempo sin pisarnos tanto, porque casi siempre cada quien modificaba aplicaciones distintas.

### 7.1.1 Estructura del proyecto

La carpeta principal contiene el archivo `manage.py`, con el que se ejecutan los comandos del proyecto, la lista de dependencias en `requirements.txt`, un ejemplo del archivo de configuración `.env.example` y las carpetas que se muestran a continuación.

```
config/        configuración general: settings, rutas principales y arranque
accounts/      usuarios, registro, inicio de sesión y datos de la tienda
core/          caché por negocio, sincronización sin conexión y comandos de importación
inventario/    productos, proveedores, categorías, alertas, importación desde CSV
ventas/        mostrador, cajas, cobro, historial y tickets
finanzas/      gastos, fórmulas financieras, reportes y pronóstico de ventas
avi/           asistente virtual: conexión con las APIs de IA y funciones que ejecuta
templates/     plantillas compartidas (menú, ayuda y panel del chat)
static/        hojas de estilo y JavaScript compartidos
database/      guía de instalación de PostgreSQL y archivos de ejemplo
```

La carpeta `config` guarda la configuración, como la base de datos, el caché y las llaves que se leen del `.env`. La aplicación `accounts` administra a los usuarios, y `core` guarda lo que usan todas las demás: el caché, la sincronización de lo hecho sin internet y los comandos para cargar datos desde archivos. Cada una de las aplicaciones `inventario`, `ventas`, `finanzas` y `avi` corresponde a un módulo del sistema y lleva en su carpeta sus propios estilos y scripts, además de sus pruebas.

### 7.1.2 Modelos de datos

Las tablas del sistema ya se listaron en la Tabla 6.1, así que aquí solo se explican los campos que llevan más lógica. Todos los modelos heredan de uno base que registra cuándo se creó y se actualizó cada registro.

En el producto, la cantidad actual y la cantidad mínima son decimales con tres posiciones, porque los productos a granel se guardan en kilos. El campo del stock ideal sirve para el semáforo y el de pendiente de validación marca los productos que se vendieron como "no encontrados" y todavía no se completan. Un producto no se borra, solo se desactiva con un campo de estado. En la venta, el estado indica si está en curso, cobrada o cancelada, y el número de caja permite tener dos ventas abiertas a la vez. En cada renglón de venta se guardan el precio y el costo del producto en ese momento. En el gasto, el tipo puede ser fijo, variable o mercancía, y este último es el que distingue las compras al proveedor de los gastos de operación. Además, cada gasto guarda el mes al que corresponde (como el primer día de ese mes), que es el que cuentan los reportes, y por separado la fecha en que se capturó. Cada cambio en las existencias deja un renglón en el kardex (el modelo de movimientos de inventario), que guarda el tipo de movimiento (entrada, venta, merma o ajuste), la cantidad con signo, la existencia que quedó después, el costo por pieza, el motivo y el usuario que lo hizo; con esto se puede reconstruir cómo llegó un producto a su existencia actual. Cada compra de mercancía abre además un lote (el modelo de lotes de inventario) con su cantidad restante y su costo, que las ventas van gastando desde el más viejo. Las llaves de ChatGPT y de Gemini viven en su propio modelo, siempre cifradas, y el negocio guarda sus preferencias (como el margen de ganancia elegido) en un campo de texto JSON. Por último, el modelo de operación sincronizada guarda un identificador único por cada operación hecha sin internet, para saber cuáles ya llegaron al servidor.

### 7.1.3 Vistas y rutas

La Tabla 7.1 muestra las rutas principales del sistema. Las de tipo `api` responden con JSON en lugar de una página completa, porque las usa el JavaScript del navegador.

Tabla 7.1. Rutas principales.

| Ruta | Qué hace |
|---|---|
| `/` | Lleva al mostrador de ventas |
| `/cuenta/login/`, `/cuenta/registro/` | Inicio de sesión y registro de una tienda nueva |
| `/ventas/` | Pantalla de mostrador con los dos cajas |
| `/ventas/buscar/` | Busca productos mientras el tendero escribe |
| `/ventas/api/carrito/<n>/agregar/` | Agrega un producto a la caja n |
| `/ventas/api/carrito/<n>/cobrar/` | Cobra la caja y descuenta las existencias |
| `/ventas/api/carrito/<n>/no-encontrado/` | Agrega un producto que no está en el catálogo |
| `/ventas/api/codigo/` | Busca un producto por su código de barras |
| `/ventas/historial/`, `/ventas/ticket/<id>/` | Ventas anteriores y su ticket |
| `/inventario/` | Catálogo de productos con el semáforo |
| `/inventario/alertas/` | Productos en alerta, con búsqueda y filtros |
| `/inventario/importar/` | Importación de productos desde un CSV |
| `/inventario/productos/<id>/resurtir/` | Suma piezas a un producto y registra la compra |
| `/inventario/movimientos/` | Kardex de movimientos, con filtros y exportación a CSV |
| `/finanzas/` | Inicio del agente financiero |
| `/finanzas/gastos/` | Registro de gastos |
| `/finanzas/reportes/` | Reportes de 1, 3, 6 o 12 meses, o de un rango de meses elegido |
| `/finanzas/reportes/ventas/` | Reporte de ventas por periodo, con exportación a CSV |
| `/finanzas/equilibrio/`, `/finanzas/precios/` | Punto de equilibrio y precios sugeridos |
| `/finanzas/pronostico/` | Pronóstico de ventas; carga primero la base y luego cada modelo por separado |
| `/avi/chat/` | Recibe el mensaje del tendero y regresa la respuesta del asistente |
| `/avi/resumen/`, `/avi/explicar/<tipo>/` | Resumen del día y explicaciones con IA |
| `/sincronizar/` | Recibe lo que se hizo sin internet |
| `/terminos/` | Términos y condiciones y aviso de protección de datos (público) |

### 7.1.4 Servicios y fórmulas

Para que las vistas no se llenaran de cálculos, la lógica importante se puso en módulos aparte, que se muestran en la Tabla 7.2. Las pantallas solo llaman a estas funciones, y por eso el asistente puede hacer lo mismo que el tendero a mano: usa las mismas funciones.

Tabla 7.2. Módulos con la lógica del sistema.

| Módulo | Qué contiene |
|---|---|
| `finanzas/calculos.py` | Fórmulas financieras (utilidad, flujo, ISR, punto de equilibrio, precio sugerido) y los modelos de pronóstico |
| `finanzas/graficas.py` | Datos reales de las gráficas del inicio y de los reportes |
| `ventas/cobro.py` | Cobro de la venta y la regla de oro |
| `ventas/carrito.py` | Operaciones de la caja: agregar, quitar, cambiar cantidad y cancelar |
| `inventario/busqueda.py` | Búsqueda aproximada de productos |
| `inventario/compras.py` | Compras de mercancía y suma de existencias |
| `inventario/importacion.py` | Lectura y revisión del archivo CSV |
| `inventario/movimientos.py` | Registro y consulta del kardex |
| `inventario/lotes.py` | Lotes de compra: abre un lote por cada entrada y calcula el costo de lo que sale (PEPS) |
| `inventario/alertas.py` | Cálculo de los productos en alerta, ordenados por urgencia según el ritmo de venta |
| `core/cache_negocio.py` | Caché por tienda |
| `core/llaves.py` | Guarda y lee las llaves de la IA cifradas con Fernet |
| `core/sync.py` | Procesa lo que se hizo sin internet |
| `avi/clients.py` | Comunicación con Gemini y ChatGPT, reintentos y respaldo |
| `avi/services.py` | Las 25 funciones que puede ejecutar el asistente |

### 7.1.5 API interna en JSON

El mostrador no recarga la página cada vez que algo cambia. En su lugar, el JavaScript del navegador manda una petición al servidor con la función `fetch`, el servidor hace la operación y regresa un JSON con la caja actualizado, y la pantalla solo cambia lo que se modificó. Todas las peticiones que cambian datos llevan el código de seguridad de Django. Este mismo esquema se usa para la búsqueda mientras se escribe, para los lotes de "Ver más" y para el chat con el asistente, al que además se le manda en qué pantalla está el tendero y qué carrito tiene abierto.

### 7.1.6 Convenciones del código

Escribimos los nombres de variables, funciones y modelos en español, porque el vocabulario del proyecto (venta, producto, tendero) se entiende mejor así y porque los dos nos sentimos más cómodos. Las funciones llevan un comentario corto que explica qué hacen y, cuando no es obvio, por qué se hacen así. Cada aplicación tiene sus pruebas en su propio archivo de pruebas, con nombres que describen lo que se comprueba, y las pruebas de la importación se separaron en un archivo distinto por su tamaño. Las decisiones que afectan a más de una parte, como la regla de oro o la forma de calcular la utilidad, están escritas en un solo lugar y se reutilizan en las demás.

### 7.1.7 Dónde está el detalle

Este capítulo solo resume cómo está organizado el código. Los pasos para instalar y ejecutar el sistema están en el Anexo B (manual técnico), y los fragmentos del código más representativos, como las fórmulas financieras, la validación de la regla de oro y el despachador de funciones del asistente, están en el Anexo C.

## 7.2 Problemas y limitaciones durante el desarrollo

### 7.2.1 Problemas técnicos

Durante el desarrollo tuvimos varios problemas que nos tomaron tiempo. La Tabla 7.3 resume los más importantes, con lo que los causó, cómo los resolvimos y lo que aprendimos de cada uno.

Tabla 7.3. Problemas técnicos del desarrollo.

| Problema | Causa | Solución | Aprendizaje |
|---|---|---|---|
| Las pantallas tardaban mucho en cargar los datos | Los datos estaban en archivos CSV y en SQLite, y cada consulta leía el archivo completo | Pasar los datos a PostgreSQL y cargar el historial con un comando de importación por lotes | Los archivos planos sirven para empezar, pero no para consultas frecuentes |
| Conflictos al unir el trabajo de los dos en Git | Las migraciones de Django se generaron por separado en cada computadora y chocaban | Borrar las migraciones repetidas, volver a generarlas y avisar antes de subir cambios al modelo | Las migraciones deben tratarse como código y revisarse igual que el resto |
| La pantalla de inventario hacía demasiadas consultas | Por cada producto se pedían aparte datos relacionados, y se cargaban todos de golpe | Pedir los datos relacionados junto con el producto, mostrar 20 por lote con un botón de "Ver más" y usar el caché. En una prueba con 1,100 productos pasó de 92 a 19 consultas y de 207 KB a 83 KB | Hay que revisar cuántas consultas hace cada pantalla |
| La utilidad de ventas viejas cambiaba al modificar el costo de un producto | El costo se leía del producto en cada reporte | Guardar el costo del producto en cada renglón de venta, junto con el precio | Los datos de una venta deben ser una fotografía del momento |
| Al subir el precio del proveedor, las piezas compradas antes se vendían con el costo nuevo | El producto tenía un solo costo, el de la última compra | Abrir un lote por cada compra y vender primero el más viejo (PEPS), guardando en cada renglón el costo de lo que salió | Se encontró probando con compras de la misma coca a 15 y a 17 pesos |
| La utilidad salía distorsionada | La compra de mercancía se capturaba como un gasto | Crear un tipo de gasto aparte para la mercancía, que cuenta en el flujo de efectivo pero no en la utilidad | Compra de mercancía y gasto son cosas distintas (sección 6.4.3) |
| El asistente dejaba de contestar a veces | Las APIs de IA se saturaban o se acababa su límite de uso | Reintentar, avisar con mensajes claros y cambiar a ChatGPT si Gemini falla | Un servicio externo siempre puede fallar y hay que tener un plan |
| Cada mensaje al asistente salía caro y lento | Se enviaban las descripciones de las 25 funciones en cada mensaje | Enviar solo las funciones de la pantalla actual y contestar directo cuando solo se hicieron acciones | Mandar menos datos a la IA ahorra dinero y tiempo |
| El chat se borraba al cambiar de pantalla | La conversación solo existía en la página abierta | Guardarla en la base de datos y mostrar las últimas 24 horas | Lo que el usuario ve debe poder reconstruirse |
| La caja se recargaba entero con cada clic | Los botones de cantidad mandaban un formulario y la página se volvía a cargar | Pasar la caja a peticiones en segundo plano con JSON | Cada recarga cuenta cuando hay una fila de clientes |
| Fallaba el registro de usuarios nuevos | Había dos métodos de autenticación configurados y Django no sabía con cuál iniciar la sesión | Indicar el método de forma explícita al terminar el registro | Lo detectó una prueba automática del registro |

### 7.2.2 Limitaciones del entorno de desarrollo y de pruebas

El sistema se desarrolló y se probó en computadoras personales de los integrantes del equipo, con una sola instalación local de PostgreSQL. [CONFIRMAR el equipo usado: modelo, procesador y memoria RAM] No contamos con un servidor de pruebas separado ni con un entorno que simulara varias tiendas usando el sistema al mismo tiempo, por lo que no se midió el comportamiento con muchos usuarios simultáneos. Varias pruebas automáticas se corrieron con SQLite porque es más rápido de preparar, así que las diferencias propias de PostgreSQL se revisaron aparte. [CONFIRMAR]

Para el pronóstico no teníamos las ventas de una tienda propia durante un año, y usamos un historial de ventas ya existente. Esto sirve para comprobar que los modelos funcionan, pero no demuestra que acierten en una tienda en particular.

### 7.2.3 Limitaciones de las herramientas y de las APIs externas

El asistente necesita internet para contestar. Si la conexión falla, el cobro y el inventario siguen funcionando, pero el chat y los resúmenes con IA no. Las respuestas de los modelos tardan más que una consulta a la base de datos local, y su duración cambia de un momento a otro, por eso se muestra un indicador de carga en el chat. [COMPLETAR con los tiempos de respuesta que midan]

Los planes gratuitos de las APIs tienen límites de uso por minuto y por día, que son la causa de los errores de saturación que vimos. Además, un modelo de lenguaje puede equivocarse al interpretar una instrucción, y por eso las acciones que no se pueden deshacer, como cancelar una venta o dar de baja un producto, piden confirmación. El dictado de voz depende del navegador que se use y, en algunos casos, también de internet.

### 7.2.4 Decisiones para acotar el alcance

Además de las ideas que quedaron fuera por razones de costo y de uso (sección 5.2.5), tomamos decisiones técnicas para poder terminar a tiempo. Descartamos ejecutar un modelo de lenguaje dentro de la computadora de la tienda, porque requiere un equipo mucho más potente que el que tiene una tienda normal. El pronóstico se limitó a los 10 productos más vendidos, que son los que tienen datos suficientes. El costo del producto que se muestra y con el que se sugieren precios es el de la última compra, y el ISR de RESICO se estima con los ingresos de los últimos 12 meses, como se explica en la sección 6.4.2. En todos estos casos elegimos la opción más simple que sirviera al tendero y dejamos la versión más completa como mejora futura.
