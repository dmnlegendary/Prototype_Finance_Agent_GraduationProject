# Capítulo III. Plan de Desarrollo del Software

> **Nota para el equipo (borrar antes de entregar):** donde dice **[COMPLETAR]** hay información que solo ustedes conocen (fechas, roles, herramientas de seguimiento, etc.). No la inventé. Donde dice **[AJUSTAR]** hay una propuesta mía que deben confirmar.

---

## 3.1 Metodología de Desarrollo

Para construir el sistema usamos una forma de trabajo ágil, inspirada en Scrum [8]. En lugar de hacer todo el sistema de una sola vez y probarlo hasta el final, lo fuimos armando en partes pequeñas. Al terminar cada parte la revisábamos, corregíamos lo que fallaba y hasta entonces pasábamos a la siguiente. **[COMPLETAR: confirmar si realmente usaron Scrum. Si usaron otra metodología, cambiar el nombre y ajustar este apartado.]**

### 3.1.1 Por qué elegimos una forma ágil

- Somos un equipo de dos personas, así que no necesitábamos una metodología con muchos documentos ni muchos roles.
- Los requerimientos fueron cambiando mientras avanzábamos. Por ejemplo, las fórmulas financieras se definieron ya con el sistema funcionando, y los colores y el orden de las pantallas se ajustaron varias veces después de enseñarlas.
- Queríamos ver el sistema funcionando en el navegador desde las primeras semanas, para detectar errores a tiempo.

### 3.1.2 Roles del equipo

| Integrante | Rol | Actividades principales |
|---|---|---|
| Luis Bernardo Delgado Acosta | **[COMPLETAR]** | **[COMPLETAR]** |
| Jorge Arif Diaz Jimenez | **[COMPLETAR]** | **[COMPLETAR]** |
| Directores / asesores | **[COMPLETAR]** | Revisión de avances |

### 3.1.3 Etapas del desarrollo

Dividimos el trabajo en las siguientes etapas. Cada una dejó algo que se podía probar.

| Etapa | Qué se hizo | Resultado | Fechas |
|---|---|---|---|
| 1. Planeación y base | Definir los módulos del sistema, crear el proyecto en Django y el repositorio en Git. | Proyecto base funcionando. El primer registro en Git es del 8 de junio de 2026. | **[COMPLETAR]** |
| 2. Seguridad y registro | Registro en 3 pasos (cuenta, negocio y productos iniciales), inicio de sesión. | El tendero puede crear su cuenta y su tienda. | **[COMPLETAR]** |
| 3. Inventario | Alta, edición y baja de productos, proveedores, categorías y alertas de stock bajo. | Catálogo de productos y alertas funcionando. | **[COMPLETAR]** |
| 4. Ventas | Carrito, búsqueda mientras se escribe, cobro, ticket e historial de ventas. | Se puede vender y se descuenta el inventario. | **[COMPLETAR]** |
| 5. Diseño de interfaz | Pantallas adaptables a computadora, tablet y celular; iconos, colores y letra más claros. | Interfaz sencilla y con el mismo estilo en todos los módulos. | **[COMPLETAR]** |
| 6. Agente financiero | Registro de gastos, reportes y pantallas de punto de equilibrio y precios. | Módulo financiero con sus pantallas. | **[COMPLETAR]** |
| 7. Asistente virtual (AVI) | Conexión con ChatGPT y Gemini, funciones que el asistente puede ejecutar, resumen diario y dictado por voz. | El tendero puede pedir cosas escribiendo o hablando. | **[COMPLETAR]** |
| 8. Revisión de requisitos y ajustes | Revisamos los 34 requisitos funcionales contra el sistema, corregimos lo que faltaba, agregamos el tutorial e implementamos las fórmulas financieras reales. | Sistema alineado con los requisitos (ver sección 3.5.5). | Octubre de 2026 |

### 3.1.4 Herramientas de seguimiento

