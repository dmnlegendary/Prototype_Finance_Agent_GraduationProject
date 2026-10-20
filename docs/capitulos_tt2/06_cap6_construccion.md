# Capítulo 6. Construcción del software

## 6.1 Entorno y herramientas

Para programar el sistema usamos Visual Studio Code como editor. Es gratuito, ligero y tiene extensiones para Python y para las plantillas de Django, así que podíamos escribir, probar y revisar el código en un mismo lugar. El lenguaje del servidor es Python (usamos la versión 3.12), porque es el que mejor conocemos y porque tiene bibliotecas para los cálculos y para conectarse a las APIs de inteligencia artificial sin tener que mezclar lenguajes.

Sobre Python se montó Django, un framework web que organiza el proyecto en modelos, vistas y plantillas, y que ya trae resuelto el manejo de sesiones, las contraseñas y la protección contra ataques comunes [4]. Usamos la versión 5.1 o posterior, porque algunas restricciones de la base de datos que definimos solo existen desde esa versión. Para guardar la información se eligió PostgreSQL, un gestor de bases de datos relacional que atiende varias consultas a la vez sin bloquear los datos; si no se configura, el sistema funciona con SQLite, lo que sirve para probarlo rápido en cualquier computadora.

La parte visual se hizo con HTML, hojas de estilo propias y JavaScript sin frameworks. Solo las pantallas de registro e inicio de sesión usan Bootstrap, y en todo el sistema se usan sus íconos. Para el pronóstico se usó la biblioteca statsmodels, y para hablar con la IA los paquetes oficiales de OpenAI y de Google. El código se versionó con Git y se guardó en GitHub [2].

## 6.2 Módulo de ventas

El módulo de ventas es la pantalla que más se usa y la que más rápido tiene que responder, porque el tendero la maneja con el cliente enfrente. Por eso se diseñó para que cobrar tome la menor cantidad posible de pasos. En la parte de arriba está el buscador de productos, en el centro la caja con su lista y abajo el total con los botones para cancelar y cobrar.

### 6.2.1 Dos cajas y cantidad escrita

Una de las situaciones más comunes en una tienda es que el cliente pida varias cosas y se vaya por otra antes de pagar. Para no detener la fila, el sistema tiene dos cajas independientes que se cambian con un clic. El primero queda en espera, tal como estaba, mientras se cobra al siguiente cliente. Las cajas no se guardan solo en la pantalla sino en la base de datos, cada uno como una venta "en curso", así que si se recarga la página o se cierra el navegador no se pierde lo que se había capturado.

Para la cantidad, además de los botones de más y menos, se puede escribir el número directamente en la caja. Esto es útil cuando se venden muchas piezas del mismo producto, por ejemplo 90 dulces, y evita tener que dar clic decenas de veces. Antes, cada clic en los botones recargaba toda la página, lo que hacía lenta la venta de productos en cantidad. Ahora esas operaciones se comunican con el servidor en segundo plano y la pantalla no se vuelve a cargar.

### 6.2.2 Búsqueda y código de barras

La búsqueda de productos no pide que el nombre esté escrito exactamente igual. Ignora acentos y mayúsculas, no importa el orden de las palabras, acepta plurales y partes del nombre, y tolera errores de dedo: si se escribe "jbon" se encuentra "jabón". El tendero puede moverse entre los resultados con las flechas, agregar el primero con Enter y cerrar la lista con Escape. Esta misma búsqueda la usa el asistente cuando le piden agregar un producto.

También se pueden usar lectores de código de barras. Los que se conectan por USB o Bluetooth se comportan como un teclado: escriben el número y mandan un Enter. El sistema reconoce ese número, busca el producto con ese código y lo agrega. Si el código no existe, avisa y ofrece dar de alta el producto con ese código ya capturado o cobrarlo como producto no encontrado.

Para los productos a granel, como frijol o azúcar, el sistema pide la cantidad en gramos y la convierte a kilos para el cálculo. Por ejemplo, 350 g de un producto que cuesta 40 pesos el kilo se cobran en 14 pesos.

### 6.2.3 Productos no encontrados

En una tienda siempre llegan productos que todavía no se han dado de alta, o que se venden muy pocas veces. Para que la venta no se detenga, la pantalla tiene un botón "No encontrado", que pide solo el nombre y el precio y agrega el producto a la caja. El sistema lo guarda con una marca de "pendiente de validar" y evita crear dos veces el mismo si se vende otra vez con el mismo nombre. Para ahorrar tiempo, los nombres usados hace poco aparecen como botones para elegirlos con un clic.

Como todo lo que se vende se tuvo que comprar antes, el sistema también avisa en Finanzas que esos productos no tienen precio de compra. Ahí se les captura el costo, y así la utilidad de esas ventas queda bien calculada y no hay pesos que se vendan sin reflejar su costo.

### 6.2.4 Regla de oro

Definimos como regla de oro que no se puede vender un producto del que no hay existencias, porque si se permite, el inventario se llena de números negativos y los reportes dejan de servir. Al cobrar, el servidor revisa todos los productos de la caja antes de descontar cualquiera, y bloquea esos registros mientras tanto, para que dos ventas al mismo tiempo no se lleven la misma última pieza. Si falta algo, la venta no se hace y el sistema responde con un error. Para que un doble clic con internet lento no cobre dos veces la misma venta, el botón de cobrar se deshabilita en cuanto se aprieta y, además, el servidor bloquea la venta mientras la cobra y rechaza un segundo cobro de una venta que ya está cobrada.

El problema es que el tendero a veces sí tiene el producto en la mano, solo que todavía no registró la mercancía que acaba de llegar. Por eso, cuando salta esta regla, la pantalla muestra un aviso que pregunta cuántas piezas (o gramos, si es a granel) llegaron y a qué precio de compra. Con eso el sistema agrega la existencia, registra la compra en los gastos y deja continuar con el cobro, todo sin salir del mostrador.

