@@c|10||**[Insertar logotipos oficiales del IPN (arriba a la izquierda) y de ESCOM (abajo a la izquierda), como en el formato de carátula]**
@@sp|1
@@c|20|b|INSTITUTO POLITÉCNICO NACIONAL
@@c|16|b|ESCUELA SUPERIOR DE CÓMPUTO
@@sp|1
@@c|16|b|ESCOM
@@sp|2
@@c|14|i|Trabajo Terminal
@@sp|1
@@c|16|b|"Asistente Virtual Inteligente para la gestión financiera y pronóstico de ventas"
@@sp|1
@@c|14|i|20__-_____   **[CONFIRMAR: número de TT]**
@@sp|2
@@c|14|i|Presentan
@@c|14|b|Luis Bernardo Delgado Acosta
@@c|14|b|Jorge Arif Diaz Jimenez
@@sp|2
@@c|14|i|Directores
@@c|12|bi|**[CONFIRMAR: grado y nombre completo del director]**
@@c|12|bi|**[CONFIRMAR: grado y nombre completo del segundo director; si es externo, va a la derecha]**
@@sp|2
@@c|12|i|**[CONFIRMAR: mes y año de presentación de TT-II]**
@@pb
@@c|12|b|INSTITUTO POLITÉCNICO NACIONAL
@@c|12|b|ESCUELA SUPERIOR DE CÓMPUTO
@@c|12|b|SUBDIRECCIÓN ACADÉMICA
@@sp|1
@@l|12||No de TT 20__-_____   **[CONFIRMAR]**
@@l|12||Fecha de presentación de TT-II: **[CONFIRMAR]**
@@sp|1
@@c|12||Documento Técnico
@@c|14|b|"Asistente Virtual Inteligente para la gestión financiera y pronóstico de ventas"
@@sp|1
@@c|12|i|Presentan
@@c|12|b|Luis Bernardo Delgado Acosta¹
@@c|12|b|Jorge Arif Diaz Jimenez¹
@@sp|1
@@c|12|i|Directores
@@c|12|bi|**[CONFIRMAR: grado y nombre completo de los directores]**
@@sp|1
@@c|12|b|RESUMEN
En este reporte se presenta el avance del desarrollo de un asistente virtual inteligente para la gestión financiera y el pronóstico de ventas de tiendas de abarrotes. El sistema es una aplicación web hecha con Django que reúne cuatro módulos: ventas, con carrito y ticket digital; inventario, con alertas de stock bajo; agente financiero, con registro de gastos, punto de equilibrio, precios sugeridos y reportes; y un asistente conversacional que usa modelos de lenguaje (ChatGPT o Gemini) mediante *function calling* y que acepta peticiones escritas o dictadas por voz. El documento describe la metodología, los 34 requisitos funcionales, el análisis, el diseño y la construcción del sistema, las fórmulas financieras implementadas (incluido el ISR del régimen RESICO), el plan de pruebas y el plan de despliegue. A la fecha, 28 de los 34 requisitos están implementados. El modelo de pronóstico de ventas semanales se desarrolla con más de 1,000 productos y 16,000 ventas históricas y está pendiente de integrarse al sistema; también están pendientes la validación con tenderos y el despliegue en un entorno controlado.
**Palabras clave:** asistente virtual, pronóstico de ventas, punto de equilibrio, tienda de abarrotes, Django, function calling, RESICO.
@@sp|1
@@l|10||¹ Correo electrónico de los participantes: **[CONFIRMAR]**
@@pb
@@c|14|b|CARTA RESPONSIVA
@@c|10||Que otorga visto bueno y avala la conclusión de documentación del Trabajo Terminal bajo los lineamientos establecidos por la Comisión Académica de Trabajos Terminales (CATT)
@@sp|1
@@r|12||CDMX, a ___ de ____________ de 20___   **[CONFIRMAR: fecha de los cinco días hábiles posteriores a la presentación]**
@@sp|1
**M. EN C. ANDRÉS ORTIGOZA CAMPOS**
**PRESIDENTE DE LA COMISIÓN ACADÉMICA DE TRABAJOS TERMINALES**
**P R E S E N T E**
@@r|12|b|EN ATENCIÓN A:
@@r|12||M. EN E. ELIA TZINDEJHÉ RAMÍREZ MARTÍNEZ
@@r|12||SECRETARIA EJECUTIVA
@@sp|1
Por medio de la presente, se informa que el Trabajo Terminal Núm. 20__-_____ **[CONFIRMAR]**
Que lleva por Título: "Asistente Virtual Inteligente para la gestión financiera y pronóstico de ventas"
Fue concluido satisfactoriamente por:
@@c|12||Luis Bernardo Delgado Acosta
@@c|12||Jorge Arif Diaz Jimenez
Se avala que la documentación entregada mediante discos en formato DVD fue **revisada de manera precisa y exhaustiva** con el propósito de asegurar que los avances desarrollados bajo la supervisión de quien o quienes suscriben, hayan cumplido con lo planteado en el protocolo original, así como en lo establecido por el Documento Rector de Operación y Evaluación para los Trabajos Terminales de la ESCOM.
**ATENTAMENTE**
**"LA TÉCNICA AL SERVICIO DE LA PATRIA"**
@@sp|2
@@c|12||______________________________          ______________________________
@@c|12||(Nombre completo y firma)          (Nombre completo y firma)
@@c|12||Director/a          Director/a
@@c|10|i|Esta carta se imprime y se firma al entregar la versión final. Se integra escaneada, con las firmas de los directores, a este reporte, y el original se entrega junto con los discos (DVD).
@@pb
@@c|14|b|Advertencia
@@sp|1
*"Este documento contiene información desarrollada por la Escuela Superior de Cómputo del Instituto Politécnico Nacional, a partir de datos y documentos con derecho de propiedad y por lo tanto, su uso quedará restringido a las aplicaciones que explícitamente se convengan."*
La aplicación no convenida exime a la escuela su responsabilidad técnica y da lugar a las consecuencias legales que para tal efecto se determinen.
Información adicional sobre este reporte técnico podrá obtenerse en:
La Subdirección Académica de la Escuela Superior de Cómputo del Instituto Politécnico Nacional, situada en Av. Juan de Dios Bátiz s/n Teléfono: 57296000, extensión 52000.
@@pb
@@c|14|b|ÍNDICE
@@toc

# INTRODUCCIÓN

Las tiendas de abarrotes son uno de los negocios más comunes y más cercanos a la gente en México. Muchas de ellas son microempresas que llevan sus ventas y sus cuentas de forma sencilla: en un cuaderno, con una calculadora o de memoria. Esto hace difícil saber con certeza cuánto se vendió en el día, qué productos se están acabando, cuánto hay que vender al mes para no perder dinero o a qué precio conviene vender cada producto. Además, muchos de estos negocios pueden pertenecer al Régimen Simplificado de Confianza (RESICO), que tiene sus propias reglas para calcular el impuesto.

Para ayudar a resolver este problema, en este Trabajo Terminal se desarrolla un **asistente virtual inteligente para la gestión financiera y el pronóstico de ventas** de tiendas de abarrotes. Se trata de una aplicación web que se usa desde el navegador y que tiene cuatro partes principales:

- un **módulo de ventas**, con carrito de compras, cobro y ticket digital;
- un **auxiliar de inventario**, con el catálogo de productos, los proveedores y alertas cuando un producto se está acabando;
- un **agente financiero**, que registra los gastos y calcula el punto de equilibrio, los precios sugeridos y los reportes de ingresos, gastos y utilidad; y
- un **asistente virtual**, con el que el tendero puede platicar por escrito o por voz para vender, consultar su inventario o entender sus finanzas en palabras sencillas.

A estas partes se suma un **modelo de pronóstico de ventas semanales**, que usa el historial de ventas del negocio para estimar cuánto se venderá en las siguientes semanas.

El Trabajo Terminal 2 (TT2) tiene como objetivo central la construcción, integración y validación del prototipo funcional del sistema. Para lograrlo, el trabajo se organizó en cuatro ejes: el desarrollo del prototipo, el entrenamiento del modelo de pronóstico, las pruebas de integración y validación, y el despliegue con la documentación técnica.

## Alcance de esta versión

Este documento es la versión de avance del reporte técnico del Trabajo Terminal 2. El proyecto se encuentra en la etapa de construcción. La aplicación web ya funciona de principio a fin en sus módulos principales (ventas, inventario, agente financiero, asistente virtual y seguridad). El modelo de pronóstico de ventas se está desarrollando con un conjunto de datos históricos de más de 1,000 productos y más de 16,000 ventas. Todavía están pendientes la validación con tenderos y el despliegue en el entorno controlado.

Por esa razón, en cada sección explicamos qué ya está terminado y qué falta por hacer. Al final del proyecto, esas partes pendientes se sustituirán por los resultados reales de las pruebas, del modelo y de la validación.

En el protocolo nos comprometimos a trabajar en cuatro ejes: desarrollo del prototipo, modelo de pronóstico, validación en entorno controlado y despliegue con documentación. La siguiente tabla resume dónde estamos en cada uno.

| Eje | Terminado | En construcción | Pendiente |
|---|---|---|---|
| **Desarrollo del prototipo** | Gestión de productos con alertas de stock bajo; módulo de ventas con descuento de inventario y ticket digital; asistente conectado a un modelo de lenguaje con *function calling*. | Servidor de base de datos; pruebas de consistencia entre inventario y ventas con la carga grande de datos; reportes financieros (faltan el filtro por rango de fechas y los productos más vendidos); tableros de visualización. | — |
| **Modelo de pronóstico** | Carga de los datos históricos (más de 1,000 productos y 16,000 ventas). | Limpieza y estructuración de los datos; comparación de algoritmos, entrenamiento semanal y ajuste del modelo. | Integración del pronóstico a la pantalla del sistema. |
| **Validación** | — | Pruebas con datos incompletos o inconsistentes. | Pruebas de usabilidad con tenderos; evaluación del rendimiento. |
| **Despliegue y documentación** | — | Ejecución en una computadora del equipo; documentación técnica (este reporte). | Acceso de los participantes por navegador; migración a Azure; pruebas de conectividad. |

## Organización del documento

Este reporte sigue el formato de reporte técnico de la Escuela Superior de Cómputo. Después de esta introducción, el **Capítulo 1** describe el plan de desarrollo del software: la metodología, los requerimientos, el análisis, el diseño y la arquitectura, la construcción, el plan de pruebas, el despliegue, la capacitación de los usuarios y el plan de mantenimiento. El **Capítulo 2** presenta los resultados esperados: los beneficios y los indicadores con los que se medirá el éxito del sistema.

Después de los capítulos se incluyen las secciones de **Conclusiones**, **Trabajo a futuro**, **Referencias** y **Glosario**. Al final se encuentran los **Apéndices**: el manual de usuario, el manual técnico, las plantillas de encuestas y entrevistas, los fragmentos representativos del código fuente y el índice de figuras.

# CAPÍTULO 1. Plan de Desarrollo del Software

## 1.1 Metodología de Desarrollo

Para desarrollar el sistema trabajamos con un enfoque ágil, tomando como inspiración las ideas de Scrum [8]. Esto quiere decir que no intentamos construir todo de una sola vez para probarlo hasta el final. En cambio, fuimos armando el sistema en etapas cortas: en cada una se construía una parte, se probaba en el navegador, se corregía lo que fallaba y hasta entonces se pasaba a la siguiente.