- **Git y GitHub:** guardamos todas las versiones del código. Cuando redactamos este reporte el repositorio tenía 22 registros (commits), del 8 de junio al 1 de octubre de 2026.
- **Tablero de tareas:** **[COMPLETAR: JIRA, Trello, GitHub Projects u otro. Si no usaron ninguno, borrar esta línea y decir cómo llevaban sus pendientes.]**
- **Reuniones de revisión:** **[COMPLETAR: cada cuánto se reunían y con quién.]**

### 3.1.5 Cómo revisamos el avance

Al final de cada etapa probábamos el sistema en el navegador. Después, cuando la mayor parte estaba lista, hicimos una revisión punto por punto de los 34 requisitos funcionales contra el código. Encontramos que 9 se cumplían completos, 12 a medias y 13 no se cumplían. Los fuimos corrigiendo en tres grupos de trabajo, según qué tan grandes eran. Más adelante, en la sección 3.5.5, está la tabla con el estado final de cada uno.

---

## 3.2 Requerimientos del Sistema

### 3.2.1 Requerimientos Funcionales

Un requerimiento funcional es algo que el sistema **debe poder hacer** [9], [10]. Los agrupamos por módulo. Las letras del código indican el módulo: V (ventas), I (inventario), F (agente financiero), AVI (asistente virtual) y S (sistema en general).

> **Nota:** en el documento original, el último requisito de "Sistema en general" (sincronización de interfaz) aparece con el código RF-AVI07, igual que el de contexto de la conversación. Aquí lo nombramos **RF-S06** para que no se repitan los códigos.

#### Módulo de ventas

| Código | Nombre | Qué debe hacer el sistema |
|---|---|---|
| RF-V01 | Venta por lenguaje natural | Entender una petición escrita como la diría el tendero ("agrega 2 pepsis"), aunque tenga abreviaciones o nombres incompletos, e identificar producto y cantidad. Si el nombre es ambiguo, mostrar productos parecidos para elegir. |
| RF-V02 | Gestión de carrito | Cambiar cantidades y quitar productos del carrito de inmediato. |
| RF-V03 | Finalizar la compra | Cerrar la venta en un solo paso, generar el registro y el ticket digital, y actualizar el inventario sin retrasar el trabajo en el mostrador. |
| RF-V04 | Calcular el total | Calcular y mostrar el total siempre visible mientras se arma el carrito. |
| RF-V05 | Modificar la cantidad | Ajustar la cantidad con botones de más y menos, o con el teclado, sin pedir confirmaciones. |
| RF-V06 | Vaciar el carrito | Vaciar el carrito con una confirmación simple. |
| RF-V07 | Producto no encontrado | Poder vender un producto que no está en el catálogo (nombre, cantidad y precio) y dejarlo marcado como pendiente de validar para darlo de alta después. |
| RF-V08 | Visualizar el ticket | Mostrar el ticket con nombre y ubicación del negocio, fecha, hora y el detalle de la venta. |

#### Auxiliar de inventario

| Código | Nombre | Qué debe hacer el sistema |
|---|---|---|
| RF-I01 | Alta progresiva de productos | Dar de alta unos pocos productos al registrarse y seguir agregando después. Datos mínimos: nombre, descripción, costo, precio de venta, cantidad actual, cantidad mínima y categoría. |
| RF-I02 | Modificar productos | Cambiar costo, precio y cantidades de un producto, y pedir el motivo del cambio. |
| RF-I03 | Alertas de reabastecimiento | Avisar cuando un producto llega a su cantidad mínima, con una lista ordenada de lo que hay que surtir primero. |
| RF-I04 | Eliminar productos | Dar de baja un producto avisando si ya tiene ventas registradas. |
| RF-I05 | Productos precargados | Al crear la cuenta, ofrecer una lista de productos comunes de abarrotes para marcar los que el tendero maneja. |
| RF-I06 | Ver el catálogo | Mostrar una tabla con nombre, categoría, existencias, mínimo y costo/precio, con búsqueda por nombre y filtro por categoría. |
| RF-I07 | Proveedores | Registrar proveedores con sus datos de contacto y las categorías que surten. |

#### Agente financiero