### 6.2.5 Ticket de venta

Al cobrar se genera el ticket con un folio consecutivo por tienda, la fecha y la hora, el nombre y la ubicación del negocio, el detalle de los productos con sus cantidades y precios, y el total. Se muestra en una ventana encima de la pantalla de venta, que no la bloquea, y se puede imprimir con la opción normal del navegador. Cada renglón del ticket guarda el precio y el costo que tenía el producto en ese momento, de modo que si después cambia el precio, las ventas anteriores no se modifican (sección 7.2). Además de esto, la pantalla de historial permite consultar las ventas anteriores y volver a abrir cualquier ticket.

## 6.3 Auxiliar de inventario

El auxiliar de inventario reemplaza la costumbre de revisar el anaquel a ojo por un registro que se actualiza solo con cada venta y cada compra. Su objetivo es que el tendero sepa qué tiene, qué se está acabando y cuánto le costó.

### 6.3.1 Alta y edición de productos

Para dar de alta un producto se piden pocos datos: nombre, una descripción breve, precio de compra, precio de venta, cuántas piezas hay, el mínimo que no quiere bajar (el sistema propone 5) y la categoría, que son obligatorios, y de forma opcional el proveedor y el código de barras. Todo producto lleva una categoría válida; los que llegan de una importación sin categoría se guardan en "Otros". El sistema valida que el precio de venta nunca sea menor al precio de compra, tanto al dar de alta y editar como al resurtir (si el proveedor subió el precio, en ese mismo formulario se sube también el precio de venta), al importar un CSV y cuando el asistente cambia un precio. Cada producto lleva un ícono, que el tendero elige de una lista o que el sistema asigna solo a partir del nombre (por ejemplo, "Coca" lleva un refresco y "Leche" un vaso de leche) o, si no lo reconoce, el de su categoría. El stock ideal tampoco se captura a mano: es el promedio de las existencias que había después de cada vez que se cargó mercancía, de modo que si tras tres resurtidos quedaron 24, 26 y 29 piezas, el ideal es 26. El sistema valida que los números no sean negativos y que el código de barras no se repita dentro de la misma tienda. Mientras se capturan el costo y el precio, una barra muestra el margen de ganancia, para que se vea de inmediato si el precio es razonable.

Las piezas con las que arranca el producto se registran solas como una compra de mercancía, y esa compra aparece en el historial de gastos. Gracias a esto el tendero no tiene que capturar la misma información en dos lugares. Cuando se edita un producto, el sistema pide un motivo del cambio (por ejemplo, "subió el proveedor") y lo guarda en el historial del producto.

Los productos a granel se marcan con una casilla. Se guardan en kilos con tres decimales, se muestran en kilos en el inventario y se venden en gramos en el mostrador.

### 6.3.2 Importación de productos desde CSV

Capturar cientos de productos uno por uno es lo que más desanima a un tendero al empezar. Por eso el sistema permite importar el catálogo desde un archivo CSV. El archivo debe traer cuatro columnas obligatorias, que son producto, cantidad, precio de compra y precio de venta, y puede traer además categoría, código de barras y si es a granel. Hay una plantilla para descargar. Si falta alguna de las columnas obligatorias, el archivo no se carga.

Antes de guardar nada, el sistema muestra una pantalla de revisión que separa los productos en cuatro grupos: los que ya existen en el inventario (se les suman las piezas), los que se parecen a alguno que ya existe (el tendero decide si es el mismo), los pendientes de validar, que se completan con los datos del archivo, y los que no existen. Estos últimos no se agregan solos: se le avisa al tendero que no están en su inventario y solo se dan de alta si él lo confirma. Las piezas importadas se registran como una sola compra de mercancía.

### 6.3.3 Semáforo de reabastecimiento y alertas

Para saber qué hay que resurtir sin leer una tabla de números, los productos se marcan con un semáforo. Cada producto tiene un mínimo y un stock ideal. Se pinta de amarillo cuando queda la mitad del stock ideal, de naranja cuando queda una cuarta parte y de rojo cuando llega al mínimo. Si el tendero no capturó el stock ideal, el sistema usa cuatro veces el mínimo. Los productos con existencia suficiente no llevan color.

Dentro de cada color, las alertas se ordenan para que arriba quede lo que se acaba primero, según lo que vende cada producto: para cada uno se calculan las unidades vendidas en las últimas cuatro semanas, cuántas vende por semana y para cuántos días alcanza lo que queda. Los productos que no se han vendido en ese tiempo van al final de su color.

Los avisos se ven en tres lugares. En el inventario, cada renglón lleva la marca de su color. En el menú de arriba hay una campana con el número de productos en alerta, que cambia de color según la urgencia y se ve en todas las pantallas. Y al entrar al sistema aparece un aviso si hay productos en rojo. La pantalla de alertas permite filtrar por color y buscar un producto escribiendo, y carga los resultados de 20 en 20 con un botón de "Ver más", para que no se vuelva lenta cuando hay muchos productos.

### 6.3.4 Proveedores y categorías

Las categorías (bebidas, lácteos, botanas, etcétera) sirven para ordenar el catálogo y filtrar. Los proveedores se registran con su nombre, teléfono y correo, y se les asignan las categorías que surten. Un producto puede ligarse a un proveedor, y de esa forma el tendero sabe a quién llamar cuando algo está en rojo. Para que nadie empiece desde cero, el sistema trae cargadas 20 categorías de productos, un catálogo de 186 productos de abarrotes con su ícono y precio sugerido, y, para cada tienda nueva, 24 proveedores comunes (Coca-Cola FEMSA, Bimbo, Lala, Sabritas, Procter & Gamble, entre otros, ya ligados a las categorías que surten) y 19 categorías de gastos, cada una marcada como fija o variable para que al elegirla se proponga el tipo de gasto. Como son muchas opciones, todas las listas largas (categorías, proveedores, íconos y categorías de gasto) se muestran recogidas con las tres primeras y un botón "Mostrar más"; lo que el tendero ya eligió siempre queda a la vista.

