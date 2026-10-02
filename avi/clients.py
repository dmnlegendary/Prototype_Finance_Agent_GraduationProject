"""
Wrappers para hablar con la API de ChatGPT o de Gemini, con function calling
ya declarado (ver services.py). Para que esto funcione de verdad falta:
  1. pip install openai google-generativeai (ya están en requirements.txt)
  2. definir las variables de entorno OPENAI_API_KEY / GEMINI_API_KEY
"""
import json

from django.conf import settings

from . import services

SYSTEM_PROMPT = (
    "Eres marIA, el Asistente Virtual Inteligente (AVI) de una tienda de abarrotes. "
    "Ayudas al dueño a vender, revisar su inventario y registrar sus gastos. "
    "Responde siempre en español, de forma breve y amigable. Cuando el usuario "
    "pida una acción (agregar un producto al carrito, consultar ventas, "
    "registrar un gasto, etc.) usa las funciones disponibles en vez de "
    "inventar la respuesta. Explica todo de forma sencilla: quien te usa es el "
    "dueño de una tiendita que muy probablemente no tuvo muchos estudios, así "
    "que evita tecnicismos, usa palabras simples y ve directo al grano. Nunca "
    "des explicaciones largas.\n\n"
    "Puedes responder preguntas de cualquier módulo (ventas, inventario o "
    "finanzas) sin importar en qué pantalla esté el usuario ahorita — nunca "
    "le digas que tiene que cambiar de pantalla para preguntarte algo.\n\n"
    "Si te falta un dato necesario para hacer lo que te pidieron (por ejemplo "
    "el monto de un gasto, o a qué producto se refiere), pregúntalo primero "
    "y espera la respuesta — nunca inventes el dato ni ejecutes la acción a "
    "medias.\n\n"
    "Si la petición no tiene que ver con la tienda o no la entendiste, no "
    "digas solamente que no puedes ayudar: explica brevemente qué sí puedes "
    "hacer y dale uno o dos ejemplos concretos, como 'agrega 2 cocas al "
    "carrito' o 'registra un gasto de luz de 450 pesos'."
)


def preguntar_chatgpt(mensaje, negocio):
    """Regresa (respuesta_en_texto, nombres_de_funciones_ejecutadas)."""
    if not settings.OPENAI_API_KEY:
        return "Todavía no se configuró la variable de entorno OPENAI_API_KEY.", []

    from openai import OpenAI

    cliente = OpenAI(api_key=settings.OPENAI_API_KEY)
    mensajes = [{"role": "system", "content": SYSTEM_PROMPT}]
    for previo in services.historial_reciente(negocio):
        rol = "user" if previo.rol == previo.Rol.USUARIO else "assistant"
        mensajes.append({"role": rol, "content": previo.mensaje})
    mensajes.append({"role": "user", "content": mensaje})

    respuesta = cliente.chat.completions.create(
        model="gpt-4o-mini",
        messages=mensajes,
        tools=services.tools_openai(),
    )
    mensaje_respuesta = respuesta.choices[0].message

    if mensaje_respuesta.tool_calls:
        funciones_ejecutadas = []
        mensajes.append(mensaje_respuesta)
        for llamada in mensaje_respuesta.tool_calls:
            argumentos = json.loads(llamada.function.arguments)
            resultado = services.ejecutar_funcion(llamada.function.name, argumentos, negocio)
            funciones_ejecutadas.append(llamada.function.name)
            mensajes.append({
                "role": "tool",
                "tool_call_id": llamada.id,
                "content": json.dumps(resultado, ensure_ascii=False),
            })
        segunda_respuesta = cliente.chat.completions.create(model="gpt-4o-mini", messages=mensajes)
        return segunda_respuesta.choices[0].message.content, funciones_ejecutadas

    return mensaje_respuesta.content, []


def preguntar_gemini(mensaje, negocio):
    """Regresa (respuesta_en_texto, nombres_de_funciones_ejecutadas)."""
    if not settings.GEMINI_API_KEY:
        return "Todavía no se configuró la variable de entorno GEMINI_API_KEY.", []

    import google.generativeai as genai

    genai.configure(api_key=settings.GEMINI_API_KEY)
    modelo = genai.GenerativeModel(
        "gemini-2.5-flash",
        tools=services.tools_gemini(),
        system_instruction=SYSTEM_PROMPT,
    )
    historial = [
        {"role": "user" if previo.rol == previo.Rol.USUARIO else "model", "parts": [previo.mensaje]}
        for previo in services.historial_reciente(negocio)
    ]
    chat = modelo.start_chat(history=historial)
    respuesta = chat.send_message(mensaje)

    llamadas = [
        parte.function_call
        for parte in respuesta.candidates[0].content.parts
        if getattr(parte, "function_call", None)
    ]

    if llamadas:
        funciones_ejecutadas = []
        partes_respuesta = []
        for fn in llamadas:
            argumentos = dict(fn.args)
            resultado = services.ejecutar_funcion(fn.name, argumentos, negocio)
            funciones_ejecutadas.append(fn.name)
            partes_respuesta.append(genai.protos.Part(
                function_response=genai.protos.FunctionResponse(name=fn.name, response=resultado),
            ))
        respuesta = chat.send_message(genai.protos.Content(parts=partes_respuesta))
        return respuesta.text, funciones_ejecutadas

    return respuesta.text, []
