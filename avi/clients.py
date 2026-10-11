"""
Wrappers para hablar con la API de ChatGPT o de Gemini, con function calling
ya declarado (ver services.py). Para que esto funcione de verdad falta:
  1. pip install -r requirements.txt (ya incluye openai y google-generativeai)
  2. tener las llaves de las APIs: corre `python manage.py configurar_ia`
"""
import json

from django.conf import settings

from . import services


class SinLlaveError(Exception):
    """No hay llave de API para el modelo elegido."""


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
    "Todo lo que el dueño puede hacer a mano en el sistema, tú lo puedes hacer con las funciones "
    "disponibles: agregar o quitar productos del carrito, cobrar, cancelar la venta, dar de alta o "
    "modificar productos, sumar piezas al inventario, registrar proveedores y gastos, ver las "
    "alertas de reabastecimiento y consultar ventas y finanzas. Cuando pida una acción, usa "
    "la función de inmediato en vez de inventar la respuesta.\n\n"
    "Puedes responder preguntas de cualquier módulo (ventas, inventario o finanzas) sin importar "
    "en qué pantalla esté el usuario ahorita — nunca le digas que tiene que cambiar de pantalla "
    "para preguntarte algo.\n\n"
    "Si te falta un dato necesario para hacer lo que te pidieron (por ejemplo el monto de un "
    "gasto, el costo de un producto nuevo, o a qué producto se refiere), pregúntalo primero y "
    "espera la respuesta — nunca inventes el dato ni ejecutes la acción a medias.\n\n"
    "Para cancelar una venta o dar de baja un producto, primero pregunta si está seguro y solo "
    "cuando conteste que sí vuelve a llamar la función con confirmar=true.\n\n"
    "Cuando te pregunten por sus finanzas (ganancias, utilidad, impuestos, punto de equilibrio), "
    "consulta las funciones y explica el resultado con palabras sencillas y un ejemplo del día a "
    "día, sin fórmulas ni términos contables.\n\n"
    "Si la petición no tiene que ver con la tienda o no la entendiste, no digas solamente que no "
    "puedes ayudar: explica brevemente qué sí puedes hacer y dale uno o dos ejemplos concretos, "
    "como 'agrega 2 cocas al carrito' o 'registra un gasto de luz de 450 pesos'."
)

PROMPT_RESUMEN = (
    "Eres marIA, la asistente de una tienda de abarrotes. Explica los números al dueño de la "
    "tienda en español, con palabras de todos los días, sin tecnicismos ni fórmulas. Sé breve y "
    "amigable, y termina siempre con consejos prácticos."
)


def modelo_disponible(modelo):
    """Si el modelo elegido no tiene llave pero el otro sí, usa el otro.
    Así el sistema funciona aunque solo se haya configurado una de las dos."""
    tiene_llave = {"chatgpt": bool(settings.OPENAI_API_KEY), "gemini": bool(settings.GEMINI_API_KEY)}
    if modelo not in tiene_llave:
        modelo = "chatgpt"
    if tiene_llave[modelo]:
        return modelo
    otro = "gemini" if modelo == "chatgpt" else "chatgpt"
    return otro if tiene_llave[otro] else modelo


def _instrucciones(negocio):
    """Las instrucciones fijas más cómo va la tienda ahorita (viene del cache)."""
    return (
        SYSTEM_PROMPT
        + "\n\nDatos de la tienda ahorita (úsalos para contestar sin ejecutar funciones cuando te alcancen):\n"
        + services.contexto_negocio(negocio)
    )


def preguntar_chatgpt(mensaje, negocio):
    """Regresa (respuesta_en_texto, nombres_de_funciones_ejecutadas)."""
    if not settings.OPENAI_API_KEY:
        return MENSAJE_SIN_LLAVE, []

    from openai import OpenAI

    cliente = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30)
    mensajes = [{"role": "system", "content": _instrucciones(negocio)}]
    for previo in services.historial_reciente(negocio):
        rol = "user" if previo.rol == previo.Rol.USUARIO else "assistant"
        mensajes.append({"role": rol, "content": previo.mensaje})
    mensajes.append({"role": "user", "content": mensaje})

    funciones_ejecutadas = []
    for _ in range(MAXIMO_DE_RONDAS):
        respuesta = cliente.chat.completions.create(
            model="gpt-4o-mini", messages=mensajes, tools=services.tools_openai(),
        )
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


def preguntar_gemini(mensaje, negocio):
    """Regresa (respuesta_en_texto, nombres_de_funciones_ejecutadas)."""
    if not settings.GEMINI_API_KEY:
        return MENSAJE_SIN_LLAVE, []

    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    modelo = genai.GenerativeModel(
        "gemini-2.5-flash",
        tools=services.tools_gemini(),
        system_instruction=_instrucciones(negocio),
    )
    historial = [
        {"role": "user" if previo.rol == previo.Rol.USUARIO else "model", "parts": [previo.mensaje]}
        for previo in services.historial_reciente(negocio)
    ]
    # Gemini exige que la conversación empiece con un mensaje del usuario
    while historial and historial[0]["role"] == "model":
        historial.pop(0)
    chat = modelo.start_chat(history=historial)
    respuesta = chat.send_message(mensaje, request_options={"timeout": 30})

    funciones_ejecutadas = []
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

        respuesta = chat.send_message(genai.protos.Content(parts=partes_respuesta))

    return "No pude terminar lo que me pediste. Intenta decírmelo de forma más sencilla.", funciones_ejecutadas


def generar_texto(prompt, modelo="chatgpt"):
    """Una sola pregunta a la IA, sin funciones ni historial. Es la que usan los
    resúmenes (de ayer, del dashboard y de los reportes).

    Lanza SinLlaveError si no hay ninguna llave configurada."""
    modelo = modelo_disponible(modelo)

    if modelo == "gemini":
        if not settings.GEMINI_API_KEY:
            raise SinLlaveError(MENSAJE_SIN_LLAVE)
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        modelo_gemini = genai.GenerativeModel("gemini-2.5-flash", system_instruction=PROMPT_RESUMEN)
        return modelo_gemini.generate_content(prompt, request_options={"timeout": 30}).text

    if not settings.OPENAI_API_KEY:
        raise SinLlaveError(MENSAJE_SIN_LLAVE)
    from openai import OpenAI

    cliente = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=30)
    respuesta = cliente.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": PROMPT_RESUMEN}, {"role": "user", "content": prompt}],
    )
    return respuesta.choices[0].message.content