### 6.3.5 Historial de cambios y compra de mercancía

Cada vez que cambian las existencias de un producto, ya sea por una venta, una compra de mercancía, una merma o un ajuste de conteo, el sistema guarda un movimiento en el kardex, con la cantidad que cambió, cuántas piezas quedaron y el motivo. Ningún cambio de existencias queda sin evidencia, y los movimientos no se editan ni se borran. En la pantalla de Movimientos se pueden filtrar por producto, tipo y fechas, y se descargan como un archivo CSV que sirve como dataset para el análisis. Aparte, cada vez que se edita un producto queda un renglón en su historial de cambios con el motivo. Cuando el tendero resurte, indica cuántas piezas llegaron y a qué precio de compra. El sistema suma las piezas, abre un lote con lo que costó esa compra y la registra como gasto. Los lotes funcionan con el método PEPS (primeras entradas, primeras salidas): si la coca se compró ayer a 15 pesos y hoy a 17, las piezas de ayer se venden primero con costo de 15 y las de hoy con costo de 17, y una venta que cruza los dos lotes guarda el costo promedio de las piezas que de verdad salieron. Así, aunque el proveedor suba el precio, la utilidad de cada venta se calcula con lo que costó la mercancía vendida. El costo que se muestra en el producto, y con el que se sugieren los precios, es el de la última compra, y cada renglón del kardex guarda además el costo por pieza del movimiento.

Cuando un producto se da de baja no se borra, solo se desactiva, para que sus ventas anteriores sigan existiendo en los reportes, y el sistema pide una doble confirmación antes de hacerlo. El catálogo se muestra de 20 en 20 productos, con el botón "Ver más", y tiene un buscador y un filtro por categoría. Cuando una tienda se registra, además, puede elegir productos de un catálogo precargado y capturar cuántas piezas tiene de cada uno, su costo y su precio, para no empezar con el inventario vacío.

## 6.4 Agente financiero

El agente financiero convierte las ventas y los gastos en números que el tendero pueda entender y usar para tomar decisiones. Esta parte la hicimos siguiendo las fórmulas que se definieron en el análisis del proyecto, y todas las pantallas (inicio, reportes, punto de equilibrio y precios) usan las mismas funciones para que los números siempre coincidan.

### 6.4.1 Pantallas del agente financiero

La pantalla de inicio muestra un resumen del mes con las ventas, la utilidad y el efectivo, y desde ahí se llega a las demás secciones. En el registro de gastos se capturan los gastos de la tienda, que pueden ser fijos (renta, luz) o variables (bolsas, flete), y se les puede asignar una categoría propia. Cada gasto lleva además el mes al que corresponde, que por defecto es el mes actual pero se puede cambiar: la luz de septiembre que se paga en octubre se registra como de septiembre, y los reportes la cuentan en ese mes. Así los números de cada mes reflejan lo que realmente se gastó en ese mes y no cuándo se capturó el recibo. Los reportes financieros se pueden ver de los últimos 1, 3, 6 o 12 meses, o de un rango de meses que escoge el tendero (hasta 24), con gráficas de ingresos y egresos y de la utilidad. El sistema recuerda el último periodo que se eligió. Debajo de las gráficas aparecen alertas y sugerencias concretas: un gasto mucho más alto de lo normal, los meses en que se perdió dinero, gastos que subieron más de 20 % contra el mes anterior, un margen operativo menor a 10 % y los productos de baja rotación. Además hay un reporte de ventas, con filtro por fechas, que muestra cuánto se vendió y se ganó, el ticket promedio, los productos que más se vendieron y los que más ganancia dejaron, las ventas por categoría y las ventas de cada día. También hay una sección de productos de baja rotación, que se carga por lotes, otra de punto de equilibrio, otra de precios sugeridos y la de pronóstico de ventas, que se explica en la sección 6.6. Tanto el inicio como los reportes tienen un botón que le pide a la IA una explicación de los números en palabras sencillas. Si hay ventas de productos sin precio de compra, la pantalla lo avisa, porque en ese caso la utilidad se ve más alta de lo real.

### 6.4.2 Fórmulas implementadas

El flujo de efectivo es el dinero que realmente entró y salió de la tienda en un periodo. Se calcula restando a los ingresos por ventas los gastos operativos y las compras de mercancía.

```
Flujo de efectivo = ingresos - gastos operativos - compras de mercancía
```

Si en un día se vendieron 6,500 pesos, se pagaron 200 pesos de gastos (por ejemplo, bolsas y una parte de la luz) y se compraron 1,800 pesos de mercancía, el flujo de efectivo es de 4,500 pesos. Se usa en el inicio y en los reportes.

La utilidad neta es lo que le queda al tendero después de restar el costo de lo que vendió, los gastos y el impuesto. El costo de ventas se calcula con el costo que tenía cada producto cuando se vendió.

```
Utilidad neta = ingresos - costo de ventas - gastos operativos - ISR
Margen operativo = (ingresos - costo de ventas - gastos operativos) / ingresos x 100
```

Con ingresos de 90,000 pesos, costo de ventas de 65,000 y gastos de 12,000, la utilidad antes de impuestos es de 13,000 pesos y el margen operativo es de 14.4 %. Estas dos fórmulas se usan en los reportes.

El margen de ganancia de un producto indica qué parte del precio de venta es ganancia. Se muestra al dar de alta o editar un producto.

```
Margen = (precio de venta - costo) / precio de venta x 100
```

