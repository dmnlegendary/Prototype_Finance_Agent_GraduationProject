## 3.4 Diseño y arquitectura del Sistema

### 3.4.1 Arquitectura de Software

**Patrón que usamos: MVT.** El sistema está hecho con Django, un marco de trabajo para páginas web en Python [1]. Django organiza el código en tres partes, que se llaman MVT por sus siglas:

- **Modelo (Model):** describe los datos que se guardan (productos, ventas, gastos…) y se encarga de leerlos y guardarlos en la base de datos.
- **Vista (View):** es la parte que decide qué hacer cuando el usuario pide algo. Recibe la petición, consulta o cambia los datos y elige qué pantalla mostrar.
- **Template (plantilla):** es el HTML de la pantalla que ve el usuario.

Un ejemplo sencillo: cuando el tendero oprime "Cobrar", el navegador manda la petición a Django, la vista de cobro descuenta el inventario y marca la venta como cobrada (usando los modelos), y por último responde con la pantalla del punto de venta ya actualizada.

**Una sola aplicación.** Decidimos hacer todo dentro de Django, sin un servidor aparte para el asistente ni un framework pesado para la pantalla. Lo hicimos así porque somos un equipo pequeño, porque la instalación en la computadora de una tienda es más fácil con una sola cosa que levantar, y porque nos permitió usar solo HTML, CSS y JavaScript con Bootstrap, que son tecnologías sencillas de mantener.

**Organización por módulos.** El proyecto se dividió en "apps" de Django. Cada una corresponde a un componente de nuestro diagrama de arquitectura:

| Componente del diagrama | App de Django | Qué contiene |
|---|---|---|
| Seguridad y autenticación | `accounts` | Registro, inicio de sesión, recuperar contraseña, eliminar cuenta, datos del negocio. |
| Ventas y carrito | `ventas` | Punto de venta, carrito, cobro, ticket, historial. |
| Inventario y alertas | `inventario` | Productos, categorías, proveedores, alertas de stock y catálogo precargado. |
| Agente financiero | `finanzas` | Gastos, punto de equilibrio, precios sugeridos, reportes y todas las fórmulas (`calculos.py`). |
| Orquestador AVI | `avi` | Chat con el asistente, conexión con ChatGPT y Gemini, funciones que el asistente puede ejecutar, resumen diario. |
| Django ORM | Todos los `models.py` | Guarda y consulta datos en la base de datos sin escribir SQL a mano. |
| Elementos compartidos | `core`, `config`, `templates`, `static` | Modelo base con fechas, configuración, plantillas comunes, estilos y JavaScript. |

**Capas del sistema.**

| Capa | Con qué está hecha | Para qué sirve |
|---|---|---|
| Presentación | Plantillas HTML, CSS, JavaScript y Bootstrap | Lo que ve y toca el usuario. |
| Lógica | Vistas de Django, `avi/services.py` y `finanzas/calculos.py` | Las reglas del negocio y las fórmulas. |
| Datos | Modelos de Django y SQLite | Guarda la información. |
| Servicios externos | API de OpenAI (ChatGPT) y API de Google (Gemini) | Entienden el texto del tendero y redactan respuestas. |

**Cómo funciona el asistente (AVI).** Esta es la parte más especial de la arquitectura:

1. El tendero escribe o dicta una petición. El dictado lo hace el propio navegador (con una función llamada Web Speech API [5]); el sistema solo recibe el texto.
2. La página manda el texto a la vista del chat (`avi/views.py`).
3. El sistema le manda al modelo de lenguaje el mensaje, los últimos 10 mensajes de la conversación y la lista de funciones disponibles (agregar al carrito, consultar ventas, registrar un gasto, consultar punto de equilibrio, etc.). A esto se le llama *function calling* [6], [7]: el modelo no inventa los datos, pide que el sistema ejecute una función.
4. Si el modelo pide una o varias funciones, el sistema las ejecuta con la base de datos del negocio (`avi/services.py`) y le regresa los resultados.
5. El modelo redacta una respuesta breve y sencilla.
6. Si se cambió algo (por ejemplo, se agregó un producto al carrito), la página vuelve a pedir solo el contenido del módulo y lo actualiza, sin perder la conversación.

