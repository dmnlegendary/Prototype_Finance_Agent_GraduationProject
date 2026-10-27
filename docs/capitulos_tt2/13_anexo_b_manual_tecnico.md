# Anexo B. Manual técnico

Este manual es para quien tenga que instalar, configurar, actualizar o dar mantenimiento a marIA: los dos autores, los profesores que lo revisen o la persona que lo lleve a un servidor. Complementa al capítulo 7, que explica cómo está organizado el código, y al capítulo 9, que habla del despliegue; aquí se concentran los comandos y la configuración que hacen falta para tener el sistema funcionando.

## B.1 Requisitos

El sistema está hecho con Django, así que necesita Python 3.12 o posterior y la herramienta pip para instalar sus bibliotecas. Con eso basta para ejecutarlo en una computadora, porque por defecto usa una base de datos SQLite que no requiere instalar nada. Para trabajar con más datos o para publicarlo se recomienda PostgreSQL, que el sistema usa en cuanto se le indica una base de datos en el archivo de configuración. Para usar al asistente hacen falta una llave de la API de Google (Gemini), una de OpenAI (ChatGPT) o ambas; sin ninguna, todo lo demás funciona y solo el chat y las explicaciones avisan que no están disponibles. En el navegador del usuario, Chrome o Edge permiten el dictado por voz; el resto del sistema funciona en los navegadores modernos.

Las bibliotecas que se instalan están en `requirements.txt`: Django (de la versión 5.1 a la 5.x), las bibliotecas de OpenAI y de Google para el asistente, `python-dotenv` para leer el archivo de configuración, `psycopg` como controlador de PostgreSQL, `statsmodels` para el pronóstico de ventas y `cryptography` para cifrar las llaves de las APIs.

## B.2 Instalación en una computadora nueva

Todos los comandos se ejecutan desde la carpeta del proyecto. En Windows quedan así.

```
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py configurar_ia
python manage.py seed_catalogo --negocios
python manage.py runserver
```

El primer comando crea un entorno virtual, para que las bibliotecas del proyecto no se mezclen con las de otros programas, y el segundo lo activa. Conviene usar siempre `python -m pip` en lugar de `pip` a secas, porque si hay más de un Python instalado un `pip` suelto puede instalar en el equivocado. El archivo `.env` se crea copiando el ejemplo y es donde viven los datos propios de cada instalación (sección B.3); nunca se sube al repositorio. El comando `migrate` crea las tablas, y debe ir antes de `configurar_ia`, que usa una de ellas. `seed_catalogo` carga las categorías y el catálogo de productos que se ofrece al registrar una tienda, y con `--negocios` completa las tiendas que ya existan con sus proveedores y categorías de gastos. Al final, `runserver` inicia el sistema en `http://localhost:8000/`. No hace falta crear un administrador, porque cada tienda se registra desde la propia aplicación; para entrar al panel de administración de Django (`/admin/`) se puede crear uno con `python manage.py createsuperuser`.

Para comprobar que la instalación quedó bien se corren las pruebas automáticas, que crean una base de datos temporal y la borran al terminar.

```
python manage.py test
```

Al momento de escribir este manual el sistema tiene 472 pruebas, que se pueden correr por aplicación indicando su nombre, por ejemplo `python manage.py test inventario`.

## B.3 Configuración con el archivo .env

Todo lo que cambia de una instalación a otra se lee del archivo `.env`, y el archivo `.env.example` trae las variables comentadas para copiarlas. Ninguna es obligatoria para desarrollo local. La Tabla B.1 las resume.

Tabla B.1. Variables del archivo .env.

