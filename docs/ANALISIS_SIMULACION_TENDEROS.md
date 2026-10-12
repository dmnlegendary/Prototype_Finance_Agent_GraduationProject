# Simulación de un mes con 10 tenderos de la CDMX: hallazgos y mejoras para marIA

## 0. Qué es esto y qué NO es

- Los 10 tenderos son **perfiles inventados** (compuestos a partir de cómo suele operar una tienda de abarrotes). No son personas reales ni datos de campo.
- El mes de uso **sí se corrió sobre el código real del sistema**: se crearon 10 tiendas con 250 a 1,100 productos y unos 30,000 tickets (6.4 millones de pesos vendidos) y se midieron las pantallas, la búsqueda, las alertas y las finanzas con las funciones reales de marIA.
- Cada hallazgo lleva una etiqueta de qué tan firme es:
  - **[MEDIDO]** se midió en el sistema con esos datos.
  - **[CÓDIGO]** se comprobó leyendo el código o la pantalla: es un hecho, no una opinión.
  - **[SIMULADO]** sale de un modelo con supuestos (los digo). Sirve para comparar, no como cifra absoluta.
  - **[HIPÓTESIS]** suena razonable pero hay que probarlo con tenderos de verdad.
- Los milisegundos de las páginas se midieron en un entorno lento (Python dentro del navegador), así que sirven solo para comparar entre pantallas. El **número de consultas** y el **tamaño de página** sí son exactos.

---

## 1. Los 10 perfiles

| # | Quién | Zona | Giro | Tickets/día | Productos | Su rasgo |
|---|---|---|---|---|---|---|
| 1 | Doña Mari, 58 | Iztapalapa (Santa Cruz Meyehualco) | Abarrotes familiar de 25 años | 90 | 420 | Usa la laptop vieja de su hija. Fía a unos 30 vecinos. |
| 2 | Don Chuy, 64 | GAM (Cuautepec) | Esquina con productos a granel | 60 | 250 | Vende frijol y azúcar por kilo o por 250 g. |
| 3 | Lupita, 41 | Álvaro Obregón (Jalalpa) | Minisúper con refrigeradores | 160 | 900 | Su hijo atiende la caja. Cobra con terminal de tarjeta. |
| 4 | Arturo, 35 | Tlalpan (Ajusco Medio) | Tienda moderna | 120 | 1,100 | Le gustan los reportes. Pide por WhatsApp a sus proveedores. |
| 5 | Doña Cony, 52 | Coyoacán (Santo Domingo) | Abarrotes, dulcería y papelería | 110 | 700 | Mucha pieza suelta de dulces. |
| 6 | Don Beto, 67 | Xochimilco (San Gregorio) | Abarrotes y verdura | 45 | 300 | Mala señal de internet. |
| 7 | Marce, 29 | Iztapalapa (Constitución de 1917) | Tiendita con recargas y pago de servicios | 200 | 500 | Muchos tickets muy chicos, en hora pico. |
| 8 | Don Pepe, 71 | GAM (Martín Carrera) | Cigarros sueltos, cheve y envases | 80 | 330 | Vende "un cigarro" y maneja casco de envase. |
| 9 | Karen, 33 | Benito Juárez (Narvarte) | Snacks saludables | 70 | 380 | Su alcaldía no existe en el sistema. |
| 10 | Don Tomás, 60 | Venustiano Carranza (Moctezuma) | Abarrotes de mayoreo y menudeo | 50 | 600 | Vende por caja de 12, 24 o 48. |

### Su mes, en una línea cada uno (lo que más les pesó)