**Resumen diario.** Para no llamar al modelo cada vez que el tendero inicia sesión, el resumen de "cómo te fue ayer" se genera la primera vez que alguien del negocio entra ese día y se guarda en la base de datos. Las demás veces que entre ese día, se muestra el guardado. Así se evitan llamadas innecesarias (y costos) cuando hay muchos usuarios.

**Estructura de carpetas.**

```
config/        configuración general (settings, rutas principales)
core/          modelo base con fechas de creación y actualización
accounts/      seguridad: registro, login, negocio
inventario/    productos, proveedores, alertas
ventas/        punto de venta, carrito, tickets
finanzas/      gastos, reportes, fórmulas financieras (calculos.py)
avi/           asistente: chat, funciones, conexión con los modelos
templates/     plantillas base y barra de navegación
static/        estilos (CSS) y JavaScript compartidos
docs/          documentación del proyecto
```

**Despliegue.** El sistema corre en la computadora del negocio (un servidor de Django local) y guarda todo en un archivo de base de datos SQLite en esa misma computadora. Solo el asistente necesita internet para hablar con ChatGPT o Gemini. Figura sugerida para este apartado: **Figura 3.7, diagrama de componentes y de despliegue** (navegador, servidor Django, base SQLite y las dos APIs externas).

---

### 3.4.2 Diseño de Base de Datos

Usamos **SQLite** [3], una base de datos relacional (SQL) que se guarda en un solo archivo. La elegimos porque no hay que instalar ni configurar un servidor de base de datos, lo que hace sencillo instalar el sistema en una tienda. Django crea las tablas a partir de los modelos con unos archivos llamados *migraciones*.

El sistema tiene 13 tablas principales (y una tabla intermedia para la relación entre proveedores y categorías).

| Tabla (modelo) | Para qué sirve | Campos principales |
|---|---|---|
| `Usuario` | La persona que usa el sistema. | nombre completo, teléfono (único), correo, contraseña cifrada. |
| `Negocio` | La tienda del usuario. | nombre de la tienda, alcaldía, años de operación, si está en RESICO, RFC. |
| `Categoria` | Tipo de producto (bebidas, lácteos…). | nombre (único), icono. |
| `Proveedor` | Quién surte al negocio. | nombre, teléfono, correo, categorías que surte. |
| `ProductoCatalogo` | Lista de productos comunes que se ofrece al registrarse. | nombre, categoría, icono, precio sugerido. |
| `Producto` | Producto real del inventario. | nombre, descripción, categoría, proveedor, costo, precio de venta, cantidad actual, cantidad mínima, activo, pendiente de validar. |
| `HistorialModificacionProducto` | Motivo de cada cambio hecho a un producto. | producto, usuario, motivo, fecha. |
| `Venta` | Un ticket de venta. | folio (único por negocio), estado (en curso, cobrada o cancelada), total. |
| `ItemVenta` | Cada renglón del carrito. | venta, producto, cantidad, precio unitario. |
| `CategoriaGasto` | Tipo de gasto creado por el tendero. | negocio, nombre. |
| `GastoOperativo` | Un gasto del negocio. | tipo (fijo o variable), categoría, concepto, monto, nota, fecha. |
| `HistorialConversacion` | Mensajes del chat con el asistente. | negocio, usuario, quién habló (usuario o asistente), mensaje. |
| `ResumenDiario` | Resumen del día generado por la IA. | negocio, fecha (única por negocio), texto, ventas, ganancia, gastos. |

**Reglas importantes de la base de datos:**

