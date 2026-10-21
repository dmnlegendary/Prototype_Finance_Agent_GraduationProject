# Capítulo 9. Implementación, capacitación y mantenimiento

## 9.1 Implementación y despliegue

Hasta ahora el sistema se ha ejecutado completo en una computadora local: el servidor de Django y la base de datos PostgreSQL funcionan en el mismo equipo y se abren desde el navegador de esa misma computadora. Esto es lo que se usó para el desarrollo y para las pruebas. El siguiente paso es llevar la parte visual a Azure, manteniendo el servidor y la base de datos en el equipo local, que es lo que se describe en esta sección.

### 9.1.1 Arquitectura de despliegue

La idea es dividir el sistema en dos partes. El frontend, es decir, lo que se ve en el navegador (las pantallas, los estilos y el JavaScript), se publicaría en un servicio de Azure. El backend, que es el servidor de Django con la lógica del negocio y la base de datos, seguiría en la computadora de la tienda. Dejar los datos en el equipo local tiene dos ventajas: la información del negocio no sale de la tienda y no se paga por una base de datos en la nube. El diagrama de despliegue está en la sección 4.7.

Hay un detalle por resolver. En el sistema actual, Django es quien genera las pantallas, así que no es tan directo mover "solo el frontend". Hay dos caminos: publicar en Azure únicamente los archivos estáticos (hojas de estilo, scripts e imágenes) y dejar que Django siga armando las páginas, o convertir las pantallas en una aplicación independiente que consuma la API en JSON del backend. El primero es más sencillo y el segundo es más parecido a una arquitectura separada. [DECIDIR cuál van a hacer y ajustar esta sección]

### 9.1.2 Instalación del backend local

Para instalar el sistema en una computadora nueva se necesita Python 3.12 o posterior y, si se va a usar PostgreSQL, instalarlo y crear la base de datos con el archivo `database/crear_base.sql`, como se explica en la guía de la carpeta `database`. Si no se configura una base de datos, el sistema usa SQLite y funciona igual, aunque más lento con muchos datos. Después se ejecutan estos comandos desde la carpeta del proyecto.

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

El primer comando crea un entorno virtual para que las bibliotecas del proyecto no se mezclen con las del resto de la computadora. El tercero instala las dependencias que están en `requirements.txt`. El archivo `.env` contiene los datos de la base de datos y, de forma opcional, los de seguridad, el correo y el video de bienvenida. El comando `migrate` crea las tablas, y debe ir antes de `configurar_ia`, que pide las llaves de ChatGPT y Gemini sin mostrarlas en pantalla y las guarda cifradas en la base de datos (con `--desde-env` pasa a la base las que ya estén en el `.env`, y con `--ver` muestra cuáles hay, tapadas). El cifrado usa la `SECRET_KEY` de Django, así que en un servidor publicado esa llave debe fijarse en el `.env` con `DJANGO_SECRET_KEY`; si cambia, las llaves guardadas ya no se pueden descifrar y hay que capturarlas otra vez. Por último, `seed_catalogo` carga el catálogo de productos que se ofrece al registrar una tienda. Al final, `runserver` inicia el sistema, que se abre en `http://localhost:8000/`. No hace falta crear un administrador, porque cada tienda se registra desde la propia aplicación.

Con la configuración actual el sistema solo acepta conexiones desde la misma computadora. Si se quisiera usar desde una tableta o un celular conectado a la misma red de la tienda, habría que permitir la dirección del equipo en la configuración de Django y arrancar el servidor para que acepte conexiones de la red. [COMPLETAR si se va a hacer así y probarlo]

### 9.1.3 Publicación del frontend en Azure

[COMPLETAR cuando se haga el despliegue: qué servicio de Azure se usó, cómo se subieron los archivos, la dirección final y los problemas que aparecieron]

### 9.1.4 Comunicación entre frontend y backend

Hoy el navegador y el servidor están en el mismo origen, así que las peticiones funcionan sin configuración extra, y el sistema se protege con la sesión y con el código de seguridad de Django. Cuando el frontend esté en Azure y el backend en la tienda, el navegador va a hacer peticiones a otro dominio, y habrá que resolver tres cosas: permitir ese origen en el servidor (lo que se conoce como CORS), usar conexiones seguras con HTTPS y lograr que Azure, o más bien el navegador del tendero, pueda llegar al equipo de la tienda desde internet. Esto último es lo más delicado, porque un equipo en una red doméstica normalmente no es accesible desde fuera. [DECIDIR cómo se va a resolver y escribir aquí la solución elegida]