| Variable | Para qué sirve |
|---|---|
| `OPENAI_API_KEY`, `GEMINI_API_KEY` | Llaves de las APIs de IA. Se pueden dejar vacías si se guardan con `configurar_ia` |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexión a PostgreSQL. Si `DB_NAME` está vacío se usa SQLite |
| `DJANGO_SECRET_KEY` | Llave secreta de Django. En un servidor debe fijarse y no cambiar, porque con ella se cifran las llaves de las APIs |
| `DJANGO_DEBUG` | `False` en producción |
| `ALLOWED_HOSTS` | Direcciones desde las que se acepta el sistema, separadas por comas |
| `CSRF_TRUSTED_ORIGINS` | Orígenes seguros para los formularios cuando hay un dominio propio |
| `USAR_HTTPS` | Con `True` obliga a usar HTTPS y marca las cookies como seguras |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS` | Servidor de correo para recuperar contraseñas. Sin ellos el correo se imprime en la terminal |
| `VIDEO_INTRODUCTORIO_URL` | Enlace de incrustación del video de bienvenida |
| `PRONOSTICO_MINIMO_DIAS` | Días mínimos de ventas para calcular el pronóstico (30 por defecto) |

Las llaves de las APIs y la llave secreta nunca deben escribirse en el código, en capturas ni en el documento. Para guardar las llaves de las APIs se usa el comando `configurar_ia`, que las pide sin mostrarlas en pantalla y las guarda cifradas en la base de datos.

```
python manage.py configurar_ia
python manage.py configurar_ia --openai sk-... --gemini AIza...
python manage.py configurar_ia --archivo claves.txt
python manage.py configurar_ia --desde-env
python manage.py configurar_ia --ver
```

La segunda forma recibe las llaves como parámetros, la tercera lee un archivo de texto con líneas como `OPENAI_API_KEY=...`, la cuarta pasa a la base de datos las llaves que ya estén en el `.env` y la última muestra cuáles hay y de dónde salen, siempre tapadas. Las llaves se cifran con Fernet, usando una clave derivada de `DJANGO_SECRET_KEY`. Por eso, si esa llave secreta cambia, las llaves guardadas ya no se pueden descifrar: el sistema no truena, simplemente las trata como ausentes y hay que capturarlas de nuevo.

## B.4 Base de datos

Con SQLite no hay nada que hacer: el archivo `db.sqlite3` se crea con las migraciones. Para usar PostgreSQL se instala el servidor, se crea la base de datos con el archivo `database/crear_base.sql` y se llenan las variables `DB_*` del `.env`; los pasos detallados están en `database/README.md`, que también incluye consultas útiles en `consultas_utiles.sql`. Después se corre `python manage.py migrate` para crear las tablas.

El sistema tiene 18 tablas propias. Las de cuentas son el usuario y el negocio; las de inventario, las categorías, los proveedores, el catálogo precargado, los productos, el historial de cambios de cada producto, el kardex de movimientos y los lotes de compra; las de ventas, la venta y sus renglones; las de finanzas, los gastos y sus categorías; las del asistente, la conversación, el resumen diario y las explicaciones con IA; y las de uso interno, las operaciones sincronizadas sin internet y las llaves cifradas de las APIs. La Tabla 6.1 del capítulo 6 las describe una por una.

La base de datos cuida sus propias reglas con restricciones: no puede haber dos ventas con el mismo folio en una tienda, ni existencias o precios negativos, ni cantidades vendidas en cero o menos. Esas restricciones, junto con las validaciones de los formularios, evitan que un error de la pantalla deje datos inconsistentes.

Los datos de ejemplo para pruebas están en `database/ejemplos`. Para cargar un historial grande de productos y ventas se usa un comando que inserta por paquetes de mil registros dentro de una sola transacción, y por eso es rápido.

```
python manage.py importar_csv --usuario correo_o_telefono --productos productos.csv --ventas ventas.csv
```

El archivo de productos lleva el nombre, la categoría, el costo, el precio de venta y las cantidades; el de ventas, la fecha, el folio, el producto, la cantidad y el precio, con un renglón por producto vendido y el mismo folio para los de un mismo ticket.

## B.5 Actualizar el sistema

Cuando el código cambia, la estructura de la base de datos puede cambiar con él, y Django lo maneja con migraciones. El orden recomendado para actualizar una instalación es hacer un respaldo de la base de datos, descargar el código nuevo, volver a instalar las dependencias por si se agregó alguna, aplicar las migraciones y reiniciar el servidor.

```
python -m pip install -r requirements.txt
python manage.py migrate
```

Si algo sale mal, se puede regresar a una migración anterior con el mismo comando indicando su número, y restaurar el respaldo que se hizo al principio. Las migraciones del sistema incluyen pasos que llenan datos de lo que ya había, por ejemplo al agregar los lotes de compra se crea uno por cada producto que ya tenía piezas.

## B.6 Cómo está organizado el código

El proyecto es una aplicación de Django dividida por módulos, como se vio en el capítulo 7. La carpeta `config` guarda la configuración y las rutas; `core` guarda lo compartido, como el caché por tienda, la sincronización de lo hecho sin internet, el cifrado de llaves y los comandos de carga; `accounts` maneja usuarios, registro y datos de la tienda; `inventario`, `ventas` y `finanzas` son los tres módulos que ve el tendero; y `avi` es el asistente. Cada aplicación lleva sus plantillas, sus archivos de estilos y scripts y sus pruebas.

La regla de diseño que más importa para darle mantenimiento es que la lógica no vive en las vistas sino en módulos aparte, y que las pantallas y el asistente llaman a las mismas funciones. Por eso `finanzas/calculos.py` concentra las fórmulas financieras y el pronóstico, `finanzas/graficas.py` prepara los datos de las gráficas, `ventas/cobro.py` el cobro y la regla de oro, `inventario/compras.py` las entradas de mercancía, `inventario/lotes.py` el costo por lotes y `inventario/movimientos.py` el kardex. Cualquier regla de negocio nueva debe ponerse ahí y no en una pantalla. Por ejemplo, la regla de que el precio de venta no sea menor al costo está en una sola función de `inventario/compras.py`, que usan el formulario de productos, el resurtido, la importación y el asistente.

El navegador habla con el servidor con peticiones a rutas que responden en JSON (las `api` de ventas, la búsqueda, el chat y la sincronización) y todas las que modifican datos llevan el código de seguridad de Django. La Tabla 7.1 lista las rutas principales.

## B.7 El asistente de inteligencia artificial

El asistente usa llamadas a funciones: el modelo no accede a la base de datos ni escribe consultas, solo elige entre una lista fija de 25 funciones definidas en `avi/services.py`, que ejecutan las mismas operaciones que la interfaz y con las mismas validaciones. A cada mensaje se le manda al modelo solo las funciones de la pantalla donde está el usuario, más las consultas, para gastar menos. La comunicación con las APIs está en `avi/clients.py`: primero se intenta con Gemini (Interactions API, paquete `google-genai`, modelo `gemini-3.8-flash`) y, si no responde, con ChatGPT (`gpt-4o-mini`). Si el primer modelo ya alcanzó a ejecutar una acción antes de fallar, no se repite con el segundo, para no duplicarla.

Para controlar el costo, el sistema contesta directo sin una segunda llamada cuando solo se ejecutaron acciones, guarda el resumen del día y las explicaciones para no pedirlas otra vez y usa un caché del contexto de la tienda. El chat conserva 24 horas de historial. Las explicaciones de reportes, del inicio y del pronóstico se piden aparte y solo se mandan a la API cuando hay datos suficientes.

El texto que guía al modelo (el prompt) está en `avi/clients.py`. Ahí se define que solo atiende temas de la tienda y el mensaje estándar con el que rechaza lo demás, y cualquier cambio en el comportamiento del asistente empieza por ese texto y por las descripciones de las funciones.

## B.8 Pronóstico de ventas

El pronóstico se calcula en `finanzas/calculos.py` con los diez productos más vendidos y las ventas de las últimas 26 semanas. Se ajustan tres modelos, una regresión lineal escrita a mano, un ARIMA(1,1,1) y un Holt-Winters aditivo con estacionalidad de cuatro semanas, y se compara el error absoluto medio de cada uno contra las últimas cuatro semanas conocidas. Los modelos no se guardan: se ajustan cada vez que se abre la pantalla, y por eso el resultado se guarda en el caché por tienda y se invalida con cada venta nueva. La pantalla pide primero la base y luego cada modelo por separado, para no bloquearse. Si hay menos días de ventas que los de `PRONOSTICO_MINIMO_DIAS`, el sistema no calcula y avisa por qué.

## B.9 Funcionamiento sin internet

Las pantallas principales las guarda un service worker (`static/sw.js`) para poder abrirlas sin conexión. Los archivos propios de estilos y scripts se piden primero al servidor y solo se usa la copia guardada cuando no hay internet, así no se quedan versiones viejas; cuando se cambia la lógica del service worker conviene subir su número de versión. Los datos no se guardan ahí: lo que se hace sin conexión se pone en una cola en el navegador (`static/js/sinconexion.js`) y se manda al servidor al regresar el internet, donde `core/sync.py` lo aplica. Cada operación lleva un identificador único, así que si se manda dos veces solo se guarda una.

## B.10 Seguridad

El acceso se controla con sesiones de Django. Las contraseñas se guardan con los algoritmos de la biblioteca, pasan por los validadores de contraseñas y no pueden recuperarse, solo restablecerse por correo. Se puede iniciar sesión con el correo o con el teléfono. Los formularios y las peticiones que cambian datos llevan el código CSRF, y cada consulta se filtra por la tienda del usuario, de modo que una tienda no puede ver ni modificar los datos de otra. Las llaves de las APIs se cifran en la base de datos y nunca llegan al navegador. Al crear la cuenta se guarda la fecha en que se aceptaron los términos y condiciones.

Para publicar el sistema deben fijarse `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`, y activarse `USAR_HTTPS=True`, que redirige a HTTPS y marca las cookies como seguras. Los temas de TLS 1.3, cifrado en reposo y OAuth 2.0 que se mencionan en los términos y condiciones son lo que se recomendaría en un entorno productivo y no están implementados en el prototipo.

## B.11 Despliegue

El sistema se despliega completo en una computadora del equipo (el servidor local) y se publica en internet con un túnel de Cloudflare, que funciona como puente entre la web y esa computadora. No se usa Azure ni otro servicio de hosting. El túnel lo crea el programa `cloudflared`, que abre una conexión de salida hacia Cloudflare y por ella recibe las peticiones de la dirección pública del sistema, de modo que no hay que abrir puertos en el router ni contar con una IP pública. Cloudflare además entrega el certificado HTTPS.

Los pasos generales son los siguientes. En la computadora del servidor se instalan Python, PostgreSQL y las dependencias como se explica en las secciones B.2 y B.4, y se prepara el `.env` con `DJANGO_DEBUG=False`, una `DJANGO_SECRET_KEY` fija, `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` con el dominio público en `https://` y `USAR_HTTPS=True`. El servidor de Django debe ejecutarse con un servidor de aplicaciones como gunicorn, que todavía no está en `requirements.txt`, y no con `runserver`. En la cuenta de Cloudflare se crea un túnel, se asocia un nombre público con la dirección local donde escucha Django (por ejemplo `http://localhost:8000`) y se instala `cloudflared` en la computadora, dejándolo como servicio para que arranque con el equipo. Cloudflare avisa que la conexión original fue segura con el encabezado `X-Forwarded-Proto`, que la configuración del proyecto ya reconoce con `SECURE_PROXY_SSL_HEADER`, así que no se forman ciclos de redirección.

