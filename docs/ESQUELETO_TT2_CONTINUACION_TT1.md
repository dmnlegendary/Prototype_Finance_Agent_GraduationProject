# Esqueleto del documento (continuación del TT1)

Un solo documento. Los capítulos 1 a 4 del TT1 se conservan (con los ajustes de la sección A). El capítulo 5 de TT1 ("Conclusiones parciales y trabajo a futuro") se retira y su contenido pasa a ser el capítulo 11. Los capítulos 5 a 11 son nuevos (los borradores redactados de 5 a 9 están en `docs/capitulos_tt2/`).

Marcas: **[NUEVO]** hay que escribirlo, **[AJUSTAR]** ya existe en TT1 y se actualiza, **[COMPLETAR]** depende de datos que faltan (pruebas piloto, despliegue en Azure).

Etiquetas para los evaluadores: **[ANÁLISIS]** análisis cuantitativo y cualitativo del sistema, **[DISEÑO]** diagramas y arquitectura del software, **[AGENTE]** finanzas elementales y sistemas inteligentes (asistente vs. agente). Son las secciones que conviene desarrollar con más profundidad.

## Mapa para los evaluadores

| Perfil del evaluador | Qué busca | Secciones que se resaltan |
|---|---|---|
| Análisis del sistema | Análisis completo, cuantitativo y cualitativo | 3.1 a 3.8 (análisis), 5.2 (evolución), 7.2 (problemas), capítulo 8 (pruebas), 10.3 y 10.4 (indicadores y resultados) |
| Diseño del sistema | Diagramas y arquitectura del software | Capítulo 4 completo (con los diagramas actualizados y el 4.5 nuevo), 6.5, 6.8, 7.1 y 9.1.1 |
| Finanzas elementales y sistemas inteligentes | Cómo se considera un agente o un asistente | 2.3.6, 2.6, 2.7.5, 4.10, 6.4, 6.6 y 6.7 |

---

## A. Ajustes a lo que ya existe (capítulos 1 a 4 de TT1)

- **Preliminares:** [AJUSTAR] actualizar glosario y lista de abreviaciones (agregar: MVT, ORM, API, LLM, function calling, CSV, POS, PWA, CORS, RESICO si no está).
- **Índices:** [AJUSTAR] el índice de figuras y de tablas se rehacen al final (capturas reales de pantalla en lugar de mockups).
- **1.6 Propuesta de solución y 1.7 Metodología:** [AJUSTAR] la solución final es un sistema web con frontend en Azure y backend local; la metodología se amplía en 5.1 y la evolución del sistema en 5.2.
- **2. Marco teórico:** [AJUSTAR] 2.4 y 2.5 (nube y Azure) quedan; agregar la justificación de la arquitectura híbrida (frontend en nube, backend local). Secciones nuevas:
  - 2.11 Framework Django y patrón MVT.
  - 2.12 Modelos de lenguaje y *function calling* (cómo el asistente ejecuta acciones del sistema).
  - 2.13 Trabajo sin conexión (almacenamiento local en el navegador y sincronización).
  - 2.14 Búsqueda aproximada de texto (tolerancia a acentos y errores de dedo).
  - 2.15 Metodología Scrum.
  - 2.3.6 **[AGENTE]** Asistente virtual frente a agente inteligente: criterios (percepción del entorno, autonomía, objetivos, capacidad de actuar, aprendizaje) y con base en ellos cómo se clasifica cada parte de marIA. [DECIDIR la clasificación del equipo]
  - 2.7.5 y 2.6 **[AGENTE]** Finanzas elementales: ampliar con las fórmulas que usa el sistema (utilidad bruta y neta, flujo de efectivo, margen, punto de equilibrio, ISR RESICO) y la diferencia entre compra de mercancía y gasto.
- **3. Análisis:** [AJUSTAR] corregir numeración (3.3.4 antes de 3.3.2; "Análisis de costos" y "Modelo de negocios Canvas" sin número) y agregar:
  - 3.1 (nueva) **Actores**: tendero y sistema/asistente.
  - 3.1.x Requisitos actualizados a lo realmente implementado.
  - 3.2.x Reglas de negocio nuevas: regla de oro (no se vende con 0 piezas), compra de mercancía automática, precio y costo del momento en cada venta.
  - 3.x **[ANÁLISIS]** Análisis cuantitativo: tiempos por venta, consultas y peso por pantalla, número de pruebas, indicadores del pronóstico. Análisis cualitativo: entrevistas, observación y retroalimentación de los 3 tenderos, observaciones de los profesores.
