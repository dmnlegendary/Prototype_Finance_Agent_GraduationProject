# Checklist de requisitos y reglas de negocio

Este checklist compara cada requisito y cada regla con lo que hace el sistema hoy. El estado sale de revisar el código y las pruebas automáticas (más de 400), no de la memoria.

Estados: **Cumple** (hace lo que dice), **Cumple con ajuste** (lo hace, pero de una forma distinta a la escrita, y conviene cambiar el texto del requisito o de la regla) y **No verificable** (depende de la instalación o de una medición que todavía no se hace).

## Resumen

| Grupo | Total | Cumplen | Con ajuste | No verificables |
|---|---|---|---|---|
| Ventas (RF-V) | 8 | 7 | 1 | 0 |
| Inventario (RF-I) | 7 | 7 | 0 | 0 |
| Finanzas (RF-F) | 5 | 5 | 0 | 0 |
| Asistente (RF-AVI) | 8 | 8 | 0 | 0 |
| Sistema (RF-S) | 9 | 8 | 1 | 0 |
| No funcionales (RNF) | 9 | 5 | 1 | 3 |
| Reglas de negocio (RN) | 24 | 21 | 3 | 0 |

Hay cinco puntos donde el requisito o la regla se contradice con otra, o con lo que ya se construyó, y la decisión es de ustedes: RN-17 y RN-23 frente a RF-AVI02, RN-20, RF-S05 y RNF-08. Se explican al final.

## Requisitos funcionales de ventas

| Código | Estado | Cómo se cumple |
|---|---|---|
| RF-V01 | Cumple | El asistente entiende frases como "agrega 2 pepsis". La búsqueda tolera errores de dedo, acentos y nombres incompletos. Si el nombre es ambiguo, pregunta cuál es. |
| RF-V02 | Cumple | Cantidades y productos se cambian al instante, sin recargar. Hay dos cajas. |
| RF-V03 | Cumple | Un solo paso: cobrar. Descuenta el inventario, guarda la venta y abre el ticket sin bloquear la pantalla. |
| RF-V04 | Cumple | El total está siempre visible debajo de la caja. |
| RF-V05 | Cumple | Botones de más y menos, o escribir la cantidad. |
| RF-V06 | Cumple | Cancelar la venta pide una confirmación sencilla. |
| RF-V07 | Cumple con ajuste | Pide nombre y precio de venta, no el costo ni la cantidad. La cantidad se ajusta en la caja y el costo se completa después en Finanzas, donde el producto queda pendiente de validar. Conviene cambiar el texto del requisito. |
| RF-V08 | Cumple | Muestra tienda, ubicación, fecha, hora, folio y detalle. |

## Requisitos funcionales de inventario

| Código | Estado | Cómo se cumple |
|---|---|---|
| RF-I01 | Cumple | Alta progresiva. Ahora el formulario pide nombre, descripción, costo, precio, cantidad, mínimo y **categoría** (la descripción y la categoría eran opcionales y ahora son obligatorias). |
| RF-I02 | Cumple | Se edita con un motivo obligatorio, que queda en el historial. |
| RF-I03 | Cumple | Semáforo por colores. Se ordena por criticidad y, dentro de cada color, por el producto que se acaba antes según lo que vende. |
| RF-I04 | Cumple | Baja lógica con advertencia si hay ventas, y ahora con doble confirmación. |
| RF-I05 | Cumple | Catálogo precargado al registrarse. |
| RF-I06 | Cumple | Tabla con búsqueda y filtro por categoría, ordenada por lo más crítico. |
| RF-I07 | Cumple | Proveedores con contacto y categorías que surten. |

## Requisitos funcionales de finanzas

| Código | Estado | Cómo se cumple |
|---|---|---|
| RF-F01 | Cumple | Gastos fijos y variables, con categorías propias y con el mes al que corresponde cada uno. |
| RF-F02 | Cumple | Punto de equilibrio mensual y diario, con explicación en lenguaje sencillo. |
| RF-F03 | Cumple | Precios sugeridos con el costo y los gastos: la opción "Cubrir mis gastos" calcula el margen necesario. Se acepta, ajusta o rechaza cada precio. |
| RF-F04 | Cumple | Pronóstico semanal con tres modelos, comparación contra la última semana, nivel de confianza y explicación con IA. Se muestra de forma progresiva. |
| RF-F05 | Cumple | Reportes de 1, 3, 6 o 12 meses, o de un rango de meses que el tendero escoge, con alertas y sugerencias concretas (gasto inusual, meses con pérdida, gastos que suben, margen bajo, baja rotación). Además hay un reporte de ventas con filtro por fechas, productos más vendidos y ganancias. |