1. **Doña Mari.** El día 1 no puede capturar 420 productos a mano; elige los 20 del catálogo precargado y le quedan **los 20 en rojo**, con costo igual al precio. Su fiado sigue en el cuaderno, así que lo que dice el sistema no cuadra con su caja. Escribe "jabon" y no aparece "Jabón".
2. **Don Chuy.** Un cliente pide 250 g de frijol y el carrito solo sabe sumar de 1 en 1. Registra "1 pieza" y lleva el peso real en el cuaderno.
3. **Lupita.** Ella con el celular y su hijo con la tablet **comparten el mismo carrito**: lo que agrega uno aparece al otro y se cobran ventas ajenas. Lo que paga con tarjeta no se distingue de lo que paga en efectivo y su corte no cuadra.
4. **Arturo.** Quiere cargar su Excel y solo hay un comando de terminal. Siguiendo la ayuda de la pantalla registra "compra de mercancía" como gasto y su **utilidad pasa de +18.9 % a −35.8 %**. Deja de confiar en las finanzas.
5. **Doña Cony.** Vende 10 chicles y 6 paletas por ticket. Con 7 piezas promedio por ticket la pantalla se recarga **8 veces por venta**.
6. **Don Beto.** Se le cae la señal a media venta y no puede cobrar. La pantalla de inventario pesa 207 KB y se arrastra con datos móviles lentos.
7. **Marce.** Cobra recargas y pagos de servicio como "producto no encontrado" y crea **un producto nuevo pendiente cada vez** (cien "Recarga Telcel" duplicados al mes). Con 200 tickets al día, cada segundo de más se nota.
8. **Don Pepe.** El cigarro suelto y el casco de envase no caben en el modelo (no hay unidades ni presentaciones).
9. **Karen.** Elige "Otra" como alcaldía y su ticket dice "Otra, CDMX". El catálogo de 20 productos genéricos no tiene lo que ella vende.
10. **Don Tomás.** El **98 % de sus tickets** tiene algún renglón de varias piezas y llega a 96 piezas en uno: serían 95 toques en "+", con 95 recargas de pantalla.

---

## 2. Resultados medidos

### 2.1 Cuántas veces se recarga la pantalla por venta [MEDIDO con los tickets simulados]

Hoy cada "+" y cada producto agregado es un envío de formulario y una recarga completa.

| Tienda | Piezas por ticket | Recargas por ticket | % de tickets con algún renglón de 2+ piezas |
|---|---|---|---|
| Marce | 2.4 | 3.4 | 34 % |
| Don Beto | 2.6 | 3.6 | 39 % |
| Don Chuy | 2.8 | 3.8 | 40 % |
| Don Pepe | 2.5 | 3.5 | 35 % |
| Doña Mari | 3.3 | 4.3 | 45 % |
| Karen | 3.5 | 4.5 | 50 % |
| Lupita | 4.3 | 5.3 | 53 % |
| Arturo | 4.7 | 5.7 | 59 % |
| Doña Cony | 7.2 | 8.2 | 72 % |
| Don Tomás | 48.6 | 49.6 | 98 % |

### 2.2 La búsqueda manual de la caja [MEDIDO, 1,100 productos]

Se probaron 250 consultas por tipo. "Asistente" es la búsqueda que usa el chat.

| Cómo escribe el tendero | Encuentra la búsqueda manual | Encuentra el asistente |
|---|---|---|
| Primeras letras (`sabri`) | 64 % | 63 % |
| Sin acento (`jabon`, `pinol`) | **0 %** | 80 % |
| Palabras en otro orden (`600 coca`) | **0 %** | 76 % |
| Apodo corto (`coca 600`) | **9 %** | 76 % |
| Una letra mal (`sabrtas`) | 0 % | 0 % |

La búsqueda manual solo encuentra texto que sea una parte literal y seguida del nombre. Escribir como se habla ("coca 600") casi nunca funciona.

### 2.3 Qué tan pesadas son las pantallas con un mes de datos [MEDIDO, tienda de 1,100 productos]

| Pantalla | Consultas a la base | Tamaño |
|---|---|---|
| Punto de venta (carrito de 15 renglones) | 6 | 43 KB |
| Inventario (cualquier página) | **92** | **207 KB** |
| Alertas de reabastecimiento | 4 | 140 KB |
| Historial de ventas | 5 | 27 KB |
| Finanzas: inicio | 16 | 20 KB |
| Finanzas: reportes | **25** | 23 KB |
| Punto de equilibrio / precios sugeridos | 6 | 20 a 32 KB |

La pantalla de inventario hace 92 consultas aunque solo muestra 25 productos: arma un formulario de edición oculto por cada uno.

### 2.4 Las primeras horas de una tienda nueva [MEDIDO]

Una tienda que elige los 20 productos precargados termina con: **20 de 20 con costo igual al precio** (ganancia de $0 en cualquier venta), **20 de 20 con cero piezas** y **20 alertas rojas** desde el primer minuto.

### 2.5 Finanzas [MEDIDO, tienda de Arturo]

- **Doble conteo de la mercancía.** Con sus ventas del mes ($527,621) y sus gastos fijos ($18,000), la utilidad neta es **+$94,182 (18.9 %)**. Si registra además lo que compró a proveedores ($288,350) como gasto, la utilidad se vuelve **−$194,168 (−35.8 %)**. El sistema ya resta el costo de lo vendido, así que esa compra se cuenta dos veces. Aun así, la pantalla de gastos (`registrar_gastos.html`) dice que los variables son "inventario, merma, bolsas", y el modelo y el asistente también ponen "inventario" de ejemplo.
- **Costo retroactivo.** Al subir 50 % el costo de un solo producto, el costo de ventas de la primera semana del mes **cambió +5.6 %**, porque el reporte usa el costo actual y no el que tenía al vender.
- **Punto de equilibrio:** las 10 tiendas lo calcularon bien.