- **3.4.5 Propuesta de investigación para TT2:** [AJUSTAR] quitar o reescribir; ya se ejecutó.
- **4. Diseño:** [AJUSTAR] No se agregan diagramas fuera del capítulo 4. Los que ya existen se actualizan en su mismo punto, y los de secuencia entran en el 4.5, que en TT1 está vacío (la numeración salta de 4.4 a 4.6).
  - 4.1 y 4.2 Diagrama ER y modelo relacional: actualizar con las tablas finales.
  - 4.3 Casos de uso: actualizar y agregar importar CSV, vender producto a granel, vender sin internet y resurtir desde la venta.
  - 4.4 Diagrama de componentes: actualizar con la capa de sincronización sin conexión, el módulo del asistente y las APIs externas.
  - 4.5 **[DISEÑO] [NUEVO]** Diagramas de secuencia (no hay diagrama de clases): cobrar una venta con la regla de oro, chat con function calling (Gemini y respaldo con ChatGPT) y sincronización sin conexión. [DECIDIR si son tres o menos]
  - 4.6 Diagrama de actividades: actualizar los flujos que cambiaron (venta con dos carritos, alta con compra automática, importar CSV).
  - 4.7 Diagrama de despliegue: actualizar a frontend en Azure y backend local.
  - 4.8 Mockups: reemplazar por capturas del sistema final.
  - 4.9 Arquitectura: agregar la capa de sincronización sin conexión y el respaldo de modelos de IA.
  - 4.10 **[DISEÑO] [AGENTE]** Clasificación de marIA: dónde actúa como asistente (responde y ejecuta lo que se le pide) y dónde como agente (calcula y recomienda por sí mismo). Se apoya en el diagrama de componentes (4.4), sin diagrama nuevo.
  - 4.11 **[DISEÑO]** Registro de decisiones de arquitectura (tabla de texto: decisión, alternativas y por qué se eligió).
- **Capítulo 5 de TT1:** [AJUSTAR] mover a las conclusiones del capítulo 11 (la lista de "trabajo a futuro" de TT1 ya se cumplió en gran parte).

---

## B. Capítulos nuevos

### Capítulo 5. Metodología y evolución del sistema

**5.1 Metodología de desarrollo** [NUEVO]
- 5.1.1 Roles del equipo (Luis Bernardo Delgado Acosta, Jorge Arif Díaz Jiménez, director/es)
- 5.1.2 Product Backlog
- 5.1.3 Sprints e iteraciones (tabla: sprint, fechas, objetivo, entregable) [COMPLETAR fechas]
- 5.1.4 Definition of Done
- 5.1.5 Control de versiones (GitHub, ramas, merges)
- 5.1.6 Herramienta de seguimiento (Jira o tablero Kanban) [CONFIRMAR cuál usaron]

**5.2 Evolución del sistema** [NUEVO]
- 5.2.1 Versión inicial: primeras funcionalidades (qué se construyó primero y por qué)
- 5.2.2 Línea del tiempo (tabla: fecha, funcionalidad agregada o cambiada, origen, motivo) [COMPLETAR, se puede armar con el historial de commits]
- 5.2.3 Cambios por observaciones de los profesores (semáforo de reabastecimiento, búsqueda instantánea en alertas, base de datos SQL, llaves de IA, resúmenes con IA, function calling, caché por usuario)
- 5.2.4 **[ANÁLISIS]** Cambios por lo observado en tiendas y por la encuesta a tenderos [COMPLETAR con lo que observaron]
- 5.2.5 Funcionalidades descartadas y por qué (hardware externo, recargas, tarjeta, WhatsApp, caducidad, roles)

### Capítulo 6. Construcción del software

**6.1 Entorno y herramientas** [NUEVO]
- VS Code, Python, Django, Git/GitHub, SQLite y PostgreSQL, Bootstrap

**6.2 Módulo de ventas** [NUEVO]
- 6.2.1 Carrito doble y cantidad escrita
- 6.2.2 Búsqueda aproximada y código de barras con lector tipo teclado
- 6.2.3 Productos no encontrados
- 6.2.4 Regla de oro (no se vende con 0 piezas)
- 6.2.5 Ticket de venta

**6.3 Auxiliar de inventario** [NUEVO]
- 6.3.1 Alta y edición de productos, productos a granel
- 6.3.2 Importación de productos desde CSV
- 6.3.3 Semáforo de reabastecimiento y alertas
- 6.3.4 Proveedores y categorías
- 6.3.5 Historial de cambios y compra de mercancía automática

