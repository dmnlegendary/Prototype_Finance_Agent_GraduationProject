# Capítulo 5. Metodología y evolución del sistema

## 5.1 Metodología de desarrollo

Para construir el prototipo en el Trabajo Terminal 2 usamos Scrum, adaptado al tamaño de nuestro equipo [1]. Elegimos un marco ágil porque teníamos poco tiempo, éramos solo dos desarrolladores y varias decisiones sobre el alcance cambiaron conforme probábamos el sistema y recibíamos observaciones de los directores. Trabajar en ciclos cortos nos permitió que al terminar cada uno hubiera algo que ya se pudiera abrir en el navegador y probar, en lugar de dejar todo para el final.

### 5.1.1 Roles del equipo

Los directores del proyecto, el Dr. Andrés García Floriano y el Dr. Eduardo Rodríguez Flores, tuvieron el papel de Product Owner. Ellos validaron qué era lo más importante del sistema, revisaron lo que presentábamos al terminar cada ciclo y nos dieron las observaciones que se describen en la sección 5.2.3. El rol de Scrum Master lo compartimos Luis Bernardo Delgado Acosta y Jorge Arif Díaz Jiménez, y consistió sobre todo en organizar las tareas, vigilar el avance y resolver los bloqueos técnicos. El equipo de desarrollo fuimos los mismos dos.

Para repartir el trabajo, cada quien se hizo cargo de una parte. [CONFIRMAR el reparto] Luis llevó la estructura del proyecto en Django, los módulos de ventas e inventario, la interfaz y la integración del asistente con las APIs de inteligencia artificial. Jorge llevó los modelos de pronóstico de ventas, la base de datos en PostgreSQL y las cuentas de prueba. Los cambios importantes los revisábamos entre los dos antes de darlos por buenos.

### 5.1.2 Product Backlog

El Product Backlog fue la lista de todo lo que el sistema debía hacer. Lo armamos a partir de los requisitos del capítulo 3 y lo escribimos como historias de usuario, con el formato "como tendero quiero tal cosa para tal beneficio". Después las agrupamos en cinco bloques grandes, que se muestran en la Tabla 5.1.

Tabla 5.1. Bloques del Product Backlog.

| Bloque | Qué incluye |
|---|---|
| Base y datos | Proyecto en Django, modelo de datos, base de datos PostgreSQL, registro e inicio de sesión |
| Ventas | Pantalla de mostrador, cajas, búsqueda de productos, código de barras, cobro y ticket |
| Inventario | Catálogo, productos a granel, importación desde CSV, alertas de reabastecimiento, proveedores |
| Agente financiero | Gastos, reportes, punto de equilibrio, precios sugeridos, ISR de RESICO y pronóstico de ventas |
| Asistente virtual y resistencia a fallas | Chat con la IA, llamadas a funciones, respaldo entre proveedores de IA y trabajo sin internet |

### 5.1.3 Sprints e iteraciones

El desarrollo se organizó en iteraciones de entre una y tres semanas, con ritmo irregular porque coincidían con otras materias. Las fechas de la Tabla 5.2 salen del historial de commits del repositorio, así que reflejan cuándo se integró cada cosa y no cuándo se planeó. [CONFIRMAR contra el tablero de Jira y ajustar los nombres de los sprints]

Tabla 5.2. Iteraciones del desarrollo.

| Iteración | Periodo | Objetivo | Entregable |
|---|---|---|---|
| 1. Preparación | 8 de junio de 2026 | Crear el repositorio en GitHub, la licencia y el README | Repositorio inicial |
| 2. Primeros pasos | 16 de agosto de 2026 | Armar la estructura inicial y un primer menú de la aplicación | Esqueleto con navegación |
| 3. Rediseño | 26 al 29 de septiembre de 2026 | Rehacer el proyecto con Django, crear las cuentas de usuario, conectar el inventario con una cuenta de prueba, probar los primeros modelos de pronóstico y conectar la API de IA | Sistema funcionando en local con los tres módulos y el asistente |
| 4. Requisitos y pronóstico | 1 al 5 de octubre de 2026 | Completar los requisitos funcionales y enfocar el pronóstico en los 10 productos más vendidos | Pronóstico semanal con tres modelos |
| 5. Observaciones y pulido | 11 y 12 de octubre de 2026 | Atender las observaciones de los directores y de los tenderos, pasar el historial a PostgreSQL y agregar el respaldo entre Gemini y ChatGPT | Prototipo casi final |
| 6. Pruebas y despliegue | Octubre de 2026 en adelante [COMPLETAR] | Pruebas de aceptación y despliegue del frontend en Azure | [COMPLETAR] |

