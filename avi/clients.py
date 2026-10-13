"""
Wrappers para hablar con la API de ChatGPT o de Gemini, con function calling
ya declarado (ver services.py). Para que esto funcione de verdad falta:
  1. pip install -r requirements.txt (ya incluye openai y google-generativeai)
  2. tener las llaves de las APIs: corre `python manage.py configurar_ia`
"""
import json
import logging
import time

from django.conf import settings

from . import services

registro = logging.getLogger(__name__)


class SinLlaveError(Exception):
    """No hay ninguna llave de API configurada."""


# pistas en el texto del error de una falla "pasajera" (saturación, límite por minuto, red)
# que vale la pena volver a intentar unos segundos después
FALLAS_PASAJERAS = (
    "429", "500", "502", "503", "504", "timeout", "timed out", "overloaded", "unavailable",
    "rate limit", "resource exhausted", "connection", "temporarily",
)


def con_reintentos(llamada, intentos=3, espera=1.5):
    """Ejecuta `llamada()`; si falla por algo pasajero (la IA saturada, por ejemplo)
    espera un poco y lo vuelve a intentar, hasta `intentos` veces."""
    for numero in range(1, intentos + 1):
        try:
            return llamada()
        except ImportError:
            raise
        except Exception as error:
            es_pasajera = any(pista in str(error).lower() for pista in FALLAS_PASAJERAS)
            if numero == intentos or not es_pasajera:
                raise
            time.sleep(espera * numero)


def mensaje_de_error(error):
    """Un texto claro para el tendero según lo que falló (el detalle técnico
    se queda en la terminal, ver registro.exception en views.py)."""
    texto = str(error).lower()
    if "429" in texto or "quota" in texto or "rate limit" in texto or "resource exhausted" in texto:
        return "La IA alcanzó su límite de uso por ahora. Espera un minuto e intenta de nuevo."
    if any(pista in texto for pista in ("api key", "api_key", "401", "403", "unauthorized", "permission")):
        return "La llave de IA no es válida o no tiene permiso. Revísala con: python manage.py configurar_ia"
    if "timeout" in texto or "timed out" in texto:
        return "La IA tardó demasiado en contestar. Intenta de nuevo."
    if "503" in texto or "overloaded" in texto or "unavailable" in texto:
        return "La IA está saturada en este momento. Intenta de nuevo en unos segundos."
    return "No pude conectarme con el modelo de lenguaje en este momento."


MENSAJE_SIN_LLAVE = (
    "Todavía no hay una llave de IA configurada. En la terminal corre: python manage.py configurar_ia"
)

# cuántas veces seguidas puede la IA pedir funciones antes de darle una respuesta al usuario
MAXIMO_DE_RONDAS = 3

SYSTEM_PROMPT = (
    "Eres marIA, el Asistente Virtual Inteligente (AVI) de una tienda de abarrotes. "
    "Ayudas al dueño a vender, revisar su inventario y llevar sus finanzas. "
    "Responde siempre en español, de forma breve y amigable. Explica todo de forma sencilla: "
    "quien te usa es el dueño de una tiendita que muy probablemente no tuvo muchos estudios, "
    "así que evita tecnicismos, usa palabras simples y ve directo al grano. Nunca des "
    "explicaciones largas.\n\n"
    "Todo lo que el dueño puede hacer a mano en la pantalla donde está, tú lo puedes hacer con las "
    "funciones disponibles. Cuando pida una acción, usa la función de inmediato en vez de inventar "
    "la respuesta. Solo tienes las funciones de la pantalla actual: si te pide algo que se hace en "
    "otra pantalla (Módulo de ventas, Auxiliar de inventario o Agente financiero), dile con "
    "amabilidad en cuál se hace.\n\n"
    "Regla de oro: no se puede vender lo que no hay en el inventario. Si falta, pregunta cuántas "
    "piezas (o kilos, en productos a granel) quiere agregar y a qué precio de compra, agrégalas "
    "con ajustar_existencias y sigue con la venta.\n\n"
    "Si te falta un dato necesario para hacer lo que te pidieron (por ejemplo el monto de un "
    "gasto, el costo de un producto nuevo, o a qué producto se refiere), pregúntalo primero y "
    "espera la respuesta — nunca inventes el dato ni ejecutes la acción a medias.\n\n"
    "Para cancelar una venta o dar de baja un producto, primero pregunta si está seguro y solo "
    "cuando conteste que sí vuelve a llamar la función con confirmar=true.\n\n"
    "Cuando te pregunten por sus finanzas (ganancias, utilidad, impuestos, punto de equilibrio), "
    "consulta las funciones y explica el resultado con palabras sencillas y un ejemplo del día a "
    "día, sin fórmulas ni términos contables.\n\n"
    "Para saber qué productos hay, cuántos son o cuántos de un tipo (por ejemplo 'aguas'), usa "
    "consultar_inventario o buscar_producto con una palabra: nunca digas que solo puedes buscar "
    "uno por uno. Si te dictan un correo con la palabra 'arroba', escríbelo con @.\n\n"
    "El pronóstico de ventas todavía está en construcción: si lo piden, dilo con sinceridad y ofrece "
    "mejor las ventas de hoy o el punto de equilibrio. No puedes cambiar todos los productos de un "
    "jalón; si lo piden, explica que se hace producto por producto.\n\n"
    "Si la petición no tiene que ver con la tienda o no la entendiste, no digas solamente que no "
    "puedes ayudar: explica brevemente qué sí puedes hacer y dale uno o dos ejemplos concretos, "
    "como 'agrega 2 cocas al carrito' o 'registra un gasto de luz de 450 pesos'."
)