**6.4 Agente financiero** [NUEVO] **[AGENTE]**
- 6.4.1 Dashboard, registro de gastos y reportes
- 6.4.2 Fórmulas implementadas: cada una con su definición, un ejemplo con números y dónde se usa en el sistema (utilidad, flujo de efectivo, margen, punto de equilibrio, ISR RESICO, precios sugeridos)
- 6.4.3 Criterio contable: la compra de mercancía no es gasto (se registra al cargar inventario)

**6.5 Base de datos implementada** [NUEVO] **[DISEÑO]**
- 6.5.1 Tablas finales, relaciones e índices
- 6.5.2 Caché por negocio
- 6.5.3 De CSV a PostgreSQL: primero se usó un archivo CSV para los datos y tardaba mucho en cargar; se migró a PostgreSQL (motivo, comparación de tiempos [COMPLETAR], cómo se hizo la migración)

**6.6 Modelos de pronóstico de ventas** [COMPLETAR]
- 6.6.1 Datos utilizados y su preparación
- 6.6.2 Modelos considerados y el elegido, con la justificación
- 6.6.3 Métricas de evaluación (por ejemplo RMSE) y resultados
- 6.6.4 Cómo se integra al sistema y limitaciones

**6.7 Asistente Virtual Inteligente (AVI) y APIs utilizadas** [NUEVO] **[AGENTE]** (qué lo hace asistente y qué lo acerca a un agente, según 2.3.6)
- 6.7.1 APIs de Gemini y de OpenAI (ChatGPT): modelos usados, autenticación, límites y costos
- 6.7.2 Function calling: cómo el asistente ejecuta acciones del sistema (catálogo de funciones)
- 6.7.3 Herramientas por pantalla (para reducir costo)
- 6.7.4 Respaldo automático: primero Gemini y, si falla, ChatGPT
- 6.7.5 Historial de 24 horas, resúmenes con IA y dictado de voz del navegador

**6.8 Trabajo sin conexión y sincronización** [NUEVO] **[DISEÑO]** (el diagrama de secuencia está en 4.5)

**6.9 Seguridad y sesiones** [NUEVO]
- Autenticación, contraseñas, llaves de IA fuera del código

**6.10 Diseño de interfaz** [NUEVO]
- Paleta de colores con significado (morado = IA, amarillo = búsqueda, naranja = filtros y categorías, verde = ventas, azul = inventario, rosa = agente financiero, rojo = alertas) y diseño adaptable a celular

**6.11 Tamaño del proyecto** [NUEVO]
- Archivos y líneas de código [CONFIRMAR]

### Capítulo 7. Documentación del código y problemas del desarrollo

**7.1 Documentación del código** [NUEVO]
- 7.1.1 Estructura del proyecto (aplicaciones: accounts, core, inventario, ventas, finanzas, avi) y qué hace cada carpeta
- 7.1.2 Modelos de datos (descripción de cada clase y sus relaciones)
- 7.1.3 Vistas y rutas (URLs principales y qué responde cada una)
- 7.1.4 Servicios y fórmulas (cálculos financieros, búsqueda, cobro, importación)
- 7.1.5 API interna en JSON (carrito, búsqueda, sincronización)
- 7.1.6 Convenciones del código (nombres, comentarios, organización de pruebas)
- 7.1.7 Dónde está el detalle: Anexo B (manual técnico) y Anexo C (fragmentos de código)

**7.2 Problemas y limitaciones durante el desarrollo** [NUEVO]
- 7.2.1 **[ANÁLISIS]** Tabla de problemas técnicos: problema, causa, solución, aprendizaje. Incluir: carga lenta con CSV y migración a PostgreSQL (por ejemplo migraciones en conflicto, versiones de Django, consultas pesadas, costo de la IA, saturación de la API, ventas con precios que cambiaban)
- 7.2.2 Limitaciones del entorno de desarrollo y de pruebas
- 7.2.3 Limitaciones de las herramientas y de las APIs externas
- 7.2.4 Decisiones que se tomaron para acotar el alcance

### Capítulo 8. Plan de pruebas

- 8.1 Pruebas unitarias **[ANÁLISIS]**: 8.1.1 en el entorno local (pruebas automáticas, tiempos y consultas por pantalla) y 8.1.2 de los servicios en la nube (APIs de IA)
- 8.2 Pruebas funcionales **[ANÁLISIS]**: casos por módulo, incluyendo la integración con la base de datos y el trabajo sin conexión
- 8.3 Validación con tenderos **[ANÁLISIS]**: encuesta (7 respuestas), observación en una tienda real y prueba de aceptación del sistema (pendiente) [COMPLETAR]