- Todas las tablas heredan de un modelo base que guarda la fecha de creación y de actualización.
- El folio de venta no se repite dentro de un mismo negocio.
- Los productos **no se borran de verdad** cuando se da de baja: solo se marcan como inactivos, para no perder las ventas anteriores.
- Un renglón de venta está protegido: no se puede borrar un producto que ya se vendió. Por eso, al eliminar una cuenta completa, primero se borran los renglones de venta y después todo lo demás.
- Todos los montos tienen 2 decimales.
- Todo lo del negocio (productos, ventas, gastos, historial) está ligado al negocio, y el negocio al usuario. Si se elimina al usuario, se elimina todo lo suyo.

**Relación con el pronóstico.** Las tablas `Venta` y `ItemVenta` guardan el historial de ventas por producto y por fecha. Ese historial será la materia prima del modelo de pronóstico en la fase 2.

### 3.4.3 Modelo Entidad-Relación

> **Este diagrama lo hacen ustedes (Figura 3.8).** Estas son las relaciones que debe mostrar:

| Relación | Tipo | Explicación |
|---|---|---|
| Usuario — Negocio | 1 a 1 | Cada usuario tiene un negocio. |
| Negocio — Producto | 1 a muchos | Un negocio tiene muchos productos. |
| Negocio — Venta | 1 a muchos | Un negocio tiene muchas ventas. |
| Negocio — Proveedor | 1 a muchos | Un negocio tiene varios proveedores. |
| Negocio — GastoOperativo | 1 a muchos | Un negocio registra muchos gastos. |
| Negocio — CategoriaGasto | 1 a muchos | Cada negocio crea sus categorías de gasto. |
| Negocio — HistorialConversacion | 1 a muchos | Mensajes del chat del negocio. |
| Negocio — ResumenDiario | 1 a muchos | Un resumen por día. |
| Categoria — Producto | 1 a muchos | Un producto pertenece a una categoría. |
| Categoria — Proveedor | muchos a muchos | Un proveedor surte varias categorías y una categoría la surten varios proveedores. |
| Proveedor — Producto | 1 a muchos | Un producto puede tener un proveedor. |
| Venta — ItemVenta | 1 a muchos | Una venta tiene varios renglones. |
| Producto — ItemVenta | 1 a muchos | Un producto aparece en muchos renglones de venta. |
| Producto — HistorialModificacionProducto | 1 a muchos | Cada producto guarda el historial de sus cambios. |
| CategoriaGasto — GastoOperativo | 1 a muchos | Un gasto puede tener una categoría. |
| ProductoCatalogo — Producto | 1 a muchos | De qué producto precargado salió un producto (opcional). |

### 3.4.4 Diagramas UML

> **Los diagramas los hacen ustedes.** Les dejo qué incluir.

**Figura 3.9. Diagrama de clases.** Una clase por cada tabla de la sección 3.4.2, con sus atributos y las relaciones de la sección 3.4.3. Agreguen los métodos importantes: `Producto.stock_critico`, `Producto.margen_porcentaje`, `Producto.tiene_ventas`, `ItemVenta.subtotal` y `Venta.recalcular_total`.

**Figura 3.10. Diagrama de secuencia: cobrar una venta.**
1. El tendero oprime "Cobrar" en el navegador.
2. El navegador manda la petición a la vista `cobrar`.
3. La vista revisa que el carrito no esté vacío.
4. La vista, en una sola transacción, descuenta la cantidad de cada producto (`Producto`) y cambia el estado de la `Venta` a "cobrada".
5. La vista recalcula el total y redirige a la pantalla de ventas con el folio del ticket.
6. El navegador muestra la notificación y el ticket.