Un refresco que se compra en 14 pesos y se vende en 19 deja un margen de 26.3 %.

El ISR de RESICO se calcula como una estimación para que el tendero sepa cuánto debe apartar. La ley fija una tasa que sube conforme aumentan los ingresos, entre 1.00 % y 2.50 % [5]. El sistema toma los ingresos de los últimos 12 meses para escoger la tasa de la tabla anual (1.00 % hasta 300,000 pesos, 1.10 % hasta 600,000, 1.50 % hasta 1,000,000, 2.00 % hasta 2,500,000 y 2.50 % hasta 3,500,000) y la aplica a los ingresos del periodo. Esto solo se hace si la tienda indicó que está en RESICO.

```
ISR estimado = ingresos del periodo x tasa
```

Si una tienda tuvo 45,000 pesos de ingresos en el mes y 540,000 en el último año, le corresponde la tasa de 1.10 % y el ISR estimado es de 495 pesos. Cabe aclarar que la ley calcula la tasa con los ingresos de cada mes y no con los del año, por lo que esta es una aproximación, y por eso la mostramos siempre como estimación y no como el impuesto oficial.

El punto de equilibrio es cuánto hay que vender para no ganar ni perder. Como en una tienda se venden productos con márgenes muy distintos, se calcula por categorías, tomando como base la mezcla de ventas de los últimos tres meses y los gastos fijos del mes.

```
r_i  = (precio promedio_i - costo promedio_i) / precio promedio_i
PE   = gastos fijos / suma(w_i x r_i)
PE diario = PE / días del mes
```

Aquí w_i es la proporción de las ventas que representa la categoría i. Por ejemplo, con gastos fijos de 30,000 pesos y tres categorías, bebidas (50 % de las ventas y margen de 40 %), lácteos (20 % y 33.3 %) y abarrotes (30 % y 33.3 %), la suma ponderada es 0.50 x 0.40 + 0.20 x 0.333 + 0.30 x 0.333, que da 0.367, y el punto de equilibrio es de 30,000 / 0.367, es decir, unos 81,818 pesos al mes. Repartido por categoría, son unos 40,909 en bebidas, 16,364 en lácteos y 24,545 en abarrotes, y dividido entre los días del mes da la meta diaria que se muestra en pantalla.

Por último, el precio sugerido indica a cuánto debería venderse un producto para ganar el margen que se busca.

```
Precio sugerido = costo / (1 - margen)
```

Con un costo de 35 pesos y un margen de 25 %, el precio sugerido es de 35 / 0.75, es decir, 46.67 pesos. El margen se puede escoger de dos maneras. En la primera, el tendero escribe el margen que quiere. En la segunda, el sistema lo calcula para que las ventas alcancen a pagar los gastos del negocio: primero se ve qué parte de lo vendido en los últimos tres meses se fue en gastos y después se le suma una ganancia extra que escoge el tendero.

```
Gastos sobre ventas = gastos del negocio / ventas x 100
Margen para cubrir gastos = gastos sobre ventas + ganancia extra
```

Si en los últimos tres meses se vendieron 100,000 pesos y se gastaron 20,000 en gastos del negocio, de cada 100 pesos vendidos se van 20 en gastos. Si el tendero quiere además una ganancia extra de 10 %, el margen debe ser de 30 %, y un producto que le cuesta 15 pesos se sugiere en 15 / 0.70, es decir, 21.43 pesos. Es una estimación que supone que se venderá lo mismo que en los meses anteriores y que el cambio de precio no modifica las ventas. El tendero puede aceptar el precio sugerido con un botón, ajustarlo o rechazarlo, y cuando lo acepta se actualiza en el producto y queda anotado en su historial.

### 6.4.3 Criterio contable: la compra de mercancía no es un gasto

Una confusión muy común es registrar como gasto lo que se le paga al proveedor. Pero cuando el tendero compra mercancía no gasta ese dinero, solo lo cambia por inventario, y el costo se refleja hasta que el producto se vende. Las normas de información financiera en México tratan así a los inventarios, y mandan reconocer su valor como costo de ventas en el momento en que se reconocen los ingresos de esa venta [6].

Por esa razón, en el sistema la compra de mercancía se registra al cargar o resurtir el inventario, aparece como un tipo aparte en el historial de gastos y no se puede capturar como un gasto cualquiera. Cuenta para el flujo de efectivo, porque ese dinero sí salió de la caja, pero no se resta de la utilidad, porque ya se descuenta en el costo de ventas y se contaría dos veces. Si se registrara como gasto una compra grande de refrescos, el punto de equilibrio saldría inflado y los reportes mostrarían pérdidas que no existen.

## 6.5 Base de datos implementada

Las funciones que agregamos durante el desarrollo, como la compra de mercancía automática, los dos cajas, la importación desde CSV o el trabajo sin conexión, no estaban en el diseño inicial. Son trabajo extra que fue necesario hacer para que el sistema realmente le sirviera a un tendero, y varias de ellas obligaron a crear tablas y campos nuevos. En esta sección se describe cómo quedó la base de datos al final, y el diagrama entidad-relación actualizado está en el capítulo 4.

### 6.5.1 Tablas finales, relaciones e índices

La base de datos quedó con 18 tablas propias del sistema, además de las que Django crea para sus sesiones y permisos. Se resumen en la Tabla 6.1.

Tabla 6.1. Tablas del sistema.

