"""
Guarda las llaves de ChatGPT y Gemini en el archivo .env, para no tener que
editarlo a mano cada vez que se clona el proyecto en otra computadora.

Formas de usarlo:
    python manage.py configurar_ia                 (pregunta las llaves)
    python manage.py configurar_ia --openai sk-... --gemini AIza...
    python manage.py configurar_ia --archivo claves.txt
    python manage.py configurar_ia --ver           (muestra cuáles ya están guardadas)

El archivo de --archivo puede tener líneas como OPENAI_API_KEY=... y
GEMINI_API_KEY=... (por ejemplo, el que se pasen entre ustedes por un medio
privado). Las llaves nunca se imprimen completas.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

NOMBRES = ["OPENAI_API_KEY", "GEMINI_API_KEY"]
RUTA_ENV = Path(settings.BASE_DIR) / ".env"


def leer_lineas():
    if not RUTA_ENV.exists():
        return []
    return RUTA_ENV.read_text(encoding="utf-8").splitlines()


def valor_guardado(lineas, nombre):
    for linea in lineas:
        if linea.startswith(nombre + "="):
            return linea.split("=", 1)[1].strip()
    return ""


def poner_valor(lineas, nombre, valor):
    """Cambia la línea NOMBRE=... si ya existe; si no, la agrega al final."""
    for numero, linea in enumerate(lineas):
        if linea.startswith(nombre + "="):
            lineas[numero] = f"{nombre}={valor}"
            return
    lineas.append(f"{nombre}={valor}")


def tapar(valor):
    """sk-abc...wxyz, para confirmar cuál llave es sin mostrarla completa."""
    if not valor:
        return "(sin configurar)"
    if len(valor) <= 8:
        return "********"
    return valor[:4] + "..." + valor[-4:]


class Command(BaseCommand):
    help = "Guarda las llaves de ChatGPT y Gemini en el archivo .env"

    def add_arguments(self, parser):
        parser.add_argument("--openai", help="Llave de OpenAI (ChatGPT)")
        parser.add_argument("--gemini", help="Llave de Google (Gemini)")
        parser.add_argument("--archivo", help="Archivo de texto con líneas NOMBRE=valor")
        parser.add_argument("--ver", action="store_true", help="Solo muestra qué llaves hay guardadas")

    def handle(self, *args, **opciones):
        lineas = leer_lineas()

        if opciones["ver"]:
            for nombre in NOMBRES:
                self.stdout.write(f"{nombre}: {tapar(valor_guardado(lineas, nombre))}")
            return

        nuevas = {}
        if opciones["archivo"]:
            nuevas.update(self.leer_archivo(opciones["archivo"]))
        if opciones["openai"]:
            nuevas["OPENAI_API_KEY"] = opciones["openai"].strip()
        if opciones["gemini"]:
            nuevas["GEMINI_API_KEY"] = opciones["gemini"].strip()

        # si no dijeron nada por argumentos, se preguntan una por una
        if not nuevas:
            nuevas = self.preguntar(lineas)

        if not nuevas:
            self.stdout.write("No se cambió nada.")
            return

        for nombre, valor in nuevas.items():
            poner_valor(lineas, nombre, valor)
            self.stdout.write(self.style.SUCCESS(f"{nombre} guardada: {tapar(valor)}"))

        RUTA_ENV.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        self.stdout.write("Listo. Si el servidor está corriendo, deténlo y vuelve a iniciarlo para que lea las llaves.")

    def leer_archivo(self, ruta):
        archivo = Path(ruta)
        if not archivo.exists():
            raise CommandError(f"No encontré el archivo {ruta}")

        encontradas = {}
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            if "=" not in linea or linea.strip().startswith("#"):
                continue
            nombre, valor = linea.split("=", 1)
            if nombre.strip() in NOMBRES and valor.strip():
                encontradas[nombre.strip()] = valor.strip()
        if not encontradas:
            raise CommandError("En ese archivo no encontré OPENAI_API_KEY ni GEMINI_API_KEY.")
        return encontradas

    def preguntar(self, lineas):
        self.stdout.write("Pega cada llave y presiona Enter. Si la dejas vacía, se conserva la que ya había.\n")
        respuestas = {}
        for nombre in NOMBRES:
            actual = tapar(valor_guardado(lineas, nombre))
            texto = input(f"{nombre} [{actual}]: ").strip()
            if texto:
                respuestas[nombre] = texto
        return respuestas