**Figura 3.11. Diagrama de secuencia: mensaje al asistente.**
1. El tendero escribe "agrega 2 pepsis".
2. La página manda el mensaje a `avi/views.py`.
3. La vista pide al cliente (`clients.py`) que le pregunte al modelo de lenguaje, enviando mensaje, historial y funciones disponibles.
4. El modelo pide ejecutar `agregar_al_carrito`.
5. `clients.py` llama a `services.py`, que busca el producto, lo agrega al carrito y regresa el resultado.
6. El modelo redacta la respuesta.
7. La vista guarda el mensaje y la respuesta en `HistorialConversacion` y le dice a la página que se actualice.
8. La página muestra la respuesta y vuelve a cargar el contenido del carrito.

**Figura 3.12. Diagrama de secuencia: resumen del día.**
1. El tendero inicia sesión y el sistema deja una marca de "mostrar resumen".
2. La pantalla de ventas pide `/avi/resumen/`.
3. La vista busca un `ResumenDiario` de hoy para ese negocio.
4. Si existe, lo regresa. Si no, calcula los números de ayer, le pide al modelo que los explique, guarda el resultado y lo regresa.

**Figura 3.13. Diagrama de secuencia: aceptar un precio sugerido.**
1. El tendero escribe un margen y oprime "Calcular".
2. La vista calcula el precio sugerido de cada producto con la fórmula costo ÷ (1 − margen).
3. El tendero ajusta un precio y oprime "Aceptar".
4. La vista actualiza el precio del producto y guarda el motivo en `HistorialModificacionProducto`.

### 3.4.5 Diseño de Interfaces

La interfaz está pensada para un tendero que trabaja rápido en el mostrador y que, muy probablemente, no tiene conocimientos técnicos. Nos guiamos por estas ideas:

- **Lenguaje de todos los días.** Los textos evitan palabras técnicas ("Cobrar", "Cancelar venta", "Producto no encontrado").
- **Colores con significado.** Para que el usuario identifique las cosas a simple vista:

| Color | Dónde se usa | Significado |
|---|---|---|
| Verde | Cobrar, botón "+", alta de productos | Avanzar o agregar |
| Rojo | Cancelar venta, botón "−", alertas de reabastecimiento, "Baja" | Peligro o quitar |
| Amarillo | Barras de búsqueda | "Aquí se busca" |
| Naranja | Producto no encontrado | Atención, caso especial |
| Morado y azul | Modificar productos, proveedores, asistente | Acciones de gestión |

- **Letra y fondo cómodos para la vista.** Usamos la letra Inter y un fondo blanco hueso en lugar de blanco puro, para cansar menos la vista durante todo el día.
- **Dos columnas.** A la izquierda está siempre el chat del asistente; a la derecha, el sistema con su barra de navegación (ventas, inventario y finanzas). Así el asistente nunca estorba al trabajo.
- **Diseño adaptable.** La pantalla se ajusta a computadora, tablet y celular. En pantallas pequeñas los menús se reducen a iconos.
- **Avisos claros.** Las confirmaciones aparecen como notificaciones flotantes que se quitan solas, y las acciones delicadas (cancelar una venta, dar de baja un producto, eliminar la cuenta) piden confirmación.
- **Ayuda a la mano.** La primera vez en cada módulo aparecen consejos sobre los botones importantes, y siempre hay un botón "?" para volver a verlos.
- **Íconos que se entienden.** Usamos iconos de Bootstrap Icons en lugar de texto largo.

Estas ideas siguen las heurísticas de usabilidad de Nielsen [11] (hablar el lenguaje del usuario, prevenir errores, mostrar el estado del sistema y dar ayuda).

> **Capturas que deben ir como figuras (Figura 3.14 en adelante):** inicio de sesión, registro (3 pasos), punto de venta con carrito, ticket, producto no encontrado, inventario con catálogo, alta de producto, alertas, proveedores, dashboard financiero, registrar gastos, punto de equilibrio, sugerir precios, reportes, chat del asistente con el resumen del día, vista en celular.

---

## 3.5 Construcción del Software

### 3.5.1 Herramientas utilizadas