| Código | Nombre | Qué debe hacer el sistema |
|---|---|---|
| RF-F01 | Registrar gastos | Registrar y clasificar gastos (renta, luz, internet…), de forma opcional, y poder crear categorías nuevas. |
| RF-F02 | Punto de equilibrio | Mostrar en pesos la venta mínima para no perder dinero, con una explicación breve y sencilla. |
| RF-F03 | Precios sugeridos | Sugerir precios de venta a partir del costo, dejando que el usuario acepte, ajuste o rechace cada propuesta. |
| RF-F04 | Pronóstico de ventas | Generar proyecciones semanales con inteligencia artificial, con comparación contra el periodo anterior, nivel de confianza y una explicación corta. |
| RF-F05 | Reportes financieros | Mostrar ingresos, egresos y utilidades por periodos, con alertas (productos que no se venden, gastos fuera de lo normal). |

#### Asistente virtual inteligente (AVI)

| Código | Nombre | Qué debe hacer el sistema |
|---|---|---|
| RF-AVI01 | Identificar la intención | Entender qué quiere el usuario según el módulo en el que está, sin impedirle preguntar cosas de otros módulos. |
| RF-AVI02 | Extraer la información de la petición | Sacar varios productos y cantidades de una sola frase ("5 leches y 2 panes") y decidir qué función ejecutar. |
| RF-AVI03 | Responder de forma guiada | Responder amable y, si la petición no es válida, dar ejemplos de qué sí se puede pedir. |
| RF-AVI04 | Explicar los resultados financieros | Convertir cifras (punto de equilibrio, utilidad) en un resumen en palabras sencillas. |
| RF-AVI05 | Datos incompletos | Detectar lo que falta en una petición y pedirlo antes de hacer cambios. |
| RF-AVI06 | Confirmar acciones críticas | Pedir confirmación solo antes de acciones que no se pueden deshacer. |
| RF-AVI07 | Contexto de la conversación | Recordar lo que se habló para entender frases como "¿cuánto cuesta?", y conservar preferencias básicas entre sesiones. |
| RF-AVI08 | Ingresar la petición | Poder escribir la petición en el chat del asistente. |

#### Sistema en general

| Código | Nombre | Qué debe hacer el sistema |
|---|---|---|
| RF-S01 | Registro de cuenta | Registrar nombre del propietario, empresa, alcaldía de la CDMX y correo. |
| RF-S02 | Inicio de sesión | Entrar con correo y contraseña. |
| RF-S03 | Recuperar contraseña | Restablecer la contraseña por correo electrónico. |
| RF-S04 | Eliminar la cuenta | Dar de baja la cuenta y todos sus datos de forma permanente. |
| RF-S05 | Tutorial contextual | Ayudar con microtutoriales por módulo, ejemplos en pantalla y un video de introducción la primera vez. |
| RF-S06 | Sincronización de interfaz | Actualizar solo la pantalla del módulo cuando el asistente termina una acción con éxito. |

### 3.2.2 Requerimientos No Funcionales

Un requerimiento no funcional dice **cómo** debe comportarse el sistema (qué tan rápido, qué tan seguro, qué tan fácil de usar), no qué hace. Los agrupamos tomando como guía las características de calidad de la norma ISO/IEC 25010 [16], como rendimiento, usabilidad, seguridad y mantenimiento.

