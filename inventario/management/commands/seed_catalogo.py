from django.core.management.base import BaseCommand

from inventario.models import Categoria, ProductoCatalogo

CATEGORIAS = [
    ("Bebidas", "🥤"),
    ("Abarrotes", "🍞"),
    ("Lácteos", "🥛"),
    ("Limpieza", "🧴"),
    ("Botanas", "🍟"),
    ("Dulcería", "🍬"),
]

PRODUCTOS = [
    ("Coca-Cola 600ml", "Bebidas", "🥤", 18.00),
    ("Pepsi 600ml", "Bebidas", "🥤", 17.00),
    ("Agua Ciel 1.5L", "Bebidas", "💧", 15.00),
    ("Jugo Del Valle 1L", "Bebidas", "🧃", 24.00),
    ("Cerveza Modelo 355ml", "Bebidas", "🍺", 22.00),
    ("Pan Bimbo Blanco", "Abarrotes", "🍞", 32.00),
    ("Arroz 1kg", "Abarrotes", "🍚", 28.00),
    ("Frijol 1kg", "Abarrotes", "🫘", 30.00),
    ("Aceite 1L", "Abarrotes", "🛢️", 35.00),
    ("Atún Dolores 140g", "Abarrotes", "🐟", 18.50),
    ("Leche Lala 1L", "Lácteos", "🥛", 26.50),
    ("Yogurt Danone 1L", "Lácteos", "🥛", 32.00),
    ("Queso Oaxaca 400g", "Lácteos", "🧀", 55.00),
    ("Cloralex 950ml", "Limpieza", "🧴", 25.00),
    ("Jabón Zote", "Limpieza", "🧼", 14.00),
    ("Fabuloso 1L", "Limpieza", "🧴", 28.00),
    ("Sabritas Original 45g", "Botanas", "🍟", 18.00),
    ("Galletas Marías", "Botanas", "🍪", 12.00),
    ("Chicles Trident", "Dulcería", "🍬", 12.00),
    ("Chocolate Carlos V", "Dulcería", "🍫", 8.50),
]


class Command(BaseCommand):
    help = "Carga un catálogo de ejemplo con 20 productos de abarrotes, para poder probar el onboarding y el inventario."

    def handle(self, *args, **options):
        categorias_creadas = {}
        for nombre, icono in CATEGORIAS:
            categoria, creada = Categoria.objects.get_or_create(nombre=nombre, defaults={"icono": icono})
            categorias_creadas[nombre] = categoria

        total_nuevos = 0
        for nombre, categoria_nombre, icono, precio in PRODUCTOS:
            _, creado = ProductoCatalogo.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "categoria": categorias_creadas[categoria_nombre],
                    "icono": icono,
                    "precio_sugerido": precio,
                },
            )
            if creado:
                total_nuevos += 1

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {len(categorias_creadas)} categorías y {total_nuevos} productos nuevos en el catálogo."
        ))
