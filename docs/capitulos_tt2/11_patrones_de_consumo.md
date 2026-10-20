# Patrones de consumo relevantes para el inventario

Esta sección sirve para justificar varias decisiones del sistema con datos y no solo con intuición. Se puede colocar como una subsección nueva antes de los modelos de pronóstico (por ejemplo, como 6.6.1, y recorrer la numeración de las demás), o en el análisis del capítulo 3 como parte del análisis cuantitativo. Aquí se redacta de forma que funcione en cualquiera de los dos lugares.

## Datos analizados

Para buscar patrones usamos el historial de ventas de una tienda, que es el mismo que se usó para probar los modelos de pronóstico. [CONFIRMAR el origen del historial y si se puede mencionar] El archivo trae 63,411 renglones de venta, de 16,131 tickets, con fechas del 30 de mayo de 2025 al 7 de abril de 2026. Antes de analizarlo se descartaron 36 renglones con precios imposibles, como una mantequilla cobrada a 10 mil millones de pesos por pieza o una leche a 3,100 pesos, que son errores de captura. Quedaron 63,375 renglones útiles de 16,128 tickets, 306 días con ventas y 2,477 productos distintos. El ticket promedio es de 120.82 pesos, con 3.9 productos por ticket.

## Pocos productos concentran las ventas

El resultado más claro es que las ventas se concentran en una parte pequeña del catálogo. Con solo 425 productos, que son el 17.2 % de los 2,477, se logra el 80 % de lo vendido, y con 1,043 (42.1 %) se llega al 95 %. En el otro extremo, 1,127 productos (45.5 %) se vendieron cinco veces o menos en cerca de diez meses. La Tabla 1 resume esto.

Tabla 1. Concentración de las ventas por producto.

| Grupo | Productos | Porcentaje del catálogo | Parte de las ventas |
|---|---|---|---|
| Los que suman el 80 % de las ventas | 425 | 17.2 % | 80 % |
| Los que suman el 95 % de las ventas | 1,043 | 42.1 % | 95 % |
| Los que vendieron 5 unidades o menos | 1,127 | 45.5 % | casi nada |

Entre los productos que más dinero dejan están la Coca-Cola de 2 litros (71,970 pesos y 2,320 piezas), la cecina (43,735 pesos), la crema de 426 ml (36,841), la Coca-Cola de vidrio de 500 ml (36,702 pesos y 2,735 piezas) y el aguacate (34,803). Se nota que algunos de los que más venden en pesos, como la cecina, el aguacate, el chicharrón o la longaniza, se venden por peso y en pocas unidades, y que hay muchos productos de vida corta, como verduras, carnes frías y lácteos.

Para el inventario esto quiere decir que el cuidado debe concentrarse en unos cuatrocientos productos: son los que no pueden faltar, los que conviene vigilar con el semáforo y los que tiene sentido pronosticar, que es justo lo que hace el pronóstico al tomar los diez más vendidos. También justifica el reporte de baja rotación, porque casi la mitad del catálogo ocupa espacio y dinero sin moverse.

## Las ventas se concentran en la tarde y la noche

Por hora, el movimiento es bajo en la mañana y sube desde las 2 de la tarde. De las 14:00 a las 22:00 horas se hace cerca del 77 % de los tickets (12,403 de 16,128), con un máximo entre las 18:00 y las 21:00, donde se atienden alrededor de 1,800 tickets por cada hora. En la mañana, entre las 8:00 y las 13:00, solo hay entre 344 y 868 tickets por hora.

Esto se traduce en una recomendación práctica: la mercancía conviene recibirla y acomodarla en la mañana, que es cuando hay menos clientes, y los productos más vendidos deben estar surtidos antes de las 2 de la tarde. Por eso las alertas de reabastecimiento son más útiles al abrir la tienda que por la noche.

## Los domingos hay menos clientes, pero compran más

Las ventas totales por día son parecidas entre semana, entre 5,800 y 7,200 pesos, así que no hay un día claramente malo. Lo que cambia es cómo se compone la venta. Los domingos se atienden menos tickets (35 en promedio frente a entre 48 y 65 de lunes a sábado), pero es el día con más ventas, porque cada ticket es casi el doble de grande. La Tabla 2 lo muestra.

Tabla 2. Ventas por día de la semana (promedio de los días con ventas).

| Día | Tickets por día | Ventas por día | Ticket promedio |
|---|---|---|---|
| Domingo | 35.0 | $7,213 | $206 |
| Lunes | 56.8 | $6,135 | $108 |
| Martes | 58.1 | $6,267 | $108 |
| Miércoles | 55.7 | $6,163 | $111 |
| Jueves | 64.6 | $6,533 | $101 |
| Viernes | 51.6 | $5,779 | $112 |
| Sábado | 47.9 | $6,469 | $135 |

El domingo parece ser el día de la despensa, con compras más grandes. Para el inventario significa que conviene llegar al fin de semana con buen surtido de los productos de mayor volumen.

## Las quincenas se notan

Al revisar las ventas promedio por día del mes aparece un patrón que se repite con el pago de la quincena. Los días 14 a 17 se vende más (entre 7,580 y 8,723 pesos por día) y también el 30 y el 31 (7,052 y 7,959), mientras que los días 9 y 10 son los más flojos, con menos de 4,000 pesos, alrededor de 38 % menos que un día normal de unos 6,200. Con esto, los mínimos de los productos de más rotación deberían revisarse antes del día 14 y antes del día 30. Como solo hay diez meses de datos, estos números son una pista y no una regla.

## Un problema con los datos

Hay algo que se debe tomar en cuenta al interpretar el pronóstico. El número de tickets por mes baja de forma muy marcada: 4,959 en junio de 2025, 803 en diciembre y 243 en marzo de 2026. Una caída así en una tienda es poco probable, y lo más seguro es que, con el tiempo, se fueron dejando de registrar ventas en el sistema de donde salió el archivo. [CONFIRMAR con quien tiene el historial] Como el pronóstico usa las últimas 26 semanas, que en este archivo son las que menos registros tienen, los modelos aprenden una caída que quizá no sea real. Para evaluar los modelos de forma justa conviene usar un periodo con registros completos, como junio a septiembre de 2025, y aclarar esta limitación en el documento.

## Qué decisiones respaldan estos patrones

Estos hallazgos justifican varias decisiones que se tomaron en el sistema. El semáforo usa el stock ideal y no solo el mínimo, porque los productos que más se venden necesitan más margen de seguridad. Las alertas muestran cuánto vende cada producto por semana y para cuántos días alcanza lo que queda, de modo que lo que se acaba primero va arriba. El reporte de baja rotación señala la cola larga de productos que casi no se venden. Y el pronóstico se concentra en los diez productos más vendidos, que son los que tienen datos suficientes y los que más importan.