Hay tres puntos que hay que resolver antes de publicar. Primero, con `DJANGO_DEBUG=False` Django no sirve los archivos de estilos y scripts, así que hace falta WhiteNoise o un servidor web que lo haga, y WhiteNoise tampoco está en las dependencias; antes de arrancar se ejecuta `python manage.py collectstatic`. Segundo, el caché del sistema es el de memoria de Django, que vive dentro de cada proceso; con un solo proceso funciona bien, pero si se ejecutan varios cada uno tendría su propio caché y las invalidaciones no se compartirían, por lo que habría que cambiarlo por uno compartido como Redis. Tercero, la disponibilidad depende de que el equipo esté encendido y con internet, por lo que conviene configurar el arranque automático de PostgreSQL, Django y `cloudflared` y hacer respaldos de la base de datos hacia otro equipo. Un `docker compose` con Django, PostgreSQL y `cloudflared` facilitaría repetir la instalación en otra computadora, pero no está implementado. [COMPLETAR cuando se haga el despliegue: dominio, nombre del túnel, forma de arranque automático y problemas encontrados]
## B.12 Problemas frecuentes

La Tabla B.2 reúne los problemas que más se presentaron durante el desarrollo y cómo resolverlos.

Tabla B.2. Problemas frecuentes y su solución.