Elegimos esta forma de trabajo por tres razones. La primera es que somos un equipo de dos personas, y no necesitábamos una metodología con muchos roles ni muchos documentos. La segunda es que los requerimientos fueron cambiando mientras avanzábamos. Por ejemplo, las fórmulas financieras se definieron cuando el sistema ya tenía pantallas funcionando, y el diseño de la interfaz se ajustó varias veces después de revisar comentarios. La tercera es que queríamos ver el sistema funcionando desde pronto, para encontrar los errores a tiempo.

El trabajo se dividió entre los dos integrantes. Una parte del equipo se encargó de la aplicación web, es decir, los módulos de ventas, inventario, finanzas, asistente y seguridad. La otra parte se encargó del modelo de pronóstico de ventas, que es la parte de aprendizaje automático del proyecto. Para guardar cada versión del código usamos Git y GitHub, y el historial de versiones nos sirvió como bitácora del avance.

La siguiente tabla muestra las etapas por las que ha pasado el proyecto, tomadas de ese historial.

| Fecha | Etapa | Qué se hizo |
|---|---|---|
| 8 de junio de 2026 | Inicio del proyecto | Se creó el repositorio, el README con la descripción del proyecto y la licencia. |
| 16 de agosto de 2026 | Primeros pasos | Se armó la estructura base del proyecto en Django y un menú ilustrativo. |
| 26 de septiembre de 2026 | Rediseño | Se reorganizó todo el código en módulos (ventas, inventario, finanzas, asistente y seguridad) y se rehízo la interfaz. |
| 27 y 28 de septiembre de 2026 | Asistente virtual | Se conectó el sistema con las API de inteligencia artificial y se agregaron el resumen del día, las consultas del tablero y el dictado por voz. |
| 1 de octubre de 2026 | Revisión de requisitos | Se revisaron los 34 requisitos funcionales contra el sistema y se corrigieron los que faltaban. |
| Octubre de 2026 (en curso) | Finanzas, pruebas y pronóstico | Se implementaron las fórmulas financieras reales y las pruebas automáticas, y se está desarrollando el modelo de pronóstico con los datos históricos cargados. |

Un momento importante fue la revisión de requisitos. Cuando ya teníamos casi todo construido, comparamos uno por uno los 34 requisitos funcionales contra el sistema real. Encontramos que 9 se cumplían completos, 12 se cumplían a medias y 13 no se cumplían. Los fuimos corrigiendo en tres grupos de trabajo, de acuerdo con su tamaño y con las decisiones que había que tomar. El resultado de esa corrección se muestra en la sección 1.2.1.

## 1.2 Requerimientos del Sistema

### 1.2.1 Requerimientos Funcionales

Un requerimiento funcional describe algo que el sistema debe poder hacer [9], [10]. Definimos 34, agrupados según el módulo al que pertenecen. La letra del código indica el módulo: V para ventas, I para inventario, F para el agente financiero, AVI para el asistente virtual y S para el sistema en general. En el documento original, el último requisito del sistema en general (sincronización de la interfaz) aparecía con el código RF-AVI07, igual que el del contexto de la conversación; aquí lo llamamos RF-S06 para que no se repitan los códigos.

En cada tabla se indica el estado actual de cada requisito.

**Módulo de ventas**

| Código | Requisito | Qué debe hacer el sistema | Estado |
|---|---|---|---|
| RF-V01 | Venta por lenguaje natural | Entender una petición escrita como la diría el tendero ("agrega 2 pepsis"), aunque tenga abreviaciones o nombres incompletos, e identificar producto y cantidad. Si el nombre es ambiguo, mostrar productos parecidos para elegir. | Implementado; por validar con el asistente real |
| RF-V02 | Gestión de carrito | Cambiar cantidades y quitar productos del carrito de inmediato. | Implementado |
| RF-V03 | Finalizar la compra | Cerrar la venta en un solo paso, generar el registro y el ticket digital, y actualizar el inventario sin retrasar el trabajo en el mostrador. | Implementado |
| RF-V04 | Calcular el total | Calcular y mostrar el total siempre visible mientras se arma el carrito. | Implementado |
| RF-V05 | Modificar la cantidad | Ajustar la cantidad con botones de más y menos, o con el teclado, sin pedir confirmaciones. | Implementado |
| RF-V06 | Vaciar el carrito | Vaciar el carrito con una confirmación simple. | Implementado |
| RF-V07 | Producto no encontrado | Vender un producto que no está en el catálogo y dejarlo marcado como pendiente de validar para darlo de alta después. | Implementado |
| RF-V08 | Visualizar el ticket | Mostrar nombre y ubicación del negocio, fecha, hora y detalle de la venta. | Implementado |

**Auxiliar de inventario**

| Código | Requisito | Qué debe hacer el sistema | Estado |
|---|---|---|---|
| RF-I01 | Alta progresiva de productos | Dar de alta unos pocos productos al registrarse y seguir agregando después, con nombre, descripción, costo, precio, cantidades y categoría. | Implementado |
| RF-I02 | Modificar productos | Cambiar costo, precio y cantidades, y pedir el motivo del cambio. | Implementado |
| RF-I03 | Alertas de reabastecimiento | Avisar cuando un producto llega a su cantidad mínima, con una lista ordenada de lo que hay que surtir primero. | Parcial: ordena por qué tan crítico es el producto, no por rotación de ventas |
| RF-I04 | Eliminar productos | Dar de baja un producto avisando si ya tiene ventas registradas. | Implementado |
| RF-I05 | Productos precargados | Ofrecer una lista de productos comunes de abarrotes al crear la cuenta. | Implementado |
| RF-I06 | Ver el catálogo | Mostrar una tabla con búsqueda por nombre y filtro por categoría, ordenada por lo más crítico. | Parcial: falta ordenar por movimiento de ventas |
| RF-I07 | Proveedores | Registrar proveedores con sus datos de contacto y las categorías que surten. | Implementado |

**Agente financiero**

| Código | Requisito | Qué debe hacer el sistema | Estado |
|---|---|---|---|
| RF-F01 | Registrar gastos | Registrar y clasificar los gastos del negocio, con categorías nuevas que el tendero puede crear. | Implementado |
| RF-F02 | Punto de equilibrio | Mostrar en pesos la venta mínima para no perder dinero, con una explicación sencilla. | Implementado |
| RF-F03 | Precios sugeridos | Sugerir precios a partir del costo, dejando que el usuario acepte, ajuste o rechace cada uno. | Implementado |
| RF-F04 | Pronóstico de ventas | Generar proyecciones semanales con inteligencia artificial, con comparación contra el periodo anterior, nivel de confianza y una explicación breve. | En desarrollo; aún no está integrado |
| RF-F05 | Reportes financieros | Mostrar ingresos, egresos y utilidades por periodos, con alertas de productos de baja rotación y gastos fuera de lo normal. | Implementado por periodos de 3 y 6 meses; en construcción el filtro por rango de fechas y los productos más vendidos |

**Asistente virtual inteligente (AVI)**

| Código | Requisito | Qué debe hacer el sistema | Estado |
|---|---|---|---|
| RF-AVI01 | Identificar la intención | Entender qué quiere el usuario según el módulo en que está, sin impedirle preguntar cosas de otros módulos. | Implementado; por validar |
| RF-AVI02 | Extraer información de la petición | Sacar varios productos y cantidades de una sola frase y decidir qué función ejecutar. | Implementado; por validar |
| RF-AVI03 | Responder de forma guiada | Responder amable y, si la petición no es válida, dar ejemplos de lo que sí se puede pedir. | Implementado; por validar |
| RF-AVI04 | Explicar resultados financieros | Convertir cifras (punto de equilibrio, utilidad) en un resumen en palabras sencillas. | Implementado |
| RF-AVI05 | Datos incompletos | Detectar lo que falta en una petición y pedirlo antes de hacer cambios. | Implementado; por validar |
| RF-AVI06 | Confirmar acciones críticas | Pedir confirmación solo antes de acciones que no se pueden deshacer. | Parcial: el asistente aún no tiene acciones irreversibles |
| RF-AVI07 | Contexto de la conversación | Recordar lo que se habló para entender frases como "¿cuánto cuesta?". | Parcial: recuerda los últimos 10 mensajes |
| RF-AVI08 | Ingresar la petición | Poder escribir la petición en el chat. | Implementado (además, dictado por voz) |

**Sistema en general**

| Código | Requisito | Qué debe hacer el sistema | Estado |
|---|---|---|---|
| RF-S01 | Registro de cuenta | Registrar nombre del propietario, empresa, alcaldía de la CDMX y correo. | Implementado |
| RF-S02 | Inicio de sesión | Entrar con correo y contraseña. | Implementado (también con teléfono) |
| RF-S03 | Recuperar contraseña | Restablecer la contraseña por correo. | Implementado en modo desarrollo |
| RF-S04 | Eliminar la cuenta | Dar de baja la cuenta y todos sus datos de forma permanente. | Implementado |
| RF-S05 | Tutorial contextual | Ayudar con microtutoriales por módulo y un video de introducción. | Parcial: falta el video |
| RF-S06 | Sincronización de interfaz | Actualizar solo la pantalla del módulo cuando el asistente termina una acción. | Implementado |

**Estado actual de los requisitos.** De los 34 requisitos, 23 están implementados y 5 más también lo están, pero todavía deben validarse con el asistente real porque su resultado depende de cómo responda el modelo de lenguaje. Cinco requisitos están parciales (RF-I03, RF-I06, RF-AVI06, RF-AVI07 y RF-S05) y uno, el pronóstico de ventas (RF-F04), está en desarrollo. Además, el protocolo contempla que los reportes tengan filtros por rango de fechas y un listado de productos más vendidos; estas dos mejoras están en construcción.

### 1.2.2 Requerimientos No Funcionales

Un requerimiento no funcional no dice qué hace el sistema, sino cómo debe comportarse: qué tan rápido, qué tan seguro o qué tan fácil de usar. Los agrupamos tomando como guía las características de calidad de la norma ISO/IEC 25010 [16].

| Código | Tipo | Requerimiento |
|---|---|---|
| RNF-01 | Rendimiento | Las acciones normales (abrir una pantalla, agregar al carrito, cobrar) deben responder en menos de 3 segundos en una computadora de gama básica. Las respuestas del asistente dependen de internet y del proveedor del modelo, por lo que pueden tardar un poco más. |
| RNF-02 | Facilidad de uso | Lenguaje sencillo, botones grandes, colores con significado y un tutorial para el primer uso. El usuario no necesita conocimientos técnicos. |
| RNF-03 | Dispositivos | La interfaz se adapta a computadora, tablet y celular. |
| RNF-04 | Navegadores | Funciona en navegadores modernos. El dictado por voz solo funciona en los que lo permiten, como Chrome y Edge. |
| RNF-05 | Almacenamiento | Los datos se guardan en una base de datos SQL. |
| RNF-06 | Seguridad | Las contraseñas se guardan cifradas, los formularios tienen protección contra falsificación de peticiones (CSRF), solo se entra con sesión iniciada, cada negocio ve únicamente sus propios datos y las llaves de las API se guardan en un archivo `.env` que no se sube al repositorio. |
| RNF-07 | Privacidad | Al usar el asistente, el mensaje del usuario y algunos datos del negocio (como totales de ventas o gastos) se envían al proveedor del modelo de lenguaje. Nunca se envían contraseñas. |
| RNF-08 | Uso sin internet | Las ventas, el inventario y las pantallas financieras no dependen de la nube. Solo el asistente necesita internet. Hoy los iconos y la letra también se descargan de internet. |
| RNF-09 | Mantenimiento | El código está separado por módulos, las fórmulas financieras están en un solo archivo y hay pruebas automáticas. |
| RNF-10 | Instalación | Se instala en Windows con Python 3.12 y el archivo `requirements.txt`. |
| RNF-11 | Integridad de datos | Los montos se manejan con 2 decimales y el inventario se descuenta en el mismo paso que se cobra la venta. |
| RNF-12 | Volumen de datos | El sistema debe funcionar con el volumen de prueba (más de 1,000 productos y 16,000 ventas). Esto está en construcción: falta paginar el catálogo y el historial de ventas. |