| Herramienta | Para qué se usó |
|---|---|
| Visual Studio Code | Escribir el código. |
| Python 3.12 [2] | Lenguaje de programación. |
| Django (versión 5) [1] | Marco de trabajo web. |
| SQLite [3] | Base de datos local. |
| HTML, CSS y JavaScript | Pantallas y comportamiento en el navegador. |
| Bootstrap 5.3 [4] y Bootstrap Icons | Estilos base e iconos. |
| Google Fonts (Inter) | Tipografía. |
| API de OpenAI (modelo `gpt-4o-mini`) | Asistente con ChatGPT. |
| API de Google (modelo `gemini-2.5-flash`) | Asistente con Gemini. |
| Web Speech API del navegador | Dictado por voz. |
| `python-dotenv` | Leer las llaves de las API desde el archivo `.env`. |
| Git y GitHub | Control de versiones y repositorio. |
| Entorno virtual de Python (`venv`) | Mantener las librerías del proyecto separadas de las del resto de la computadora. |
| Otras herramientas de apoyo | **[COMPLETAR: lo que hayan usado y deban declarar según el reglamento de su escuela]** |

Las librerías externas del proyecto están en el archivo `requirements.txt`: Django, openai, google-generativeai y python-dotenv.

### 3.5.2 Tamaño del proyecto

Al momento de redactar este reporte, sin contar migraciones ni librerías de terceros:

| Tipo de archivo | Líneas aproximadas |
|---|---|
| Python | 2,800 |
| HTML (plantillas) | 2,100 |
| CSS | 1,900 |
| JavaScript | 500 |

### 3.5.3 Cómo se construyó cada módulo

- **Seguridad:** el registro es en 3 pasos. El inicio de sesión acepta correo o teléfono mediante un validador propio. La recuperación de contraseña usa las vistas que ya trae Django. Eliminar la cuenta pide la contraseña otra vez.
- **Inventario:** todo se hace en ventanas emergentes dentro de la misma pantalla (alta, edición, proveedores, nueva categoría). Cada cambio a un producto guarda su motivo.
- **Ventas:** el carrito es una venta en estado "en curso". Las acciones del carrito usan formularios normales; solo la búsqueda mientras se escribe usa JavaScript para no recargar la página.
- **Finanzas:** todas las fórmulas están en `finanzas/calculos.py`, para que el dashboard, los reportes y el punto de equilibrio usen siempre los mismos números (ver abajo).
- **Asistente:** `clients.py` habla con ChatGPT o Gemini, `services.py` tiene las funciones que el asistente puede ejecutar y `views.py` conecta todo con la pantalla.

**Fórmulas financieras implementadas**

| Concepto | Fórmula |
|---|---|
| Flujo de efectivo | Ingresos − egresos (gastos registrados). |
| Margen bruto de un producto | ((precio de venta − costo) ÷ precio de venta) × 100. |
| Margen operativo | ((ingresos − costo de ventas − gastos operativos) ÷ ingresos) × 100. |
| Utilidad neta | Ingresos − costo de ventas − gastos operativos − ISR RESICO. |
| ISR RESICO [13], [14] | Tasa × ingresos del periodo. La tasa depende de los ingresos de los últimos 12 meses: hasta $300,000 → 1.00 %; hasta $600,000 → 1.10 %; hasta $1,000,000 → 1.50 %; hasta $2,500,000 → 2.00 %; hasta $3,500,000 → 2.50 %. |
| Precio sugerido | Costo ÷ (1 − margen deseado). |
| Punto de equilibrio por categoría | PE = F ÷ Σ(wᵢ · rᵢ), donde F son los gastos fijos del mes, wᵢ es la proporción de ventas de la categoría i y rᵢ = (pᵢ − cvᵢ) ÷ pᵢ es su margen de contribución (pᵢ precio promedio y cvᵢ costo promedio por unidad). Después se reparte por categoría: Vᵢ = wᵢ · PE y Qᵢ = Vᵢ ÷ pᵢ. |

### 3.5.4 Problemas que encontramos y cómo los resolvimos

