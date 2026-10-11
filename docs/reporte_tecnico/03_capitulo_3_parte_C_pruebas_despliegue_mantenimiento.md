## 3.6 Plan de Pruebas

### Objetivo y estrategia

Las pruebas sirven para comprobar que el sistema hace lo que prometen los requisitos y que no se rompe cuando se le cambia algo. Combinamos dos tipos:

- **Pruebas automáticas:** son programas pequeños que usan el sistema por nosotros y revisan los resultados. Se pueden repetir en segundos cada vez que cambiamos código. Están en los archivos `tests.py` de cada módulo.
- **Pruebas manuales:** las hace una persona siguiendo un guion (por ejemplo, simular un día de trabajo en la tienda). Se usan para lo que es difícil automatizar, como la facilidad de uso o las respuestas del asistente con ChatGPT y Gemini.

En total hay **61 pruebas automáticas**: 8 unitarias y 53 de integración. Se ejecutan con el entorno virtual activado:

```
python manage.py test
```

Django crea una base de datos temporal solo para las pruebas, así que **no toca los datos reales** de la tienda. Las pruebas del asistente simulan la respuesta de ChatGPT/Gemini, por lo que no gastan saldo ni necesitan internet.

> **Importante para el equipo:** los resultados reales de cada prueba (columnas "Obtenido") **solo se pueden llenar después de ejecutarlas**. No dejen la columna con resultados inventados. Si alguna prueba falla, se anota, se corrige el código y se vuelve a ejecutar. Resultado de la última ejecución: **[COMPLETAR: por ejemplo "Ran 61 tests... OK" con fecha]**.

---

### 3.6.1 Pruebas Unitarias

Una prueba unitaria revisa una sola operación, sola, sin pantallas ni base de datos. Aquí probamos sobre todo las **fórmulas**, que son lo más delicado: si fallan, el tendero toma malas decisiones con dinero.

| Código | Qué se prueba | Dato de entrada | Resultado esperado | Obtenido |
|---|---|---|---|---|
| PU-01 | Punto de equilibrio con el **ejemplo numérico de nuestro documento** (3 categorías) | F = 30,000; w = 0.50/0.20/0.30; p = 25/18/12; cv = 15/12/8 | PE = $81,818.18; bebidas deben vender $40,909.09 (1,637 unidades) | **[COMPLETAR]** |
| PU-02 | Punto de equilibrio cuando se vende por debajo del costo | Precio 10, costo 12 | No existe punto de equilibrio | **[COMPLETAR]** |
| PU-03 | Tasa de ISR RESICO en los límites de cada rango | $300,000; $300,001; $600,001; $1,000,001; $3,500,000 | 1.00 %; 1.10 %; 1.50 %; 2.00 %; 2.50 % | **[COMPLETAR]** |
| PU-04 | Precio sugerido | Costo 15 y margen 40 %; costo 18 y margen 30 % | $25.00 y $25.71 | **[COMPLETAR]** |
| PU-05 | Flujo de efectivo, margen operativo, ISR y utilidad neta | Ingresos 100,000; costo de ventas 60,000; gastos 20,000; tasa 1 % | Flujo 80,000; margen 20.0 %; ISR 1,000; utilidad neta 19,000 | **[COMPLETAR]** |
| PU-06 | Subtotal con 2 decimales | 1.5 unidades × $12.99 | $19.49 | **[COMPLETAR]** |
| PU-07 | Margen bruto de un producto | Costo 15, precio 25 | 40.0 % | **[COMPLETAR]** |
| PU-08 | Producto en nivel crítico | Cantidad actual igual al mínimo | Es crítico; con una unidad más ya no | **[COMPLETAR]** |

### 3.6.2 Pruebas de Integración

Estas pruebas revisan que varias partes trabajen bien juntas: la pantalla (vista), las reglas y la base de datos. Por ejemplo, que al cobrar una venta de verdad baje el inventario.