## 1.3 Análisis del Sistema

### 1.3.1 Identificación de Actores

Un actor es cualquier persona o sistema que interactúa con nuestro sistema.

El **tendero o dueño del negocio** es el actor principal. Usa todos los módulos: vende, controla su inventario, registra gastos, consulta los reportes y platica con el asistente. También administra su cuenta. Junto a él puede haber un **cajero**, que ayuda a cobrar en el mostrador; por ahora el cajero comparte la cuenta del dueño, porque todavía no existe un rol separado con permisos propios.

El **asistente virtual (AVI)** es un actor del sistema: recibe las peticiones del tendero y ejecuta funciones por él, como agregar un producto al carrito o consultar las ventas. Para entender el texto y redactar las respuestas, el asistente se apoya en un actor externo, el **proveedor del modelo de lenguaje** (OpenAI con ChatGPT o Google con Gemini). Por último, el **motor de pronóstico** será otro actor del sistema encargado de calcular las ventas esperadas de cada semana; está en construcción.

### 1.3.2 Casos de Uso

Un caso de uso describe, paso a paso, algo que el usuario hace con el sistema. Identificamos 21, que se resumen en la siguiente tabla. Después se detallan los más importantes.

| Código | Caso de uso | Descripción breve | Requisitos |
|---|---|---|---|
| CU-01 | Registrar cuenta y negocio | El tendero crea su cuenta, da los datos de su tienda y elige productos iniciales. | RF-S01, RF-I05 |
| CU-02 | Iniciar sesión | Entra con correo o teléfono y contraseña. | RF-S02 |
| CU-03 | Armar el carrito de una venta | Busca productos, ajusta cantidades y ve el total. | RF-V01, V02, V04, V05 |
| CU-04 | Vender un producto no encontrado | Vende algo que no está en el catálogo sin detener la venta. | RF-V07 |
| CU-05 | Cobrar y ver el ticket | Cierra la venta y consulta el ticket. | RF-V03, V08 |
| CU-06 | Cancelar una venta | Vacía el carrito con una confirmación simple. | RF-V06 |
| CU-07 | Dar de alta un producto | Agrega un producto nuevo al inventario. | RF-I01 |
| CU-08 | Modificar un producto | Cambia sus datos y anota el motivo. | RF-I02 |
| CU-09 | Dar de baja un producto | Lo retira del catálogo conservando sus ventas anteriores. | RF-I04 |
| CU-10 | Ver alertas y catálogo | Revisa qué hay que surtir y busca o filtra productos. | RF-I03, I06 |
| CU-11 | Gestionar proveedores | Registra y edita proveedores y las categorías que surten. | RF-I07 |
| CU-12 | Registrar un gasto | Anota gastos fijos o variables con su categoría. | RF-F01 |
| CU-13 | Ver el punto de equilibrio | Consulta cuánto debe vender al mes para no perder dinero. | RF-F02 |
| CU-14 | Ver y aceptar precios sugeridos | Revisa precios sugeridos y acepta, ajusta o rechaza cada uno. | RF-F03 |
| CU-15 | Ver reportes financieros | Consulta ingresos, flujo de efectivo, margen y utilidad. | RF-F05 |
| CU-16 | Hablar con el asistente | Pide cosas por texto o voz. | RF-AVI01 a AVI08, S06 |
| CU-17 | Ver el resumen del día | El asistente le cuenta cómo le fue ayer. | RF-AVI04 |
| CU-18 | Recuperar la contraseña | Restablece su contraseña desde un enlace por correo. | RF-S03 |
| CU-19 | Eliminar la cuenta | Borra su cuenta y todos sus datos. | RF-S04 |
| CU-20 | Ver la ayuda de la pantalla | Revisa los consejos de cada módulo. | RF-S05 |
| CU-21 | Ver el pronóstico de ventas | Consulta las ventas esperadas de la semana. | RF-F04 (en construcción) |

**CU-01. Registrar cuenta y negocio.** El actor es el tendero y no debe tener sesión iniciada. Entra a la pantalla de registro y escribe su nombre completo, teléfono, correo y contraseña. El sistema revisa que el teléfono y el correo no estén repetidos y que la contraseña sea válida; si todo está bien, crea la cuenta e inicia la sesión. Después le pide los datos del negocio (nombre de la tienda, alcaldía, años de operación, si está en el régimen RESICO y su RFC). Finalmente le muestra una lista de productos comunes de abarrotes para que marque los que maneja, los crea en su inventario y lo lleva al punto de venta. Si el teléfono o el correo ya existen, el sistema avisa y no crea la cuenta.

**CU-03. Armar el carrito de una venta.** El tendero tiene sesión iniciada y productos en su inventario. Escribe el nombre del producto en la barra de búsqueda y el sistema muestra coincidencias mientras escribe. Al elegir una, el producto entra al carrito. Con los botones de más y menos (o con las teclas + y −) cambia la cantidad, y con el icono del bote de basura quita un producto de una sola vez. El total se actualiza y siempre está a la vista. Como alternativa, puede pedirle al asistente "agrega 2 pepsis"; si hay varios productos parecidos, el asistente le pregunta cuál quiere.

**CU-04. Vender un producto no encontrado.** Si el cliente pide algo que no está en el sistema, el tendero oprime "No encontrado", escribe el nombre y el precio, y el producto entra al carrito. La venta no se detiene. El producto queda guardado como "pendiente de validar", y después, en el inventario, el tendero puede completar sus datos (CU-08) para darlo de alta.

**CU-05. Cobrar y ver el ticket.** El tendero oprime "Cobrar". El sistema descuenta del inventario lo que se vendió, marca la venta como cobrada y muestra una notificación con el folio y el total. Desde ahí puede abrir el ticket, que muestra el nombre y la alcaldía del negocio, la fecha, la hora y el detalle de la venta. Si el carrito está vacío, el sistema avisa que no hay nada que cobrar.

**CU-08. Modificar un producto.** Desde el catálogo, el tendero oprime "Editar" en el producto, cambia los datos que necesite y escribe el motivo del cambio, que es obligatorio. El sistema guarda el cambio y el motivo en un historial. Si el producto estaba pendiente de validar, al guardarlo queda activo en el catálogo.

**CU-13. Ver el punto de equilibrio.** El tendero entra a "Punto de equilibrio". El sistema calcula la venta mínima del mes con los gastos fijos registrados y con lo que se ha vendido en los últimos tres meses. Muestra la cifra mensual y por día, una explicación en palabras sencillas, el avance del mes y cuánto debe vender de cada categoría. Si todavía no hay gastos fijos o ventas, el sistema explica qué falta para poder calcularlo.

**CU-14. Ver y aceptar precios sugeridos.** El tendero escribe el margen de ganancia que quiere y el sistema calcula el precio sugerido de cada producto. Por cada producto puede ajustar el precio y oprimir "Aceptar", o bien "Rechazar" para dejar el precio actual. Si acepta, el precio cambia y queda registrado en el historial del producto.

**CU-16. Hablar con el asistente.** El tendero escribe su petición en el chat o la dice con el micrófono. El sistema manda el mensaje y los últimos mensajes de la conversación al modelo de lenguaje, junto con la lista de funciones que puede usar. El modelo pide ejecutar una función (por ejemplo, agregar al carrito), el sistema la ejecuta con los datos del negocio y le regresa el resultado, y el modelo redacta una respuesta corta y sencilla. Si algo cambió, la pantalla del módulo se actualiza sola. Si falta un dato, el asistente lo pregunta; si la petición no tiene que ver con la tienda, responde con ejemplos de lo que sí puede hacer; y si no hay internet o falta la llave de la API, muestra un mensaje claro.

**CU-17. Ver el resumen del día.** Al iniciar sesión, el asistente muestra cómo le fue al negocio el día anterior (ventas, ganancia y gastos) con una recomendación corta, y ofrece dos botones: "Preguntar más" e "Ir a pronóstico de ventas". Este resumen se genera una sola vez al día; si el tendero entra otra vez ese mismo día, se muestra el que ya estaba guardado.

### 1.3.3 Diagramas de Casos de Uso

Los casos de uso anteriores se representan en seis diagramas. La Figura 1.1 es el diagrama general, con todos los actores y los 21 casos de uso agrupados por módulo. Las Figuras 1.2 a 1.6 muestran el detalle de cada módulo: ventas (CU-03 a CU-06), inventario (CU-07 a CU-11), agente financiero (CU-12 a CU-15 y CU-21), asistente virtual (CU-16 y CU-17) y seguridad y cuenta (CU-01, CU-02, CU-18, CU-19 y CU-20). En el diagrama del asistente se marca que el caso de uso "Hablar con el asistente" utiliza las funciones de ventas, inventario y finanzas.

**[Insertar Figuras 1.1 a 1.6]**

## 1.4 Diseño y arquitectura del Sistema

### 1.4.1 Arquitectura de Software

El sistema está hecho con Django, un marco de trabajo para páginas web en Python [1]. Django organiza el código en tres partes que se conocen como MVT. El **Modelo** describe los datos que se guardan (productos, ventas, gastos) y se encarga de leerlos y escribirlos en la base de datos. La **Vista** decide qué hacer cuando el usuario pide algo: recibe la petición, consulta o cambia los datos y elige qué pantalla mostrar. El **Template** es la plantilla en HTML con la pantalla que ve el usuario. Por ejemplo, cuando el tendero oprime "Cobrar", el navegador manda la petición a Django, la vista de cobro descuenta el inventario y marca la venta como cobrada usando los modelos, y finalmente responde con la pantalla ya actualizada.

Decidimos hacer todo dentro de una sola aplicación Django, sin un servidor aparte para el asistente y sin un framework pesado para la interfaz. Esto nos permitió usar tecnologías sencillas de mantener (HTML, CSS y JavaScript con Bootstrap) y hace más fácil instalar el sistema, porque solo hay una cosa que levantar.

El proyecto se dividió en módulos, llamados "apps" en Django, que corresponden a los componentes de nuestro diagrama de arquitectura:

| Componente del diagrama | App de Django | Qué contiene |
|---|---|---|
| Seguridad y autenticación | `accounts` | Registro, inicio de sesión, recuperar contraseña, eliminar cuenta y datos del negocio. |
| Ventas y carrito | `ventas` | Punto de venta, carrito, cobro, ticket e historial. |
| Inventario y alertas | `inventario` | Productos, categorías, proveedores, alertas de stock y catálogo precargado. |
| Agente financiero | `finanzas` | Gastos, punto de equilibrio, precios sugeridos, reportes y todas las fórmulas (`calculos.py`). |
| Orquestador AVI | `avi` | Chat, conexión con ChatGPT y Gemini, funciones que puede ejecutar y resumen diario. |
| Django ORM | Los `models.py` de todas las apps | Guardar y consultar datos sin escribir SQL a mano. |

El sistema se puede ver en cuatro capas. La capa de **presentación** son las plantillas HTML, CSS y JavaScript con Bootstrap; es lo que ve y toca el usuario. La capa de **lógica** son las vistas de Django y los archivos `services.py` y `calculos.py`, donde viven las reglas del negocio y las fórmulas. La capa de **datos** son los modelos de Django y la base de datos. Por último están los **servicios externos**: las API de OpenAI y de Google, que entienden el texto del tendero y redactan las respuestas.