| Problema | Causa probable | Qué hacer |
|---|---|---|
| El chat dice que no pudo conectarse | Ninguna llave configurada, sin saldo o servicio saturado | Revisar con `configurar_ia --ver`; el sistema ya intenta con el segundo proveedor |
| Las llaves guardadas ya no funcionan | Cambió `DJANGO_SECRET_KEY` | Fijar la llave secreta y volver a capturar las llaves con `configurar_ia` |
| Error al iniciar por una tabla que no existe | Faltan migraciones | Correr `python manage.py migrate` |
| `configurar_ia` falla por una tabla | Se corrió antes de `migrate` | Correr primero `migrate` |
| Una pantalla se ve con estilos o comportamiento viejo | El navegador tiene guardada una versión anterior | Recargar con Ctrl+F5; si persiste, borrar los datos del sitio |
| El dictado por voz no responde | Navegador sin soporte (Firefox), sin permiso de micrófono o sin internet | Usar Chrome o Edge y permitir el micrófono |
| El pronóstico no se calcula | Hay menos días de ventas que `PRONOSTICO_MINIMO_DIAS` | Esperar a tener historial o bajar el valor en el `.env` |
| No se conecta a PostgreSQL | Datos de `DB_*` incorrectos o servicio apagado | Revisar el `.env` y que el servidor de PostgreSQL esté activo |
| `pip` instala en otro Python | Hay varios Python instalados | Usar siempre `python -m pip` con el entorno virtual activo |

## B.13 Mantenimiento

Con el uso normal conviene hacer respaldos de la base de datos, revisar de vez en cuando el consumo de las APIs de IA, que es el único gasto variable del sistema, y volver a correr las pruebas automáticas después de cada cambio. Los errores al hablar con la IA se escriben completos en la terminal donde corre el servidor y el usuario ve un mensaje claro; hoy esos registros no se guardan en un archivo, así que para revisar fallas de días anteriores habría que agregar un registro a archivo en la configuración.