| Tabla | Para qué sirve |
|---|---|
| accounts_usuario | Usuario de la tienda: nombre, teléfono y correo |
| accounts_negocio | Datos de la tienda: nombre, alcaldía o lugar, años de operación, si está en RESICO y RFC |
| inventario_categoria | Categorías de productos |
| inventario_proveedor | Proveedores de cada tienda y las categorías que surten |
| inventario_productocatalogo | Catálogo precargado que se ofrece al registrarse |
| inventario_producto | Productos de la tienda: costo, precio, existencias, mínimo, stock ideal, si es a granel y su código de barras |
| inventario_historialmodificacionproducto | Historial de cambios de cada producto, con su motivo |
| inventario_movimientoinventario | Kardex: cada cambio de existencias con su origen (venta, entrada, merma o ajuste) |
| inventario_loteinventario | Lotes de compra con su cantidad restante y su costo por pieza (PEPS) |
| ventas_venta | Ventas: folio, estado (en curso, cobrada o cancelada), número de caja y total |
| ventas_itemventa | Renglones de cada venta, con cantidad, precio y costo del momento |
| finanzas_categoriagasto | Categorías de gasto que crea el tendero |
| finanzas_gastooperativo | Gastos: fijos, variables y compras de mercancía, con el mes al que corresponde cada uno |
| avi_historialconversacion | Mensajes del chat con el asistente |
| avi_resumendiario | Resumen de IA de cómo le fue a la tienda cada día |
| avi_explicacionia | Explicaciones de IA del inicio y de los reportes |
| core_operacionsincronizada | Operaciones hechas sin internet que ya se sincronizaron |
| core_llaveia | Llaves de acceso a la IA, guardadas cifradas |

Casi todas las tablas se relacionan con la tienda (accounts_negocio), de modo que cada tienda solo ve sus propios datos. Un producto pertenece a una tienda, a una categoría y, opcionalmente, a un proveedor. Una venta tiene muchos renglones, y cada renglón apunta a un producto.

Para que la base de datos cuide sus propias reglas, definimos restricciones directamente en ella. No puede haber dos ventas con el mismo folio en una tienda, no puede haber dos productos con el mismo código de barras dentro de la misma tienda, y la cantidad de un renglón de venta debe ser mayor que cero. Tampoco pueden ser negativos los precios, los totales ni los gastos. Además, solo puede existir una venta en curso por cada caja, de modo que dos pestañas del navegador no creen cajas duplicados.

Se crearon índices en las consultas más frecuentes: productos por tienda y estado, productos por tienda y nombre, ventas por tienda, estado y fecha, gastos por tienda y fecha, y conversaciones por tienda y fecha. La búsqueda de productos no depende de un índice especial, porque se hace en memoria sobre el catálogo de la tienda, que se guarda en el caché.

### 6.5.2 Caché por negocio

Calcular las alertas, las ventas de hoy o el resumen financiero cada vez que se abre una pantalla o se manda un mensaje al asistente hacía muchas consultas repetidas. Para evitarlo se usó el caché de Django en memoria [4]. Los resultados más pedidos (conteo de alertas, catálogo para el buscador, ventas de hoy, resumen financiero, punto de equilibrio y el contexto que se le da a la IA) se guardan por tienda y por día, y duran como máximo cinco minutos.

En lugar de dejar pasar el tiempo para que se actualicen, el caché se limpia cuando algo cambia. Cada vez que se guarda o se borra un producto, una venta o un gasto, una señal de Django borra los datos guardados de esa tienda, de modo que el siguiente cálculo ya trae la información nueva. Una limitación es que este caché vive dentro del proceso de Python, por lo que funciona bien con un solo servidor y tendría que cambiarse por uno compartido, como Redis, si algún día se usan varios.

### 6.5.3 De CSV a PostgreSQL

Al principio los datos se leían de archivos CSV y de una base SQLite. Para probar los modelos de pronóstico usamos un archivo con el historial de ventas de una tienda: 63,411 renglones de ventas, de 16,131 tickets y 2,480 productos distintos, con fechas desde el 30 de mayo de 2025 hasta el 7 de abril de 2026. [CONFIRMAR de dónde salió este historial y si se puede mencionar su origen] Cada vez que alguna pantalla necesitaba esos datos, había que leer todo el archivo, y las pantallas empezaron a tardar demasiado.

Pasamos los datos a PostgreSQL porque SQLite bloquea el archivo completo cuando alguien escribe, no maneja bien varias consultas a la vez y no trae todas las restricciones que queríamos, mientras que PostgreSQL está hecho para eso. Además, en la nube se ofrece como servicio, lo que facilita el despliegue que planeamos. La migración se hizo en cuatro pasos: primero se definieron los modelos en Django, después se generaron y aplicaron las migraciones sobre PostgreSQL, luego se cargaron los datos del CSV con un comando de importación que los inserta en paquetes de mil dentro de una sola transacción [CONFIRMAR cómo se cargó este archivo en concreto], y por último se probó que las pantallas leyeran de la base de datos.

La Tabla 6.2 compara los tiempos de las mismas operaciones con cada forma de guardar los datos. [COMPLETAR con tiempos medidos en su equipo; las instrucciones para medirlos están en el archivo de notas]

Tabla 6.2. Tiempos de respuesta según el almacenamiento.

| Operación | CSV | SQLite | PostgreSQL |
|---|---|---|---|
| Buscar un producto por nombre | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] |
| Registrar una venta de 5 productos | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] |
| Calcular el punto de equilibrio | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] |
| Cargar el historial de 63,411 renglones | [COMPLETAR] | [COMPLETAR] | [COMPLETAR] |

## 6.6 Modelos de pronóstico de ventas

El pronóstico de ventas estima cuántas piezas de un producto podrían venderse la semana siguiente para apoyar la decisión de cuánto comprar. Para facilitar la explicación y mantener una sola metodología de pronóstico, la versión actual del sistema utiliza exclusivamente ARIMA(1,1,1).

### 6.6.1 Datos utilizados y su preparación