**Cómo funciona el asistente.** El tendero escribe o dicta una petición; el dictado lo hace el propio navegador con una función llamada Web Speech API [5], y el sistema solo recibe el texto. La página manda ese texto a la vista del chat. El sistema le entrega al modelo de lenguaje el mensaje, los últimos 10 mensajes de la conversación y la lista de funciones disponibles, como agregar al carrito, consultar ventas, registrar un gasto o consultar el punto de equilibrio. A esto se le llama *function calling* [6], [7]: el modelo no inventa los datos, sino que pide que el sistema ejecute una función. Si el modelo pide una o varias funciones, el sistema las ejecuta con la base de datos del negocio y le devuelve los resultados; con ellos, el modelo redacta una respuesta breve. Si algo cambió, la página vuelve a pedir solo el contenido del módulo y lo actualiza, sin perder la conversación.

**Resumen diario.** Para no llamar al modelo de lenguaje cada vez que el tendero inicia sesión, el resumen de cómo le fue ayer se genera la primera vez que alguien del negocio entra ese día y se guarda en la base de datos. Las demás veces ese día se muestra el guardado. Así se evitan llamadas innecesarias y su costo, sobre todo cuando hay muchos usuarios.

**Pronóstico de ventas.** Se integrará como un módulo más que lee el historial de ventas guardado en la base de datos y entrega las ventas esperadas por semana a la pantalla del agente financiero y al asistente, que las explicará en palabras sencillas (sección 1.5.6).

**Estructura de carpetas:**

```
config/        configuración general del proyecto
core/          modelo base con fechas de creación y actualización
accounts/      seguridad: registro, login, negocio
inventario/    productos, proveedores, alertas
ventas/        punto de venta, carrito, tickets
finanzas/      gastos, reportes, fórmulas financieras
avi/           asistente: chat, funciones, conexión con los modelos
templates/     plantillas base y barra de navegación
static/        estilos (CSS) y JavaScript compartidos
docs/          documentación del proyecto
```

**[Insertar Figura 1.7: diagrama de arquitectura y de despliegue]**

### 1.4.2 Diseño de Base de Datos

Hoy el sistema usa SQLite [3], una base de datos relacional (SQL) que se guarda en un solo archivo. La elegimos para el desarrollo porque no hay que instalar ni configurar un servidor de base de datos. Django crea las tablas a partir de los modelos mediante archivos llamados migraciones. Como parte de la etapa de construcción está pendiente dejar configurado el servidor de base de datos que se usará en el entorno de validación (sección 1.7).

El sistema tiene 13 tablas principales y una tabla intermedia para la relación entre proveedores y categorías:

| Tabla | Para qué sirve | Campos principales |
|---|---|---|
| `Usuario` | La persona que usa el sistema. | Nombre completo, teléfono (único), correo, contraseña cifrada. |
| `Negocio` | La tienda del usuario. | Nombre de la tienda, alcaldía, años de operación, régimen RESICO, RFC. |
| `Categoria` | Tipo de producto (bebidas, lácteos…). | Nombre, icono. |
| `Proveedor` | Quién surte al negocio. | Nombre, teléfono, correo, categorías que surte. |
| `ProductoCatalogo` | Productos comunes ofrecidos al registrarse. | Nombre, categoría, icono, precio sugerido. |
| `Producto` | Producto real del inventario. | Nombre, descripción, categoría, proveedor, costo, precio de venta, cantidad actual y mínima, activo, pendiente de validar. |
| `HistorialModificacionProducto` | Motivo de cada cambio a un producto. | Producto, usuario, motivo, fecha. |
| `Venta` | Un ticket de venta. | Folio (único por negocio), estado (en curso, cobrada o cancelada), total. |
| `ItemVenta` | Cada renglón de una venta. | Venta, producto, cantidad, precio unitario. |
| `CategoriaGasto` | Tipo de gasto creado por el tendero. | Negocio, nombre. |
| `GastoOperativo` | Un gasto del negocio. | Tipo (fijo o variable), categoría, concepto, monto, nota, fecha. |
| `HistorialConversacion` | Mensajes del chat con el asistente. | Negocio, usuario, quién habló, mensaje. |
| `ResumenDiario` | Resumen del día generado por la IA. | Negocio, fecha (única por negocio), texto, ventas, ganancia, gastos. |

Hay algunas reglas importantes en el diseño de la base. Todas las tablas guardan su fecha de creación y de actualización. El folio de una venta no se repite dentro de un mismo negocio. Los productos no se borran de verdad cuando se dan de baja, solo se marcan como inactivos, para no perder las ventas anteriores. Un renglón de venta protege al producto vendido, de modo que no se puede borrar un producto que ya se vendió; por eso, al eliminar una cuenta completa se borran primero los renglones de venta y después todo lo demás. Todos los montos tienen 2 decimales. Y todo lo que pertenece a un negocio (productos, ventas, gastos, historial) está ligado a ese negocio, y el negocio a su usuario, por lo que si se elimina al usuario se elimina todo lo suyo.

**Datos para el pronóstico.** Para entrenar y probar el modelo de pronóstico se cargaron en el sistema más de 1,000 productos y más de 16,000 ventas históricas. Estos datos usan las tablas `Producto`, `Venta` e `ItemVenta`, que guardan el historial de ventas por producto y por fecha y son la materia prima del modelo.

### 1.4.3 Modelo Entidad-Relación

El modelo entidad-relación muestra cómo se conectan las tablas. Cada usuario tiene un solo negocio (relación de uno a uno). Un negocio tiene muchos productos, muchas ventas, varios proveedores y muchos gastos, además de sus categorías de gasto, su historial de conversación y sus resúmenes diarios (relaciones de uno a muchos). Una categoría agrupa muchos productos, y un producto puede tener un proveedor. Los proveedores y las categorías se relacionan de muchos a muchos, porque un proveedor puede surtir varias categorías y una categoría puede ser surtida por varios proveedores. Cada venta tiene varios renglones, y cada producto puede aparecer en muchos renglones de distintas ventas. Además, cada producto guarda el historial de sus modificaciones, cada gasto puede tener una categoría de gasto y cada producto puede venir de un producto del catálogo precargado.

**[Insertar Figura 1.8: modelo entidad-relación]**

### 1.4.4 Diagramas UML

Para describir el diseño usaremos un diagrama de clases y cuatro diagramas de secuencia.

El **diagrama de clases (Figura 1.9)** tiene una clase por cada tabla de la sección 1.4.2, con sus atributos y relaciones, y los métodos más importantes: `stock_critico`, `margen_porcentaje` y `tiene_ventas` en `Producto`, `subtotal` en `ItemVenta` y `recalcular_total` en `Venta`.

El **diagrama de secuencia de cobrar una venta (Figura 1.10)** empieza cuando el tendero oprime "Cobrar" en el navegador. La petición llega a la vista de cobro, que revisa que el carrito no esté vacío. Después, dentro de una sola transacción, descuenta la cantidad vendida de cada producto y cambia el estado de la venta a cobrada. Por último recalcula el total y responde con la pantalla de ventas y el folio del ticket.

El **diagrama de secuencia de un mensaje al asistente (Figura 1.11)** empieza cuando el tendero escribe "agrega 2 pepsis". La página manda el mensaje a la vista del chat, que pide al módulo de conexión que le pregunte al modelo de lenguaje, enviando el mensaje, el historial y las funciones disponibles. El modelo pide ejecutar la función de agregar al carrito; el módulo de funciones busca el producto, lo agrega al carrito y regresa el resultado. El modelo redacta la respuesta, la vista guarda la conversación en el historial y le indica a la página que se actualice, y la página muestra la respuesta y vuelve a cargar el contenido del carrito.

El **diagrama de secuencia del resumen del día (Figura 1.12)** empieza cuando el tendero inicia sesión. La pantalla de ventas pide el resumen a la vista correspondiente, que busca si ya existe uno de hoy para ese negocio. Si existe, lo regresa; si no, calcula los números de ayer, le pide al modelo que los explique, guarda el resultado y lo regresa.

El **diagrama de secuencia de aceptar un precio sugerido (Figura 1.13)** empieza cuando el tendero escribe un margen y oprime "Calcular". La vista calcula el precio sugerido de cada producto con la fórmula costo entre uno menos el margen. El tendero ajusta un precio y oprime "Aceptar", y la vista actualiza el precio y guarda el motivo en el historial del producto. Cuando el modelo de pronóstico esté integrado se agregará su diagrama de secuencia.

**[Insertar Figuras 1.9 a 1.13]**

### 1.4.5 Diseño de Interfaces

La interfaz está pensada para un tendero que trabaja rápido en el mostrador y que muy probablemente no tiene conocimientos técnicos. Por eso nos guiamos por estas ideas.

Primero, los textos usan palabras de todos los días, como "Cobrar", "Cancelar venta" o "Producto no encontrado". Segundo, los colores tienen significado para que el usuario identifique cada cosa a simple vista:

| Color | Dónde se usa | Significado |
|---|---|---|
| Verde | Cobrar, botón "+", alta de productos | Avanzar o agregar |
| Rojo | Cancelar venta, botón "−", alertas de reabastecimiento, dar de baja | Peligro o quitar |
| Amarillo | Barras de búsqueda | "Aquí se busca" |
| Naranja | Producto no encontrado | Caso especial |
| Morado y azul | Modificar productos, proveedores, asistente | Gestión |

Tercero, usamos la letra Inter y un fondo blanco hueso en lugar de blanco puro, porque cansa menos la vista durante todo el día. Cuarto, la pantalla tiene dos columnas: a la izquierda siempre está el chat del asistente y a la derecha está el sistema con su barra de navegación (ventas, inventario y finanzas), así el asistente nunca estorba al trabajo. Quinto, el diseño se adapta a computadora, tablet y celular; en pantallas pequeñas los menús se reducen a iconos. Sexto, las confirmaciones aparecen como notificaciones que se quitan solas y las acciones delicadas (cancelar una venta, dar de baja un producto, eliminar la cuenta) piden confirmación. Por último, la primera vez que se entra a cada módulo aparecen consejos sobre los botones importantes, y siempre hay un botón "?" para volver a verlos. Estas ideas siguen las heurísticas de usabilidad de Nielsen [11]: hablar el lenguaje del usuario, prevenir errores, mostrar el estado del sistema y dar ayuda.

**[Insertar capturas de pantalla finales como Figuras 1.14 en adelante: inicio de sesión, registro, punto de venta, ticket, inventario, alertas, dashboard financiero, punto de equilibrio, precios sugeridos, reportes, chat del asistente y vista en celular]**

## 1.5 Construcción del Software

### 1.5.1 Herramientas utilizadas

Escribimos el código en Visual Studio Code, con Python 3.12 [2] y Django 5 [1]. Las pantallas están hechas con HTML, CSS y JavaScript, con Bootstrap 5.3 [4] y Bootstrap Icons para los estilos y los iconos, y la letra Inter de Google Fonts. Para el asistente usamos las API de OpenAI (modelo `gpt-4o-mini`) [6] y de Google (modelo `gemini-2.5-flash`) [7], y el dictado por voz usa la función del navegador [5]. Las llaves de las API se leen de un archivo `.env` con la librería `python-dotenv`. Para el control de versiones usamos Git y GitHub, y para mantener las librerías del proyecto separadas del resto de la computadora usamos un entorno virtual de Python. Las librerías externas del proyecto están en el archivo `requirements.txt`. El modelo de pronóstico usará además librerías de ciencia de datos, que se agregarán a ese archivo cuando se integre.