| Grupo | Qué comprueban | Requisitos | Archivo | Pruebas |
|---|---|---|---|---|
| Carrito y cobro | Abrir la pantalla; agregar productos; subir y bajar cantidades (bajar a cero lo quita); quitar de un golpe; cobrar descuenta el inventario y cierra la venta; cancelar no mueve el inventario; el total se guarda con 2 decimales | RF-V02 a RF-V06, RNF-11 | `ventas/tests.py` | 6 |
| Producto no encontrado y búsqueda | El producto no encontrado queda "pendiente de validar" e inactivo; la búsqueda instantánea encuentra por nombre | RF-V01, RF-V07 | `ventas/tests.py` | 2 |
| Ticket | El ticket muestra nombre y ubicación del negocio | RF-V08 | `ventas/tests.py` | 1 |
| Aislamiento entre negocios (ventas) | Otro negocio no puede quitar productos de mi carrito (error 404) | RNF-06 | `ventas/tests.py` | 1 |
| Inventario | Las pantallas abren; alta de producto; editar sin motivo no cambia nada; editar con motivo guarda cambio e historial; la baja conserva las ventas anteriores; un producto pendiente se activa al completarlo; las alertas ponen primero lo más crítico; otro negocio no puede editar mi producto | RF-I01 a RF-I04, RF-V07, RNF-06 | `inventario/tests.py` | 8 |
| Inicio de sesión y seguridad | Entrar con correo, con correo en mayúsculas y con teléfono; contraseña incorrecta no entra; las pantallas piden sesión | RF-S02, RNF-06 | `accounts/tests.py` | 5 |
| Registro | Registro correcto; el correo es obligatorio; no se repiten correo ni teléfono | RF-S01 | `accounts/tests.py` | 4 |
| Recuperar contraseña | Se manda el enlace al correo registrado; con un correo desconocido no se manda nada | RF-S03 | `accounts/tests.py` | 2 |
| Eliminar cuenta | Con la contraseña correcta se borra todo (incluso con ventas); con una incorrecta no se borra nada | RF-S04 | `accounts/tests.py` | 2 |
| Chat del asistente | Guarda el historial y pide refrescar la pantalla cuando cambia algo; una consulta no refresca; un mensaje vacío no llama al modelo; el resumen se pide a la IA una sola vez al día; el chat pide sesión | RF-AVI08, RF-S06, RF-AVI04 | `avi/tests.py` | 5 |
| Memoria del asistente | El historial reciente trae los últimos 10 mensajes en orden | RF-AVI07 | `avi/tests.py` | 1 |
| Funciones del asistente | Si hay productos parecidos pregunta cuál; si hay uno solo lo agrega; si no existe avisa; una función inexistente da error; registrar gasto | RF-V01, RF-AVI02, RF-AVI05 | `avi/tests.py` | 5 |
| Finanzas con datos reales | Todas las pantallas abren con y sin datos; punto de equilibrio con ventas y gastos reales ($1,000 en el ejemplo); mensajes cuando faltan gastos fijos o ventas; resumen del mes con ISR; el ISR depende del régimen; precio sugerido en pantalla; aceptar un precio lo cambia y guarda historial; un precio inválido no cambia nada; registrar un gasto con una categoría nueva | RF-F01, RF-F02, RF-F03, RF-F05 | `finanzas/tests.py` | 11 |
| **Total** | | | | **53** |

Resultado de la ejecución: **[COMPLETAR]**.

### 3.6.3 Pruebas Funcionales

Las pruebas funcionales revisan el sistema completo como lo usaría el tendero. Hacemos **una simulación de un día completo en una tienda de abarrotes**, siguiendo este guion con datos de ejemplo (catálogo precargado de 20 productos con `python manage.py seed_catalogo`).