| Problema | Qué pasaba | Solución |
|---|---|---|
| Decimales de más en los totales | Al multiplicar cantidad por precio, el total podía quedar con 4 decimales. | Se redondea a 2 decimales en cada renglón y en el total. |
| No se podía eliminar una cuenta con ventas | La base protege a los productos que ya se vendieron y el borrado fallaba. | Antes de borrar, se eliminan los renglones de venta de ese negocio. |
| El asistente no recordaba nada | Cada mensaje empezaba una conversación nueva. | Se agregó la memoria de los últimos 10 mensajes. |
| Con Gemini solo se ejecutaba la primera función | "2 leches y 3 panes" solo agregaba uno. | Ahora se ejecutan todas las funciones que pida el modelo. |
| El asistente elegía en silencio entre productos parecidos | Si había "Coca 600" y "Coca 2L", agregaba cualquiera. | Ahora el asistente pregunta cuál de las opciones quiere. |
| Producto "no encontrado" y producto "dado de baja" eran lo mismo | Ambos estaban inactivos y no se podían distinguir. | Se agregó el campo "pendiente de validar". |
| Llamadas repetidas al modelo de lenguaje | Cada inicio de sesión generaba una llamada. | El resumen del día se guarda y se genera una sola vez al día. |
| Faltaban avisos en finanzas | Los mensajes "Gasto registrado" no se mostraban. | Se agregaron a la plantilla base de finanzas. |
| El ticket no mostraba la ubicación | Solo traía el nombre del negocio. | Se agregó la alcaldía. |
| Librerías instaladas en el lugar equivocado | Las instalaciones iban al Python general y no al entorno virtual. | Se documentó usar siempre `python -m pip install` con el entorno virtual activado. |

### 3.5.5 Cobertura de requisitos funcionales

Esta tabla compara los 34 requisitos de la sección 3.2.1 contra lo construido. Estados: **Implementado**, **Implementado (por validar en vivo)** cuando depende de cómo responda el modelo de lenguaje y falta probarlo con las llaves reales, **Parcial** y **Pendiente**.