### 1.5.2 Tamaño del proyecto

Al momento de redactar este reporte, sin contar migraciones ni librerías de terceros, el proyecto tiene alrededor de 2,800 líneas de Python, 2,100 de HTML, 1,900 de CSS y 500 de JavaScript, además de 61 pruebas automáticas.

### 1.5.3 Módulos desarrollados

**Seguridad.** El registro es en tres pasos: cuenta, negocio y productos iniciales. El inicio de sesión acepta correo o teléfono mediante un validador propio. La recuperación de contraseña usa las vistas que ya trae Django y, en el modo de desarrollo, el enlace aparece en la terminal en lugar de enviarse por correo. Para eliminar la cuenta se pide la contraseña otra vez.

**Inventario.** La gestión de productos se hace en ventanas emergentes dentro de la misma pantalla (alta, edición, proveedores y nueva categoría). Cada cambio a un producto guarda su motivo. Las alertas muestran primero los productos más críticos, y los productos creados desde "no encontrado" aparecen con la etiqueta "Pendiente de validar" hasta que el tendero completa sus datos.

**Ventas.** El carrito es una venta en estado "en curso". Las acciones del carrito usan formularios normales y solo la búsqueda mientras se escribe usa JavaScript, para no recargar la página. El cobro descuenta el inventario y cierra la venta en una sola transacción, de modo que o se hacen las dos cosas o no se hace ninguna.

**Agente financiero.** Todas las fórmulas están en un solo archivo, `finanzas/calculos.py`, para que el tablero, los reportes y el punto de equilibrio siempre usen los mismos números. Incluye el registro de gastos con categorías propias, el punto de equilibrio por categoría, los precios sugeridos y los reportes de ingresos, flujo de efectivo, margen operativo y utilidad neta, con alertas de productos que no se venden y gastos fuera de lo normal. Está en construcción el filtro por rango de fechas y el listado de productos más vendidos.

**Asistente virtual.** El archivo `clients.py` habla con ChatGPT o Gemini, `services.py` tiene las funciones que el asistente puede ejecutar y `views.py` conecta todo con la pantalla. Además incluye la memoria de los últimos mensajes, el resumen diario y el dictado por voz.

### 1.5.4 Fórmulas financieras implementadas

| Concepto | Fórmula |
|---|---|
| Flujo de efectivo | Ingresos − egresos (gastos registrados). |
| Margen bruto de un producto | ((precio de venta − costo) ÷ precio de venta) × 100. |
| Margen operativo | ((ingresos − costo de ventas − gastos operativos) ÷ ingresos) × 100. |
| Utilidad neta | Ingresos − costo de ventas − gastos operativos − ISR RESICO. |
| ISR RESICO [13], [14] | Tasa × ingresos del periodo. La tasa depende de los ingresos de los últimos 12 meses: hasta $300,000 → 1.00 %; hasta $600,000 → 1.10 %; hasta $1,000,000 → 1.50 %; hasta $2,500,000 → 2.00 %; hasta $3,500,000 → 2.50 %. |
| Precio sugerido | Costo ÷ (1 − margen deseado). |
| Punto de equilibrio por categoría | PE = F ÷ Σ(wᵢ · rᵢ), donde F son los gastos fijos del mes, wᵢ es la proporción de ventas de la categoría i y rᵢ = (pᵢ − cvᵢ) ÷ pᵢ es su margen de contribución, con pᵢ el precio promedio y cvᵢ el costo variable promedio por unidad. Después se reparte por categoría: Vᵢ = wᵢ · PE (pesos a vender) y Qᵢ = Vᵢ ÷ pᵢ (unidades a vender). |

Todas estas fórmulas están comprobadas con pruebas automáticas, incluido el ejemplo numérico de nuestro documento de diseño: con gastos fijos de $30,000 y las categorías de bebidas, lácteos y abarrotes, el punto de equilibrio es de $81,818.18.

### 1.5.5 Problemas encontrados y cómo se resolvieron

Durante la construcción encontramos varios problemas que vale la pena documentar.

- **Decimales de más en los totales.** Al multiplicar cantidad por precio, el total podía quedar con cuatro decimales. Ahora se redondea a dos decimales en cada renglón y en el total.
- **No se podía eliminar una cuenta con ventas.** La base de datos protege a los productos que ya se vendieron y el borrado fallaba. Antes de borrar la cuenta se eliminan ahora los renglones de venta de ese negocio.
- **El asistente no recordaba la conversación.** Cada mensaje empezaba una conversación nueva. Se agregó la memoria de los últimos 10 mensajes y se cuidó el orden de los mensajes guardados.
- **Con Gemini solo se ejecutaba la primera función.** Si el usuario pedía "2 leches y 3 panes", solo se agregaba uno. Ahora se ejecutan todas las funciones que pide el modelo.
- **El asistente elegía en silencio entre productos parecidos.** Si había "Coca 600" y "Coca 2L", agregaba cualquiera. Ahora pregunta cuál de las opciones quiere el usuario.
- **Un mismo marcador para dos cosas distintas.** Los productos "no encontrados" y los productos dados de baja estaban igual de inactivos y no se podían distinguir. Se agregó un campo específico para los productos pendientes de validar.
- **Llamadas repetidas a la inteligencia artificial.** Cada inicio de sesión generaba una llamada. El resumen del día ahora se guarda y se genera una sola vez al día.
- **Librerías instaladas en el lugar equivocado.** Las instalaciones iban al Python general de la computadora y no al entorno virtual. Se documentó usar siempre `python -m pip install` con el entorno activo.

### 1.5.6 Módulo de pronóstico de ventas (en desarrollo)

El pronóstico de ventas es la parte de aprendizaje automático del proyecto y se desarrolla en paralelo a la aplicación web. El objetivo es estimar las ventas de cada semana para un negocio con datos históricos limitados o con ruido, que es lo normal en una tienda de abarrotes.

Para poder entrenar y probar el modelo se cargaron en el sistema más de 1,000 productos y más de 16,000 ventas históricas. Con ese conjunto de datos, el trabajo sigue las etapas que planteamos en el protocolo:

1. **Recolección y limpieza de los datos.** Se revisan los datos para tratar valores vacíos, registros erróneos y días sin ventas, y se normalizan las series de tiempo.
2. **Estructuración de los conjuntos de datos.** Se arman las series de ventas por periodo y se separan en una parte para entrenar el modelo y otra para probarlo.
3. **Comparación de algoritmos.** Se evalúan distintos algoritmos aplicables a series de tiempo en tiendas pequeñas. En la literatura se encuentran desde métodos sencillos, como promedios móviles y suavizamiento exponencial, hasta ARIMA [17] y modelos de aprendizaje automático como los bosques aleatorios [18]. La idea es quedarnos con el que mejor funcione para este caso, no con el más complicado.
4. **Entrenamiento del modelo seleccionado** para pronosticar las ventas semanales.
5. **Ajuste de hiperparámetros** para reducir el error de las estimaciones. El error se medirá con métricas como RMSE, MAE y MAPE [12], que comparan lo que el modelo pronosticó contra lo que realmente se vendió.

Cuando el modelo esté listo se integrará a la pantalla de pronóstico del agente financiero. Ahí mostrará las ventas esperadas de la semana, una comparación contra el periodo anterior, un indicador del nivel de confianza y una explicación breve que dará el asistente, tal como lo pide el requisito RF-F04. Hoy esa pantalla existe como una maqueta de diseño.

**Estado actual:** el desarrollo del modelo está en curso. La comparación de algoritmos, las métricas de error y el modelo seleccionado se incluirán, con sus gráficas, en la versión final de este reporte.

### 1.5.7 Trabajo pendiente de construcción

Para terminar la construcción nos faltan principalmente cuatro cosas. Primero, integrar el modelo de pronóstico a la aplicación. Segundo, completar el módulo financiero con el filtro de reportes por rango de fechas y el listado de productos más vendidos que prometimos en el protocolo. Tercero, mejorar el rendimiento con la carga grande de datos: el catálogo de inventario y el historial de ventas cargan hoy todos los registros a la vez, y con más de 1,000 productos y 16,000 ventas necesitan paginación. Cuarto, dejar configurado el servidor de base de datos. Además, hay detalles menores: un orden por rotación de ventas en el catálogo y las alertas, el video introductorio del tutorial y la validación del asistente con las llaves reales.

## 1.6 Plan de Pruebas

Las pruebas sirven para comprobar que el sistema hace lo que piden los requisitos y que no se rompe cuando se le cambia algo. Combinamos dos tipos. Las **pruebas automáticas** son programas pequeños que usan el sistema por nosotros y revisan los resultados; se pueden repetir en segundos cada vez que se cambia el código y están en los archivos `tests.py` de cada módulo. Las **pruebas manuales** las hace una persona siguiendo un guion, y se usan para lo que es difícil automatizar, como la facilidad de uso o las respuestas del asistente con ChatGPT y Gemini.

Hasta ahora escribimos 61 pruebas automáticas, 8 unitarias y 53 de integración, que forman parte del repositorio. Se ejecutan con el comando `python manage.py test`; Django crea una base de datos temporal solo para ellas, así que no tocan los datos reales. Las pruebas del asistente simulan la respuesta de ChatGPT o Gemini, por lo que no gastan saldo ni necesitan internet. Los resultados de la ejecución se presentarán en la versión final de este reporte.

### 1.6.1 Pruebas Unitarias

Una prueba unitaria revisa una sola operación, sola, sin pantallas ni base de datos. Aquí probamos sobre todo las fórmulas, que son lo más delicado: si fallan, el tendero toma malas decisiones con su dinero. Las ocho pruebas verifican lo siguiente:

1. El punto de equilibrio con el ejemplo numérico de nuestro documento de diseño, que debe dar $81,818.18, con $40,909.09 por vender en bebidas (1,637 unidades).
2. Que no exista punto de equilibrio cuando los productos se venden por debajo de su costo.
3. La tasa de ISR RESICO en los límites de cada rango (por ejemplo, $300,000 da 1.00 % y $300,001 da 1.10 %).
4. El precio sugerido (costo de $15 con margen de 40 % da $25.00).
5. El flujo de efectivo, el margen operativo, el ISR y la utilidad neta con un ejemplo de cifras redondas.
6. Que el subtotal de un renglón se redondee a dos decimales (1.5 unidades a $12.99 dan $19.49).
7. El margen bruto de un producto (costo de $15 y precio de $25 dan 40 %).
8. Que un producto se considere crítico cuando su cantidad llega al mínimo.

### 1.6.2 Pruebas de Integración

Estas pruebas revisan que varias partes trabajen bien juntas: la pantalla, las reglas y la base de datos. Por ejemplo, que al cobrar una venta de verdad baje el inventario. Las 53 pruebas de integración cubren estos grupos de comportamiento:

