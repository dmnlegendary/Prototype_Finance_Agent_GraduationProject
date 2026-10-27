# Anexo A. Manual de usuario

Este manual explica cómo usar marIA en la tienda, paso a paso y sin términos técnicos. Está pensado para el tendero que va a cobrar, controlar su inventario y revisar sus finanzas, y puede leerse de corrido o por partes: cada sección se entiende sola. Donde dice «Insertar captura» va una imagen de la pantalla que se describe.

## A.1 Para qué sirve marIA

marIA junta en un solo lugar tres cosas que en una tienda normalmente se hacen por separado: cobrar las ventas, saber qué hay en el inventario y entender cómo va el negocio en dinero. Además trae una asistente, también llamada marIA, a la que se le puede pedir por escrito o con la voz que haga lo mismo que se hace a mano, como agregar un producto a la caja o registrar un gasto, o que conteste dudas como cuánto se vendió hoy.

El sistema se divide en tres módulos que se cambian desde la barra de arriba: el **Módulo de ventas**, el **Auxiliar de inventario** y el **Agente financiero**. Para no perderse, cada módulo tiene su propio color, como se explica en la sección A.3.

## A.2 Crear la cuenta y entrar por primera vez

Para empezar hay que registrarse, y el registro se hace en tres pasos que se ven arriba de la pantalla.

En el primer paso se crea la cuenta con el nombre completo, el teléfono celular, un correo electrónico y una contraseña. Antes de continuar hay que marcar que se aceptan los términos y condiciones y el aviso de protección de datos; el texto se puede leer en el enlace de esa misma casilla, y sin aceptarlo no se crea la cuenta.

[Insertar captura: pantalla de registro con la casilla de términos y condiciones]

En el segundo paso se piden los datos de la tienda: su nombre, la alcaldía donde está (o el nombre del lugar si no es de la Ciudad de México), cuántos años lleva funcionando, si pertenece al régimen RESICO y, de forma opcional, el RFC. El régimen se usa para calcular el impuesto en los reportes, así que conviene contestarlo con cuidado.

En el tercer paso se eligen los productos con los que arranca la tienda. El sistema ofrece una lista de productos comunes de abarrotes, con su ícono, que se puede buscar por nombre o filtrar por categoría. Por cada producto elegido se escribe cuántas piezas hay, cuánto costó cada una y en cuánto se vende; el sistema no deja poner un precio de venta menor al de compra. Si por ahora no se quiere cargar nada, se puede dejar vacío y agregar los productos después. Al terminar se abre la pantalla de ventas.

[Insertar captura: lista de productos para elegir al registrarse]

La primera vez que se entra aparece una ventana con los colores del sistema (sección A.3) y, si ya se configuró, un video corto de bienvenida. Ambos se muestran una sola vez.

Para iniciar sesión en otras ocasiones se escribe el correo o el teléfono y la contraseña. Si la contraseña se olvidó, en esa misma pantalla está el enlace «¿Olvidaste tu contraseña?», que manda un correo para escribir una nueva.

## A.3 Los colores de marIA

Cada color significa siempre lo mismo en todo el sistema, así que basta con fijarse en él para saber dónde se está. El morado es de la inteligencia artificial, es decir, del chat de marIA, de los resúmenes y de las explicaciones. El rosa es del agente financiero, con sus reportes, gastos, punto de equilibrio, precios y pronóstico. El verde es de las ventas: la caja, agregar productos y cobrar. El azul es del inventario. El naranja se usa en las categorías y los filtros, por ejemplo las categorías de productos, las de gastos y los proveedores. El amarillo es de la búsqueda de productos y el rojo avisa de que algo necesita atención, como un producto que está por agotarse.

Esta explicación también aparece en la pantalla de inicio de sesión, en «¿Qué significan los colores de marIA?», y en la ayuda del sistema.

[Insertar captura: ventana de la guía de colores]

## A.4 Módulo de ventas

### A.4.1 Cobrar una venta