| Código | Estado | Dónde está | Notas |
|---|---|---|---|
| RF-V01 | Implementado (por validar en vivo) | `avi/services.py`, `ventas/views.py` | Si hay varios productos parecidos, el asistente pregunta cuál. La tolerancia a errores de escritura depende del modelo de lenguaje. |
| RF-V02 | Implementado | `ventas/views.py` | Botones +/− y botón de quitar producto. |
| RF-V03 | Implementado | `ventas/views.py` (cobrar) | Todo en una sola transacción. |
| RF-V04 | Implementado | Pantalla de ventas | El total siempre está visible. |
| RF-V05 | Implementado | `ventas.js` | Botones y teclado, sin confirmaciones. |
| RF-V06 | Implementado | `ventas/views.py` (cancelar) | Confirmación simple. |
| RF-V07 | Implementado | `ventas/views.py`, inventario | El producto queda "pendiente de validar" y se completa desde Editar. |
| RF-V08 | Implementado | Plantilla del ticket | Nombre, alcaldía, fecha, hora, folio y detalle. |
| RF-I01 | Implementado | `inventario/models.py` | Todos los campos mínimos. |
| RF-I02 | Implementado | `inventario/views.py` | Motivo obligatorio, guardado en historial. |
| RF-I03 | **Parcial** | `inventario/views.py` (alertas) | Se ordena por qué tan abajo del mínimo está cada producto (criticidad), pero no por rotación de ventas. |
| RF-I04 | Implementado | `inventario/views.py` | Avisa si el producto tiene ventas; la baja es lógica. |
| RF-I05 | Implementado | `accounts/views.py`, `seed_catalogo` | Paso 3 del registro. |
| RF-I06 | **Parcial** | `inventario/views.py` | Búsqueda, filtro y orden por críticos; falta ordenar por mayor movimiento. |
| RF-I07 | Implementado | `inventario/views.py` | Con categorías que surte. |
| RF-F01 | Implementado | `finanzas/views.py` | Tipo fijo/variable y categorías propias. |
| RF-F02 | Implementado | `finanzas/calculos.py` | Fórmula por categoría con explicación sencilla. |
| RF-F03 | Implementado | `finanzas/views.py` | Aceptar, ajustar o rechazar. |
| RF-F04 | **Pendiente** | — | Solo existe la pantalla como maqueta. Se deja para la fase 2 (ver capítulo VI). |
| RF-F05 | Implementado | `finanzas/views.py` | Periodos de 3 y 6 meses, alertas de baja rotación y gasto inusual. |
| RF-AVI01 | Implementado (por validar en vivo) | `avi/clients.py` | Sin restricción por módulo. |
| RF-AVI02 | Implementado (por validar en vivo) | `avi/clients.py` | Varias funciones por mensaje, en ChatGPT y en Gemini. |
| RF-AVI03 | Implementado (por validar en vivo) | `avi/clients.py` | Instrucciones y ejemplos en el mensaje base. |
| RF-AVI04 | Implementado | `avi/services.py` | Funciones para consultar resumen financiero y punto de equilibrio. |
| RF-AVI05 | Implementado (por validar en vivo) | `avi/services.py`, `clients.py` | Parámetros obligatorios e instrucción de preguntar lo que falte. |
| RF-AVI06 | **Parcial** | — | Hoy el asistente no tiene acciones que no se puedan deshacer (agregar al carrito y registrar un gasto se corrigen), por eso aún no pide confirmación. Habrá que agregarla si se suman acciones como borrar. |
| RF-AVI07 | **Parcial** | `avi/services.py` | Recuerda los últimos 10 mensajes, incluso entre sesiones. Las preferencias guardadas son pocas (modelo elegido, icono, chat minimizado). |
| RF-AVI08 | Implementado | `avi/views.py` | Además se agregó el dictado por voz. |
| RF-S01 | Implementado | `accounts/forms.py` | Correo obligatorio. |
| RF-S02 | Implementado | `accounts/backends.py` | Correo o teléfono. |
| RF-S03 | Implementado | `accounts/urls.py` | En desarrollo el enlace sale en la terminal; falta configurar un servicio de correo real. |
| RF-S04 | Implementado | `accounts/views.py` | Pide contraseña y borra todo. |
| RF-S05 | **Parcial** | `static/js/app.js` | Hay consejos por módulo y botón de ayuda; falta el video de introducción. |
| RF-S06 | Implementado | `static/js/app.js` | Solo se refresca el contenido del módulo, sin perder el chat. |

**Resumen:** 23 implementados, 5 implementados por validar en vivo, 5 parciales y 1 pendiente (total 34).

### 3.5.6 Limitaciones conocidas

- **Pronóstico de ventas:** no está construido. Se dejó para la fase 2.
- **Video introductorio:** no se grabó.
- **Correo de recuperación:** funciona en modo desarrollo; falta conectar un servicio de correo real.
- **Internet:** el asistente la necesita siempre. Además, los iconos y la letra se descargan de internet.
- **Tamaño de datos:** el catálogo de inventario y el historial de ventas cargan todos los registros sin paginar. Con miles de productos o ventas se volverían lentos.
- **Categorías de productos compartidas:** hoy son las mismas para todos los negocios.
- **Roles:** no existe todavía un cajero con permisos distintos al dueño.
- **Costo de ventas:** se calcula con el costo actual del producto, no con el costo que tenía el día de la venta.
- **Servidor:** se usa el servidor de desarrollo de Django. Para un negocio real hay que cambiar algunas cosas (ver sección 3.7).
- **Asistente:** su comportamiento depende del modelo de lenguaje y no se puede garantizar al 100 %. **[COMPLETAR: si ya lo probaron con las llaves reales, decir cómo les fue.]**