- **Carrito y cobro:** agregar productos, subir y bajar cantidades (bajar a cero quita el producto), quitar un producto de una sola vez, cobrar descuenta el inventario y cierra la venta, y cancelar no mueve el inventario.
- **Producto no encontrado y búsqueda:** el producto queda pendiente de validar y la búsqueda encuentra por nombre.
- **Ticket:** muestra el nombre y la ubicación del negocio.
- **Inventario:** alta de productos, editar sin motivo no cambia nada y con motivo guarda el cambio y su historial, la baja conserva las ventas anteriores, un producto pendiente se activa al completarlo y las alertas ponen primero lo más crítico.
- **Seguridad entre negocios:** otro negocio no puede tocar mi carrito ni editar mis productos.
- **Cuenta:** inicio de sesión con correo, con correo en mayúsculas y con teléfono; contraseña incorrecta; pantallas que piden sesión; registro (el correo es obligatorio y no se repiten correo ni teléfono); recuperación de contraseña; y eliminación de cuenta, incluso con ventas.
- **Asistente:** el chat guarda el historial y pide refrescar la pantalla cuando algo cambia, una consulta no refresca, un mensaje vacío no llama al modelo, el resumen se pide a la IA una sola vez por día, el historial reciente trae los últimos 10 mensajes en orden, y las funciones piden elegir cuando hay productos parecidos.
- **Finanzas con datos reales:** todas las pantallas abren con y sin datos; el punto de equilibrio con ventas y gastos reales; los mensajes cuando faltan gastos fijos o ventas; el resumen del mes con ISR; el precio sugerido; aceptar o rechazar un precio; y registrar un gasto con una categoría nueva.

Además de estas pruebas, como parte de las pruebas de integridad del protocolo, se repetirán las verificaciones de consistencia entre inventario y ventas con la carga grande de datos: que el total de cada venta coincida con la suma de sus renglones y que el inventario no quede en negativo.

### 1.6.3 Pruebas Funcionales

Las pruebas funcionales revisan el sistema completo como lo usaría el tendero. Haremos una simulación de un día completo en una tienda de abarrotes, siguiendo un guion con el catálogo precargado de ejemplo. El día empieza con el inicio de sesión y la lectura del resumen del día. En la mañana se registran unas diez ventas de uno a cuatro productos, se cambian cantidades con los botones y con el teclado, se vende un producto que no está en el catálogo y se cancela una venta a medias. Al mediodía un producto llega a su cantidad mínima y debe aparecer la alerta, y se completan los datos del producto pendiente. En la tarde se da de alta un producto nuevo con una categoría nueva, se cambia un precio anotando el motivo y se registran gastos fijos y variables. Al cierre se consultan el punto de equilibrio, los precios sugeridos y los reportes, y se revisan los historiales, verificando que las cifras coincidan con lo vendido y gastado en el día.

Como el comportamiento del asistente depende del modelo de lenguaje, también probaremos con las llaves reales, en ChatGPT y en Gemini, una lista de frases: agregar uno y varios productos en una sola frase; pedir un producto ambiguo, para ver si pregunta cuál; preguntar "¿cuánto cuesta?" justo después de nombrar un producto, para comprobar que recuerda el contexto; registrar un gasto sin decir el monto, para ver si lo pide; preguntar por las finanzas del mes estando en otro módulo; pedir el punto de equilibrio; hacer una pregunta fuera de contexto, para ver si da ejemplos de lo que sí puede hacer; y repetir una de las frases con el micrófono en Chrome.

### 1.6.4 Pruebas de Aceptación

La prueba de aceptación la hacen las personas para quienes se hizo el sistema, los tenderos. Se realizará en un entorno controlado con tenderos representativos de los perfiles de usuario definidos en el protocolo. A cada persona se le explica en pocas palabras para qué sirve el sistema y se le piden seis tareas, sin ayudarle: registrar y cobrar una venta de tres productos, vender un producto que no está en el sistema, dar de alta un producto nuevo, pedirle al asistente que agregue un producto, registrar un gasto de luz y encontrar cuánto necesita vender al mes para no perder dinero. Quien observa anota si la persona logró la tarea, cuánto tardó, cuántos errores tuvo y si pidió ayuda. Al final, la persona contesta una encuesta de facilidad de uso con la escala SUS [15], más unas preguntas sobre el asistente y la comprensión de las recomendaciones, para evaluar la percepción de utilidad.

Daremos por aceptado el sistema si al menos 8 de cada 10 tenderos terminan las tareas sin ayuda, si registrar una venta de tres productos toma menos de un minuto después del tutorial, y si la calificación SUS es de 68 o más. Las plantillas de la encuesta y de la hoja de observación están en el Apéndice C.

Como parte de la validación también se probará el comportamiento del sistema con **datos incompletos o inconsistentes** (por ejemplo, sin gastos fijos registrados, sin ventas suficientes o con productos sin costo), y se evaluará el **rendimiento** del sistema con más de 1,000 productos y 16,000 ventas, midiendo los tiempos de respuesta de las pantallas principales.

## 1.7 Implementación o despliegue

### 1.7.1 Estado actual

Hoy el sistema se ejecuta en una computadora con Windows, Python 3.12 y un entorno virtual, y se usa desde el navegador. No se instala con un programa tradicional: se copia la carpeta del proyecto y se levanta un servidor pequeño en la misma computadora. Los pasos son los siguientes, con PowerShell en la carpeta del proyecto:

1. Crear el entorno virtual con `python -m venv .venv` y activarlo con `.venv\Scripts\Activate.ps1`. Se sabe que quedó activo porque el renglón empieza con `(.venv)`.
2. Instalar las librerías con `python -m pip install -r requirements.txt`. Se usa siempre `python -m pip` para que se instalen en el entorno correcto.
3. Crear un archivo `.env` junto a `manage.py` con las llaves de las API (`OPENAI_API_KEY` y `GEMINI_API_KEY`).
4. Crear las tablas de la base de datos con `python manage.py makemigrations` y `python manage.py migrate`.
5. Cargar el catálogo de productos de ejemplo con `python manage.py seed_catalogo`.
6. Levantar el sistema con `python manage.py runserver` y abrir `http://127.0.0.1:8000/` en el navegador.

### 1.7.2 Plan de despliegue para la validación

El despliegue está planeado en dos etapas. En la **primera etapa**, tal como lo planteamos en el protocolo, el servidor de la aplicación (Django) y el servidor de base de datos se dejan operativos en una computadora del equipo de desarrollo, y los participantes de las pruebas entran por el navegador. Esto mantiene los costos controlados. Para esta etapa falta dejar configurado el servidor de base de datos, habilitar el acceso desde los navegadores de los participantes y hacer las pruebas de conectividad entre el navegador y el equipo que aloja el sistema.

En la **segunda etapa** se migrará el sistema a Microsoft Azure [19] para ejecutar el entorno controlado de validación en la nube. Esta migración implica elegir los servicios de aplicación y de base de datos, mover los datos de SQLite al servidor de base de datos elegido, guardar las llaves de las API como variables secretas y no dentro del código, y apagar el modo de desarrollo de Django. Después se repetirán las pruebas de despliegue y de conectividad. El protocolo planteaba la nube como una posible evolución futura del proyecto; incluirla en esta etapa nos permite probar el sistema en condiciones más cercanas a las de un uso real.

### 1.7.3 Cambios necesarios para usarlo en un entorno real

El proyecto está hoy en modo de desarrollo, por lo que antes de usarlo con participantes hay que hacer algunos ajustes de configuración: poner `DEBUG = False`, cambiar la `SECRET_KEY` por una propia y secreta, indicar en `ALLOWED_HOSTS` el nombre o la dirección desde donde se accederá, usar un servidor de producción en lugar del servidor de desarrollo de Django, preparar los archivos estáticos con `collectstatic` y conectar un servicio de correo para que el enlace de recuperar contraseña llegue por correo. Si se quiere trabajar sin depender de internet para la interfaz, habría que guardar los iconos y la letra dentro del proyecto.

## 1.8 Capacitación de Usuarios

Pensamos en un tendero que no tiene tiempo para cursos largos y que seguramente no estudió computación. Por eso, la capacitación está dentro del propio sistema y se complementa con material corto.

Dentro del sistema, la primera vez que se entra a ventas, inventario o finanzas aparecen dos o tres globos de ayuda que señalan los botones importantes, por ejemplo "Busca un producto aquí" o "Cobra desde aquí". Se pueden omitir y ya no vuelven a salir solos, pero con el botón "?" de la barra superior se pueden ver de nuevo en cualquier momento. Además, el asistente funciona como guía: si el tendero pide algo que no se entiende, le explica qué puede pedirle y le da ejemplos, como "agrega 2 cocas al carrito" o "registra un gasto de luz de 450 pesos". También cada día le cuenta, en palabras simples, cómo le fue ayer y le da una recomendación. Las pantallas financieras traen explicaciones "en palabras simples" y los colores tienen significado, lo que reduce la necesidad de aprender cosas nuevas.

Como material complementario se está elaborando el manual de usuario (necesita capturas de la versión final) y están planeadas una guía rápida de una hoja con ejemplos de frases para el asistente y una sesión práctica corta con el sistema abierto, de unos 60 minutos, dividida en registro y primer ingreso, cómo vender, inventario, gastos y reportes sencillos, y cómo hablar con el asistente. La evaluación de esta capacitación será la realización de las tareas de la prueba de aceptación. Queda pendiente el video introductorio que pide el requisito RF-S05.

## 1.9 Plan de Mantenimiento

Mantener el sistema es cuidar que siga funcionando y mejorarlo con el tiempo. Lo dividimos en cuatro tipos: el correctivo, que arregla errores; el preventivo, que hace revisiones y respaldos para que no ocurran fallas; el adaptativo, que ajusta el sistema a cambios de afuera, como nuevas tasas del SAT o cambios en las API de ChatGPT y Gemini; y el perfectivo, que agrega mejoras, como el pronóstico de ventas.

La rutina más importante es el **respaldo de la base de datos**: debe hacerse todos los días o al cerrar la tienda, y una vez al mes hay que comprobar que el respaldo realmente se puede restaurar. También se propone revisar cada mes cuánto se ha gastado en las API de inteligencia artificial, ya que el chat y el resumen del día generan costo; cambiar las llaves cada seis meses o cuando se sospeche que se filtraron; actualizar las librerías cada tres meses corriendo antes las pruebas automáticas; revisar cada año la tabla de ISR RESICO por si el SAT la cambia; y depurar de vez en cuando el historial del chat, que crece con el tiempo.

Para actualizar el sistema sin perder datos se sigue este orden: hacer un respaldo de la base de datos, copiar la versión nueva del código, instalar las librerías, aplicar los cambios de la base con `python manage.py migrate`, correr las pruebas automáticas y probar una venta antes de volver a usarlo. Para restaurar un respaldo, con el sistema cerrado se reemplaza la base de datos por la copia guardada. Cuando el modelo de pronóstico esté integrado, habrá que volver a entrenarlo cada cierto tiempo con las ventas nuevas para que no se desactualice.

# CAPÍTULO 2. Resultados Esperados

En esta etapa todavía no tenemos mediciones, por lo que este capítulo describe lo que esperamos lograr con el sistema y cómo lo vamos a medir. Antes de medir una mejora hay que saber cómo estaba el negocio sin el sistema. Por eso, en la prueba con tenderos se anotará primero cómo llevaban sus cuentas antes (cuaderno, calculadora, memoria u hoja de cálculo) y cuánto tiempo les tomaba.

## 2.1 Beneficios Tangibles

Los beneficios tangibles son los que se pueden contar o medir. Esperamos que el sistema reduzca el tiempo para registrar una venta, porque la búsqueda mientras se escribe, el carrito con botones y el cobro en un solo paso evitan sumar a mano; esto se medirá con un cronómetro en la prueba, comparado con la forma de trabajar de antes. Esperamos también menos errores al cobrar, porque el total se calcula solo y cada venta genera su ticket, y menos productos agotados sin darse cuenta, gracias a las alertas de reabastecimiento. Otro beneficio esperado es el ahorro de tiempo en las cuentas: los reportes de ingresos, gastos y utilidad salen solos, y el punto de equilibrio y los precios sugeridos se calculan automáticamente. Esto se medirá preguntando cuántas horas por semana dedicaban a las cuentas antes y durante la prueba. Cuando el modelo de pronóstico esté integrado, esperamos además que el tendero pueda planear mejor sus compras con las ventas esperadas de la semana. Finalmente, al usar herramientas de código abierto, el costo de software del sistema es bajo; el costo principal será el uso de las API del asistente, que mediremos durante la prueba.

