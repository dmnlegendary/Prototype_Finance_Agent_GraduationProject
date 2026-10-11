# Capítulo V. Resultados Esperados

> **Nota para el equipo (borrar antes de entregar):** este capítulo habla de lo que **esperamos** lograr, no de lo que ya medimos. Por eso las metas están marcadas con **[AJUSTAR]**. Ninguna cifra de aquí viene de una medición real todavía; cuando hagan la prueba con tenderos, reemplacen las metas por los resultados y agreguen sus gráficas. No inventen números.

Antes de medir una mejora hay que saber cómo estaba el negocio sin el sistema. Por eso, en la prueba con tenderos hay que anotar primero **cómo llevaban sus cuentas antes** (cuaderno, calculadora, memoria, hoja de Excel) y cuánto tardaban. A eso se le llama línea base.

---

## 5.1 Beneficios Tangibles

Los beneficios tangibles son los que se pueden contar o medir.

| Beneficio esperado | Cómo creemos que lo logra el sistema | Cómo se va a medir | Meta **[AJUSTAR]** |
|---|---|---|---|
| **Menos tiempo para registrar una venta** | La búsqueda mientras se escribe, el carrito con botones y el cobro en un solo paso evitan sumar a mano. | Cronometrar una venta de 3 productos con el sistema y compararla con la forma de antes. | Menos de 1 minuto por venta de 3 productos. |
| **Menos errores al cobrar** | El total se calcula solo, se ve siempre y cada venta genera su ticket. | Contar errores de cobro por semana, antes y durante la prueba. | Que bajen los errores respecto a la línea base. |
| **Menos productos agotados sin darse cuenta** | Las alertas avisan cuando un producto llega a su cantidad mínima y la lista pone primero lo más urgente. | Contar las veces que se acabó un producto durante la prueba, antes y después. | Menos faltantes que en la línea base. |
| **Ahorro de tiempo en las cuentas** | Los reportes de ingresos, gastos y utilidad salen solos; el punto de equilibrio y los precios sugeridos se calculan automáticamente. | Preguntar cuántas horas por semana dedicaban a las cuentas y comparar. | Que ese tiempo baje. |
| **Mejores precios y márgenes** | El sistema sugiere precios a partir del costo y el margen que el tendero quiere ganar. | Número de precios revisados o ajustados y margen promedio antes y después. | Que el margen no baje y que los productos con margen muy bajo disminuyan. |
| **Costo bajo de software** | Se usan herramientas de código abierto (Python, Django, SQLite, Bootstrap), sin licencias. | Costo mensual real del sistema, que sería principalmente el uso de las API del asistente. | **[COMPLETAR: medir el costo real de las API por tienda al mes.]** |

> **Sobre las mermas por caducidad:** el sistema todavía **no** guarda fechas de caducidad, así que no podemos decir que reduce las mermas. Se menciona como mejora futura en el capítulo VI.

## 5.2 Beneficios Intangibles

Son beneficios que no se miden fácil en números, pero que importan:

- **Más tranquilidad para el dueño.** Saber cuánto vendió, cuánto gastó y cuánto le queda sin hacer cuentas a mano reduce el estrés administrativo.
- **Decisiones con datos y no con corazonadas.** Cuando el tendero ve su punto de equilibrio o qué productos no se venden, puede decidir mejor qué comprar y a qué precio vender.
- **Tecnología al alcance de todos.** El asistente habla en palabras sencillas y se le puede hablar con la voz, lo que ayuda a personas que no están acostumbradas a usar sistemas de computadora.
- **Un paso hacia la formalidad.** El sistema muestra una estimación del impuesto ISR del régimen RESICO y ordena los ingresos y gastos, lo que ayuda a llevar mejor la contabilidad del negocio.
- **Independencia.** Los datos se guardan en la computadora del propio negocio y el tendero no depende de un servicio de pago mensual para llevar sus ventas.
- **Aprendizaje para el equipo.** Desarrollar el proyecto nos permitió practicar análisis de requisitos, diseño de bases de datos, desarrollo web y uso de inteligencia artificial en un caso real.

## 5.3 Indicadores de Éxito

Un indicador es un número que nos dice si el proyecto va bien. La columna "Estado" dice si ya se puede medir o si falta.

| Indicador | Qué mide | Cómo se mide | Meta **[AJUSTAR]** | Estado |
|---|---|---|---|---|
| Requisitos funcionales implementados | Qué tanto del sistema está construido | Tabla de la sección 3.5.5 | 34 de 34 | **Hoy: 28 implementados (5 de ellos por validar con el asistente real), 5 parciales y 1 pendiente** |
| Pruebas automáticas aprobadas | Que el código haga lo que debe | `python manage.py test` | 100 % | **[COMPLETAR: 61 pruebas, resultado real]** |
| Tiempo de respuesta de las pantallas | Rapidez del sistema | Medir tiempo de carga en una computadora de gama básica | Menos de 3 segundos | Por medir |
| Tiempo por venta | Rapidez en el mostrador | Cronómetro en la prueba de aceptación (tarea T1) | Menos de 1 minuto | Por medir |
| Tareas completadas sin ayuda | Facilidad de uso | Hoja de observación en la prueba de aceptación | 8 de cada 10 tenderos | Por medir |
| Satisfacción de uso | Qué tan fácil les pareció | Encuesta SUS del Anexo C (calificación de 0 a 100) | 68 o más (promedio de referencia) | Por medir |
| Aciertos del asistente | Qué tanto entiende y ejecuta lo que se le pide | Frases de prueba PA-01 a PA-10 en ChatGPT y en Gemini | 8 de 10 por modelo | Por medir |
| Adopción durante la prueba | Si de verdad lo usan | Días con al menos una venta registrada ÷ días que abrió la tienda | 80 % o más | Por medir |
| Costo de las API por tienda | Cuánto cuesta usar el asistente | Consumo mensual en OpenAI/Google dividido entre tiendas | **[COMPLETAR]** | Por medir |
| Error del pronóstico (RMSE) | Qué tan cerca está el pronóstico de lo que realmente se vendió | Raíz del error cuadrático medio entre lo pronosticado y lo vendido | — | **No aplica todavía**: el modelo de pronóstico es de la fase 2 |

> **¿Qué es el RMSE?** Es una forma de medir el error de un pronóstico: se compara lo que se dijo que se iba a vender con lo que realmente se vendió. Mientras más bajo, mejor. Como el pronóstico no está construido, este indicador se medirá en la siguiente fase.
