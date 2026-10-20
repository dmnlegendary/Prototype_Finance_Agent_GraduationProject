# Capítulo 8. Plan de pruebas

Las pruebas del sistema se organizaron en tres niveles, siguiendo la idea de ir de lo más pequeño a lo más parecido al uso real [14]. Primero se probaron por separado las funciones y las operaciones básicas (pruebas unitarias), después se probó que los módulos funcionaran completos y juntos, tal como los pide cada requisito funcional (pruebas funcionales, que incluyen las de integración) y, por último, se buscó la opinión de tenderos reales, primero con una encuesta y con la observación de una tienda y, como paso que sigue, con una prueba de aceptación del sistema. No hicimos una sección aparte para el rendimiento porque los tiempos de respuesta se revisaron dentro de las pruebas unitarias.

## 8.1 Pruebas unitarias

Las pruebas unitarias revisan las tareas pequeñas del sistema una por una, como sumar una caja, calcular una fórmula o cargar el inventario, y comprueban dos cosas: que el resultado sea correcto y que no tarde ni consulte más de lo necesario. Se dividieron en las que dependen solo de la computadora local y las que dependen de servicios en la nube.

### 8.1.1 Pruebas en el entorno local

Para las pruebas locales usamos las herramientas de pruebas de Django [4], que crean una base de datos temporal, ejecutan cada prueba y la borran al terminar. Al final del desarrollo el sistema tiene 452 pruebas automáticas, que se corren con un solo comando (`python manage.py test`) y que pasaron todas en la última corrida. La Tabla 8.1 muestra cómo se reparten por aplicación y qué revisan.

Tabla 8.1. Pruebas automáticas por aplicación.

| Aplicación | Pruebas | Qué se comprueba |
|---|---|---|
| finanzas | 92 | Flujo de efectivo, utilidad, margen, ISR de RESICO, punto de equilibrio (también cuando todavía no hay costos), precio sugerido (también el que cubre los gastos), el mes de cada gasto, que la compra de mercancía no se cuente como gasto, los modelos de pronóstico con sus niveles de confianza, el pronóstico por partes, los reportes configurables y el reporte de ventas |
| ventas | 43 | Que los dos cajas no se mezclen, el cambio de cantidad, el cobro, la regla de oro, los productos a granel, que el precio y el costo queden guardados en cada renglón y que una venta no se cobre dos veces |
| inventario | 121 | Alta y edición de productos con sus campos obligatorios, búsqueda con errores de dedo y acentos, importación desde CSV, semáforo, alertas por lotes y por ritmo de venta, compras automáticas y el kardex de movimientos, el costo por lotes (PEPS), la regla de que el precio de venta no sea menor al costo, el stock ideal por promedio, los íconos y los datos base |
| accounts | 32 | Registro, inicio de sesión, datos de la tienda, catálogo inicial, preferencias del negocio y video de bienvenida |
| core | 47 | Caché por negocio, sincronización de operaciones hechas sin internet (también el kardex), llaves de la IA cifradas y comandos de carga |
| avi | 117 | Funciones del asistente, uso de las herramientas por pantalla, reglas del asistente (mensaje fuera de tema, alta con categoría), explicación del pronóstico, historial de 24 horas, mensajes de error y respaldo entre proveedores |

Para revisar el tiempo de respuesta contamos las consultas a la base de datos y el tamaño de la página en las pantallas principales, con una tienda de prueba de 1,100 productos. Es una forma de medir el peso de una pantalla que no depende de qué tan rápida sea la computadora. Con esta revisión encontramos que la pantalla de inventario hacía 92 consultas y pesaba 207 KB, así que se corrigió hasta dejarla en 19 consultas y 83 KB. La Tabla 8.2 muestra el resultado final.

Tabla 8.2. Consultas y tamaño de las pantallas principales (tienda de prueba con 1,100 productos).

| Pantalla | Consultas antes | Consultas después | Tamaño antes | Tamaño después |
|---|---|---|---|---|
| Mostrador de ventas | Sin medir | 9 | Sin medir | 31 KB |
| Búsqueda de productos | Sin medir | 4 | Sin medir | 1 KB |
| Inventario | 92 | 19 | 207 KB | 83 KB |
| Alertas | Sin medir | 4 | 140 KB | 27 KB |
| Historial de ventas | Sin medir | 5 | Sin medir | 29 KB |
| Reportes financieros | 25 | 11 | Sin medir | Sin medir |

Estos números se midieron con SQLite en el entorno de pruebas. [COMPLETAR con los tiempos en milisegundos de las operaciones básicas (buscar un producto, sumar la caja, cargar el inventario, cobrar una venta) medidos en PostgreSQL en su equipo]