Se toman los 10 productos con más unidades vendidas en todo el historial disponible del negocio. De cada uno se arma una serie semanal desde la primera semana con ventas del negocio hasta la última semana registrada. Las semanas en las que no se vendió el producto cuentan como cero, incluso las anteriores a su primera venta registrada, para que todas las series cubran el mismo periodo; por eso el número de semanas depende de los datos cargados y no de una ventana fija. Para determinar si un producto tiene historia suficiente, se cuentan los días desde su primera venta registrada, sin considerar los ceros previos. Si tiene menos de 30 días (configurable), la pantalla dice "Datos insuficientes" y no se estima nada, ni siquiera un cero. Antes de calcular se hace un filtrado ligero sobre el historial utilizado: si un solo día concentra la mitad o más de todas las unidades vendidas, ese día se cambia por el siguiente día más alto para que no engañe al modelo. Como el sistema no guarda cuántas piezas había en cada día, la mitad se mide contra el total vendido del historial.

### 6.6.2 Modelo elegido y justificación

Se eligió ARIMA porque es una familia clásica de métodos para series temporales y permite representar tanto los cambios entre observaciones como la dependencia de los valores y errores anteriores [7], [8]. Esto resulta adecuado para explicar el problema como una secuencia de ventas semanales y deja una estructura conocida para evolucionar posteriormente el análisis.

La implementación actual usa el orden fijo (1, 1, 1): un término autorregresivo, una diferenciación y un término de media móvil. Se ajusta con la biblioteca `statsmodels`, con `enforce_stationarity=False` y `enforce_invertibility=False`. No se realiza una búsqueda automática del orden ni una optimización comparativa de configuraciones. Por tanto, la elección de ARIMA como modelo único es una decisión metodológica del proyecto; no se afirma que haya obtenido el menor error en datos reales.

### 6.6.3 Métrica de evaluación

El error absoluto medio se calcula como el promedio de las diferencias, sin importar el signo, entre lo que realmente se vendió y lo que el modelo estimó.

```
MAE = (1 / n) x suma de |ventas reales - ventas estimadas|
```

La prueba actual utiliza las últimas cuatro semanas disponibles como bloque de evaluación y entrena ARIMA con todas las semanas anteriores. Por ejemplo, si hay 45 semanas, usa 41 para entrenamiento y cuatro para prueba. La pantalla muestra el MAE en unidades por semana. El pronóstico para la semana siguiente se obtiene volviendo a ajustar ARIMA con todo el historial disponible.

Las pruebas unitarias usan datos sintéticos y verifican el funcionamiento del cálculo, la preparación de la serie y la respuesta de la pantalla. No constituyen una evaluación de precisión con ventas reales. En una medición exploratoria anterior, con un patrón sintético de 12 semanas y 10 productos, ARIMA obtuvo un MAE de 0.79 unidades semanales; una regresión lineal obtuvo 0.75 y Holt-Winters 1.38. Ese ejemplo sintético no demuestra que ARIMA sea el más preciso; se conserva únicamente como antecedente de comparación y no forma parte de la funcionalidad actual.

Tabla 6.3. Métrica de ARIMA en el fixture sintético exploratorio (no representa ventas reales).

| Productos evaluados | Semanas de entrenamiento | Semanas de prueba | Modelo vigente | MAE de referencia |
|---:|---:|---:|---|---:|
| 10 | 8 | 4 | ARIMA(1,1,1) | 0.79 unidades/semana |

### 6.6.4 Integración al sistema y limitaciones

Al abrir la pantalla, el sistema obtiene la serie semanal de cada producto elegible y ajusta ARIMA(1,1,1). Muestra la última venta semanal, el pronóstico para la semana siguiente, el cambio porcentual, el MAE y un nivel de confianza orientativo. La confianza compara el MAE con el promedio semanal reciente: alta hasta 25 %, media hasta 50 % y baja por encima de ese umbral. No representa una probabilidad estadística. Un botón permite solicitar a la IA una explicación en lenguaje sencillo. El modelo se ajusta nuevamente con las ventas recientes cada vez que se calcula el pronóstico; no se guarda un modelo entrenado.

Tiene varias limitaciones. Solo pronostica productos con al menos 30 días de historia; utiliza todas las semanas disponibles y rellena con cero aquellas sin ventas registradas. Esto presupone que la ausencia de un registro significa que no hubo ventas, lo cual puede ser falso si el historial está incompleto. El CSV de referencia contiene fechas desde el 30 de mayo de 2025 hasta el 7 de abril de 2026; se importaron 63,409 de sus 63,411 renglones. Como el archivo no contiene costos ni existencias, los 2,298 productos creados desde ventas están pendientes de validar y tienen costo e inventario inicial en cero. El MAE de las últimas cuatro semanas es una evaluación corta y exploratoria, no una garantía de error futuro. La configuración ARIMA(1,1,1) es fija y aún no se ha calibrado con datos reales de múltiples tiendas. El modelo solo observa ventas pasadas: no incorpora promociones, días festivos, clima, faltantes de inventario ni cambios de precio. Por eso el resultado es una estimación de apoyo y la decisión de compra sigue siendo del tendero.

## 6.7 Asistente Virtual Inteligente (AVI) y APIs utilizadas

Hay una diferencia entre un asistente y un agente. Según Russell y Norvig, un agente es algo que percibe su entorno y actúa sobre él para lograr un objetivo [9]. Un asistente que solo contesta preguntas no actúa, mientras que uno que además ejecuta acciones se acerca más a un agente. En nuestro caso, el chat es un asistente con capacidad de acción: espera instrucciones del tendero, pero puede hacer cosas reales en el sistema, como agregar productos a la caja, cobrar o registrar un gasto. Por otro lado, el agente financiero se parece más a un agente porque revisa los datos de la tienda por su cuenta y avisa, por ejemplo, con el resumen del día anterior y con las alertas de productos en rojo, sin que alguien se lo pida. [DECIDIR cómo quieren clasificar cada parte en 2.3.6 y que coincida con este texto]