Las fechas de la tabla no coinciden con las del cronograma que presentamos en el TT1, y conviene explicar por qué. En ese cronograma, el módulo de ventas, el servidor y la base de datos estaban planeados desde junio, el modelo de pronóstico entre agosto y septiembre, y el despliegue y las pruebas de usabilidad hacia octubre y noviembre, con la presentación del TT2 en diciembre. [CONFIRMAR contra los cronogramas del TT1] En la práctica empezamos a construir el sistema a mediados de agosto, porque antes tuvimos que atender las observaciones de los sinodales sobre el TT1, y eso recorrió el calendario varias semanas. [CONFIRMAR] Para recuperar el tiempo, comprimimos el trabajo en iteraciones más cortas, pero seguimos el mismo orden lógico del cronograma: primero la base del proyecto y los módulos de ventas e inventario, después los datos y los modelos de pronóstico, luego el agente financiero y, al final, las pruebas y el despliegue.

### 5.1.4 Definition of Done

Acordamos que una tarea estaba terminada cuando se podía usar completa desde el navegador, las pruebas automáticas seguían pasando, las migraciones de la base de datos se aplicaban sin errores sobre una base limpia y el otro integrante del equipo la había revisado. [CONFIRMAR que este es el criterio que usaron] Esta idea de "terminado" es la que propone la guía de Scrum para que todos entiendan lo mismo cuando algo se da por concluido [1].

### 5.1.5 Control de versiones

El código se guardó con Git en un repositorio de GitHub [2]. Cada integrante trabajó en su propia rama (por ejemplo `Arif` y `Bernardo`) y también usamos ramas por equipo de cómputo (`machine`, `machine2` y `machine3`) para probar el sistema en distintas computadoras. Lo que ya funcionaba se unía a la rama `main`. En algunos casos se hizo con pull request, como los dos primeros que vinieron de `machine2` y `machine3`, y en otros con un merge directo.

Este esquema nos dio problemas más de una vez. Cuando los dos subíamos cambios a `main` casi al mismo tiempo, Git nos pedía mezclar las dos versiones antes de aceptar el push, y con las migraciones de Django la mezcla no siempre salió limpia (se explica en la sección 7.2). Para un equipo de dos personas fue suficiente, pero si el proyecto crece convendría tener una rama de integración y revisar siempre con pull request.

### 5.1.6 Herramienta de seguimiento

Para dar seguimiento a las tareas usamos Jira, con un tablero de columnas por estado: pendiente, por hacer, en desarrollo, en revisión, en pruebas y terminado. [CONFIRMAR que se usó Jira] Cada historia se estimó con puntos de historia, y los problemas que nos detenían (por ejemplo, la respuesta lenta de la API de IA) se registraron como incidencias para decidir si se reasignaba la tarea o se recortaba su alcance.

## 5.2 Evolución del sistema

El sistema no quedó como lo imaginamos al principio. Cambió por tres razones: lo que fuimos aprendiendo al construirlo, las observaciones de los directores y lo que vimos en una tienda real y respondieron los tenderos en una encuesta. Esta sección cuenta cómo empezó, cómo fue cambiando y qué ideas dejamos fuera.

### 5.2.1 Versión inicial

Lo primero que se construyó fue lo que cualquier otra función necesita: una forma de registrar ventas y de saber qué hay en el inventario. Sin esos datos no hay nada que calcular ni nada que predecir, así que empezamos por un catálogo de productos y una pantalla de venta con una sola caja. Los datos vivían al principio en archivos CSV y en una base SQLite.

La primera versión del agente financiero se hizo como una aplicación aparte, en React, y el resto del sistema en otra estructura. [CONFIRMAR] A finales de septiembre revisamos el proyecto y vimos que esa forma de trabajar nos estaba dando muchas inconsistencias, porque cada parte tenía su propio código y sus propios datos. Por eso el 26 de septiembre decidimos rehacer todo dentro de un solo proyecto de Django, con una interfaz nueva. De esa decisión salió la estructura que se describe en el capítulo 7.