PROMPT_RESUMEN = (
    "Eres marIA, la asistente de una tienda de abarrotes. Explica los números al dueño de la "
    "tienda en español, con palabras de todos los días, sin tecnicismos ni fórmulas. Sé breve y "
    "amigable, y termina siempre con consejos prácticos."
)


def modelos_en_orden():
    """Los modelos que se pueden usar, en el orden en que se intentan:
    primero Gemini y, si no contesta, ChatGPT. Solo entran los que tienen llave."""
    modelos = []
    if settings.GEMINI_API_KEY:
        modelos.append("gemini")
    if settings.OPENAI_API_KEY:
        modelos.append("chatgpt")
    return modelos


def _instrucciones(negocio, pantalla=None):
    """Las instrucciones fijas, en qué pantalla está el usuario y cómo va la tienda ahorita (del cache)."""
    nombre_pantalla = services.NOMBRES_DE_PANTALLA.get(pantalla)
    donde_esta = f"\n\nEl usuario está en la pantalla: {nombre_pantalla}." if nombre_pantalla else ""
    return (
        SYSTEM_PROMPT
        + donde_esta
        + "\n\nDatos de la tienda ahorita (úsalos para contestar sin ejecutar funciones cuando te alcancen):\n"
        + services.contexto_negocio(negocio)
    )


def preguntar_chatgpt(mensaje, negocio, pantalla=None, funciones_ejecutadas=None):
    """Regresa (respuesta_en_texto, nombres_de_funciones_ejecutadas)."""
    if funciones_ejecutadas is None:
        funciones_ejecutadas = []
    if not settings.OPENAI_API_KEY:
        return MENSAJE_SIN_LLAVE, []

    from openai import OpenAI

    cliente = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30)
    mensajes = [{"role": "system", "content": _instrucciones(negocio, pantalla)}]
    for previo in services.historial_reciente(negocio):
        rol = "user" if previo.rol == previo.Rol.USUARIO else "assistant"
        mensajes.append({"role": rol, "content": previo.mensaje})
    mensajes.append({"role": "user", "content": mensaje})

    for _ in range(MAXIMO_DE_RONDAS):
        respuesta = con_reintentos(lambda: cliente.chat.completions.create(
            model="gpt-4o-mini", messages=mensajes, tools=services.tools_openai(pantalla),
        ))
        mensaje_respuesta = respuesta.choices[0].message

        if not mensaje_respuesta.tool_calls:
            return mensaje_respuesta.content or "No supe qué responder, ¿me lo repites?", funciones_ejecutadas

        mensajes.append(mensaje_respuesta)
        ejecuciones = []
        for llamada in mensaje_respuesta.tool_calls:
            argumentos = json.loads(llamada.function.arguments or "{}")
            resultado = services.ejecutar_funcion(llamada.function.name, argumentos, negocio)
            ejecuciones.append((llamada.function.name, resultado))
            mensajes.append({
                "role": "tool",
                "tool_call_id": llamada.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            })
        funciones_ejecutadas += [nombre for nombre, _ in ejecuciones]

        # si solo fueron acciones, se contesta con su mensaje y se ahorra otra llamada a la IA
        directa = services.respuesta_directa(ejecuciones)
        if directa:
            return directa, funciones_ejecutadas

    return "No pude terminar lo que me pediste. Intenta decírmelo de forma más sencilla.", funciones_ejecutadas


def _texto_de_gemini(respuesta):
    try:
        return respuesta.text
    except ValueError:
        # Gemini a veces contesta sin texto (por ejemplo si bloquea la respuesta)
        return ""