### 6.7.1 APIs de Gemini y de OpenAI

Hacer funcionar un modelo de lenguaje grande dentro de la computadora de una tienda no es viable, porque necesita mucha memoria y una tarjeta gráfica potente que un equipo básico no tiene. Por eso el sistema usa dos servicios por internet. El principal es Gemini 2.5 Flash, de Google, y el de respaldo es GPT-4o mini, de OpenAI. Los dos se eligieron por su bajo costo y su rapidez.

Las llaves de acceso nunca van en el código ni en el navegador. Se guardan en el archivo `.env` del servidor y solo el servidor se comunica con las APIs. Al modelo se le envían el mensaje del tendero, un resumen corto de la tienda (su nombre, las ventas del día, lo que hay en las cajas y cuántos productos están en alerta) y los resultados de las funciones que consulta. No se le envían el teléfono, el correo ni la contraseña del tendero. Las llamadas tienen un tiempo máximo de espera de 30 segundos, y si fallan por una causa pasajera, como saturación del servicio, el sistema espera unos segundos y reintenta hasta tres veces. El costo depende de cuántas palabras se envían y reciben, y el presupuesto contemplado está en el capítulo 3. [CONFIRMAR]

### 6.7.2 Llamadas a funciones

El asistente no entra directamente a la base de datos. Funciona mediante llamadas a funciones: el sistema le describe al modelo qué acciones existen y qué datos necesita cada una; cuando el tendero escribe algo como "agrega dos cocas", el modelo no contesta con un texto sino con el nombre de la función y los datos que entendió; el servidor valida esos datos, ejecuta la acción y le regresa el resultado al modelo, que lo explica con palabras sencillas [10], [11]. Así el modelo solo puede hacer lo que el programa permite: no tiene acceso a la base de datos ni escribe consultas, solo escoge entre una lista fija de funciones, las mismas que usa la interfaz y con las mismas validaciones.

Hay 25 funciones, que se agrupan según la pantalla donde se usan (Tabla 6.4). Cuando el modelo solo ejecutó acciones, el sistema contesta directamente con el mensaje de la acción y se ahorra la segunda llamada al modelo, con lo que la respuesta es casi inmediata. Las acciones delicadas, como cancelar una venta o dar de baja un producto, piden confirmación antes de hacerse.

Tabla 6.4. Funciones del asistente por pantalla.

| Pantalla | Funciones |
|---|---|
| Ventas | agregar y quitar productos, cambiar cantidad, ver la caja, cobrar, cancelar la venta, agregar un producto no encontrado, ver las últimas ventas y ajustar existencias |
| Inventario | consultar el inventario y las alertas, dar de alta, modificar, ajustar existencias y dar de baja productos, crear categorías, dar de alta y modificar proveedores y consultarlos |
| Finanzas | registrar un gasto, consultar los gastos del mes, el resumen financiero y el punto de equilibrio, y sugerir un precio |
| En todas | buscar un producto y consultar las ventas de hoy |

### 6.7.3 Herramientas por pantalla

Cada vez que se envía un mensaje, la descripción de las funciones también se envía y se cobra. Con las 25 funciones, cada mensaje llevaba alrededor de 4,000 tokens (la unidad con la que se mide y se cobra el texto) solo en descripciones de funciones. [CONFIRMAR la cifra con una medición propia] Para reducirlo, las consultas (ver existencias, alertas, gastos, ventas o finanzas) se mandan siempre, para poder preguntar por cualquier módulo desde cualquier pantalla, pero las acciones que cambian datos solo se mandan las de la pantalla donde está el tendero. Si le piden cambiar algo que se hace en otra pantalla, le dice dónde se hace. Con esto, las funciones que se envían en la pantalla de ventas pesan menos que todas juntas, aunque el ahorro es menor que si se mandaran solo las de la pantalla.

### 6.7.4 Respaldo automático entre proveedores

Si Gemini no responde, por una falla o porque se acabó su cuota, el sistema intenta con ChatGPT sin que el tendero tenga que hacer nada. El orden es siempre el mismo: primero Gemini y luego ChatGPT, y basta con tener la llave de uno de los dos para que funcione. Hay un caso en el que no se cambia de proveedor, y es cuando Gemini ya alcanzó a ejecutar una acción, como agregar un producto a la caja, y falla después. Si en ese momento se intentara con ChatGPT, la acción podría hacerse dos veces, así que en ese caso se avisa del error. Si los dos proveedores fallan, el asistente muestra un mensaje claro de lo que pasó y el resto del sistema sigue funcionando.

### 6.7.5 Historial, resúmenes y dictado de voz

El chat conserva la conversación de las últimas 24 horas. El asistente también recuerda lo que el tendero ya escogió en otras pantallas, como el margen de ganancia que usa para sus precios, de modo que si después le pide un precio sugerido sin decir el margen, usa ese. Cuando le preguntan algo que no tiene que ver con la tienda, no lo contesta y responde con un mensaje estándar que recuerda en qué sí puede ayudar, con tres ejemplos. Antes se borraba cada vez que el tendero cambiaba de pantalla, lo cual era incómodo, así que ahora se guarda en la base de datos y se vuelve a mostrar. De esa conversación, el asistente usa los últimos mensajes para entender frases como "¿y cuánto cuesta ese?". Los mensajes que fallaron no se guardan, para no confundir al modelo.

Además del chat, la IA se usa para dos resúmenes. Al entrar por primera vez en el día, el sistema muestra un resumen de cómo le fue a la tienda el día anterior, que se genera una sola vez y se guarda. El inicio y los reportes tienen un botón que explica los números; esa explicación también se guarda y solo se pide de nuevo a la IA si los números cambiaron.

