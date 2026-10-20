"""
Guarda las llaves de ChatGPT y Gemini CIFRADAS en la base de datos (nunca en texto plano).

Formas de usarlo:
    python manage.py configurar_ia                 (pregunta las llaves, sin mostrarlas al escribir)
    python manage.py configurar_ia --openai sk-... --gemini AIza...
    python manage.py configurar_ia --archivo claves.txt
    python manage.py configurar_ia --desde-env     (pasa a la base de datos las llaves que estén en el .env)
    python manage.py configurar_ia --ver           (muestra cuáles ya están guardadas y dónde)

El archivo de --archivo puede tener líneas como OPENAI_API_KEY=... y GEMINI_API_KEY=... (por ejemplo,
el que se pasen entre ustedes por un medio privado). Las llaves nunca se imprimen completas.
"""
from getpass import getpass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from core import llaves

# nombre en el archivo de claves -> proveedor
NOMBRES = {"OPENAI_API_KEY": llaves.LlaveIA.OPENAI, "GEMINI_API_KEY": llaves.LlaveIA.GEMINI}


def tapar(valor):
    """sk-abc...wxyz, para confirmar cuál llave es sin mostrarla completa."""
    if not valor:
        return "(sin configurar)"
    if len(valor) <= 8:
        return "********"
    return valor[:4] + "..." + valor[-4:]


class Command(BaseCommand):
    help = "Guarda las llaves de ChatGPT y Gemini cifradas en la base de datos"

    def add_arguments(self, parser):
        parser.add_argument("--openai", help="Llave de OpenAI (ChatGPT)")
        parser.add_argument("--gemini", help="Llave de Google (Gemini)")
        parser.add_argument("--archivo", help="Archivo de texto con líneas NOMBRE=valor")
        parser.add_argument("--desde-env", action="store_true", help="Pasa a la base de datos las llaves que estén en el .env")
        parser.add_argument("--ver", action="store_true", help="Solo muestra qué llaves hay guardadas")

    def handle(self, *args, **opciones):
        if opciones["ver"]:
            for nombre, proveedor in NOMBRES.items():
                self.stdout.write(f"{nombre}: {tapar(llaves.obtener(proveedor))}  [{llaves.origen(proveedor)}]")
            return

        nuevas = {}
        if opciones["desde_env"]:
            from django.conf import settings
            for nombre, proveedor in NOMBRES.items():
                valor = getattr(settings, llaves.VARIABLES[proveedor], "")
                if valor:
                    nuevas[proveedor] = valor
            if not nuevas:
                raise CommandError("No hay ninguna llave en el .env para pasar a la base de datos.")
        if opciones["archivo"]:
            nuevas.update(self.leer_archivo(opciones["archivo"]))
        if opciones["openai"]:
            nuevas[llaves.LlaveIA.OPENAI] = opciones["openai"].strip()
        if opciones["gemini"]:
            nuevas[llaves.LlaveIA.GEMINI] = opciones["gemini"].strip()

        # si no dijeron nada por argumentos, se preguntan una por una
        if not nuevas:
            nuevas = self.preguntar()

        if not nuevas:
            self.stdout.write("No se cambió nada.")
            return

        for proveedor, valor in nuevas.items():
            llaves.guardar(proveedor, valor)
            self.stdout.write(self.style.SUCCESS(f"{proveedor}: guardada cifrada ({tapar(valor)})"))

        self.stdout.write(
            "Listo. Las llaves quedaron cifradas en la base de datos; si todavía están en el archivo .env, "
            "puedes borrarlas de ahí (el sistema ya no las necesita)."
        )

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
                encontradas[NOMBRES[nombre.strip()]] = valor.strip()
        if not encontradas:
            raise CommandError("En ese archivo no encontré OPENAI_API_KEY ni GEMINI_API_KEY.")
        return encontradas

    def preguntar(self):
        self.stdout.write("Pega cada llave y presiona Enter (no se ve al escribirla). Si la dejas vacía, se conserva la que ya había.\n")
        respuestas = {}
        for nombre, proveedor in NOMBRES.items():
            actual = tapar(llaves.obtener(proveedor))
            texto = getpass(f"{nombre} [{actual}]: ").strip()
            if texto:
                respuestas[proveedor] = texto
        return respuestas