## Requisitos funcionales del asistente

| Código | Estado | Cómo se cumple |
|---|---|---|
| RF-AVI01 | Cumple | El asistente sabe en qué pantalla está el usuario. Las consultas de cualquier módulo se pueden hacer desde cualquier pantalla; las acciones que cambian datos, solo las de la pantalla actual. |
| RF-AVI02 | Cumple | Extrae varios productos y cantidades de una frase y ejecuta una función por cada uno. |
| RF-AVI03 | Cumple | Respuestas amables. Las peticiones que no son de la tienda reciben un mensaje estándar con ejemplos. |
| RF-AVI04 | Cumple | Explica el inicio, los reportes, el punto de equilibrio y el pronóstico en palabras sencillas. |
| RF-AVI05 | Cumple | Si falta un dato (monto, categoría, costo), lo pregunta antes de hacer nada. |
| RF-AVI06 | Cumple | Pide confirmación solo para cancelar una venta o dar de baja un producto. |
| RF-AVI07 | Cumple | Recuerda la conversación de 24 horas y las preferencias del tendero entre sesiones (margen de precios, modo de precios, periodo de reportes). |
| RF-AVI08 | Cumple | Chat por texto, además de dictado por voz. |

## Requisitos funcionales del sistema

| Código | Estado | Cómo se cumple |
|---|---|---|
| RF-S01 | Cumple | Nombre, tienda, alcaldía (o lugar) y correo o teléfono. |
| RF-S02 | Cumple | Con correo o teléfono y contraseña. |
| RF-S03 | Cumple | Recuperación por correo. En desarrollo el correo se imprime en la terminal; con `EMAIL_HOST` en el `.env` se manda por SMTP de verdad. |
| RF-S04 | Cumple | Elimina la cuenta y todos sus datos. |
| RF-S05 | Cumple con ajuste | Hay ayuda por módulo (botón "?" con preguntas frecuentes), ejemplos en pantalla y un video de bienvenida que se muestra solo la primera vez cuando se configura `VIDEO_INTRODUCTORIO_URL`. El recorrido guiado ("mini tutoriales") se retiró por decisión del equipo. Falta poner el enlace del video. |
| RF-S06 | Cumple | La pantalla se actualiza sola después de una acción del asistente. |
| RF-S07 a RF-S09 | Cumple | Los tres módulos se abren desde la barra de navegación. |

## Requisitos no funcionales

| Código | Estado | Cómo se cumple |
|---|---|---|
| RNF-01 | Cumple | Ayuda integrada (preguntas frecuentes, ejemplos y video) y lenguaje sencillo. Falta medirlo con un tendero. |
| RNF-02 | Cumple con ajuste | Fondo cálido y claro y tipografía legible. Los colores de cada módulo (verde, azul, rosa, morado) son más vivos que "cálidos"; se eligieron porque significan algo (sección 6.10). |
| RNF-03 | Cumple | Diseño adaptable a computadora, tableta y celular. |
| RNF-04 | No verificable | Las pantallas hacen entre 4 y 20 consultas y la búsqueda es en memoria, pero falta medir los tiempos en el equipo real. |
| RNF-05 | Cumple | El pronóstico muestra un resultado preliminar enseguida y lo va refinando, con barra de avance y mensajes de estado. |
| RNF-06 | No verificable | Depende del servicio de IA. Hay respuestas directas sin segunda llamada, pero el tiempo máximo de espera es de 30 segundos y 3 segundos no se puede garantizar. |
| RNF-07 | Cumple | Una aplicación por módulo y las fórmulas en un solo archivo. |
| RNF-08 | No verificable | 99.5 % de disponibilidad depende de la infraestructura. El cobro funciona sin internet, lo que ayuda, pero no se puede garantizar. |
| RNF-09 | Cumple | Contraseñas con PBKDF2. HTTPS se activa con `USAR_HTTPS=True` cuando el sistema se publica con certificado. |

## Reglas de negocio