| Código | Tipo | Requerimiento | Cómo se revisa |
|---|---|---|---|
| RNF-01 | Rendimiento | Las acciones normales (abrir una pantalla, agregar al carrito, cobrar) deben responder en menos de 3 segundos en una computadora de gama básica. Las respuestas del asistente dependen del internet y del proveedor del modelo, por eso pueden tardar un poco más. **[AJUSTAR]** | Medir tiempos en las pruebas (sección 3.6). |
| RNF-02 | Facilidad de uso | Lenguaje sencillo, botones grandes, colores con significado (verde para cobrar, rojo para cancelar) y un tutorial para el primer uso. El usuario no necesita conocimientos técnicos. | Encuesta de usabilidad a tenderos (sección 3.6.4). |
| RNF-03 | Dispositivos | La interfaz se adapta a computadora, tablet y celular. | Probar con distintos tamaños de pantalla. |
| RNF-04 | Navegadores | Funciona en navegadores modernos. El dictado por voz solo funciona en los que lo permiten (por ejemplo Chrome y Edge). | Probar en Chrome, Edge y Firefox. |
| RNF-05 | Almacenamiento | Los datos se guardan en una base de datos SQL local (SQLite), en la misma computadora donde corre el sistema. | Revisar el archivo de base de datos. |
| RNF-06 | Seguridad | Las contraseñas se guardan cifradas, los formularios tienen protección CSRF, solo se entra con sesión iniciada, cada negocio ve únicamente sus propios datos y las llaves de las API se guardan en un archivo `.env` que no se sube al repositorio. | Probar accesos sin sesión y con otra cuenta. |
| RNF-07 | Privacidad | Cuando se usa el asistente, el mensaje del usuario y algunos datos del negocio (por ejemplo totales de ventas o gastos) se envían al proveedor del modelo de lenguaje para generar la respuesta. Nunca se envían contraseñas. | Revisar qué datos manda cada función. |
| RNF-08 | Uso sin internet | Las ventas, el inventario y las pantallas financieras funcionan sin depender de la nube. Lo único que necesita internet es el asistente. **Limitación:** hoy los iconos y la letra se descargan de internet; para trabajar 100 % sin internet habría que guardarlos dentro del proyecto. | Probar el sistema sin conexión. |
| RNF-09 | Mantenimiento | El código está separado por módulos (apps de Django), las fórmulas financieras están en un solo archivo y hay pruebas automáticas para las más importantes. | Revisar la estructura del proyecto. |
| RNF-10 | Instalación | Se instala en Windows con Python 3.12 y el archivo `requirements.txt`. | Seguir el manual técnico en una computadora nueva. |
| RNF-11 | Integridad de datos | Los montos se manejan con 2 decimales, el inventario se descuenta en el mismo paso que se cobra la venta y una venta cancelada no mueve el inventario. | Pruebas de integración (sección 3.6.2). |
| RNF-12 | Tamaño del negocio | Pensado para una tienda de abarrotes pequeña (cientos de productos). **Limitación:** con miles de productos algunas pantallas (como el catálogo) necesitan paginación, que aún no está hecha. | Probar con datos de muestra grandes. |

---

## 3.3 Análisis del Sistema

### 3.3.1 Identificación de Actores

Un actor es quien interactúa con el sistema.

| Actor | Tipo | Qué hace |
|---|---|---|
| **Tendero / dueño del negocio** | Principal | Usa todos los módulos: vende, controla el inventario, registra gastos, consulta reportes y platica con el asistente. También es quien administra su cuenta. |
| **Cajero** | Principal (opcional) | Persona que ayuda a cobrar en el mostrador. En el sistema actual comparte la cuenta del negocio; todavía no tiene un rol separado con permisos propios. |
| **Asistente virtual (AVI)** | Del sistema | Recibe peticiones del tendero y ejecuta funciones del sistema por él (agregar al carrito, consultar ventas, registrar un gasto, etc.). |
| **Proveedor del modelo de lenguaje** (ChatGPT o Gemini) | Externo | Interpreta el texto del tendero y redacta las respuestas del asistente. |
| **Servicio de correo** | Externo | Envía el enlace para recuperar la contraseña. Por ahora, en desarrollo, el enlace se muestra en la terminal en lugar de enviarse. |
| **Motor de pronóstico** | Del sistema (pendiente) | Calculará el pronóstico de ventas. Está planeado para la fase 2. |

### 3.3.2 Casos de Uso

Un caso de uso describe, paso a paso, algo que el usuario hace con el sistema.