### 9.1.5 Costos del despliegue

El sistema se diseñó para que no tenga costos fijos de servidor: no se compra hosting ni se paga una base de datos en la nube. Los costos que quedan son los del equipo que ya tiene la tienda, el internet, la electricidad y el uso de las APIs de IA. La Tabla 9.1 retoma las cifras del análisis de factibilidad del capítulo 3. [CONFIRMAR que estos montos coinciden con el capítulo 3 y agregar el costo de Azure una vez que se defina el servicio]

Tabla 9.1. Costos considerados para el piloto.

| Concepto | Tipo | Monto (MXN) |
|---|---|---|
| Computadora de la tienda | Recurso que ya existía | 10,000.00 |
| Licencias de software (Python, Django, PostgreSQL) | Software libre | 0.00 |
| Uso de las APIs de IA | Operación | 750.00 |
| Internet | Operación | 800.00 |
| Electricidad del equipo | Operación | 600.00 |
| Frontend en Azure | Operación | [COMPLETAR] |

### 9.1.6 Verificación posterior al despliegue

Después de instalar el sistema en un equipo conviene hacer una revisión rápida antes de empezar a usarlo con clientes. Primero, comprobar que se pueda registrar una tienda, iniciar sesión y que el catálogo cargue. Segundo, hacer una venta de prueba con dos cajas y revisar que baje el inventario y que el ticket salga bien. Tercero, mandar un mensaje al asistente para confirmar que la llave de IA sirve, y comprobar que sin internet el cobro sigue funcionando. Por último, si se usa lector de código de barras, escanear un producto para ver que el número se capture en el buscador.

## 9.2 Capacitación de usuarios

Los dueños de tiendas trabajan muchas horas y no tienen tiempo de leer manuales o tomar cursos. Muchos, además, prefieren abrir una aplicación y empezar a tocar, así que nos pareció que la capacitación debía ser corta y estar dentro del propio sistema, y no en un documento aparte. En la encuesta, dos de siete tenderos pidieron un tutorial en video y uno dijo que no sabe usar bien la computadora (sección 8.3).

### 9.2.1 Video de presentación

Se va a elaborar un video corto, de dos a tres minutos y con un ritmo parecido al de un tráiler, que muestre el problema de la fila detenida en el mostrador y cómo lo resuelve el sistema: dos cajas, semáforo de reabastecimiento, cobro con regla de oro y el asistente. Además del video principal, conviene grabar clips de menos de un minuto para cada módulo, pensados para verse desde el celular, por si algún tendero quiere ver cómo se hace algo específico. [COMPLETAR con los enlaces cuando estén listos] [DECIDIR si los clips serán verticales]

### 9.2.2 Preguntas frecuentes dentro del sistema

El sistema tiene un botón con un signo de interrogación, al lado de la foto de perfil, que abre una ventana con preguntas frecuentes. Las preguntas están agrupadas por tema (ventas, inventario, finanzas, asistente y cuenta) y se responden con texto corto. Hay un buscador para escribir la duda con las propias palabras del tendero. La ventana se abre y se cierra sin recargar la página ni interrumpir lo que esté haciendo.

### 9.2.3 El asistente como apoyo

El asistente también ayuda a aprender el sistema. Si el tendero le pide algo que se hace en otra pantalla, le explica en cuál. Si no entiende lo que le pidieron, en lugar de marcar un error le explica qué sí puede hacer y le da ejemplos, como "agrega dos cocas a la caja" o "registra un gasto de luz de 450 pesos". Y como puede ejecutar las acciones directamente, también sirve para hacer las cosas sin tener que aprender dónde está cada botón.

## 9.3 Plan de mantenimiento

Con el sistema instalado en la tienda, alguien tiene que cuidar que los datos no se pierdan y que el sistema siga funcionando con el paso del tiempo. Las tareas que siguen se plantean como recomendaciones para quien lo instale, y se indica cuáles ya están en el sistema y cuáles todavía no.

### 9.3.1 Respaldos de la base de datos

Todo lo que el tendero captura vive en la base de datos, por lo que perderla significaría perder su historial de ventas y de inventario. PostgreSQL trae la herramienta `pg_dump`, que genera un archivo con una copia completa de la base de datos [16]. La recomendación es programar una copia diaria, al cerrar la tienda, con el Programador de tareas de Windows, y conservar las de los últimos siete días. Para más seguridad, esa carpeta se puede copiar a una memoria USB o a otra computadora, porque una copia que está en el mismo disco se pierde si el disco falla.

