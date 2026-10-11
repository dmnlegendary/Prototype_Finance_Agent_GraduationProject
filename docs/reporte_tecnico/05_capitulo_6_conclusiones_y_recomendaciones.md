# Capítulo VI. Conclusiones y recomendaciones

> **Nota:** en la lista que nos dieron, los apartados de este capítulo aparecen como 10.1 y 10.2. Aquí los numeramos 6.1 y 6.2 para que coincidan con el capítulo. Si su escuela quiere la numeración original, solo cámbienla.

## Conclusiones

El objetivo de este trabajo fue **[COMPLETAR: copiar aquí el objetivo general del TT]**. Al terminar esta etapa podemos concluir lo siguiente:

1. **Se construyó un sistema que funciona de punta a punta.** Una persona puede registrarse, dar de alta su tienda, vender, controlar su inventario, registrar sus gastos, ver sus finanzas y platicar con un asistente por texto o por voz, todo desde el navegador y con los datos guardados en su propia computadora.
2. **Casi todos los requisitos quedaron cubiertos.** De los 34 requisitos funcionales, 28 están implementados (5 de ellos todavía deben validarse con el asistente real), 5 están parciales y 1 está pendiente: el pronóstico de ventas.
3. **Las fórmulas financieras quedaron implementadas y probadas.** Utilidad neta con ISR RESICO, margen operativo, precio sugerido y punto de equilibrio por categoría se calculan con datos reales del negocio, y las comprobamos con el ejemplo numérico de nuestro propio documento. **[COMPLETAR: confirmar cuando las pruebas pasen.]**
4. **El asistente puede hacer cosas útiles sin inventar datos.** Gracias a que el modelo de lenguaje pide funciones del sistema en lugar de adivinar, las respuestas salen de la base de datos de la tienda. Aun así, su calidad depende del modelo y de tener internet, y esto no se puede garantizar al 100 %.
5. **Falta validar el sistema con tenderos reales.** Sin la prueba de aceptación no podemos afirmar todavía que sea fácil de usar para ellos ni medir los beneficios del capítulo V. **[COMPLETAR: cuando se haga la prueba, resumir aquí los resultados.]**
6. **El objetivo se cumplió [COMPLETAR: totalmente / en su mayor parte / parcialmente], con la limitación principal de que el modelo de pronóstico se dejó para una siguiente fase.**

---

## 6.1 Lecciones aprendidas

- **Delimitar el alcance desde el principio.** Quisimos abarcar mucho (ventas, inventario, finanzas, asistente y pronóstico). Decidimos dejar el pronóstico para la fase 2 para poder entregar un sistema completo y estable. Aprendimos que es mejor terminar bien lo esencial que dejar todo a medias.
- **Revisar los requisitos contra el sistema desde temprano.** Cuando hicimos la revisión de los 34 requisitos ya con casi todo construido, encontramos que 13 no se cumplían y 12 se cumplían a medias. Corregirlos nos tomó tres rondas de trabajo. Si hubiéramos revisado cada etapa, habría costado menos.
- **Definir las fórmulas de negocio antes de programarlas.** Las fórmulas de finanzas llegaron cuando las pantallas ya existían como maqueta. Al ponerlas en un solo archivo y probarlas con el ejemplo numérico del documento, evitamos que cada pantalla calculara algo distinto.
- **Trabajar con inteligencia artificial requiere cuidado.** El asistente no siempre responde igual, así que aprendimos a darle instrucciones claras, a que use funciones del sistema en vez de inventar datos y a probar su lógica simulando sus respuestas. También aprendimos que cada llamada cuesta, por eso el resumen del día se genera una sola vez.
- **Los detalles de los datos importan.** Nos encontramos con totales con decimales de más, una cuenta que no se podía borrar por tener ventas y un campo que significaba dos cosas distintas (producto dado de baja y producto no encontrado). Resolverlos nos enseñó a pensar bien en las reglas de la base de datos.
- **Las pruebas automáticas ayudan mucho, y es mejor escribirlas desde el principio.** Las hicimos hasta el final y, al escribirlas, encontramos un error: dos mensajes del chat guardados casi al mismo tiempo podían quedar en desorden. Con pruebas desde el inicio habríamos encontrado errores así más rápido.
- **Diseñar para personas que no son técnicas.** Probamos una interfaz muy sobria, pero la retroalimentación nos mostró que el tendero necesita identificar los botones de un vistazo; por eso volvimos a usar colores con significado (verde para cobrar, rojo para cancelar, amarillo para buscar). Aprendimos que el diseño bonito no sirve si no se entiende rápido.
- **Cuidar el entorno de trabajo.** Perdimos tiempo con librerías instaladas en el Python equivocado. Desde entonces escribimos el paso a paso de instalación en el README y usamos `python -m pip`.
- **Mejorar la forma de usar Git.** Varios de nuestros registros se llaman simplemente "cambios". Para la siguiente vez, escribiríamos mensajes que digan qué se hizo y por qué, para que el historial sirva como bitácora.
- **Pensar en el tamaño de los datos desde el inicio.** Varias pantallas cargan todos los registros a la vez. Funciona bien para una tienda pequeña, pero habría que paginar desde el diseño para negocios con muchos productos.