### 2.6 Alertas de reabastecimiento sin mínimo configurado [MEDIDO + SIMULADO]

El mínimo es opcional y por defecto vale 0, así que el rojo solo salta cuando la pieza **ya se acabó**. Tras un mes, las tiendas tenían entre 87 y 227 productos en rojo (18 % a 26 % de su catálogo): demasiadas para atenderlas, y todas llegan tarde.

Simulación de un mes con la misma demanda, comparando dos formas de resurtir (visitas del proveedor lunes y jueves):

- **A (como hoy):** el tendero resurte lo que ve vacío o casi vacío.
- **B (con semáforo):** el sistema propone un mínimo igual a 4 días de ventas promedio, y el tendero resurte todo lo que no esté en verde.

| Tienda | Piezas pedidas que no había (A) | (B) | Inventario promedio, B contra A |
|---|---|---|---|
| Doña Mari | 16.7 % | 4.8 % | +36 % |
| Don Chuy | 14.4 % | 3.7 % | +29 % |
| Lupita | 17.0 % | 4.3 % | +36 % |
| Arturo | 17.5 % | 4.6 % | +34 % |
| Doña Cony | 21.3 % | 9.1 % | +30 % |
| Don Beto | 20.2 % | 5.8 % | +36 % |
| Marce | 16.9 % | 3.7 % | +35 % |
| Don Pepe | 18.6 % | 4.5 % | +42 % |
| Karen | 17.8 % | 4.6 % | +36 % |
| Don Tomás | 28.5 % | 15.2 % | +32 % |

**Cómo leerlo:** los porcentajes absolutos dependen de mi modelo del tendero "A", que es pasivo y seguramente peor que uno real. Lo que sí se sostiene es la dirección: un mínimo calculado con las ventas reduce mucho las faltantes, **a cambio de tener 30 a 40 % más dinero en mercancía**. Por eso conviene dejar elegir los días de cobertura, no imponerlos.

### 2.7 Botones rápidos [SIMULADO con la hipótesis de que unos pocos productos dominan la venta]

Los 12 productos más vendidos de cada tienda cubrieron **34 a 52 %** de los renglones de sus tickets, y los 30 más vendidos **46 a 67 %**. Con datos reales esto puede variar, pero es la regla de Pareto que se ve en casi cualquier tienda.

### 2.8 Datos sueltos del sistema

- **[MEDIDO]** El asistente envía unas 3,700 palabras-pieza ("tokens") de instrucciones y herramientas en cada mensaje. A los precios de los modelos pequeños son centavos de dólar al mes por tienda (conviene revisar la tarifa vigente), pero se puede reducir.
- **[CÓDIGO]** Solo hay un carrito abierto por negocio (`_venta_en_curso`), y `Venta.cajero` nunca se llena.
- **[MEDIDO]** La lista de alcaldías trae 6 de las 16 de la CDMX más "Otra".

---

## 3. Problemas, ordenados por qué tan graves son

### Nivel 1: afectan la confianza en los números o fallan con dos personas

| # | Problema | Evidencia | Qué hacer |
|---|---|---|---|
| 1 | Pantalla, modelo y asistente invitan a registrar "inventario" como gasto y eso duplica el costo de la mercancía | §2.5 | **Decisión suya** (las fórmulas las definieron ustedes): quitar "inventario" de los ejemplos, o tratar las compras a proveedores aparte para el flujo de efectivo pero fuera de la utilidad. Ya corregí solo mi línea del panel de ayuda. |
| 2 | La alta con el catálogo precargado deja costo = precio, 0 piezas y 20 alertas rojas | §2.4 | Pedir costo y existencias al elegir los productos (dos columnas rápidas) y no alertar mientras no se hayan capturado. |
| 3 | Un solo carrito por negocio: dos dispositivos o dos cajeros se pisan | §2.8 | Carrito por sesión o por usuario con cajero registrado, y varios usuarios por tienda. |
| 4 | El costo del reporte es el costo actual, no el de cuando se vendió | §2.5 | Guardar el costo en cada renglón de la venta (`costo_unitario`) en el momento de vender. |

### Nivel 2: retrasan al tendero en la venta