### 5.2.2 Línea del tiempo

La Tabla 5.3 resume los cambios principales con su fecha de integración, de dónde vino cada uno y por qué se hizo.

Tabla 5.3. Línea del tiempo de los cambios más importantes.

| Fecha | Cambio | Origen | Motivo |
|---|---|---|---|
| 16 ago 2026 | Estructura inicial y primer menú | Plan inicial | Tener una base para empezar a construir los módulos |
| 26 sep 2026 | Proyecto rehecho en Django con interfaz nueva | Decisión del equipo | Evitar un sistema dividido en piezas sueltas y con inconsistencias |
| 27 sep 2026 | Registro e inicio de sesión | Plan inicial | Que cada tienda vea solo sus datos |
| 28 sep 2026 | Primera API de IA, resumen del día y del dashboard, dictado de voz | Plan inicial | Que el tendero pueda hablar con el sistema y entender sus números |
| 29 sep 2026 | Inventario conectado a una cuenta de prueba, con historial | Mejora interna | Probar el sistema con datos parecidos a los de una tienda |
| 5 oct 2026 | Pronóstico enfocado en los 10 productos más vendidos | Mejora interna | Los productos con pocas ventas no tienen datos suficientes para predecir |
| 11 oct 2026 | Semáforo de reabastecimiento por colores, búsqueda instantánea en alertas, resúmenes con IA, caché por negocio y preguntas frecuentes | Observaciones de los directores | Hacer más rápido entender qué hay que resurtir y qué dicen los números |
| 11 oct 2026 | Segunda caja, importación desde CSV, venta con stock en cero y productos a granel | Análisis del equipo sobre el mostrador | Quitar fricción en el mostrador y en el arranque |
| 12 oct 2026 | Paleta de colores con significado | Respuestas de la encuesta a tenderos | Ayudar a ubicar cada función de un vistazo |
| 12 oct 2026 | Historial de ventas e inventario en PostgreSQL | Mejora interna | La lectura de los CSV tardaba demasiado (sección 6.5.3) |
| 12 oct 2026 | Respaldo automático entre Gemini y ChatGPT | Mejora interna | Que el asistente siga contestando si una API falla |

### 5.2.3 Cambios por observaciones de los directores

En las revisiones de avance los directores nos hicieron ocho observaciones que cambiaron partes importantes del sistema. La primera fue sobre cómo avisar que un producto se está acabando. En un inicio solo había una tabla con la cantidad de cada producto. Ahora se usa un semáforo que depende de un campo nuevo, el stock ideal: el producto se marca en amarillo cuando queda la mitad de ese stock, en naranja cuando queda una cuarta parte y en rojo cuando llega a su mínimo. Además, la pantalla de alertas tiene una búsqueda que filtra mientras el tendero escribe, para encontrar un producto sin recorrer toda la lista.

La segunda parte tuvo que ver con la base de datos y las llaves de las APIs. Nos pidieron una base de datos SQL bien armada, y eso nos llevó a PostgreSQL (sección 6.5). También pidieron una forma fácil de poner las llaves de la IA, que resolvimos con un archivo `.env` y un comando que las guarda por nosotros.

La tercera parte fue sobre el asistente. Pidieron que al iniciar sesión aparezca un resumen de cómo le fue a la tienda el día anterior, que el dashboard y los reportes tengan una explicación con IA en palabras sencillas, y que todo lo que se hace a mano en las pantallas se pueda hacer también hablando con el asistente, mediante llamadas a funciones (sección 6.7). Para que no se hicieran consultas repetidas a la IA y a la base de datos, se agregó un caché por negocio (sección 6.5.2). Por último, recomendaron que el sistema se explicara solo, y de ahí salió el botón "?" con preguntas frecuentes (sección 9.2).

### 5.2.4 Cambios por lo observado en tiendas y por la encuesta a tenderos