La pantalla de ventas es la que más se usa. Arriba están las dos cajas, **Caja 1** y **Caja 2**, y en el centro la lista de lo que se lleva el cliente. Se usan dos cajas para poder dejar una cuenta en espera: si un cliente se va a buscar otra cosa a mitad del cobro, se cambia a la otra caja para atender al siguiente y después se regresa sin haber perdido nada. Cobrar en una caja no mueve la otra, y junto al nombre de cada caja se ve cuántos productos lleva.

Para agregar un producto se escribe su nombre en la barra amarilla de búsqueda. No importan los acentos, el orden de las palabras ni un error de dedo, porque «jbon» encuentra «Jabón». Al presionar **Enter** se agrega el primer resultado, o se toca el que se quiera de la lista. Si la tienda tiene lector de códigos de barras, basta con escanear el producto, ya que el lector «escribe» el código y el sistema lo reconoce solo.

[Insertar captura: pantalla de ventas con productos en la caja]

Para cambiar una cantidad se escribe el número directamente en el cuadro del producto, por ejemplo 90 si se llevan noventa piezas, o se usan los botones de más y de menos. El bote de basura quita el producto de la caja, y antes de quitarlo el sistema pregunta si de verdad se quiere. El total siempre está visible debajo de la lista.

Los productos que se venden a granel, como el frijol o el azúcar, se capturan en gramos. Al tocarlos aparece una ventana donde se escribe cuántos gramos pide el cliente, con atajos de un cuarto, medio y un kilo, y el sistema calcula el importe.

Cuando todo está listo se presiona **Cobrar**. El sistema descuenta las piezas del inventario y avisa abajo en la pantalla con «Venta cobrada», el folio y el total, para no estorbar al siguiente cobro. Con el botón **Ver ticket** de ese aviso se abre el ticket, con su folio, la fecha y la hora, el nombre de la tienda, los productos y el total. El ticket se puede imprimir con la opción normal del navegador. Si se presiona **Cancelar venta**, la caja se vacía sin cobrar nada. Para evitar cobros dobles, el botón de cobrar se desactiva en cuanto se presiona.

[Insertar captura: ticket de una venta]

### A.4.2 Cuando no hay existencias

El sistema no deja vender más de lo que hay en el inventario, porque si se permitiera las existencias quedarían en negativo y los reportes dejarían de ser confiables. Pero tampoco obliga a salir de la pantalla de ventas: si se intenta vender algo de lo que no hay, aparece una ventana que pregunta cuántas piezas llegaron y a qué precio las compró el tendero. Al confirmar, las piezas se suman al inventario, la compra se anota en los gastos y la venta continúa. Si el precio de compra nuevo es mayor que el de venta, la misma ventana pide también el nuevo precio de venta, porque el sistema no permite vender por debajo del costo.

### A.4.3 Productos que no están en el catálogo

Si el cliente pide algo que todavía no se ha dado de alta, el botón **No encontrado** permite cobrarlo de todos modos: se escribe solo el nombre y el precio de venta. Ese producto queda pendiente de validar, y más tarde, en Finanzas, el sistema pide su precio de compra para que la utilidad sea la real.

### A.4.4 Historial de ventas

Con el botón **Historial** se ven las ventas anteriores y se puede volver a abrir el ticket de cualquiera.

### A.4.5 Qué pasa si se va el internet

Si se pierde la conexión, el sistema lo avisa con una barra en la parte de abajo, pero la tienda puede seguir trabajando. Lo que ya estaba en las cajas se conserva, se puede buscar en una copia del catálogo que guarda el navegador, y se puede cobrar. Las ventas, los productos dados de alta y la mercancía resurtida sin conexión se guardan en el dispositivo y se mandan solos cuando regresa el internet, una sola vez cada una. Mientras no hay conexión, los tickets no tienen folio, y lo reciben al sincronizarse. Para que todo esto funcione, las pantallas principales deben haberse abierto al menos una vez con internet.

## A.5 Auxiliar de inventario