El sistema todavía no guarda fechas de caducidad, por lo que no podemos afirmar que reduzca las mermas por productos vencidos. Esto se considera como mejora futura.

## 2.2 Beneficios Intangibles

Los beneficios intangibles son los que no se miden fácilmente en números, pero son importantes. Esperamos dar más tranquilidad al dueño, porque saber cuánto vendió, cuánto gastó y cuánto le queda sin hacer cuentas a mano reduce el estrés administrativo. También esperamos que tome decisiones con datos y no con corazonadas: cuando ve su punto de equilibrio o los productos que no se venden, puede decidir mejor qué comprar y a qué precio vender. El asistente habla en palabras sencillas y se le puede hablar con la voz, lo que acerca la tecnología a personas que no están acostumbradas a usar sistemas de computadora. Además, el sistema muestra una estimación del impuesto ISR del régimen RESICO y ordena los ingresos y gastos, lo que ayuda a llevar mejor la contabilidad y es un paso hacia la formalidad. Por último, los datos se guardan en el equipo del propio negocio, por lo que el tendero no depende de un pago mensual para llevar sus ventas. Para nosotros como equipo, el proyecto también es un aprendizaje práctico en análisis de requisitos, diseño de bases de datos, desarrollo web y uso de inteligencia artificial.

## 2.3 Indicadores de Éxito

Un indicador es un número que nos dice si el proyecto va bien. La siguiente tabla muestra los que usaremos y en qué punto está cada uno.

| Indicador | Cómo se mide | Meta | Estado |
|---|---|---|---|
| Requisitos funcionales implementados | Tabla de la sección 1.2.1 | 34 de 34 | 28 implementados (5 por validar), 5 parciales y 1 en desarrollo |
| Pruebas automáticas aprobadas | `python manage.py test` | 100 % | 61 pruebas escritas; resultados en la versión final |
| Tiempo de respuesta de las pantallas | Medición con la carga grande de datos | Menos de 3 segundos | Por medir |
| Tiempo por venta | Cronómetro en la prueba de aceptación | Menos de 1 minuto | Por medir |
| Tareas completadas sin ayuda | Hoja de observación | 8 de cada 10 tenderos | Por medir |
| Facilidad de uso | Encuesta SUS [15] | 68 puntos o más | Por medir |
| Aciertos del asistente | Frases de prueba en ChatGPT y Gemini | 8 de cada 10 por modelo | Por medir |
| Adopción durante la prueba | Días con al menos una venta registrada entre días que abrió la tienda | 80 % o más | Por medir |
| Costo de las API por tienda | Consumo mensual dividido entre tiendas | Por definir | Por medir |
| Error del pronóstico (RMSE, MAE o MAPE) | Comparación entre lo pronosticado y lo vendido | Por definir con los datos | En medición por el modelo en desarrollo |

El RMSE es una forma de medir el error de un pronóstico: se compara lo que se dijo que se iba a vender con lo que realmente se vendió, y mientras más bajo sea, mejor es el modelo.

# CONCLUSIONES

## Conclusiones parciales

A la fecha de este reporte contamos con un sistema que funciona de principio a fin: se puede registrar una tienda, vender, controlar el inventario, registrar gastos, consultar finanzas con fórmulas reales y platicar con un asistente por texto o por voz. Está implementada la gran mayoría de los requisitos funcionales (28 de 34) y las fórmulas financieras están comprobadas con pruebas automáticas, incluyendo el ejemplo numérico de nuestro diseño. El asistente aprovecha un modelo de lenguaje sin inventar datos, porque sus respuestas salen de la información del negocio; aun así, su calidad depende del modelo y de la conexión a internet, y por eso falta validarlo con las llaves reales.

Todavía está en desarrollo la parte central del TT2: el modelo de pronóstico de ventas, que se está entrenando con más de 1,000 productos y 16,000 ventas. También están pendientes la validación con tenderos, el despliegue en el entorno controlado y la medición del rendimiento. Las conclusiones finales sobre el cumplimiento del objetivo se redactarán cuando estas actividades terminen.

## Lecciones aprendidas

Hasta ahora, el proyecto nos ha dejado varias lecciones. La primera es que conviene delimitar el alcance y terminar bien lo esencial, en lugar de querer abarcar todo a la vez. La segunda es revisar los requisitos contra el sistema desde temprano: cuando lo hicimos con casi todo construido, encontramos 13 requisitos sin cumplir y 12 a medias, y corregirlos nos tomó tres rondas de trabajo; si hubiéramos revisado cada etapa, habría costado menos.

También aprendimos que las fórmulas del negocio deben definirse antes de programarlas y probarse con ejemplos numéricos, y que es mejor ponerlas en un solo lugar para que todas las pantallas calculen lo mismo. Al trabajar con inteligencia artificial, aprendimos a darle instrucciones claras, a que use funciones del sistema en lugar de inventar datos, a probar su lógica simulando sus respuestas y a cuidar el costo de cada llamada, por lo que el resumen del día se genera una sola vez.

En cuanto a los datos, vimos que hay que pensar en el volumen desde el diseño: al cargar más de 16,000 ventas notamos que varias pantallas necesitan paginación. Escribir las pruebas automáticas nos ayudó a encontrar errores, como un problema en el orden de los mensajes del chat, y nos hizo ver que habría sido mejor escribirlas desde el principio. Sobre el diseño, probamos una interfaz muy sobria, pero los comentarios que recibimos mostraron que el tendero necesita identificar los botones a simple vista; por eso usamos colores con significado. Finalmente, perdimos tiempo con librerías instaladas en el lugar equivocado, y desde entonces documentamos el paso a paso de instalación; y reconocimos que debemos escribir mensajes más descriptivos al guardar versiones en Git, para que el historial sirva mejor como bitácora.

# TRABAJO A FUTURO

Esta sección reúne, primero, lo que falta para terminar el TT2 y, después, las mejoras que recomendamos para trabajos posteriores.

## Actividades pendientes del TT2

Para cerrar el TT2 nos falta principalmente lo siguiente:

1. **Integrar el modelo de pronóstico de ventas** a la aplicación, incluyendo la comparación contra el periodo anterior, el nivel de confianza y la explicación del asistente, y documentar el entrenamiento, la comparación de algoritmos, las métricas de error y el modelo seleccionado.
2. **Completar el agente financiero** con el filtro de reportes por rango de fechas y el listado de productos más vendidos.
3. **Mejorar el rendimiento con la carga grande de datos** (más de 1,000 productos y 16,000 ventas), paginando el catálogo de inventario y el historial de ventas.
4. **Dejar configurado el servidor de base de datos** y migrar los datos de prueba.
5. **Desplegar el sistema en el entorno de validación**: primero en una computadora del equipo, como se planteó en el protocolo, y después en Microsoft Azure; con las pruebas de despliegue y de conectividad.
6. **Ejecutar las pruebas**: registrar los resultados de las pruebas automáticas, hacer la simulación de un día completo y las pruebas del asistente con las llaves reales, y medir el rendimiento.
7. **Validar el sistema con tenderos** mediante las pruebas de usabilidad y de aceptación, y reportar sus resultados.
8. **Terminar la documentación**: el manual de usuario, el manual técnico, los resultados del modelo de pronóstico y las conclusiones de la validación.

## Recomendaciones para trabajos futuros

Además de terminar las actividades pendientes del TT2, vemos varias mejoras para trabajos futuros.

En el sistema, recomendamos paginar el catálogo y el historial de ventas para negocios con muchos registros; separar los roles de dueño y cajero, con permisos distintos; guardar el costo del producto el día de la venta, para que la utilidad histórica no cambie cuando cambia el costo actual; registrar las compras a proveedores, para que el flujo de efectivo incluya la compra de mercancía; registrar fechas de caducidad y avisar de productos por vencer; y dar a cada negocio sus propias categorías, porque hoy son compartidas. También sería útil ordenar alertas y catálogo por rotación de ventas, pedir confirmación en el asistente si en el futuro se le agregan acciones que no se pueden deshacer, y agregar la lectura de las respuestas en voz alta, ya que hoy la voz solo sirve para dictar.

En infraestructura, recomendamos guardar los iconos y la letra dentro del proyecto para poder trabajar sin internet, estudiar un modelo de lenguaje que corra en la misma computadora para no depender de la nube ni compartir datos con terceros, conectar un servicio de correo real, programar respaldos automáticos y reforzar la seguridad para producción (HTTPS y límite de intentos de inicio de sesión).

A largo plazo, el sistema podría ofrecerse como un servicio en la nube que varios negocios usen sin instalar nada y desde el celular, y conectarse con el SAT para facturación electrónica y apoyo con la declaración del régimen RESICO. Esto último debe revisarse con un contador, porque las reglas fiscales cambian [13], [14]. También se pueden construir reportes avanzados con Power BI conectado a la base de datos.

# REFERENCIAS

[1] Django Software Foundation, "Django documentation," Django 5.x. [Online]. Available: https://docs.djangoproject.com/

[2] Python Software Foundation, "Python 3 documentation." [Online]. Available: https://docs.python.org/3/

[3] SQLite Consortium, "SQLite documentation." [Online]. Available: https://www.sqlite.org/docs.html

[4] Bootstrap Team, "Bootstrap 5.3 documentation." [Online]. Available: https://getbootstrap.com/docs/5.3/

[5] Mozilla, "Web Speech API," MDN Web Docs. [Online]. Available: https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API

[6] OpenAI, "Function calling," OpenAI Platform Documentation. [Online]. Available: https://platform.openai.com/docs/guides/function-calling

[7] Google, "Function calling with the Gemini API," Google AI for Developers. [Online]. Available: https://ai.google.dev/gemini-api/docs/function-calling

[8] K. Schwaber and J. Sutherland, "The Scrum Guide," Nov. 2020. [Online]. Available: https://scrumguides.org/

[9] I. Sommerville, *Software Engineering*, 10th ed. Harlow, U.K.: Pearson, 2016.

[10] R. S. Pressman and B. R. Maxim, *Ingeniería del software: un enfoque práctico*, 8.ª ed. Ciudad de México, México: McGraw-Hill, 2015.

[11] J. Nielsen, "10 usability heuristics for user interface design," Nielsen Norman Group. [Online]. Available: https://www.nngroup.com/articles/ten-usability-heuristics/

[12] R. J. Hyndman and G. Athanasopoulos, *Forecasting: Principles and Practice*, 3rd ed. Melbourne, Australia: OTexts, 2021. [Online]. Available: https://otexts.com/fpp3/

[13] Congreso de la Unión, "Ley del Impuesto sobre la Renta," *Diario Oficial de la Federación*, Título IV, Capítulo II, Sección IV, "Régimen Simplificado de Confianza."

[14] Servicio de Administración Tributaria, "Régimen Simplificado de Confianza (RESICO)." [Online]. Available: https://www.sat.gob.mx/

[15] J. Brooke, "SUS: A 'quick and dirty' usability scale," in *Usability Evaluation in Industry*, P. W. Jordan, B. Thomas, B. A. Weerdmeester, and I. L. McClelland, Eds. London, U.K.: Taylor & Francis, 1996, pp. 189–194.

