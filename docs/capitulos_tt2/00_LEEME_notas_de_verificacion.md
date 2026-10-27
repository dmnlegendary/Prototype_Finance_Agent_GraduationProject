# Notas de verificación de los capítulos 5 a 9

Estas notas son para ti, no para el documento. Explican qué encontré al comparar tu texto con el proyecto real, qué cambié y qué falta que llenes tú.

## 1. Cómo usar los archivos

Cada capítulo está en su propio archivo (`05_` a `09_`), con las referencias en `10_`. Todo lo que dice `[COMPLETAR]`, `[CONFIRMAR]` o `[DECIDIR]` sale resaltado en amarillo en el Word y es algo que no puedo saber yo. Las referencias están numeradas [1] a [17]; al unirlas con las del TT1 hay que renumerar. Los capítulos 10 y 11 no los toqué porque no me pasaste su texto.

## 2. Lo que no coincidía con el proyecto

Esta es la parte más importante. Muchas cosas del texto que pegaste no existen en el código o no coinciden con el historial de Git. En un documento que se defiende, un profesor puede abrir el sistema y preguntar por ellas. Esto fue lo que corregí.

| Decía el texto | Lo que hay en realidad | Qué hice |
|---|---|---|
| Seis sprints de junio a octubre, con PostgreSQL el 5 de junio | El primer código es del 16 de agosto y PostgreSQL entra el 12 de octubre | Reconstruí la tabla con el historial de Git |
| Ramas `dev` y `feature/...`, y `main` protegida | Hay `main` y ramas `Arif`, `Bernardo` y `machine`, `machine2` y `machine3`; hubo 2 pull requests y varios commits directos a `main` | Lo escribí como fue |
| Jorge hizo el asistente y la seguridad | Según Git, el asistente y casi todos los módulos son de Luis; Jorge hizo el pronóstico, PostgreSQL y cuentas de prueba | Lo dejé con `[CONFIRMAR]` |
| Semáforo: rojo con 2 o menos, amarillo de 3 a 5 y verde | Se calcula con el stock ideal: amarillo a la mitad, naranja a un cuarto y rojo en el mínimo | Corregido |
| Pronóstico con Random Forest, RMSE de 3.12, "zona A" y partición 80/20 | En la implementación inicial se comparaban regresión lineal, ARIMA (1,1,1) y Holt-Winters, con MAE sobre las últimas 4 semanas, para los 10 productos más vendidos. Tras la retroalimentación, el código actual usa únicamente ARIMA. No hay scikit-learn ni pandas | Reescribí 6.6 con lo real y dejé la tabla de resultados para que la llenes; después se unificó el pronóstico en ARIMA |
| Reentrenamiento quincenal y modelos guardados con joblib | Los modelos se ajustan cada vez que se abre la pantalla | Corregido en 9.3.3 |
| Tablas `Kardex`, `DetalleVenta`, `tiendita_project`, `pytest`, `django-cors-headers`, `google-genai`, `psycopg2` | Son `HistorialModificacionProducto`, `ItemVenta`, `config`, pruebas de Django, no hay CORS, el paquete actual es `google-genai` y el driver `psycopg` | Usé los nombres reales |
| Índice trigrama (`pg_trgm`) para buscar | La búsqueda se hace en memoria con el catálogo guardado en el caché | Corregido |
| El caché redujo las consultas 68 % | Nadie lo midió | Lo quité |
| Caja con atajo de teclado, `sessionStorage`, campo de efectivo y cambio, impuestos en el ticket, Escape que cierra el ticket | No existen. Las cajas se guardan en la base de datos, y no hay cálculo de cambio. Escape solo cierra la lista de resultados | Lo quité |
| Importar CSV con columnas `nombre, costo, stock_actual...`, que crea categorías y proveedores, 200 productos en 3.4 segundos | El archivo lleva producto, cantidad, precio de compra y precio de venta; hay pantalla de revisión; no crea nada sin confirmar; esos tiempos no se midieron | Corregido |
| Costo ponderado en cada compra | Se reemplaza por el último costo | Lo aclaré como simplificación |
| Gemini 1.5 Flash, límite de 10 peticiones por minuto, tabla `avi_consumoapi`, tope de 100 consultas al día, alerta al 80 %, tiempo de espera de 3 segundos | El modelo actual es Gemini 3.8 Flash mediante `google-genai`; el tiempo máximo es de 30 segundos y nada de lo demás existe | Lo pasé a "mejoras futuras" en 9.3.4 |
| Funciones `consultar_existencias`, `obtener_pronostico_demanda`... | Las 25 funciones tienen otros nombres, y no hay una de pronóstico | Usé las reales |
| El historial del chat se purga cada 24 horas | Se guarda y solo se muestran las últimas 24 horas | Corregido |
| El dictado de voz se procesa en el dispositivo | Depende del navegador, y en varios necesita internet | Corregido |
| Paleta con los colores de Bootstrap (`#28a745`...) | Los colores reales son otros (por ejemplo, verde `#16a34a`, rosa `#d6409f`) | Usé la descripción por significado |
| 38 pruebas con pytest y tiempos por prueba | Hay cerca de 300 pruebas con las herramientas de Django, y no se midieron tiempos por prueba | Corregido |
| Resultados y tiempos de las pruebas funcionales | No hay mediciones | Usé los casos que sí verificamos |
| Flujo de efectivo sin restar las compras; ISR con una tabla de "300,001 a 600,000" mezclada con ingresos mensuales | El flujo resta las compras. La ley tiene una tabla mensual (hasta 25,000, 50,000...) y el sistema usa la anual con los ingresos de 12 meses | Corregido y aclarado en 6.4.2 |
| Todo el despliegue local, sin Azure | Ustedes van a poner el frontend en Azure | Reescrito, con lo que falta como `[DECIDIR]` |
| Script `backup_diario.bat` y logs rotativos de 5 MB | No existen en el proyecto | Quedaron como recomendaciones |