| Código | Caso de uso | Actor | Requisitos que cubre |
|---|---|---|---|
| CU-01 | Registrar cuenta y negocio | Tendero | RF-S01, RF-I05 |
| CU-02 | Iniciar sesión | Tendero | RF-S02 |
| CU-03 | Armar el carrito de una venta | Tendero | RF-V01, RF-V02, RF-V04, RF-V05 |
| CU-04 | Vender un producto no encontrado | Tendero | RF-V07 |
| CU-05 | Cobrar y ver el ticket | Tendero | RF-V03, RF-V08 |
| CU-06 | Cancelar una venta | Tendero | RF-V06 |
| CU-07 | Dar de alta un producto | Tendero | RF-I01 |
| CU-08 | Modificar un producto | Tendero | RF-I02, RF-V07 |
| CU-09 | Dar de baja un producto | Tendero | RF-I04 |
| CU-10 | Ver alertas de reabastecimiento y catálogo | Tendero | RF-I03, RF-I06 |
| CU-11 | Gestionar proveedores | Tendero | RF-I07 |
| CU-12 | Registrar un gasto | Tendero | RF-F01 |
| CU-13 | Ver el punto de equilibrio | Tendero | RF-F02 |
| CU-14 | Ver y aceptar precios sugeridos | Tendero | RF-F03 |
| CU-15 | Ver reportes financieros | Tendero | RF-F05 |
| CU-16 | Hablar con el asistente (texto o voz) | Tendero, AVI | RF-AVI01 a RF-AVI08, RF-S06 |
| CU-17 | Ver el resumen del día | Tendero, AVI | RF-AVI04 |
| CU-18 | Recuperar la contraseña | Tendero | RF-S03 |
| CU-19 | Eliminar la cuenta | Tendero | RF-S04 |
| CU-20 | Ver la ayuda de la pantalla | Tendero | RF-S05 |
| CU-21 | Ver el pronóstico de ventas | Tendero | RF-F04 (pendiente, fase 2) |

A continuación se describen los casos de uso.

---

**CU-01. Registrar cuenta y negocio**
- **Actor:** Tendero.
- **Antes de empezar:** no tiene una sesión iniciada.
- **Flujo principal:**
  1. Entra a la pantalla de registro.
  2. Escribe su nombre completo, teléfono, correo y contraseña.
  3. El sistema revisa que el teléfono y el correo no estén repetidos y que la contraseña sea válida.
  4. El sistema crea la cuenta e inicia la sesión.
  5. Le pide los datos del negocio: nombre de la tienda, alcaldía, años de operación, si está en RESICO y su RFC.
  6. Le muestra una lista de productos comunes de abarrotes y marca los que él maneja.
  7. El sistema crea esos productos en su inventario y lo lleva al punto de venta.
- **Flujo alterno:** si el teléfono o el correo ya existen, el sistema muestra un mensaje y no crea la cuenta.
- **Resultado:** cuenta, negocio y productos iniciales creados.

**CU-02. Iniciar sesión**
- **Actor:** Tendero.
- **Flujo principal:** 1) Escribe su correo (o teléfono) y su contraseña. 2) El sistema los revisa. 3) Lo lleva al punto de venta. 4) El asistente le muestra el resumen del día.
- **Flujo alterno:** si los datos son incorrectos, aparece el mensaje "Usuario o contraseña incorrectos".
- **Resultado:** sesión iniciada.

**CU-03. Armar el carrito de una venta**
- **Actor:** Tendero.
- **Antes de empezar:** tiene sesión iniciada y productos en su inventario.
- **Flujo principal:**
  1. Escribe el nombre del producto en la barra de búsqueda.
  2. El sistema muestra coincidencias mientras escribe.
  3. Elige un producto y el sistema lo agrega al carrito.
  4. Cambia la cantidad con los botones de más y menos (o con las teclas + y -).
  5. Si quiere quitar un producto, usa el botón del bote de basura.
  6. El total se actualiza y siempre está a la vista.
- **Flujo alterno:** el tendero puede pedirle al asistente "agrega 2 pepsis". Si hay varios productos parecidos, el asistente le pregunta cuál quiere.
- **Resultado:** carrito con los productos y el total correcto.

**CU-04. Vender un producto no encontrado**
- **Actor:** Tendero.
- **Flujo principal:** 1) Oprime "No encontrado". 2) Escribe el nombre y el precio. 3) El sistema lo agrega al carrito y lo guarda como producto pendiente de validar.
- **Resultado:** la venta no se detiene. Después, en inventario, el producto aparece con la etiqueta "Pendiente de validar" para completar sus datos (CU-08).