### 8.1.2 Pruebas de los servicios en la nube

El asistente depende de las APIs de Google y de OpenAI, y no es buena idea que las pruebas automáticas dependan de internet ni consuman el saldo, así que en esas pruebas se simula la respuesta de las APIs. Con ellas se comprueba que el sistema intente primero con Gemini y pase a ChatGPT cuando Gemini falla, que no se repita una acción si Gemini ya la había ejecutado, que los resúmenes también usen el respaldo, que un error de cuota o de saturación se reintente y uno de llave inválida no, y que cada tipo de error muestre al tendero un mensaje claro. También se comprueba que a cada pantalla solo se le envíen sus funciones.

Lo que no se puede comprobar con simulaciones es cómo se comportan las APIs reales, así que esa parte se probó a mano. [COMPLETAR con la prueba: cuántos mensajes se mandaron, cuánto tardó en promedio Gemini y cuánto ChatGPT, y si hubo respuestas mal interpretadas]

Tabla 8.3. Pruebas del asistente con las APIs reales.

| Prueba | Resultado esperado | Resultado obtenido |
|---|---|---|
| Mensaje sencillo a Gemini | Responde en pocos segundos | [COMPLETAR] |
| Instrucción que requiere una función ("agrega 2 cocas") | Se ejecuta la función y se confirma | [COMPLETAR] |
| Gemini sin llave o sin cuota | El sistema cambia a ChatGPT sin avisar al tendero | [COMPLETAR] |
| Sin llave de ningún proveedor | Mensaje que explica cómo configurarlas | [COMPLETAR] |

## 8.2 Pruebas funcionales

Las pruebas funcionales revisan que cada módulo haga lo que dicen los requisitos funcionales, desde que el tendero hace algo en la pantalla hasta que queda guardado en la base de datos. Por eso incluyen las pruebas de integración: no se probó la vista por un lado y la base de datos por otro, sino toda la cadena completa. Algunos casos se comprobaron con pruebas automáticas y otros abriendo el sistema real en un navegador de pruebas, con datos de ejemplo y manejando la interfaz como lo haría un usuario. La Tabla 8.4 resume los casos de ventas, inventario y finanzas.

Tabla 8.4. Casos de prueba funcionales.