El tendero puede dictar sus mensajes con el micrófono. El botón funciona como el micrófono de un radio: se mantiene presionado mientras se habla, el texto va apareciendo en el cuadro del chat y al soltarlo se deja de escuchar. Como el reconocimiento de voz es una función del navegador, solo está disponible en Chrome y Edge (Firefox no la incluye) y necesita internet; la primera vez se pide el permiso del micrófono aparte, para que el aviso del navegador no interrumpa el dictado. Esto usa la función de reconocimiento de voz del navegador [12], por lo que no tiene costo adicional, pero depende del navegador y, en algunos, de la conexión a internet. Funciona con el micrófono del equipo o con unos audífonos con micrófono.

## 6.8 Trabajo sin conexión y sincronización

Algunas tiendas tienen un internet que se cae, así que decidimos que lo más importante, que es cobrar, no dependiera de la conexión. Esta función no estaba en el plan original y se agregó por esa razón.

Cuando se pierde la conexión, el sistema lo avisa con una barra en la parte de abajo. Todavía se puede buscar productos en una copia del catálogo que el navegador guarda, armar la caja, cobrar y dar de alta o resurtir productos. Lo que se hace queda en una cola dentro del navegador, y la barra muestra el mensaje de que el sistema se actualizará en cuanto haya internet. Al volver la conexión, la cola se envía sola al servidor. Ahí, cada operación lleva un identificador único, y el servidor guarda cuáles ya recibió, para que una venta no se registre dos veces aunque la conexión se corte a la mitad del envío. El diagrama de secuencia de este proceso está en la sección 4.5.

Para que las pantallas abran aunque no haya internet se usa un service worker, que es un programa del navegador que guarda las páginas y archivos de la aplicación y los entrega cuando no hay red [13]. Mientras no hay conexión, la regla de oro sigue funcionando con las existencias que se conocen en ese momento, y el asistente deja de contestar, porque necesita internet. [CONFIRMAR con una prueba real en el navegador: el service worker no se pudo probar en nuestro entorno de pruebas]

## 6.9 Seguridad y sesiones

Para entrar al sistema hay que iniciar sesión con el teléfono o el correo y una contraseña, y todas las pantallas están protegidas: sin sesión no se ve nada. Las contraseñas no se guardan tal cual, sino que Django las convierte con un algoritmo de cifrado de un solo sentido y con un valor aleatorio distinto para cada usuario [4]. Cada formulario y cada petición del navegador lleva un código de seguridad que impide que otro sitio mande acciones en nombre del usuario, y las cookies de la sesión no pueden ser leídas por scripts del navegador. Además, todas las consultas filtran por tienda, de manera que un negocio nunca ve los datos de otro. El usuario puede eliminar su cuenta y sus datos desde el menú.

Las llaves de las APIs de IA no se guardan en texto plano: se cifran y se guardan en la base de datos local, con una clave que sale de la `SECRET_KEY` del proyecto. Un comando (`configurar_ia`) pide las llaves sin mostrarlas al escribirlas y las guarda ya cifradas; si el sistema se instala en un servidor donde las llaves se ponen como variables de entorno, se usan como respaldo. Por eso la `SECRET_KEY` debe ser fija: si cambia, las llaves guardadas ya no se pueden leer y hay que volver a capturarlas. Para publicar el sistema, un ajuste en el archivo `.env` (`USAR_HTTPS=True`) obliga a usar HTTPS y marca las cookies como seguras, de modo que la contraseña y la sesión nunca viajan en claro. El correo de recuperación de contraseña se imprime en la terminal mientras se desarrolla, y se manda por SMTP de verdad cuando se llena `EMAIL_HOST`. Por último, el sistema solo acepta conexiones desde la misma computadora, que es la configuración correcta mientras se prueba.

## 6.10 Diseño de interfaz

La interfaz se diseñó pensando en que el tendero la usa de pie, rápido y a veces con poca paciencia. Las respuestas de la encuesta (sección 8.3) apuntaron en la misma dirección: un tendero escribió que los colores llamativos en cada botón le ayudarían a ubicar las funciones, y varios pidieron un sistema fácil y sin palabras técnicas. Además, al revisar el prototipo nos dimos cuenta de que había demasiados elementos del mismo color y era difícil saber para qué servía cada uno, así que cambiamos a una paleta en la que cada color significa una cosa en todo el sistema. En la Tabla 6.5 se muestra cuál es.

Tabla 6.5. Paleta de colores del sistema.

| Color | Significado | Dónde se ve |
|---|---|---|
| Morado | Funciones de la inteligencia artificial | Chat del asistente, resúmenes y botones de explicar con IA |
| Amarillo | Búsqueda de productos | Buscadores del mostrador, el inventario y las alertas |
| Naranja | Filtros y categorías | Filtro por categoría, proveedores, tipo de gasto y periodos de los reportes |
| Verde | Ventas | Todo el módulo de ventas: cajas, agregar y cobrar |
| Azul | Inventario | Todo el módulo de inventario |
| Rosa | Agente financiero, como el logo | Todo el módulo de finanzas |
| Rojo | Alertas | Productos en nivel crítico, campana de avisos y falta de internet |

El color principal de las pestañas y los botones cambia según el módulo en el que está el tendero, por lo que saber en qué parte del sistema se encuentra le toma un segundo. La interfaz se adapta al tamaño de la pantalla, para poderse usar desde una computadora, una tableta o un celular.

## 6.11 Tamaño del proyecto

Sin contar las migraciones de la base de datos, el proyecto tiene unas 9,200 líneas de Python en 76 archivos, 2,700 líneas de plantillas HTML, 1,900 de JavaScript y 2,200 de hojas de estilo. [CONFIRMAR corriendo otra vez el conteo antes de entregar] Las pruebas automáticas son cerca de 300 y representan una parte importante de las líneas de Python.