### A.5.1 El catálogo y el semáforo

La pantalla principal del inventario muestra los productos de la tienda con su categoría, su precio y sus existencias. A la izquierda de cada existencia hay un color que funciona como semáforo. Rojo significa que el producto llegó a su mínimo y hay que resurtir; naranja, que le queda solo un cuarto de lo que se considera completo; amarillo, que va a la mitad, y sin color que está bien surtido. Arriba hay una barra para buscar y un filtro por categoría. Si hay muchos productos, se muestran de veinte en veinte y el botón «Ver más» carga el resto.

[Insertar captura: catálogo de inventario con el semáforo]

La campana de la parte de arriba muestra cuántos productos necesitan atención. Al tocarla se abren las **alertas**, donde primero aparece el producto que se va a acabar antes, según cuántas piezas vende por semana, y cada alerta dice ese ritmo de venta para saber con cuánta urgencia resurtir.

### A.5.2 Dar de alta un producto

El botón **Alta de productos** abre el formulario. Se piden el nombre, una descripción breve (por ejemplo el tamaño o la marca), el precio de compra, el precio de venta, cuántas piezas hay y el mínimo que no se quiere bajar, que el sistema propone en 5, y la categoría. De forma opcional se pueden elegir el proveedor, un ícono y el código de barras. Mientras se escriben los precios, una barra muestra el margen de ganancia del producto.

Hay dos reglas que el sistema cuida. La primera es que el precio de venta no puede ser menor al de compra. La segunda es que el stock ideal, es decir, la cantidad con la que se considera que el producto está bien surtido y con la que se pintan los colores del semáforo, no hay que capturarlo: el sistema lo calcula como el promedio de lo que había cada vez que se cargó mercancía, y se va afinando solo con cada resurtido.

Los productos que se venden por peso se marcan con la casilla «Se vende a granel»; entonces el precio y las existencias son por kilo. Las listas de categorías, proveedores e íconos muestran solo las tres primeras opciones, y el botón «Mostrar más» despliega el resto; lo que ya se eligió siempre queda a la vista. Si no se elige un ícono, el sistema le pone uno según el nombre del producto.

[Insertar captura: formulario de alta de producto]

### A.5.3 Modificar y dar de baja

Para cambiar un producto se usa **Modificar productos**, que permite buscarlo y abrir su formulario. Todo cambio pide un motivo (por ejemplo, «subió el proveedor»), que se guarda en el historial del producto. Para dar de baja un producto se usa la opción de eliminar, que pide una doble confirmación; el producto no se borra, solo se desactiva, para que sus ventas anteriores sigan apareciendo en los reportes.

### A.5.4 Resurtir

Cuando llega mercancía se usa el botón **Resurtir** del renglón del producto. Se escribe cuántas piezas llegaron y a qué precio de compra, y si el precio subió, se actualiza también el de venta. El sistema suma las piezas, anota la compra como gasto y guarda el costo de esa compra por separado, de modo que si ayer se compró la coca a 15 pesos y hoy a 17, las piezas de ayer se venden primero con costo de 15 y las de hoy con costo de 17, y la utilidad siempre se calcula con lo que de verdad costó lo vendido.

### A.5.5 Importar productos desde un archivo

Para una tienda que ya lleva su inventario en Excel, el botón **Importar CSV** evita capturar producto por producto. Primero se descarga la plantilla, se llena con producto, cantidad, precio de compra y precio de venta (y, si se quiere, categoría, código de barras y si es a granel) y se guarda como CSV. Al subirlo, el sistema lo revisa y muestra qué hará con cada producto: cuáles son nuevos, cuáles ya existen y se van a actualizar, y cuáles tienen errores, como un precio de venta menor al de compra. No se guarda nada hasta que se confirma.

### A.5.6 Proveedores y categorías

En **Proveedores** se consultan y editan los proveedores de la tienda, que ya vienen cargados con los más comunes, y se agregan nuevos con su teléfono, su correo y las categorías que surten. Las categorías de productos se pueden ampliar con el botón «Nueva» al dar de alta un producto.