| Caso | Módulo | Qué se hizo | Resultado | Cómo se probó |
|---|---|---|---|---|
| PF-01 | Ventas | Buscar "jbon" para encontrar "Jabón" | Lo encuentra, aunque falten letras y acentos | Navegador |
| PF-02 | Ventas | Agregar con Enter y escribir 90 como cantidad | El total se calcula bien y la pantalla no se recarga | Navegador |
| PF-03 | Ventas | Abrir dos cajas y agregar productos distintos | Cada caja conserva lo suyo | Navegador |
| PF-04 | Ventas | Cobrar un producto con 0 piezas | Se bloquea, se pregunta cuántas llegaron, se suman al inventario con su costo y se registra la compra | Navegador y automática |
| PF-05 | Ventas | Cobrar 350 g de un producto a 40 pesos el kilo | El importe es de 14 pesos | Navegador |
| PF-06 | Ventas | Escanear un código existente y uno que no existe | El primero se agrega; el segundo ofrece dar de alta o cobrar como no encontrado | Navegador |
| PF-07 | Ventas | Cobrar y abrir el ticket | El ticket muestra folio, tienda y ubicación, productos y total | Navegador |
| PF-08 | Sin internet | Cortar la conexión, buscar, armar la caja y cobrar | Funciona, queda en cola y al volver la conexión se sincroniza una sola vez | Navegador |
| PF-09 | Sin internet | Resurtir y dar de alta un producto sin conexión | Al volver la conexión las compras y los productos quedan registrados | Navegador |
| PF-10 | Inventario | Importar un CSV al que le falta una columna obligatoria | No se carga nada | Automática |
| PF-11 | Inventario | Importar un CSV completo | Muestra la revisión por grupos y solo agrega lo confirmado | Automática |
| PF-12 | Inventario | Abrir el catálogo con más de 20 productos | Muestra 20 y carga más con "Ver más" | Navegador |
| PF-13 | Inventario | Bajar un producto por debajo de su mínimo | Cambia de color en el semáforo y aparece en alertas | Automática |
| PF-14 | Finanzas | Capturar una compra de mercancía como gasto | No se permite; la compra solo entra al resurtir | Automática |
| PF-15 | Finanzas | Registrar una venta y un gasto | Las fórmulas del inicio, los reportes y el punto de equilibrio se recalculan | Automática |
| PF-15a | Finanzas | Registrar la luz de un mes pasado con el selector de mes | El gasto cuenta en ese mes y no en el actual, y el historial muestra su mes | Automática |
| PF-15b | Finanzas | Pedir precios sugeridos con la opción de cubrir mis gastos | El margen sale de los gastos sobre ventas más la ganancia extra, y avisa si el margen escrito a mano no alcanza | Automática |
| PF-15c | Inventario | Abrir las alertas con productos que se venden a distinto ritmo | Arriba queda el que se acaba primero y cada alerta dice cuántas piezas vende por semana | Automática |
| PF-16 | Asistente | Pedir "agrega 2 pepsis" estando en ventas | Ejecuta la función correcta y confirma | Automática (API simulada) |
| PF-15d | Inventario | Dar de alta un producto, venderlo y hacer una merma | El kardex tiene un renglón por cada movimiento con la existencia que quedó; se puede filtrar y exportar a CSV | Automática |
| PF-15e | Finanzas | Pedir el reporte de 3 meses y el de un rango de meses | Los totales cuadran con los gastos y ventas de cada mes, y se sugieren acciones según los números | Automática |
| PF-15f | Ventas | Apretar dos veces seguidas el botón de cobrar | Solo se cobra una vez y la segunda petición se rechaza | Automática |
| PF-15i | Inventario | Resurtir la coca con un costo mayor a su precio de venta | Se rechaza y se pide un precio de venta igual o mayor; si se escribe el precio nuevo, se acepta y se actualiza | Automática |
| PF-15j | Inventario | Cargar mercancía tres veces dejando 24, 26 y 29 piezas | El stock ideal queda en 26, el promedio | Automática |
| PF-15k | Registro | Crear una tienda nueva | Arranca con sus 24 proveedores y 19 categorías de gastos, sin duplicarlos si se editan los datos | Automática |
| PF-15h | Inventario | Comprar la coca a 15 pesos, volver a comprarla a 17 y vender 12 piezas | Salen 10 con costo de 15 y 2 con costo de 17; la venta guarda el costo promedio y el segundo lote queda con 8 piezas | Automática |
| PF-08a | Sin internet | Apagar el wifi con productos en la caja y seguir vendiendo | Los productos siguen en la caja, se cobra sin internet y al volver la conexión la venta se guarda una sola vez | Navegador |
| PF-15g | Core | Guardar una llave de la IA y revisar la base de datos | La llave queda cifrada, se lee bien y, si cambia la SECRET_KEY, no truena | Automática |
| PF-16a | Asistente | Pedir "explícame mi pronóstico" | Se manda una segunda llamada a la API con los datos del pronóstico; si no hay datos suficientes ni se llama a la API | Automática (API simulada) |
| PF-17 | Pronóstico | Abrir la pantalla con el historial de ventas | Muestra el pronóstico de cada producto con sus tres modelos | [COMPLETAR] |

La prueba que sigue pendiente es la de un día completo de trabajo en una tienda, con ventas, altas de productos, gastos y consultas al asistente de principio a fin. [COMPLETAR cuando se haga la prueba con los tenderos; se puede resumir aquí lo que se hizo y cuánto duró]

## 8.3 Validación con tenderos

Durante el proyecto quisimos saber qué piensan los tenderos de una herramienta como esta. Lo hicimos de dos maneras: con una encuesta y con la observación de cómo se trabaja en una tienda real. Hay que decir con claridad lo que estas dos cosas son y lo que no son. Sirven para saber si las funciones que proponemos les interesan y qué esperan de ellas, pero no son una prueba de que el sistema terminado les resulte fácil de usar, porque los encuestados no lo han usado. [CONFIRMAR] Esa prueba de aceptación todavía está pendiente y se describe al final de la sección.

### 8.3.1 Encuesta a tenderos

La encuesta se hizo con un formulario en línea, de unas diez preguntas, que mezcla opciones y respuestas abiertas. [COMPLETAR en qué fechas se aplicó y cómo se invitó a participar] Contestaron siete negocios de cinco alcaldías de la Ciudad de México: tres de Tlalpan y uno de cada una de Álvaro Obregón, Azcapotzalco, Coyoacán e Iztacalco. No todos son tiendas de abarrotes, porque entre ellos hay también una farmacia, una frutería y un negocio de uñas, así que sus respuestas hablan de pequeños negocios en general. Con siete respuestas los resultados no se pueden generalizar, pero sí nos dieron una idea de lo que piensan.