**CU-05. Cobrar y ver el ticket**
- **Actor:** Tendero.
- **Flujo principal:** 1) Oprime "Cobrar". 2) El sistema descuenta del inventario lo vendido y marca la venta como cobrada. 3) Muestra una notificación con el folio y el total. 4) El tendero puede abrir el ticket con nombre y ubicación del negocio, fecha, hora y detalle.
- **Flujo alterno:** si el carrito está vacío, el sistema avisa que no hay nada que cobrar.
- **Resultado:** venta registrada e inventario actualizado.

**CU-06. Cancelar una venta**
- **Actor:** Tendero.
- **Flujo principal:** 1) Oprime "Cancelar venta". 2) El sistema pide una confirmación simple. 3) Si acepta, la venta queda cancelada y se abre un carrito nuevo.
- **Resultado:** carrito vacío. El inventario no cambia.

**CU-07. Dar de alta un producto**
- **Actor:** Tendero.
- **Flujo principal:** 1) Oprime "Alta de productos". 2) Llena nombre, descripción, costo, precio, cantidad actual, cantidad mínima, categoría y proveedor. 3) Mientras escribe costo y precio ve el margen estimado. 4) Guarda y el producto aparece en el catálogo.
- **Flujo alterno:** si la categoría no existe, la crea en ese momento con el botón "Nueva". Si faltan datos obligatorios, el sistema avisa cuál falta.

**CU-08. Modificar un producto**
- **Actor:** Tendero.
- **Flujo principal:** 1) Oprime "Editar" en la fila del producto. 2) Cambia los datos que necesite. 3) Escribe el motivo del cambio (es obligatorio). 4) Guarda. 5) El sistema guarda el cambio y el motivo en un historial.
- **Variante:** si el producto estaba "pendiente de validar", al guardarlo queda activo en el catálogo.

**CU-09. Dar de baja un producto**
- **Actor:** Tendero.
- **Flujo principal:** 1) Oprime "Baja". 2) Si el producto ya tiene ventas, el sistema lo avisa en la confirmación. 3) Al aceptar, el producto deja de aparecer, pero sus ventas anteriores se conservan.

**CU-10. Ver alertas de reabastecimiento y catálogo**
- **Actor:** Tendero.
- **Flujo principal:** 1) En inventario ve una barra roja con el número de alertas. 2) La abre y ve los productos en nivel crítico primero y los que están por acabarse después. 3) En el catálogo puede buscar por nombre y filtrar por categoría; los productos más críticos salen arriba.

**CU-11. Gestionar proveedores**
- **Actor:** Tendero.
- **Flujo principal:** 1) Oprime "Proveedores". 2) Ve la lista, agrega uno nuevo con teléfono, correo y las categorías que surte, o abre uno para editarlo.

**CU-12. Registrar un gasto**
- **Actor:** Tendero.
- **Flujo principal:** 1) Entra a "Registrar gastos". 2) Elige si es fijo o variable. 3) Elige una categoría (o crea una nueva), escribe el concepto y el monto. 4) Guarda. 5) El resumen del mes se actualiza.

**CU-13. Ver el punto de equilibrio**
- **Actor:** Tendero.
- **Flujo principal:** 1) Entra a "Punto de equilibrio". 2) El sistema calcula la venta mínima del mes con sus gastos fijos y lo que ha vendido en los últimos 3 meses. 3) Muestra la cifra, cuánto es por día, una explicación sencilla, el avance del mes y cuánto vender de cada categoría.
- **Flujo alterno:** si no hay gastos fijos o no hay ventas, el sistema explica qué falta para poder calcularlo.

**CU-14. Ver y aceptar precios sugeridos**
- **Actor:** Tendero.
- **Flujo principal:** 1) Entra a "Sugerir precios". 2) Escribe el margen de ganancia que quiere. 3) El sistema muestra el precio sugerido de cada producto. 4) Por producto, el tendero puede ajustar el precio y oprimir "Aceptar", u oprimir "Rechazar" para dejar el precio actual.
- **Resultado:** si acepta, el precio del producto cambia y queda registrado en el historial.