| # | Problema | Evidencia | Qué hacer |
|---|---|---|---|
| 5 | Cantidades solo con "+" y "−", enteras, con recarga de página en cada toque | §2.1 | Campo de cantidad rápido (escribir "12" y Enter), decimales para granel, y actualizar el carrito sin recargar toda la pantalla. |
| 6 | La búsqueda manual no entiende acentos ni palabras en otro orden | §2.2 | Usar en la caja el mismo buscador del asistente y que **Enter agregue el primer resultado**. |
| 7 | Siempre hay que teclear aunque el 34 a 52 % de los renglones sean los mismos 12 productos | §2.7 | Fila de botones "más vendidos" arriba del buscador. |
| 8 | No hay "pagó con $X, cambio $Y", ni forma de pago, ni fiado | [CÓDIGO] `Venta` no tiene esos campos | Campo opcional "paga con" con cambio, forma de pago (efectivo, tarjeta, transferencia) y fiado con saldo por cliente. |
| 9 | Cada "producto no encontrado" crea otro producto pendiente | [CÓDIGO] `ventas/views.py` | Reutilizar el pendiente con el mismo nombre (el asistente ya lo hace) y permitir "ventas rápidas" como Recarga o Servicio. |

### Nivel 3: retrasan el alta y el cuidado del inventario

| # | Problema | Evidencia | Qué hacer |
|---|---|---|---|
| 10 | Cargar más de 20 productos solo se puede con un comando de terminal | [CÓDIGO] | Pantalla para subir un Excel o CSV con plantilla y vista previa. |
| 11 | El catálogo precargado tiene 20 productos y su buscador y filtros de categoría no hacen nada | [CÓDIGO] `productos_precargados.html` | Catálogo de unos 1,000 productos comunes de abarrotes con precio de referencia, y buscador funcional. |
| 12 | Cuando llega el proveedor hay que editar cada producto uno por uno, con un "motivo" obligatorio | [CÓDIGO] | Pantalla "Llegó mercancía": lista de productos, piezas y costo nuevo, un solo guardado. |
| 13 | La pantalla de inventario hace 92 consultas y pesa 207 KB | §2.3 | Un solo modal de edición compartido en vez de uno por producto. |
| 14 | Mínimo y stock ideal los captura el tendero (o nadie) | §2.6 | Sugerirlos con sus ventas ("alcanza para N días") y dejar elegir los días. |

### Nivel 4: pulido y casos especiales

15. Las 16 alcaldías de la CDMX (hoy 6 más "Otra"); mostrar "Otra, CDMX" en el ticket se ve mal.
16. Presentaciones y unidades (caja de 24, cigarro suelto, granel) para Don Tomás, Don Pepe y Don Chuy.
17. Fecha de caducidad y merma para lácteos y pan.
18. Corte de caja del día (efectivo esperado, tarjeta, transferencias).
19. Funcionar con señal intermitente (app instalable y cola de ventas); hoy sin internet no se puede cobrar.
20. Bajar el costo del asistente enviando solo las herramientas de la pantalla en que se está.
21. Páginas pesadas para datos móviles: alertas con 140 KB, reportes con 25 consultas.

---

## 4. Lo interesante: casi todo se puede sin integrar hardware

### 4.1 El lector de códigos de barras no necesita integración

Los lectores USB y Bluetooth baratos **actúan como un teclado**: "escriben" el código y pulsan Enter. Basta con (a) un campo `codigo_barras` en el producto y (b) que el buscador de la caja, al recibir un código y Enter, agregue ese producto. Así la limitante de "no integrar hardware" casi no existe para escanear: el tendero que ya tenga un lector (o compre uno de unos cientos de pesos) lo conecta y funciona. [HIPÓTESIS: probar con un lector real]

### 4.2 La cámara del celular como lector

Chrome en Android tiene una API de detección de códigos (`BarcodeDetector`) y existen librerías gratuitas para el resto de navegadores. Un botón "escanear" en la caja y en la alta de productos usaría la cámara que el tendero ya trae en el bolsillo. En la alta, el código podría traer el nombre de una base abierta de productos para que el tendero solo escriba precio y existencias. [HIPÓTESIS: hay que medir qué parte de sus productos aparece en esa base]

### 4.3 Foto de la nota del proveedor (la idea que más tiempo ahorra)

Cada visita del proveedor viene con una remisión en papel con productos, cantidades y precios. Una foto, leída por un modelo con visión (ya usan ChatGPT o Gemini), podría armar la pantalla "Llegó mercancía" ya llenada. El tendero revisa, corrige y guarda. Convierte varios minutos de captura por visita en segundos. **Riesgo:** los modelos se equivocan con letra o tickets arrugados, por eso siempre con revisión antes de guardar y nunca guardado automático. [HIPÓTESIS]