### A.5.7 Movimientos de inventario

La pantalla **Movimientos** es el registro de todo lo que ha cambiado las existencias: cada venta, entrada de mercancía, merma o ajuste, con la cantidad que cambió, cuántas piezas quedaron, a qué costo y por qué. Los movimientos no se editan ni se borran. Se pueden filtrar por producto, tipo y fechas, y descargar como un archivo CSV.

## A.6 Agente financiero

El agente financiero tiene siete pestañas arriba: Inicio, Registrar gastos, Punto de equilibrio, Sugerir precios, Pronóstico de ventas, Reportes financieros y Reporte de ventas. Todas sus gráficas son rosas y, en cada una, el icono del **ojo** la abre en una ventana grande, con los números exactos debajo cuando son pocos.

### A.6.1 Inicio

El inicio muestra cuatro cifras del momento: lo vendido hoy, los gastos del mes, la utilidad neta del mes y el punto de equilibrio, cada una comparada con el periodo anterior. Debajo hay una tarjeta por módulo, con una gráfica real de la tienda: la utilidad de los últimos seis meses, las ventas de las últimas ocho semanas, los gastos por mes, lo que se lleva vendido en el mes contra la meta del punto de equilibrio y el margen de los productos más vendidos. Un botón morado permite pedirle a marIA que explique el negocio con palabras sencillas.

[Insertar captura: inicio del agente financiero con las gráficas]

### A.6.2 Registrar gastos

Aquí se anotan los gastos del negocio. Un gasto **fijo** se paga siempre, aunque no se venda nada, como la renta, la luz o el internet; uno **variable** cambia con las ventas, como las bolsas o el flete. Al elegir una categoría, el sistema propone si es fijo o variable. Cada gasto lleva el **mes al que corresponde**, que no tiene por qué ser el actual: la luz de septiembre que se paga en octubre se anota en septiembre y cuenta ahí en los reportes.

La mercancía que se compra no se captura aquí, porque se anota sola al dar de alta o resurtir un producto. El historial de gastos muestra todo lo registrado, con su mes.

### A.6.3 Punto de equilibrio

Indica cuánto hay que vender al mes para cubrir los gastos fijos, en total, por día y por categoría de productos. Si se vende menos se pierde dinero, y lo que se venda de más es ganancia. Una barra muestra cuánto del objetivo se lleva alcanzado en el mes. Para calcularlo hacen falta gastos fijos registrados y productos con precio de compra.

### A.6.4 Sugerir precios

Calcula el precio de venta que le deja al tendero la ganancia que quiere. Hay dos formas: «Yo elijo», donde se escribe el margen de ganancia deseado, y «Cubrir mis gastos», donde el sistema calcula el margen necesario para que las ventas paguen los gastos del mes más una ganancia extra que se elige. Para cada producto se ve su precio actual, el sugerido y la ganancia por pieza, y con un botón se acepta el precio. El sistema nunca sugiere un precio menor al costo.

### A.6.5 Pronóstico de ventas

Muestra cuánto se espera vender en las próximas semanas de los diez productos que más se venden, con tres métodos distintos, y marca cuál se equivocó menos con las últimas semanas conocidas. La pantalla carga por partes y cada resultado indica qué tan confiable es según el historial disponible; con pocos días de ventas lo avisa en lugar de inventar una cifra. El botón morado **Explícame mi pronóstico** pide a marIA que lo cuente en palabras sencillas.

### A.6.6 Reportes financieros y reporte de ventas

Los reportes financieros resumen lo que entró, lo que salió y lo que realmente le queda al negocio. Se puede ver de los últimos 1, 3, 6 o 12 meses, o elegir un rango de meses. Arriba están las cifras principales: ingresos, flujo de efectivo, margen operativo y utilidad neta. Después hay dos gráficas, una de ingresos contra egresos y otra de la utilidad por mes, y una tabla que explica paso a paso cómo se llega a la utilidad neta, restando el costo de lo vendido, los gastos y, si la tienda está en RESICO, el impuesto. Al final hay alertas y sugerencias, como un gasto mucho más alto de lo normal, un mes en que se perdió dinero o un margen muy bajo.