| Código | Momento del día | Acción | Resultado esperado | Obtenido | Estado |
|---|---|---|---|---|---|
| PF-01 | Apertura | Iniciar sesión con correo | Entra al punto de venta y aparece el resumen del día en el chat con dos botones | **[COMPLETAR]** | |
| PF-02 | Mañana | Vender 10 tickets con 1 a 4 productos cada uno | Cada cobro baja el inventario y genera folio y ticket | **[COMPLETAR]** | |
| PF-03 | Mañana | Cambiar cantidades con los botones y con el teclado (+ y −) | El total se actualiza al instante | **[COMPLETAR]** | |
| PF-04 | Mañana | Vender un producto que no está en el catálogo | La venta no se detiene; el producto queda "pendiente de validar" | **[COMPLETAR]** | |
| PF-05 | Mañana | Cancelar una venta a medias | Pide confirmación; el inventario no cambia | **[COMPLETAR]** | |
| PF-06 | Mediodía | Un producto llega a su mínimo | Aparece la alerta roja y el producto sale primero en el catálogo | **[COMPLETAR]** | |
| PF-07 | Mediodía | Completar los datos del producto pendiente | Se activa y aparece en el catálogo normal | **[COMPLETAR]** | |
| PF-08 | Tarde | Dar de alta un producto nuevo con una categoría nueva | Aparece en el catálogo y se puede vender | **[COMPLETAR]** | |
| PF-09 | Tarde | Cambiar el precio de un producto y escribir el motivo | Sin el motivo no deja guardar | **[COMPLETAR]** | |
| PF-10 | Tarde | Registrar renta (fijo) y bolsas (variable) | Los totales del mes se actualizan | **[COMPLETAR]** | |
| PF-11 | Cierre | Ver punto de equilibrio, precios sugeridos y reportes | Las cifras coinciden con lo vendido y lo gastado en el día | **[COMPLETAR]** | |
| PF-12 | Cierre | Revisar el historial de ventas y de gastos | Aparece todo lo registrado | **[COMPLETAR]** | |

**Pruebas del asistente con ChatGPT y Gemini reales.** Como la respuesta depende del modelo de lenguaje, estas frases deben probarse con las llaves de API puestas, en los dos modelos:

| Código | Lo que se escribe o se dice | Comportamiento esperado | Requisito | Obtenido |
|---|---|---|---|---|
| PA-01 | "agrega 2 pepsis" | Agrega 2 al carrito y la tabla se actualiza sola | RF-V01, RF-S06 | **[COMPLETAR]** |
| PA-02 | "agrega 5 leches y 2 panes" | Agrega los dos productos con sus cantidades | RF-AVI02 | **[COMPLETAR]** |
| PA-03 | "agrega coca" (hay Coca 600 y Coca 2L) | Pregunta cuál de las dos | RF-V01 | **[COMPLETAR]** |
| PA-04 | "¿cuánto cuesta?" justo después de nombrar un producto | Entiende de qué producto se habla | RF-AVI07 | **[COMPLETAR]** |
| PA-05 | "registra un gasto de luz" (sin monto) | Pregunta el monto antes de registrar | RF-AVI05 | **[COMPLETAR]** |
| PA-06 | "registra un gasto de luz de 450 pesos fijo" | Lo registra y lo confirma | RF-AVI02 | **[COMPLETAR]** |
| PA-07 | "¿cómo voy este mes?" estando en Ventas | Responde con las finanzas del mes aunque esté en otro módulo | RF-AVI01, RF-AVI04 | **[COMPLETAR]** |
| PA-08 | "¿cuál es mi punto de equilibrio?" | Lo explica con palabras sencillas | RF-AVI04 | **[COMPLETAR]** |
| PA-09 | "¿quién ganó el mundial?" | Explica qué sí puede hacer y da ejemplos | RF-AVI03 | **[COMPLETAR]** |
| PA-10 | Lo mismo que PA-01 pero por voz (micrófono) en Chrome | El texto aparece en el cuadro y se puede enviar | RF-AVI08 | **[COMPLETAR]** |

### 3.6.4 Pruebas de Aceptación

La prueba de aceptación la hacen las personas para quienes se hizo el sistema: los **tenderos**. Se trata de ver si de verdad pueden usarlo.

- **Participantes:** **[COMPLETAR: cuántos tenderos, de qué tipo de tienda y alcaldía, y cómo los contactaron]**.
- **Fechas y lugar:** **[COMPLETAR]**.
- **Cómo se hizo:** a cada persona se le explica en pocas palabras para qué sirve el sistema y se le piden las tareas de la tabla, sin ayudarle. Quien observa anota si lo logró, cuánto tardó y si pidió ayuda. Al final contesta la encuesta del Anexo C.

| Tarea | Qué se le pide | Qué se mide |
|---|---|---|
| T1 | Registrar una venta de 3 productos y cobrarla | Tiempo y errores |
| T2 | Vender un producto que no está en el sistema | Si lo logra sin ayuda |
| T3 | Dar de alta un producto nuevo | Tiempo y errores |
| T4 | Pedirle al asistente que agregue un producto al carrito | Si lo logra sin ayuda |
| T5 | Registrar un gasto de luz | Si lo logra sin ayuda |
| T6 | Encontrar cuánto necesita vender al mes para no perder dinero | Si entiende la explicación |