[16] ISO/IEC 25010:2011, *Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — System and software quality models*, International Organization for Standardization, Geneva, Switzerland, 2011.

[17] G. E. P. Box, G. M. Jenkins, G. C. Reinsel, and G. M. Ljung, *Time Series Analysis: Forecasting and Control*, 5th ed. Hoboken, NJ, USA: Wiley, 2015.

[18] L. Breiman, "Random forests," *Machine Learning*, vol. 45, no. 1, pp. 5–32, 2001.

[19] Microsoft, "Azure App Service documentation." [Online]. Available: https://learn.microsoft.com/azure/app-service/

# GLOSARIO

- **API:** forma en que un programa le pide cosas a otro. Aquí, el sistema le pide respuestas a ChatGPT o Gemini.
- **Base de datos:** donde se guarda toda la información del sistema (productos, ventas, gastos).
- **Django:** herramienta en Python para construir páginas y sistemas web.
- **ORM:** parte de Django que permite guardar y consultar datos sin escribir SQL a mano.
- **Migración:** archivo que le indica a Django cómo crear o cambiar las tablas de la base de datos.
- **Function calling:** forma de trabajar del asistente: en vez de inventar datos, el modelo pide que el sistema ejecute una función y usa el resultado.
- **Modelo de lenguaje (LLM):** programa de inteligencia artificial que entiende y redacta texto, como ChatGPT o Gemini.
- **Entorno virtual:** carpeta con las librerías del proyecto, separada del resto de la computadora.
- **Punto de equilibrio:** venta mínima para cubrir todos los gastos sin ganar ni perder.
- **RESICO:** Régimen Simplificado de Confianza, un régimen fiscal con tasas bajas de ISR para negocios pequeños.
- **ISR:** Impuesto Sobre la Renta.
- **Pronóstico de ventas:** estimación de cuánto se va a vender en el futuro a partir de lo que se vendió antes.
- **RMSE, MAE y MAPE:** formas de medir qué tan lejos estuvo un pronóstico de lo que realmente pasó.
- **Paginación:** mostrar los registros en páginas pequeñas en lugar de todos juntos, para que la pantalla cargue rápido.

# APÉNDICES

## Apéndice A. Manual de usuario

Este manual está en elaboración, porque necesita capturas de pantalla de la versión final del sistema. Está escrito para el tendero, con frases cortas y una captura por cada paso. Tendrá las siguientes secciones:

1. **Empezar:** crear la cuenta, registrar la tienda y elegir los productos iniciales.
2. **Entrar y salir:** iniciar sesión con correo o teléfono, recuperar la contraseña y cerrar sesión.
3. **Vender:** buscar un producto, cambiar cantidades, quitar un producto, cobrar, ver el ticket y cancelar una venta.
4. **Cuando el producto no está en el sistema:** el botón "No encontrado".
5. **Inventario:** dar de alta, editar (y por qué se pide el motivo), dar de baja, proveedores, categorías nuevas y alertas.
6. **Gastos:** registrar renta, luz y otros gastos.
7. **Finanzas explicadas fácil:** qué significa el punto de equilibrio, cómo se usan los precios sugeridos y cómo leer los reportes.
8. **El asistente:** qué se le puede pedir (con ejemplos), cómo usar el micrófono y el resumen del día.
9. **Ayuda:** el botón "?" y los consejos de cada pantalla.
10. **Cuenta:** cómo eliminar la cuenta y qué pasa con los datos.
11. **Preguntas frecuentes:** por ejemplo, "no me deja entrar a mi cuenta", "el asistente no responde" o "se acabó un producto y no me avisó".

## Apéndice B. Manual técnico

El manual técnico está en construcción. Gran parte de su contenido ya está escrito en este reporte y solo falta reunirlo y ordenarlo, además de agregar el despliegue final y los resultados del modelo de pronóstico. Su contenido y el lugar de este reporte del que sale cada parte son los siguientes:

| Sección del manual | De dónde sale |
|---|---|
| 1. Requisitos e instalación (Windows, Python 3.12, entorno virtual, `requirements.txt`, archivo `.env`) | Sección 1.7.1 y el archivo `README.md` del proyecto |
| 2. Estructura del proyecto y de los módulos | Sección 1.4.1 |
| 3. Base de datos y migraciones (diccionario de datos) | Secciones 1.4.2 y 1.4.3 |
| 4. Rutas (URLs) de cada módulo | Archivos `urls.py` de cada módulo |
| 5. El asistente: conexión con ChatGPT y Gemini, lista de funciones y cómo agregar una función nueva | Archivos `avi/clients.py` y `avi/services.py` |
| 6. Fórmulas financieras y cómo cambiar la tabla de ISR | Sección 1.5.4 y archivo `finanzas/calculos.py` |
| 7. Modelo de pronóstico: datos, entrenamiento, evaluación e integración | Sección 1.5.6 (se completará) |
| 8. Cómo ejecutar las pruebas | Sección 1.6 |
| 9. Respaldo, restauración y actualización | Sección 1.9 |
| 10. Despliegue y cambios necesarios para producción | Secciones 1.7.2 y 1.7.3 |
| 11. Problemas comunes (librería instalada en el lugar equivocado, falta de llave de API, etc.) | Sección 1.5.5 |

## Apéndice C. Encuestas, entrevistas y hojas de observación

Estas plantillas se aplicarán en la prueba de aceptación con tenderos. Los resultados, con sus gráficas, se agregarán en la versión final del reporte.

### C.1 Entrevista breve inicial (antes de usar el sistema)

1. ¿Cuánto tiempo lleva con su tienda? ____
2. ¿Cómo lleva hoy sus ventas y cuentas? (cuaderno / calculadora / Excel / de memoria / otro) ____
3. ¿Cuánto tiempo a la semana le dedica a hacer cuentas? ____
4. ¿Qué es lo que más le cuesta trabajo de llevar su negocio? ____
5. ¿Usa computadora, tablet o celular en su tienda? ¿Para qué? ____
6. ¿Sabe qué es el régimen RESICO? ¿Está inscrito? ____

### C.2 Hoja de observación (la llena quien aplica la prueba)

| Tarea | ¿La terminó sin ayuda? (sí/no) | Tiempo | Errores | Comentarios |
|---|---|---|---|---|
| T1. Registrar y cobrar una venta de 3 productos | | | | |
| T2. Vender un producto que no está en el sistema | | | | |
| T3. Dar de alta un producto nuevo | | | | |
| T4. Pedirle al asistente que agregue un producto | | | | |
| T5. Registrar un gasto de luz | | | | |
| T6. Encontrar cuánto necesita vender para no perder dinero | | | | |

### C.3 Encuesta de facilidad de uso (escala SUS adaptada [15])

Marque de 1 a 5, donde **1 = Muy en desacuerdo** y **5 = Muy de acuerdo**.

| # | Afirmación | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 1 | Creo que me gustaría usar este sistema con frecuencia. | | | | | |
| 2 | Me pareció que el sistema era más complicado de lo necesario. | | | | | |
| 3 | Me pareció fácil de usar. | | | | | |
| 4 | Creo que necesitaría ayuda de alguien que sepa de computadoras para usarlo. | | | | | |
| 5 | Las partes del sistema (ventas, inventario, finanzas, asistente) se sienten bien conectadas. | | | | | |
| 6 | Noté muchas cosas que no se parecían entre sí o que me confundían. | | | | | |
| 7 | Creo que la mayoría de las personas aprendería a usarlo muy rápido. | | | | | |
| 8 | Me pareció muy incómodo de usar. | | | | | |
| 9 | Me sentí con confianza al usarlo. | | | | | |
| 10 | Necesité aprender muchas cosas antes de poder usarlo. | | | | | |

**Cómo se calcula la calificación (de 0 a 100):** en las preguntas impares (1, 3, 5, 7, 9) se resta 1 a la respuesta; en las pares (2, 4, 6, 8, 10) se resta la respuesta a 5. Se suman los 10 resultados y se multiplica por 2.5. Un promedio de 68 se considera el nivel de referencia.

### C.4 Preguntas sobre el sistema (de 1 a 5)

| # | Afirmación | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| 11 | Entendí para qué sirve cada botón. | | | | | |
| 12 | Los colores me ayudaron a saber qué hace cada botón. | | | | | |
| 13 | El asistente entendió lo que le pedí. | | | | | |
| 14 | Me gustó poder hablarle al asistente con la voz. | | | | | |
| 15 | Entendí la explicación del punto de equilibrio. | | | | | |
| 16 | Los consejos de ayuda me sirvieron. | | | | | |
| 17 | Usaría este sistema en mi tienda. | | | | | |

### C.5 Preguntas abiertas

18. ¿Qué fue lo más difícil de usar? ____
19. ¿Qué fue lo que más le gustó? ____
20. ¿Qué cambiaría o le agregaría? ____

## Apéndice D. Código fuente (fragmentos representativos)

En este apéndice se incluirán únicamente los fragmentos más representativos del código, cada uno con su título, la ruta del archivo y una breve explicación. No se incluirán el archivo `.env`, las llaves de las API ni la llave secreta de Django. Los fragmentos son los siguientes:

| Fragmento | Archivo | Qué demuestra |
|---|---|---|
| Modelos `Producto`, `Venta` e `ItemVenta` | `inventario/models.py`, `ventas/models.py` | Cómo se guardan los datos y sus relaciones. |
| Cobro de una venta en una sola transacción | `ventas/views.py` (función `cobrar`) | Que el inventario y la venta se actualizan juntos. |
| Cálculo del punto de equilibrio por categoría | `finanzas/calculos.py` (función `calcular_punto_equilibrio`) | La fórmula implementada, con el ejemplo del documento. |
| Utilidad neta, margen operativo y ISR RESICO | `finanzas/calculos.py` (`resumen_desde_sumas`, `tasa_isr_resico`) | Las fórmulas financieras del negocio. |
| Conexión con ChatGPT y Gemini usando funciones | `avi/clients.py` (`preguntar_chatgpt`, `preguntar_gemini`) | Cómo el asistente pide funciones al sistema en lugar de inventar datos. |
| Funciones que puede ejecutar el asistente | `avi/services.py` (`FUNCIONES`, `agregar_al_carrito`) | Qué puede hacer el asistente y cómo pregunta si hay varios productos parecidos. |
| Eliminación de cuenta | `accounts/views.py` (`eliminar_cuenta`) | Manejo de datos protegidos y borrado completo. |
| Pruebas de fórmulas | `finanzas/tests.py` | Cómo se verifica que las fórmulas den el resultado correcto. |

Cuando el modelo de pronóstico esté integrado, se agregarán también sus fragmentos principales.

## Apéndice E. Índice de figuras

Las figuras que acompañan a este reporte, y que elabora el equipo, son las siguientes. Al terminar el documento se les agregan los números de página.

| Figura | Contenido | Sección |
|---|---|---|
| Figura 1.1 | Diagrama general de casos de uso | 1.3.3 |
| Figuras 1.2 a 1.6 | Casos de uso por módulo: ventas, inventario, agente financiero, asistente virtual, seguridad y cuenta | 1.3.3 |
| Figura 1.7 | Diagrama de arquitectura y de despliegue | 1.4.1 |
| Figura 1.8 | Modelo entidad-relación | 1.4.3 |
| Figura 1.9 | Diagrama de clases | 1.4.4 |
| Figuras 1.10 a 1.13 | Diagramas de secuencia: cobrar una venta, mensaje al asistente, resumen del día y aceptar un precio sugerido | 1.4.4 |
| Figuras 1.14 en adelante | Capturas de pantalla del sistema | 1.4.5 |