| Código | Estado | Cómo se cumple |
|---|---|---|
| RN-01 | Cumple | No se cobra más de lo que hay; la venta se rechaza completa. |
| RN-02 | Cumple | El cobro y el descuento del inventario son una sola operación; si algo falla, no se mueve nada. |
| RN-03 | Cumple | Alerta visual por colores y campana. El mínimo que se propone es 5. |
| RN-04 | Cumple | Todo producto tiene id único, y categoría obligatoria. Los importados sin categoría van en "Otros". |
| RN-05 | Cumple | La base de datos impide existencias negativas. |
| RN-06 | Cumple | El kardex registra cada movimiento y se descarga como CSV para usarlo como dataset. |
| RN-07 | Cumple | Los movimientos y las ventas se ligan por id y cada renglón de venta guarda su precio y costo, así que editar un producto no cambia su historia. |
| RN-08 | Cumple | Proveedores y categorías tienen id propio. |
| RN-09 | Cumple | Toda venta, entrada, merma y ajuste deja un movimiento con su motivo. |
| RN-10 | Cumple | Todo gasto es fijo o variable. La compra de mercancía es un tipo aparte y se registra sola. |
| RN-11 | Cumple | El punto de equilibrio exige al menos un gasto fijo y el costo de los productos. |
| RN-12 | Cumple | Un producto necesita 30 días de historia (configurable con `PRONOSTICO_MINIMO_DIAS`). |
| RN-13 | Cumple | El precio sugerido nunca baja del costo y la pantalla muestra la ganancia por pieza. |
| RN-14 | Cumple con ajuste | Si un solo día se vendió la mitad o más de todo lo del producto, se ajusta. La regla habla de "50 % del stock", pero el sistema no guarda el stock de cada día, así que se usa el total vendido del periodo. |
| RN-15 | Cumple | Sin historia suficiente se muestra "Datos insuficientes", nunca un cero. La regla remite a "RN-17", que parece ser un error: debería ser RN-12. |
| RN-16 | Cumple | Aviso visible de que son estimaciones y la decisión es del tendero. |
| RN-17 | Cumple con ajuste | Ver "Decisiones" más abajo. |
| RN-18 | Cumple | Ninguna pantalla ni acción se abre sin sesión. |
| RN-19 | Cumple | Dar de baja un producto pide una doble confirmación. |
| RN-20 | Cumple | Las llaves de IA se guardan cifradas en la base de datos y las contraseñas con PBKDF2. |
| RN-21 | Cumple | El asistente solo recibe texto (el dictado de voz también se convierte a texto) o botones. |
| RN-22 | Cumple | Fuera de la tienda responde con un mensaje estándar y ejemplos. |
| RN-23 | Cumple con ajuste | Ver "Decisiones" más abajo. |
| RN-24 | Cumple | El botón de cobrar se deshabilita al primer clic y el servidor bloquea la venta para que nunca se cobre dos veces. |

## Decisiones que les tocan

**RN-17 y RN-23 contra RF-AVI02.** Las dos reglas dicen que el asistente es de solo lectura y que no puede agregar, modificar ni eliminar nada. Pero RF-V01 y RF-AVI02 piden que agregue productos a la caja por frase, y el sistema funciona así. Lo que sí se cumple es el espíritu de las reglas: el modelo de lenguaje no tiene acceso a la base de datos ni escribe SQL; solo puede escoger entre una lista fija de funciones del programa, que son las mismas que usa la interfaz, con las mismas validaciones, y las acciones irreversibles piden confirmación. Conviene reescribir las dos reglas con esa idea ("el asistente solo ejecuta funciones validadas del sistema, nunca consultas ni escrituras directas en la base de datos"). Si la regla se mantiene literal, habría que quitar las acciones del asistente, y eso rompe el requisito de vender por lenguaje natural.

**RN-20.** Las llaves se guardan cifradas (con Fernet y una clave que sale de `DJANGO_SECRET_KEY`). Hay una condición importante: la `SECRET_KEY` tiene que ser fija. Si cambia, las llaves guardadas ya no se pueden leer y hay que volver a capturarlas con `python manage.py configurar_ia`.

**RF-S05.** El requisito habla de "mini tutoriales contextuales". El recorrido guiado se quitó porque lo pidieron así, y el video lo van a grabar ustedes. Conviene cambiar el texto a "ayuda por módulo, ejemplos en pantalla y un video de bienvenida".

**RNF-06 y RNF-08.** Un tiempo de respuesta de 3 segundos con un servicio externo y una disponibilidad de 99.5 % no se pueden garantizar con un prototipo. Conviene presentarlos como objetivos que se miden en las pruebas, o reescribirlos.

**RNF-02.** Si el profesor insiste en "colores cálidos", se puede mostrar que el fondo y las superficies son cálidos y claros, y que los colores de cada módulo son acentos con significado.