**Criterios para dar por aceptado el sistema [AJUSTAR]:**

- Al menos 8 de cada 10 tenderos terminan las tareas T1 a T5 sin ayuda.
- Registrar una venta de 3 productos toma menos de 1 minuto después del tutorial.
- La calificación promedio de facilidad de uso en la encuesta es de 4 o más sobre 5, y la calificación SUS [15] (escala de usabilidad del Anexo C) es de 68 o más.

**Resultados:** **[COMPLETAR cuando se haga la prueba. No se deben escribir cifras que no se hayan medido.]**

---

## 3.7 Implementación o despliegue

### 3.7.1 Qué se necesita

- Computadora con **Windows 10 u 11**.
- **Python 3.12** instalado (al instalarlo hay que marcar la casilla "Add Python to PATH").
- Un navegador moderno (**Chrome o Edge** recomendados; el dictado por voz no funciona en todos).
- **Internet** para usar el asistente y para que se carguen los iconos y la letra.
- Una llave de API de OpenAI y/o de Google (Gemini) para el asistente.

### 3.7.2 Instalación paso a paso

El sistema no se instala con un programa tradicional. Se copia la carpeta del proyecto y se levanta un servidor pequeño en la misma computadora. Pasos (en la carpeta del proyecto, con PowerShell):

1. Crear el entorno virtual (una carpeta con las librerías del sistema, separada del resto de la computadora):
   ```
   python -m venv .venv
   ```
2. Activarlo. Si PowerShell no deja, antes se corre `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`:
   ```
   .venv\Scripts\Activate.ps1
   ```
   Se sabe que quedó activo porque el renglón empieza con `(.venv)`.
3. Instalar las librerías (siempre con `python -m pip`, para que se instalen en el entorno correcto):
   ```
   python -m pip install -r requirements.txt
   ```
4. Crear el archivo `.env` junto a `manage.py` con las llaves de API:
   ```
   OPENAI_API_KEY=sk-...
   GEMINI_API_KEY=...
   ```
5. Crear las tablas de la base de datos:
   ```
   python manage.py makemigrations
   python manage.py migrate
   ```
6. Cargar el catálogo de productos de ejemplo (el paso 3 del registro lo necesita):
   ```
   python manage.py seed_catalogo
   ```
7. Opcional, crear un usuario administrador:
   ```
   python manage.py createsuperuser
   ```
8. Levantar el sistema:
   ```
   python manage.py runserver
   ```
9. Abrir en el navegador `http://127.0.0.1:8000/` y crear la cuenta en `/cuenta/registro/`.

**Para el uso diario** se puede preparar un acceso directo (archivo `.bat`) que active el entorno y levante el servidor con un doble clic. **[AJUSTAR: si lo hacen, agregar aquí cómo quedó.]**

### 3.7.3 Qué cambiar antes de usarlo en un negocio real

Hoy el proyecto está en modo de desarrollo. Antes de entregarlo a un negocio habría que:

- Poner `DEBUG = False` y cambiar la `SECRET_KEY` por una propia y secreta (la actual es de ejemplo).
- Configurar `ALLOWED_HOSTS` con el nombre o IP que se vaya a usar.
- Usar un servidor de producción en lugar del servidor de desarrollo de Django (por ejemplo, `waitress` en Windows) y preparar los archivos estáticos con `collectstatic`.
- Conectar un servicio de correo real (SMTP) para que el enlace de recuperar contraseña llegue al correo y no a la terminal.
- Guardar los iconos y la letra dentro del proyecto si se quiere trabajar sin internet.
- Agregar paginación al catálogo y al historial de ventas si el negocio tiene miles de registros.
- Programar los respaldos de la sección 3.9.

---

## 3.8 Capacitación de Usuarios

Pensamos en un tendero que no tiene tiempo para cursos largos y que seguramente no estudió computación. Por eso, la capacitación está **dentro del propio sistema**, y se complementa con material corto.

**Ayudas que ya trae el sistema:**