```
pg_dump -U postgres -Fc -f respaldo_AAAA-MM-DD.dump maria_db
pg_restore -U postgres -d maria_db -c respaldo_AAAA-MM-DD.dump
```

El primer comando hace la copia y el segundo la restaura sobre la base de datos, borrando antes las tablas actuales. [COMPLETAR cuando se prepare el script automático de respaldo, porque todavía no está en el proyecto]

### 9.3.2 Actualización del sistema y migraciones

Cuando el sistema cambia, por ejemplo al agregar un campo a un producto, la estructura de la base de datos también debe cambiar, y Django lo hace con migraciones [4]. Las versiones recientes agregaron migraciones para el mes de los gastos, el kardex, las llaves cifradas, las preferencias del negocio y el tipo de explicación del pronóstico, y la biblioteca `cryptography` a los requisitos, así que al actualizar también hay que volver a correr `python -m pip install -r requirements.txt`. Para actualizar una instalación se recomienda este orden: hacer primero un respaldo de la base de datos, descargar el código nuevo desde el repositorio, aplicar las migraciones con `python manage.py migrate` y reiniciar el servidor. Si algo sale mal, se puede regresar a una migración anterior con el mismo comando indicando su número y restaurar el respaldo que se hizo al inicio.

### 9.3.3 Pronóstico de ventas

El pronóstico no usa modelos guardados que haya que volver a entrenar cada cierto tiempo. Cada vez que se calcula, ARIMA se ajusta con todo el historial semanal disponible en la base de datos del negocio. La desventaja es que el cálculo se repite en cada consulta y su duración aumenta con la longitud de la serie. Si en el futuro hay muchas tiendas o muchos años de datos, convendría medir el rendimiento y valorar guardar el resultado una vez al día. [COMPLETAR si el equipo decide agregar un reentrenamiento programado]

### 9.3.4 Uso y costo de las APIs de IA

El sistema ya hace varias cosas para gastar poco en las APIs: manda solo las funciones de la pantalla actual, contesta directo sin llamar otra vez al modelo cuando solo hubo acciones, guarda el resumen diario y las explicaciones para no pedirlas de nuevo y usa un caché del contexto de la tienda. Lo que todavía no tiene es un registro de cuántas palabras se consumen ni un límite diario de mensajes. Por ahora, el consumo se revisa en los paneles de Google AI Studio y de OpenAI, y registrar el consumo dentro del sistema sería una mejora para una versión posterior.

### 9.3.5 Soporte y corrección de errores

Cuando el sistema falla al hablar con la IA, el error completo se escribe en la terminal donde corre el servidor y el tendero ve un mensaje claro de lo que pasó, sin términos técnicos. Hoy esos registros no se guardan en un archivo, lo cual dificulta revisar fallas de días anteriores, y es otra mejora para una versión posterior. Los fallos de una parte no deben detener a las demás: si no hay internet, el cobro y el inventario siguen funcionando, y si la computadora se apaga de golpe, PostgreSQL recupera la base de datos hasta la última operación que sí se alcanzó a guardar.

### 9.3.6 Aviso de uso y privacidad

Como el sistema se presenta como prototipo académico, no se necesita un contrato formal de uso, pero sí es recomendable mostrar un aviso corto para que el tendero entienda lo que el sistema hace y lo que no. Además, el sistema guarda datos personales del tendero, como su nombre, teléfono y correo, por lo que conviene un aviso de privacidad que diga qué datos se guardan y para qué, de acuerdo con la ley de protección de datos personales en posesión de particulares que está vigente desde marzo de 2025 [17]. [CONFIRMAR con los directores si les piden incluirlo y revisar el texto con alguien que conozca la ley]

El aviso podría decir lo siguiente.

Este sistema es un prototipo desarrollado con fines académicos en la Escuela Superior de Cómputo del Instituto Politécnico Nacional. Los cálculos de utilidad, punto de equilibrio, precios sugeridos y pronósticos de venta son estimaciones que se hacen con los datos que usted captura y no sustituyen la asesoría de un contador. El cálculo del ISR de RESICO es solo una referencia para planear su efectivo, y el pago de sus impuestos es responsabilidad suya ante el SAT. Los pronósticos no garantizan ventas futuras, y la decisión de cuánto comprar es de usted. Los datos que capture en el sistema se usan únicamente para su funcionamiento y no se comparten con otras tiendas. Cuando usa el asistente, parte de la información de su tienda, como los productos, las ventas del día y los resultados que usted consulta, se envía a Google y a OpenAI para generar las respuestas.