def preguntar_gemini(mensaje, negocio, pantalla=None, funciones_ejecutadas=None):
    """Regresa (respuesta_en_texto, nombres_de_funciones_ejecutadas)."""
    if funciones_ejecutadas is None:
        funciones_ejecutadas = []
    if not settings.GEMINI_API_KEY:
        return MENSAJE_SIN_LLAVE, []

    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    modelo = genai.GenerativeModel(
        "gemini-2.5-flash",
        tools=services.tools_gemini(pantalla),
        system_instruction=_instrucciones(negocio, pantalla),
    )
    historial = [
        {"role": "user" if previo.rol == previo.Rol.USUARIO else "model", "parts": [previo.mensaje]}
        for previo in services.historial_reciente(negocio)
    ]
    # Gemini exige que la conversación empiece con un mensaje del usuario
    while historial and historial[0]["role"] == "model":
        historial.pop(0)
    chat = modelo.start_chat(history=historial)
    respuesta = con_reintentos(lambda: chat.send_message(mensaje, request_options={"timeout": 30}))

    for _ in range(MAXIMO_DE_RONDAS):
        llamadas = [
            parte.function_call
            for parte in respuesta.candidates[0].content.parts
            if getattr(parte, "function_call", None)
        ]
        if not llamadas:
            return _texto_de_gemini(respuesta) or "No supe qué responder, ¿me lo repites?", funciones_ejecutadas

        ejecuciones = []
        partes_respuesta = []
        for fn in llamadas:
            resultado = services.ejecutar_funcion(fn.name, dict(fn.args), negocio)
            ejecuciones.append((fn.name, resultado))
            partes_respuesta.append(genai.protos.Part(
                function_response=genai.protos.FunctionResponse(name=fn.name, response=resultado),
            ))
        funciones_ejecutadas += [nombre for nombre, _ in ejecuciones]

        directa = services.respuesta_directa(ejecuciones)
        if directa:
            return directa, funciones_ejecutadas

        respuesta = con_reintentos(lambda: chat.send_message(genai.protos.Content(parts=partes_respuesta)))

    return "No pude terminar lo que me pediste. Intenta decírmelo de forma más sencilla.", funciones_ejecutadas


def preguntar_ia(mensaje, negocio, pantalla=None):
    """El chat del asistente. Intenta con Gemini y, si falla, con ChatGPT.
    Regresa (respuesta_en_texto, nombres_de_funciones_ejecutadas).

    Si el primer modelo ya alcanzó a ejecutar una acción (agregar al carrito, registrar un
    gasto...) y falla después, NO se intenta con el otro: la acción se haría dos veces."""
    modelos = modelos_en_orden()
    if not modelos:
        return MENSAJE_SIN_LLAVE, []

    preguntar = {"gemini": preguntar_gemini, "chatgpt": preguntar_chatgpt}
    ultimo_error = None
    for modelo in modelos:
        ejecutadas = []
        try:
            return preguntar[modelo](mensaje, negocio, pantalla, ejecutadas)
        except Exception as error:
            if ejecutadas:
                raise
            registro.warning("Falló %s, se intenta con el siguiente modelo: %s", modelo, error)
            ultimo_error = error
    raise ultimo_error


def _texto_con_gemini(prompt):
    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    modelo_gemini = genai.GenerativeModel("gemini-2.5-flash", system_instruction=PROMPT_RESUMEN)
    return con_reintentos(lambda: modelo_gemini.generate_content(prompt, request_options={"timeout": 30})).text


def _texto_con_chatgpt(prompt):
    from openai import OpenAI

    cliente = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30)
    respuesta = con_reintentos(lambda: cliente.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": PROMPT_RESUMEN}, {"role": "user", "content": prompt}],
    ))
    return respuesta.choices[0].message.content


def generar_texto(prompt):
    """Una sola pregunta a la IA, sin funciones ni historial. Es la que usan los
    resúmenes (de ayer, del dashboard y de los reportes). Primero Gemini y, si falla, ChatGPT.

    Lanza SinLlaveError si no hay ninguna llave configurada."""
    modelos = modelos_en_orden()
    if not modelos:
        raise SinLlaveError(MENSAJE_SIN_LLAVE)

    generar = {"gemini": _texto_con_gemini, "chatgpt": _texto_con_chatgpt}
    ultimo_error = None
    for modelo in modelos:
        try:
            return generar[modelo](prompt)
        except Exception as error:
            registro.warning("Falló %s, se intenta con el siguiente modelo: %s", modelo, error)
            ultimo_error = error
    raise ultimo_error