El **reporte de ventas** responde a otras preguntas: cuánto se vendió y se ganó entre dos fechas, cuántos tickets fueron, los productos que más se vendieron y los que más ganancia dejaron, y la venta de cada día.

[Insertar captura: reportes financieros con sus gráficas]

## A.7 Hablar con marIA

El panel morado del costado es el chat con la asistente. Se le puede escribir cosas como «agrega 2 pepsis a la caja», «¿cuánto vendí hoy?», «¿qué tengo que resurtir?» o «registra un gasto de luz de 450 pesos de septiembre», y ejecuta lo mismo que se haría a mano, con las mismas reglas. Sabe en qué pantalla se está, así que en ventas puede agregar y cobrar, y en el inventario dar de alta o resurtir. Las consultas, como preguntar por ventas, existencias o gastos, funcionan en cualquier pantalla.

marIA solo atiende temas de la tienda. Si se le pregunta algo ajeno, responde con un mensaje que recuerda en qué sí puede ayudar. Para acciones delicadas, como cancelar una venta o dar de baja un producto, pide confirmación antes de hacerlas, y recuerda lo que ya se eligió, como el margen que se usa para los precios.

El chat conserva la conversación de las últimas 24 horas, y el icono del bote de basura la borra. También se le puede hablar: el botón del **micrófono** funciona como un radio, de modo que se mantiene presionado mientras se habla y se suelta al terminar. Lo que se dijo aparece en el cuadro y solo falta enviarlo. El dictado usa una función del navegador y por eso solo está disponible en Google Chrome y Microsoft Edge, necesita internet, y la primera vez pide permiso para usar el micrófono; si hay mucho ruido en la tienda, conviene usar audífonos con micrófono.

Al entrar cada día, marIA muestra un resumen de lo que pasó el día anterior, y en varias pantallas hay botones morados para que explique en palabras sencillas el inicio, los reportes o el pronóstico.

## A.8 Mi cuenta y la ayuda

Al tocar la foto de perfil, arriba a la derecha, se puede elegir un ícono, cerrar sesión o eliminar la cuenta. Eliminar la cuenta borra por completo la tienda con sus productos, ventas y gastos, y no se puede deshacer, por lo que el sistema pide confirmarlo.

El signo de interrogación abre la ayuda, con preguntas frecuentes que se pueden buscar por palabra, la guía de colores y el enlace a los términos y condiciones y al aviso de protección de datos.

## A.9 Preguntas y problemas frecuentes

Si al cobrar sale un aviso de que no hay existencias, no es un error: significa que el sistema no tiene registradas esas piezas. Se agregan en la ventana que aparece, con su precio de compra, y la venta sigue.

Si un producto no aparece al buscarlo, puede estar dado de baja o no haberse cargado todavía; se puede cobrar como «No encontrado» y darlo de alta después.

Si la pantalla dice que no hay internet pero sí hay, basta con esperar unos segundos: el sistema revisa la conexión cada cierto tiempo y sincroniza solo. Lo hecho sin conexión no se pierde.

Si el micrófono no funciona, hay que revisar que se esté usando Chrome o Edge, que el navegador tenga permiso para el micrófono (el candado junto a la dirección) y que haya internet. En Firefox no está disponible el dictado por voz.

Si marIA no contesta o dice que no pudo conectarse, probablemente el servicio de inteligencia artificial está saturado o sin saldo. El sistema intenta primero con un proveedor y después con el otro, así que basta con volver a intentarlo en un momento. Todo lo demás del sistema sigue funcionando sin la asistente.

Si los reportes o el punto de equilibrio salen en cero, casi siempre es porque faltan datos: ventas cobradas, gastos fijos del mes o productos con precio de compra. El sistema avisa qué falta en cada pantalla.