**CU-15. Ver reportes financieros**
- **Actor:** Tendero.
- **Flujo principal:** 1) Entra a "Reportes". 2) Elige 3 o 6 meses. 3) Ve ingresos, flujo de efectivo, margen operativo y utilidad neta, dos gráficas y las alertas.

**CU-16. Hablar con el asistente (texto o voz)**
- **Actor:** Tendero y asistente.
- **Flujo principal:**
  1. Escribe su petición en el chat, o la dice con el micrófono.
  2. El sistema manda el mensaje y los últimos mensajes de la conversación al modelo de lenguaje.
  3. El modelo decide si debe usar una función del sistema (por ejemplo, agregar al carrito).
  4. El sistema ejecuta la función y le devuelve el resultado al modelo.
  5. El modelo redacta una respuesta corta y sencilla.
  6. El chat la muestra y, si algo cambió, la pantalla del módulo se actualiza sola.
- **Flujos alternos:** si falta un dato, el asistente lo pregunta; si la petición no tiene que ver con la tienda, responde con ejemplos de lo que sí puede hacer; si no hay internet o falta la llave de la API, muestra un mensaje de error claro.

**CU-17. Ver el resumen del día**
- **Actor:** Tendero y asistente.
- **Flujo principal:** 1) Al iniciar sesión, el asistente muestra cómo le fue ayer (ventas, ganancia y gastos) con una recomendación corta. 2) Trae dos botones: "Preguntar más" e "Ir a pronóstico de ventas". 3) El resumen se genera una sola vez por día; si el tendero entra más veces ese día, se muestra el mismo.

**CU-18. Recuperar la contraseña**
- **Actor:** Tendero.
- **Flujo principal:** 1) Oprime "¿Olvidaste tu contraseña?". 2) Escribe su correo. 3) El sistema genera un enlace de recuperación (por ahora se ve en la terminal del servidor). 4) El tendero abre el enlace y escribe su contraseña nueva dos veces.
- **Flujo alterno:** si el enlace ya se usó o caducó, el sistema pide generar uno nuevo.

**CU-19. Eliminar la cuenta**
- **Actor:** Tendero.
- **Flujo principal:** 1) Desde el menú de usuario oprime "Eliminar mi cuenta". 2) Escribe su contraseña otra vez. 3) Confirma. 4) El sistema borra la cuenta, el negocio, el inventario, las ventas y los gastos.
- **Flujo alterno:** si la contraseña es incorrecta, no se borra nada.

**CU-20. Ver la ayuda de la pantalla**
- **Actor:** Tendero.
- **Flujo principal:** la primera vez que entra a ventas, inventario o finanzas aparecen 2 o 3 consejos que señalan los botones importantes. Después puede volver a verlos con el botón "?" de la barra superior.

**CU-21. Ver el pronóstico de ventas** *(pendiente, fase 2)*
- Hoy la pantalla existe como maqueta. El cálculo real del pronóstico queda para la siguiente fase.

---

### 3.3.3 Diagramas de Casos de Uso

> **Estos diagramas los hacen ustedes.** Les dejo qué debería llevar cada uno para que coincida con lo escrito arriba.

| Figura | Qué debe mostrar |
|---|---|
| Figura 3.1 | **Diagrama general:** actores Tendero, Asistente (AVI), Proveedor del modelo de lenguaje y Servicio de correo, con los 21 casos de uso agrupados por módulo. |
| Figura 3.2 | **Módulo de ventas:** CU-03 a CU-06. |
| Figura 3.3 | **Auxiliar de inventario:** CU-07 a CU-11. |
| Figura 3.4 | **Agente financiero:** CU-12 a CU-15 y CU-21. |
| Figura 3.5 | **Asistente virtual:** CU-16 y CU-17. Marcar con "incluye" que CU-16 usa las funciones de ventas, inventario y finanzas. |
| Figura 3.6 | **Seguridad y cuenta:** CU-01, CU-02, CU-18, CU-19 y CU-20. |