## 6.2 Recomendaciones para trabajos futuros

**Lo más importante (completar lo que quedó pendiente):**

1. **Pronóstico de ventas (RF-F04).** Construir el modelo con el historial que ya guarda el sistema (tablas de ventas y renglones de venta). Se puede empezar con métodos sencillos y compararlos entre sí: promedio móvil, suavizamiento exponencial, ARIMA o modelos de aprendizaje automático como bosques aleatorios [12]. Hay que medirlos con una métrica de error (como el RMSE) y mostrarle al tendero el resultado con su nivel de confianza y una explicación del asistente. Se necesita acumular suficiente historial de ventas para que sea confiable.
2. **Prueba de aceptación con tenderos** y ajustes según lo que se observe.
3. **Video introductorio** del tutorial (RF-S05) y guía rápida impresa.
4. **Confirmación para acciones críticas del asistente (RF-AVI06).** Hoy no hace falta porque el asistente no borra nada, pero si se le agregan acciones como eliminar productos, deberá pedir confirmación primero.
5. **Orden por rotación de ventas** en alertas y catálogo (RF-I03 y RF-I06), contando qué productos se venden más.

**Mejoras del sistema:**

6. **Rendimiento con muchos datos:** paginar el catálogo de productos y el historial de ventas, y cargar los datos de edición de un producto solo cuando se abre su ventana.
7. **Roles y permisos:** separar al dueño del cajero, para que el cajero venda pero no vea los reportes financieros ni cambie precios.
8. **Costo real en cada venta:** guardar el costo del producto el día que se vendió, para que la utilidad histórica no cambie cuando cambia el costo actual.
9. **Compras a proveedores:** registrar lo que se compra para que el flujo de efectivo incluya las compras de mercancía y no solo los gastos.
10. **Fechas de caducidad y mermas:** registrar caducidades y avisar de productos por vencer.
11. **Categorías propias por negocio:** hoy las categorías de productos son compartidas entre todos los negocios.
12. **Usar el sistema sin internet:** guardar iconos y letra dentro del proyecto, y estudiar un modelo de lenguaje que corra en la misma computadora para no depender de la nube ni compartir datos con terceros.
13. **Correo real y respaldos automáticos:** conectar un servicio de correo y programar los respaldos de la base de datos.
14. **Seguridad para producción:** apagar el modo de desarrollo, usar un servidor de producción, HTTPS y límite de intentos de inicio de sesión.
15. **Lectura de respuestas en voz alta** (hoy la voz solo sirve para dictar).
16. **Reportes avanzados con Power BI**, conectado a la base de datos.

**Visión a largo plazo:**

17. **Versión en la nube (SaaS)** con una base de datos más grande (como PostgreSQL), para que varios negocios la usen sin instalar nada y desde el celular, quizá como aplicación web instalable.
18. **Conexión con el SAT**: facturación electrónica y apoyo para la declaración del régimen RESICO. Esto debe revisarse con un contador, porque las reglas fiscales cambian [13], [14].