Sobre cómo llevan hoy su control, cinco de los siete usan una libreta a mano, dos un punto de venta tradicional y uno una hoja de Excel (podían marcar más de una opción), y ninguno dijo llevarlo solo de memoria. Al preguntarles qué tan fácil es calcular sus ganancias reales y saber qué productos se están acabando al terminar el mes, ninguno contestó "fácil": cinco dijeron "regular" y dos "difícil". Cuando se les preguntó por su mayor problema al registrar ventas, las respuestas fueron distintas: no saber con certeza cuánto se ganó realmente al terminar el día, cuadrar la caja, apuntar lo que falta de mercancía, recordar los precios de lo que menos se vende, organizar los ingresos y que se pasen ventas cuando se deja a alguien a cargo.

La parte de las funciones fue la más reveladora. Seis de los siete respondieron que un asistente digital que conteste preguntas como "¿cuánto gané hoy?" les sería útil sin duda, y seis dijeron que sería muy útil que el sistema sugiera qué productos comprar la semana siguiente. Al pedirles elegir las tres funciones con más valor, las respuestas fueron las de la Tabla 8.5.

Tabla 8.5. Funciones elegidas como más valiosas (cada encuestado elegía tres).

| Función | Respuestas | Porcentaje |
|---|---|---|
| Gestión financiera (cuánto vendí, cuánto gasté, evolución de ventas) | 6 de 7 | 85.7 % |
| Avisos de mercancía que está por terminarse | 4 de 7 | 57.1 % |
| Pronóstico de ventas | 4 de 7 | 57.1 % |
| Chat con el asistente | 2 de 7 | 28.6 % |
| Registrar el contacto de proveedores | 1 de 7 | 14.3 % |

Estos números nos hicieron ver algo importante. Lo que más valoran es saber cuánto ganan y qué deben comprar, es decir, el resultado, y menos el chat como forma de pedirlo. Por eso el sistema no obliga a usar el chat para nada: todo se puede hacer desde las pantallas, y el asistente funciona como un atajo y como una forma de explicar los números en palabras sencillas.

Por último, a la pregunta de qué necesitarían para usar el sistema o por qué no lo usarían, las respuestas se repitieron mucho: que sea fácil y práctico, con una interfaz amigable y sin palabras técnicas. Un tendero escribió que los colores llamativos en cada botón le ayudarían a entender y ubicar cada función, dos pidieron un tutorial en video, otro dijo que no lo usaría si fuera complicado o muy caro, y uno explicó que no conoce bien cómo utilizar una computadora. También hubo dos peticiones de funciones: un panel de los productos que más se mueven por temporada y la programación de pagos mes con mes. Estas respuestas influyeron en la paleta de colores (sección 6.10), en el lenguaje del sistema y en el plan de capacitación (sección 9.2).

### 8.3.2 Observación en una tienda real

[COMPLETAR con lo que observaron en la tienda: cuál fue, cuándo y cuánto tiempo estuvieron, cómo se atiende el mostrador, cuántas cosas lleva el tendero a la vez y qué dificultades vieron. Si se puede, escribir sin el nombre real del negocio]

### 8.3.3 Prueba de aceptación del sistema (pendiente)

Todavía falta que un tendero use el sistema terminado por su cuenta, y es lo que le dará validez a las conclusiones sobre su facilidad de uso. Para hacerlo se propone una sesión corta en el mostrador de una tienda, con las cuatro tareas de la Tabla 8.6, durante la cual alguien del equipo anota cuánto tarda y en qué se atora. Al terminar, el tendero contesta el cuestionario SUS, que mide con diez preguntas qué tan fácil de usar es un sistema y da una calificación de 0 a 100 [15]. Una calificación de 68 puntos suele tomarse como el promedio. Con un solo tendero los resultados serían una referencia y no una medición estadística, pero serían datos reales de uso.

Tabla 8.6. Tareas de la prueba de aceptación.

| Tarea | Qué debe hacer el tendero | Resultado |
|---|---|---|
| 1. Dos cajas | Cobrar una venta de tres productos, dejarla en espera y cobrar otra en el segunda caja | [COMPLETAR] |
| 2. Búsqueda y granel | Encontrar un producto escribiendo solo una parte de su nombre y venderlo por gramos | [COMPLETAR] |
| 3. Importación | Cargar un catálogo de productos desde un archivo CSV | [COMPLETAR] |
| 4. Finanzas y asistente | Revisar el punto de equilibrio y preguntarle algo al asistente | [COMPLETAR] |
| Calificación SUS | Contestar el cuestionario al terminar | [COMPLETAR] |

[COMPLETAR cuando se haga la sesión: tiempos, si terminó sin ayuda, calificación SUS y observaciones. Si no se alcanza a hacer antes de la entrega, esta subsección se queda como trabajo pendiente y se menciona en las limitaciones]