### 4.4 Pedido sugerido por proveedor, enviado por WhatsApp

Con las alertas y la cobertura en días, el sistema puede armar "para Sabritas conviene pedir: Doritos ×12, Takis ×8…" y abrir WhatsApp con el mensaje escrito (un enlace `wa.me`, sin integrar nada). Los tenderos de la simulación (Arturo, Lupita) ya piden así. Une las alertas con la acción que el tendero tiene que hacer.

### 4.5 Ticket y cobranza por WhatsApp; impresión

- Mandar el ticket al cliente con un enlace `wa.me`, y recordatorios de fiado igual.
- Dar formato de impresión (58 u 80 mm) al ticket para usar la impresora del sistema; funcionará según el equipo. [HIPÓTESIS]

### 4.6 Voz para dar de alta y surtir

El dictado ya existe. Probarlo en frases largas como "llegaron 2 cajas de coca de 600 y 3 de pepsi" y medirlo contra teclear. En hora pico no conviene (ruido y espera de 2 a 4 segundos), pero para surtir la tienda puede ser lo más rápido.

### 4.7 Lo que descartaría por ahora

Contar mercancía con foto de la repisa (poco preciso), cobrar con QR bancario (requiere integrar un banco; basta con registrar "transferencia") y comparar precios entre proveedores.

---

## 5. Orden sugerido de trabajo

**A. Una o dos sesiones (cambios chicos, mucho efecto)**
- Arreglar los textos de "inventario como gasto" según lo que decidan (#1).
- Catálogo precargado: pedir costo y existencias, no alertar sin existencias capturadas (#2).
- Buscador de la caja con el motor del asistente y Enter que agrega (#6).
- "Producto no encontrado" sin duplicados (#9).
- 16 alcaldías (#15).

**B. Una semana (lo que cambia el día a día)**
- Cantidad rápida con decimales y carrito sin recarga (#5).
- Botones de más vendidos (#7).
- "Paga con" y cambio, forma de pago (#8, primera parte).
- Código de barras con lector tipo teclado (4.1).
- Inventario con modal único (#13) y costo guardado en cada venta (#4).

**C. Dos a cuatro semanas (producto nuevo)**
- Importar Excel desde la pantalla y catálogo grande (#10 y #11).
- "Llegó mercancía" (#12) y, encima, la foto de la remisión (4.3).
- Mínimos sugeridos con cobertura en días y pedido por WhatsApp (#14 y 4.4).
- Carrito por usuario, varios cajeros (#3), fiado (#8, segunda parte).

**D. Después**
- Presentaciones, caducidad, corte de caja, trabajo con señal intermitente (#16 a #19).

---

## 6. Cómo comprobar todo esto con tenderos de verdad

La simulación señala dónde mirar, pero **no sustituye al piloto**. Con 3 a 5 tenderos reales (idealmente uno con poca señal, uno que fía y uno de mayoreo), medir durante una semana:

1. Tiempo por ticket con cronómetro y número de toques (hoy contra con las mejoras).
2. Cuántas veces buscan algo y no lo encuentran.
3. Cuánto tardan en dar de alta 30 productos y en registrar una visita del proveedor.
4. Qué hacen con el fiado y con las tarjetas, porque el sistema hoy no lo ve.
5. Si el semáforo les avisa a tiempo y si los mínimos sugeridos les parecen razonables.
6. La escala SUS que ya viene en el apéndice C del reporte técnico.

Preguntas abiertas para la primera visita: ¿qué parte del día es la que más les cansa?, ¿cómo saben qué hay que pedir?, ¿cuánto del dinero que entra es fiado?, ¿cómo cobran con tarjeta o transferencia?, ¿quién más atiende la caja?

---

## 7. Apéndice: cómo se hizo

- 10 tiendas con productos tomados de un catálogo de 1,315 productos típicos de abarrotes (nombres, categorías y precios realistas inventados), con popularidad tipo "pocos productos venden mucho".
- 30 días de ventas con más movimiento viernes y sábado, tickets con 1 a 5 productos y cantidades según el giro (mayoreo, dulces sueltos o normal).
- Dos formas de resurtir (A y B) sobre la misma demanda para comparar faltantes e inventario.
- Los tickets se cargaron en el sistema real y se midieron las pantallas, la búsqueda, el alta de una tienda nueva, las fórmulas financieras y las alertas.
- Supuestos importantes: el tendero "A" es pasivo (resurte lo vacío y, a veces, lo casi vacío); las visitas del proveedor son lunes y jueves; la demanda es independiente entre productos. Cualquiera de estos puede cambiar los números absolutos.