### Capítulo 9. Implementación, capacitación y mantenimiento

**9.1 Implementación y despliegue** [NUEVO]
- 9.1.1 Arquitectura de despliegue: frontend en Azure y backend local **[DISEÑO]**
- 9.1.2 Instalación del backend local (requisitos, dependencias, migraciones, configuración de llaves de IA)
- 9.1.3 Publicación del frontend en Azure [COMPLETAR, semana del despliegue]
- 9.1.4 Comunicación entre frontend y backend (HTTPS, CORS, acceso al equipo local) [DECIDIR cómo se conectan]
- 9.1.5 Costos reales del despliegue (enlazar con el análisis de costos del capítulo 3)
- 9.1.6 Verificación posterior al despliegue

**9.2 Capacitación de usuarios** [NUEVO]
- 9.2.1 Videos tutoriales por módulo [COMPLETAR, enlaces]
- 9.2.2 Preguntas frecuentes dentro del sistema (botón "?")
- 9.2.3 Estrategia de autoservicio guiado con el asistente

**9.3 Plan de mantenimiento** [NUEVO]
- 9.3.1 Respaldos de la base de datos
- 9.3.2 Actualización del sistema y migraciones
- 9.3.3 Reentrenamiento del modelo de pronóstico [COMPLETAR]
- 9.3.4 Monitoreo del uso y costo de las APIs de IA
- 9.3.5 Soporte y corrección de errores

### Capítulo 10. Resultados esperados y obtenidos

- 10.1 Beneficios tangibles [NUEVO] (solo lo que el sistema sí hace: tiempo por venta, alta de inventario, registro de compras y gastos)
- 10.2 Beneficios intangibles [NUEVO]
- 10.3 **[ANÁLISIS]** Indicadores de éxito [NUEVO] (tiempo por venta, adopción, error del pronóstico)
- 10.4 **[ANÁLISIS]** Resultados obtenidos [COMPLETAR]
  - 10.4.1 Resultados cuantitativos (pruebas automáticas, rendimiento, tiempos con los 3 tenderos, indicadores del pronóstico)
  - 10.4.2 Resultados cualitativos (opiniones y observaciones de los tenderos, observaciones de los profesores y cómo se atendieron)
  - 10.4.3 Análisis comparativo antes y después (cuadro de mejoras)
- 10.5 Limitaciones del sistema final [NUEVO] (los problemas durante el desarrollo están en 7.2): sin integración de hardware externo (impresora, báscula, terminal de tarjeta), sin recargas ni pago de servicios, sin pago con tarjeta, sin WhatsApp, sin fecha de caducidad, un solo usuario sin roles, el asistente requiere internet

### Capítulo 11. Conclusiones y recomendaciones

- 11.1 Conclusiones [NUEVO] (a partir de las conclusiones parciales de TT1 y de la evolución descrita en 5.2)
- 11.2 Lecciones aprendidas [NUEVO] (a partir de la sección 7.2)
- 11.3 Recomendaciones para trabajos futuros [NUEVO]: despliegue completo en la nube, comandos de voz avanzados, facturación electrónica (RESICO), integración con hardware, aplicación móvil con lector de código de barras, pagos con tarjeta, recargas y servicios

### Referencias [AJUSTAR]
Agregar fuentes en formato IEEE sobre Django, modelos de lenguaje y function calling, Scrum, trabajo sin conexión, ARIMA o Random Forest (según el pronóstico) y gestión de microempresas.

---

## C. Documentación adjunta

- **Anexo A. Manual de usuario** [NUEVO] (guía paso a paso con capturas)
- **Anexo B. Manual técnico** [NUEVO] (instalación, base de datos, llaves de IA, migraciones, despliegue, catálogo de funciones del asistente, rutas y modelos; amplía la sección 7.1)
- **Anexo C. Código fuente, fragmentos representativos** [NUEVO] (modelos principales, fórmulas financieras, vista de cobro, herramientas del asistente)
- **Anexo D. Encuestas, entrevistas y hojas de observación** [COMPLETAR]
- **Anexo E. Reporte Técnico 2** [CONFIRMAR si es un archivo aparte]
- **Anexo F. Enlaces a videos tutoriales** [COMPLETAR]