Durante el desarrollo no pudimos probar el prototipo terminado con tenderos que lo usaran por su cuenta. [CONFIRMAR] Lo que sí hicimos fue estar en un entorno real de tienda para ver cómo trabaja un tendero, y aplicar una encuesta a siete dueños de negocios de la Ciudad de México, cuyos resultados se presentan en la sección 8.3. [COMPLETAR dónde y cuándo fue la visita, cuánto tiempo estuvieron y qué observaron] Esas dos fuentes, junto con nuestro análisis de cómo se atiende un mostrador, explican varios de los cambios.

De la encuesta salieron ideas muy claras sobre la presentación del sistema. Varios tenderos escribieron que para usarlo les gustaría que fuera sencillo y amigable, con palabras sin tecnicismos, y uno de ellos dijo que unos colores llamativos en los botones le ayudarían a entender y a ubicar cada función. Por eso adoptamos una paleta en la que cada color significa una cosa (sección 6.10) y cuidamos que los textos del sistema y las respuestas del asistente estén en lenguaje sencillo. Otros dos pidieron un tutorial en video, lo que se refleja en la sección 9.2, y uno comentó que no conoce bien cómo usar una computadora, lo que confirma la necesidad de que la pantalla se explique sola.

Otros cambios salieron de nuestro análisis de cómo funciona un mostrador. Pensamos que es muy común que un cliente pida varias cosas y se vaya por otra a mitad del cobro mientras otra persona espera, así que agregamos una segunda caja para dejar la cuenta en espera sin perderla. También previmos que a veces el tendero tiene el producto en la mano pero todavía no registró la mercancía que llegó, y un sistema que le impida cobrar lo obligaría a salir de la pantalla de ventas. Por eso, cuando salta la regla de oro, el sistema pregunta cuántas piezas llegaron, las agrega y deja continuar. Por último, como capturar cientos de productos a mano es lo que más desanima a quien empieza, hicimos la importación desde un archivo CSV (sección 6.3.2).

Quedaron fuera algunas ideas que mencionaron los encuestados, como un panel de los productos que más se mueven por temporada y la programación de pagos mes con mes. Se dejaron como trabajo futuro.

### 5.2.5 Funcionalidades que decidimos dejar fuera

Hubo ideas que sí consideramos, pero que decidimos no incluir. En general fue por una de dos razones: salían del alcance de un Trabajo Terminal o hacían más difícil el sistema para el tendero, que es justo lo contrario de lo que queremos lograr.

No se integró hardware especial como básculas o impresoras dedicadas. Conectarlos exige controladores y configuraciones que cambian según la marca, y eso elevaría el costo de usar el sistema. En su lugar, el sistema funciona con los lectores de código de barras que se comportan como teclado, porque no necesitan configuración, y con la impresión normal del navegador para los tickets. Por la misma razón de costo y de trámites quedaron fuera el cobro con tarjeta, que requiere contratos con un banco y cumplir reglas de seguridad de pagos, y las recargas de tiempo aire y pagos de servicios, que dependen de intermediarios con sus propias cuentas y condiciones. El envío de tickets por WhatsApp tampoco se hizo, porque el servicio oficial de la empresa cobra por conversación y pide una verificación del negocio que un micronegocio informal normalmente no tiene.

Tampoco se controló la fecha de caducidad por lote. Aunque lo habíamos pensado en el diseño, pedirle al tendero que capture fecha y lote de cada producto vuelve muy lenta la recepción de mercancía, y en las tiendas de abarrotes la rotación se maneja a la vista, acomodando adelante lo que llegó primero. [CONFIRMAR que esto lo comentaron los tenderos]

Por último, el sistema solo tiene un usuario por tienda, sin roles ni permisos. En la gran mayoría de las tiendas de abarrotes el negocio lo atiende el dueño o su familia, así que separar un administrador de un cajero no resolvía ningún problema real. Los micronegocios son la gran mayoría de los establecimientos del país [3], y en ese tamaño de negocio lo normal es que quien cobra también sea quien surte y quien lleva las cuentas. Además, cada usuario nuevo trae contraseñas, permisos y pantallas por mantener, y para el dueño esas cosas son más una complicación que una ayuda. Hay un comentario de la encuesta que apunta en sentido contrario: un encuestado dijo que se le pasan ventas cuando deja a alguien a cargo, lo que sugiere que saber quién hizo cada venta sí le sería útil a algunos negocios. Por eso dejamos los roles como una mejora futura, que se puede hacer sobre la estructura actual.