## 3. Tres cosas delicadas

**Las fechas de los sprints.** Me pediste poner fechas "más o menos inventadas" para que cuadren con el cronograma. No lo hice, y creo que no hace falta. El historial de Git muestra que empezaron a construir a mediados de agosto, y tú mismo explicas el motivo: el retraso por atender las observaciones de los sinodales. Eso se puede contar tal cual. En 5.1.3 puse las fechas reales de Git, un párrafo que compara el cronograma del TT1 con lo que pasó y la explicación del retraso, y que el orden lógico del trabajo sí fue el mismo. Si pusieran fechas falsas, el repositorio las contradice, y cualquiera con acceso a GitHub puede verlo.

**Las pruebas de aceptación.** Como me dijiste que no se hicieron con tenderos usando el sistema, no podía llamarlas así. Convertí la sección 8.3 en "Validación con tenderos". Ahí van los resultados reales de su encuesta (7 respuestas), la observación en la tienda para que la completes, y la prueba de aceptación como pendiente, con las tareas y el cuestionario SUS listos. Si logran hacer aunque sea una sesión real antes de entregar, solo se llena la tabla 8.6. Si no, queda como trabajo pendiente en las limitaciones, y es una limitación válida y honesta.

**Quién propuso cada mejora.** Como no probaron el sistema con tenderos, quité de 5.2.4 la historia de "tres tenderos" con nombres y comentarios. Ahora el segunda caja, la regla de oro con stock cero y la importación desde CSV aparecen como decisiones de su análisis del mostrador, y lo que sí viene de la encuesta es la paleta de colores, el lenguaje sencillo y el video tutorial. Los negocios de la encuesta los dejé sin nombre. Donde dice `[COMPLETAR]` en 5.2.4 y 8.3.2 hay que poner lo que realmente observaron en la tienda.

Una nota sobre la encuesta: la pregunta de la calificación de 1 a 5 ("Conoce las funciones del marIA") solo tuvo 3 respuestas y no queda claro qué se preguntaba, así que no la usé. Además, entre los encuestados hay una farmacia, una frutería y un negocio de uñas, no solo abarrotes. Lo aclaré en el texto, porque un profesor lo notará.

## 4. Tus preguntas

En 6.5.1 preguntabas si "tablas finales" se refiere a los diagramas. No: son la descripción de las tablas, y el diagrama entidad-relación actualizado va en el capítulo 4. Agregué la idea de que las funciones nuevas son trabajo extra para tener un sistema útil.

En el capítulo 8 quité el 8.2 de integración y el 8.4 de rendimiento, como decías: la integración se junta con las pruebas funcionales y el rendimiento con las unitarias. Quedó 8.1 unitarias (locales y en la nube), 8.2 funcionales y 8.3 aceptación.

Sobre el video (9.2.1): recomiendo uno de 2 o 3 minutos tipo tráiler más clips cortos por módulo. Estoy de acuerdo con lo que comentan sobre que la gente prefiere abrir la aplicación directamente.

Sobre términos y condiciones (9.3.6): para un prototipo académico no son obligatorios, pero conviene un aviso corto. Además el sistema guarda nombre, teléfono y correo, así que un aviso de privacidad es buena idea, y la ley vigente es la de marzo de 2025. Revisen con sus directores si lo piden. Incluí un texto de ejemplo. También dice que, al usar el asistente, parte de la información de la tienda se envía a Google y OpenAI, que es cierto y es mejor decirlo.

Sobre el argumento de no tener roles (5.2.5): lo apoyé en que los micronegocios son la mayoría y en que el dueño o su familia atienden. Si tienen una observación directa de un tendero que lo respalde, es mejor ponerla.

## 5. Cómo medir los tiempos de la Tabla 6.2

Para comparar tiempos hay que correr las mismas operaciones con cada almacenamiento. Con el sistema configurado (primero con SQLite, y luego con `DB_NAME` en el `.env` para PostgreSQL) se puede abrir `python manage.py shell` y cronometrar.

```
import time
from accounts.models import Negocio
from inventario import busqueda
from finanzas import calculos
from datetime import date

negocio = Negocio.objects.first()

t = time.perf_counter()
busqueda.buscar(negocio, "coca")
print("buscar", time.perf_counter() - t)

t = time.perf_counter()
calculos.punto_equilibrio_negocio(negocio, date.today())
print("punto de equilibrio", time.perf_counter() - t)
```

Conviene repetir cada medición unas cinco veces y quedarse con el promedio. La primera suele ser más lenta, porque el caché está vacío.

## 6. Lo que falta por llenar

Tabla 6.2 (tiempos), tabla 6.3 (resultados del pronóstico), 5.1.3 (confirmar contra Jira y contra los cronogramas del TT1), 5.2.4 y 8.3.2 (la visita a la tienda), 8.3.3 (la prueba de aceptación, si se hace), Tabla 8.3 (pruebas con las APIs reales), el origen del historial de ventas en 6.5.3, el reparto de trabajo en 5.1.1, hardware en 7.2.2, costos en la Tabla 9.1, el despliegue en Azure en 9.1.1, 9.1.3 y 9.1.4, los enlaces de los videos y el script de respaldo. Además, las referencias con `[CONFIRMAR]` están sin verificar. Los enlaces que sí abrí y revisé tienen fecha de acceso.