- **Consejos la primera vez.** Al entrar por primera vez a Ventas, Inventario o Finanzas aparecen 2 o 3 globos que señalan los botones importantes (por ejemplo "Busca un producto aquí" o "Cobra desde aquí"). Con "Omitir" se cierran y no vuelven a salir solos.
- **Botón "?".** En la barra de arriba, para volver a ver los consejos de la pantalla en cualquier momento.
- **El asistente como guía.** Si el tendero pide algo que el sistema no entiende, el asistente le explica qué puede pedirle y le da ejemplos ("agrega 2 cocas al carrito", "registra un gasto de luz de 450 pesos"). También puede hacerlo por voz.
- **Resumen del día.** Cada día el asistente le cuenta, en palabras simples, cómo le fue ayer y le da una recomendación.
- **Mensajes claros y confirmaciones** antes de acciones delicadas (cancelar una venta, dar de baja, eliminar la cuenta).
- **Explicaciones en las pantallas financieras** ("En palabras simples…") y colores con significado.

**Material y sesión de entrenamiento [AJUSTAR]:**

| Tema | Duración propuesta | Material |
|---|---|---|
| Registro y primer ingreso | 10 min | Manual de usuario, sección 1 |
| Cómo vender (buscar, cobrar, cancelar, producto no encontrado) | 15 min | Manual de usuario, sección 2 |
| Inventario (alta, editar, alertas, proveedores) | 15 min | Manual de usuario, sección 3 |
| Gastos y reportes sencillos | 10 min | Manual de usuario, sección 4 |
| Hablar con el asistente | 10 min | Guía rápida de 1 hoja con ejemplos de frases |

Estrategia: una sesión práctica corta con el sistema abierto en la tienda, seguida de **autoservicio guiado** (los consejos y el asistente). Como evaluación, la persona realiza las tareas T1 a T5 de la prueba de aceptación.

**Pendiente:** el video introductorio que pide el requisito RF-S05 no se grabó. Queda como trabajo futuro.

---

## 3.9 Plan de Mantenimiento

Mantener el sistema es cuidar que siga funcionando y mejorarlo con el tiempo. Lo dividimos en cuatro tipos:

- **Correctivo:** arreglar errores que se encuentren.
- **Preventivo:** hacer revisiones y respaldos para que no ocurran fallas.
- **Adaptativo:** ajustar el sistema a cambios de afuera (por ejemplo, nuevas tasas del SAT o cambios en las API de ChatGPT o Gemini).
- **Perfectivo:** agregar mejoras, como el pronóstico de ventas.

**Rutinas propuestas [AJUSTAR]:**

| Rutina | Cada cuánto | Cómo |
|---|---|---|
| **Respaldo de la base de datos** | Diario (o al cerrar la tienda) | Con el sistema cerrado, copiar el archivo `db.sqlite3` a una memoria USB o a otra carpeta, con la fecha en el nombre. También se puede exportar con `python manage.py dumpdata`. |
| Probar que el respaldo sirve | Cada mes | Restaurar el respaldo en otra carpeta y abrir el sistema. |
| Revisión del gasto en las API | Cada mes | Revisar en OpenAI y Google cuánto se ha consumido. El resumen del día y el chat generan costo. |
| Cambio de llaves de API | Cada 6 meses o si se filtraron | Cambiarlas en el archivo `.env`. Nunca se suben al repositorio. |
| Actualizar librerías | Cada 3 meses | Revisar versiones, instalar con `python -m pip install -r requirements.txt` y correr `python manage.py test` antes de usar. |
| Revisar las tasas de ISR RESICO | Cada año | Si el SAT cambia la tabla, se modifica en `finanzas/calculos.py` y se actualiza la prueba PU-03. |
| Limpiar el historial del chat | Cada año | El historial de conversación crece; se puede depurar lo más viejo. |

**Cómo actualizar el sistema sin perder datos:**

1. Hacer un respaldo de `db.sqlite3`.
2. Copiar la versión nueva del código.
3. Instalar las librerías (`python -m pip install -r requirements.txt`).
4. Aplicar los cambios de la base con `python manage.py migrate`.
5. Correr `python manage.py test`.
6. Levantar el sistema y probar una venta.

**Cómo restaurar:** con el sistema cerrado, reemplazar `db.sqlite3` por el respaldo y volver a levantarlo.

**Soporte:** **[COMPLETAR: quién atiende los problemas, por qué medio y en cuánto tiempo.]**

**Reentrenamiento del pronóstico.** Cuando se construya el modelo de pronóstico (fase 2), cada cierto tiempo habrá que volver a calcularlo con las ventas nuevas para que no se desactualice. Por ahora no aplica porque ese modelo todavía no existe.
