from django.core.management.base import BaseCommand

from accounts.models import Negocio
from inventario.datos_base import cargar_catalogo, preparar_negocio


class Command(BaseCommand):
    help = (
        "Carga las categorías de productos y el catálogo de abarrotes que se ofrece al registrar una tienda. "
        "Con --negocios también les agrega sus proveedores y categorías de gastos a las tiendas que ya existen. "
        "Se puede correr varias veces sin duplicar nada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--negocios", action="store_true",
            help="Agrega proveedores y categorías de gastos a las tiendas ya registradas",
        )

    def handle(self, *args, **opciones):
        categorias, productos = cargar_catalogo()
        self.stdout.write(self.style.SUCCESS(
            f"Listo: {categorias} categorías de productos y {productos} productos nuevos en el catálogo."
        ))

        if opciones["negocios"]:
            total = 0
            for negocio in Negocio.objects.all():
                proveedores, gastos = preparar_negocio(negocio)
                total += 1
                self.stdout.write(f"{negocio.nombre_tienda}: {proveedores} proveedores y {gastos} categorías de gastos nuevos.")
            self.stdout.write(self.style.SUCCESS(f"Revisé {total} tienda(s)."))
