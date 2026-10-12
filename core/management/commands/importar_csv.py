"""
Carga productos y ventas desde archivos CSV, de golpe y rápido.

    python manage.py importar_csv --usuario correo_o_telefono --productos productos.csv --ventas ventas.csv

Por qué es rápido: en vez de guardar renglón por renglón (miles de consultas),
junta los registros en listas y los inserta por paquetes de 1000 con
bulk_create, todo dentro de una sola transacción.

Columnas que busca (en la primera fila del CSV; si el archivo usa otro nombre,
agrégalo a las listas de ALIAS de aquí abajo):

  productos.csv -> nombre, categoria, costo, precio_venta, cantidad_actual,
                   cantidad_minima, stock_ideal  (solo nombre y precio_venta son obligatorias)
  ventas.csv    -> fecha, folio, producto, cantidad, precio_unitario
                   (un renglón por producto vendido; los renglones con el
                   mismo folio forman un solo ticket)

Ver ejemplos en database/ejemplos/.
"""
import csv
import unicodedata
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core import cache_negocio
from inventario.models import Categoria, Producto
from ventas.models import ItemVenta, Venta

TAMANO_PAQUETE = 1000
CENTAVOS = Decimal("0.01")
MAXIMO_DECIMAL = Decimal("99999999.99")

# nombres que puede tener cada columna en el CSV
ALIAS = {
    "nombre": ["nombre", "producto", "descripcion", "name"],
    "categoria": ["categoria", "category"],
    "costo": ["costo", "costo_unitario", "cost"],
    "precio_venta": ["precio_venta", "precio", "price"],
    "cantidad_actual": ["cantidad_actual", "existencias", "stock", "inventario"],
    "cantidad_minima": ["cantidad_minima", "minimo", "stock_minimo"],
    "stock_ideal": ["stock_ideal", "ideal", "stock_maximo"],
    "fecha": ["fecha", "date", "fecha_venta"],
    "folio": ["folio", "ticket", "ticket_id", "id_venta"],
    "producto": ["producto", "nombre", "nombre_producto"],
    "cantidad": ["cantidad", "piezas", "unidades", "qty"],
    "precio_unitario": ["precio_unitario", "precio", "price"],
}


def normalizar(texto):
    descompuesto = unicodedata.normalize("NFD", str(texto))
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn").lower().strip()


def numero(texto, defecto=None):
    """'$1,250.50' -> Decimal('1250.50'). Si no se puede convertir regresa `defecto`."""
    limpio = str(texto or "").replace("$", "").replace(",", "").strip()
    if not limpio:
        return defecto
    try:
        valor = Decimal(limpio)
    except InvalidOperation:
        return defecto
    return valor if valor.is_finite() else defecto


def fecha_y_hora(texto):
    """Acepta 2025-03-01, 2025-03-01 10:15:00 o 01/03/2025."""
    texto = str(texto or "").strip()
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            fecha = datetime.strptime(texto, formato)
            return timezone.make_aware(fecha)
        except ValueError:
            continue
    try:
        fecha = datetime.fromisoformat(texto)
    except ValueError:
        return None
    return timezone.make_aware(fecha) if timezone.is_naive(fecha) else fecha


class Command(BaseCommand):
    help = "Carga productos y ventas desde archivos CSV (rápido, con bulk_create)."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True, help="Correo, teléfono o usuario del dueño de la tienda")
        parser.add_argument("--productos", help="Archivo CSV de productos")
        parser.add_argument("--ventas", help="Archivo CSV de ventas")
        parser.add_argument(
            "--productos-desde-ventas", action="store_true",
            help="Crea productos faltantes desde las ventas, con existencias y costo en cero, pendientes de validar",
        )
        parser.add_argument("--limpiar", action="store_true", help="Borra antes los productos y ventas de esa tienda")

    def handle(self, *args, **opciones):
        if not opciones["productos"] and not opciones["ventas"]:
            raise CommandError("Indica al menos --productos o --ventas.")
        if opciones["productos_desde_ventas"] and not opciones["ventas"]:
            raise CommandError("--productos-desde-ventas requiere que indiques --ventas.")

        negocio = self.buscar_negocio(opciones["usuario"])
        self.stdout.write(f"Tienda: {negocio.nombre_tienda}")

        if opciones["limpiar"]:
            confirmacion = input("Esto borra TODOS los productos y ventas de esa tienda. Escribe SI para continuar: ")
            if confirmacion.strip() != "SI":
                self.stdout.write("Cancelado, no se borró nada.")
                return

        with transaction.atomic():
            if opciones["limpiar"]:
                self.limpiar(negocio)
            if opciones["productos"]:
                self.importar_productos(negocio, opciones["productos"])
            if opciones["ventas"]:
                if opciones["productos_desde_ventas"]:
                    self.importar_productos_desde_ventas(negocio, opciones["ventas"])
                self.importar_ventas(negocio, opciones["ventas"])

        # bulk_create no avisa a las señales, así que se limpia el cache a mano
        cache_negocio.invalidar(negocio.pk)
        self.stdout.write(self.style.SUCCESS("Listo."))

    # ------------------------------------------------------------ apoyo

    def buscar_negocio(self, dato):
        Usuario = get_user_model()
        usuario = Usuario.objects.filter(Q(email__iexact=dato) | Q(telefono=dato) | Q(username=dato)).first()
        if usuario is None:
            raise CommandError(f"No encontré ningún usuario con '{dato}'.")
        negocio = getattr(usuario, "negocio", None)
        if negocio is None:
            raise CommandError("Ese usuario todavía no registra los datos de su negocio.")
        return negocio

    def limpiar(self, negocio):
        # ItemVenta.producto es PROTECT, por eso primero se borran los renglones de venta
        ItemVenta.objects.filter(venta__negocio=negocio).delete()
        Venta.objects.filter(negocio=negocio).delete()
        Producto.objects.filter(negocio=negocio).delete()
        self.stdout.write("Se borraron los productos y ventas anteriores.")

    def leer_csv(self, ruta, columnas_obligatorias):
        """Regresa una lista de diccionarios con las columnas ya renombradas a los nombres del sistema."""
        try:
            archivo = open(ruta, newline="", encoding="utf-8-sig")
        except OSError:
            raise CommandError(f"No pude abrir el archivo {ruta}")

        with archivo:
            lector = csv.DictReader(archivo)
            encabezados = {normalizar(nombre): nombre for nombre in (lector.fieldnames or [])}

            # para cada columna del sistema, cuál columna del CSV le toca
            equivalencias = {}
            for columna, alias in ALIAS.items():
                for nombre in alias:
                    if nombre in encabezados:
                        equivalencias[columna] = encabezados[nombre]
                        break

            faltan = [c for c in columnas_obligatorias if c not in equivalencias]
            if faltan:
                raise CommandError(f"A {ruta} le faltan las columnas: {', '.join(faltan)}")

            return [
                {columna: (renglon.get(original) or "").strip() for columna, original in equivalencias.items()}
                for renglon in lector
            ]

    # ------------------------------------------------------- productos

    def importar_productos(self, negocio, ruta):
        renglones = self.leer_csv(ruta, ["nombre", "precio_venta"])

        categorias = {normalizar(c.nombre): c for c in Categoria.objects.all()}
        ya_existen = {normalizar(nombre) for nombre in Producto.objects.filter(negocio=negocio).values_list("nombre", flat=True)}

        productos = []
        omitidos = 0
        for renglon in renglones:
            nombre = renglon["nombre"]
            precio = numero(renglon["precio_venta"])
            if not nombre or precio is None or precio < 0 or normalizar(nombre) in ya_existen:
                omitidos += 1
                continue

            categoria = None
            nombre_categoria = renglon.get("categoria", "")
            if nombre_categoria:
                categoria = categorias.get(normalizar(nombre_categoria))
                if categoria is None:
                    categoria = Categoria.objects.create(nombre=nombre_categoria)
                    categorias[normalizar(nombre_categoria)] = categoria

            minimo = max(numero(renglon.get("cantidad_minima"), Decimal("0")), Decimal("0"))
            costo = max(numero(renglon.get("costo"), Decimal("0")), Decimal("0"))
            cantidad_actual = max(numero(renglon.get("cantidad_actual"), Decimal("0")), Decimal("0"))
            stock_ideal = max(numero(renglon.get("stock_ideal"), Decimal("0")), minimo)
            if any(valor > MAXIMO_DECIMAL for valor in (precio, costo, cantidad_actual, minimo, stock_ideal)):
                omitidos += 1
                continue
            ya_existen.add(normalizar(nombre))
            productos.append(Producto(
                negocio=negocio, nombre=nombre[:150], categoria=categoria,
                costo=costo,
                precio_venta=precio.quantize(CENTAVOS, rounding=ROUND_HALF_UP),
                cantidad_actual=cantidad_actual,
                cantidad_minima=minimo,
                stock_ideal=stock_ideal,
            ))

        Producto.objects.bulk_create(productos, batch_size=TAMANO_PAQUETE)
        self.stdout.write(f"Productos importados: {len(productos)} (omitidos por datos malos o repetidos: {omitidos})")

    # ---------------------------------------------------------- ventas

    def importar_productos_desde_ventas(self, negocio, ruta):
        renglones = self.leer_csv(ruta, ["fecha", "producto", "cantidad", "precio_unitario"])
        existentes = {
            normalizar(nombre)
            for nombre in Producto.objects.filter(negocio=negocio).values_list("nombre", flat=True)
        }
        inferidos = {}
        for renglon in renglones:
            nombre = renglon["producto"].strip()
            clave = normalizar(nombre)
            fecha = fecha_y_hora(renglon["fecha"])
            cantidad = numero(renglon["cantidad"])
            precio = numero(renglon["precio_unitario"])
            if (
                not nombre or clave in existentes or fecha is None
                or cantidad is None or cantidad <= 0 or cantidad > MAXIMO_DECIMAL
                or precio is None or precio < 0 or precio > MAXIMO_DECIMAL
            ):
                continue
            if clave not in inferidos or fecha >= inferidos[clave][0]:
                inferidos[clave] = (fecha, nombre, precio)

        productos = [
            Producto(
                negocio=negocio,
                nombre=nombre[:150],
                costo=Decimal("0"),
                precio_venta=precio.quantize(CENTAVOS, rounding=ROUND_HALF_UP),
                cantidad_actual=Decimal("0"),
                cantidad_minima=Decimal("0"),
                stock_ideal=Decimal("0"),
                pendiente_validacion=True,
            )
            for _, nombre, precio in inferidos.values()
        ]
        Producto.objects.bulk_create(productos, batch_size=TAMANO_PAQUETE)
        self.stdout.write(
            f"Productos creados desde ventas: {len(productos)} (pendientes de completar y validar inventario)"
        )

    def importar_ventas(self, negocio, ruta):
        renglones = self.leer_csv(ruta, ["fecha", "producto", "cantidad"])

        # nombre -> (id, precio actual), para no consultar la base de datos por cada renglón
        productos = {
            normalizar(nombre): (pk, precio)
            for pk, nombre, precio in Producto.objects.filter(negocio=negocio).values_list("pk", "nombre", "precio_venta")
        }

        # se agrupan los renglones por folio: cada folio es un ticket (si el CSV
        # no trae folio, cada renglón es un ticket aparte)
        tickets = {}
        sin_producto = 0
        sin_fecha = 0
        for renglon in renglones:
            producto = productos.get(normalizar(renglon["producto"]))
            cantidad = numero(renglon["cantidad"])
            if cantidad is not None:
                cantidad = cantidad.quantize(CENTAVOS, rounding=ROUND_HALF_UP)
            fecha = fecha_y_hora(renglon["fecha"])
            if (
                producto is None or cantidad is None or cantidad <= 0
                or cantidad > MAXIMO_DECIMAL
            ):
                sin_producto += 1
                continue
            if fecha is None:
                sin_fecha += 1
                continue

            precio = numero(renglon.get("precio_unitario"), producto[1])
            if precio is None or precio > MAXIMO_DECIMAL:
                sin_producto += 1
                continue
            if precio < 0:
                precio = producto[1]
            clave = renglon.get("folio") or f"sin-folio-{len(tickets)}"
            if clave not in tickets:
                tickets[clave] = {"fecha": fecha, "items": []}
            tickets[clave]["items"].append((producto[0], cantidad, precio))

        # los folios del sistema siguen la numeración que ya tenga la tienda
        ventas = []
        tickets_fuera_rango = 0
        ultimo_folio = Venta.objects.filter(negocio=negocio).order_by("-folio").values_list("folio", flat=True).first() or 0
        for ticket in tickets.values():
            total = sum((c * p for _, c, p in ticket["items"]), Decimal("0")).quantize(CENTAVOS, rounding=ROUND_HALF_UP)
            if total > MAXIMO_DECIMAL:
                tickets_fuera_rango += 1
                continue
            ultimo_folio += 1
            ticket["venta"] = Venta(negocio=negocio, folio=ultimo_folio, estado=Venta.Estado.COBRADA, total=total)
            ventas.append(ticket["venta"])
        Venta.objects.bulk_create(ventas, batch_size=TAMANO_PAQUETE)

        # creado_en es auto_now_add: al crear se llena con "ahora", así que se
        # corrige después con la fecha real del CSV (bulk_update sí respeta el valor)
        folio_a_pk = dict(Venta.objects.filter(negocio=negocio).values_list("folio", "pk"))
        items = []
        for ticket in tickets.values():
            if "venta" not in ticket:
                continue
            venta = ticket["venta"]
            venta.pk = folio_a_pk[venta.folio]
            venta.creado_en = ticket["fecha"]
            for producto_id, cantidad, precio in ticket["items"]:
                items.append(ItemVenta(
                    venta=venta, producto_id=producto_id, cantidad=cantidad,
                    precio_unitario=precio.quantize(CENTAVOS, rounding=ROUND_HALF_UP),
                ))
        Venta.objects.bulk_update(ventas, ["creado_en"], batch_size=TAMANO_PAQUETE)
        ItemVenta.objects.bulk_create(items, batch_size=TAMANO_PAQUETE)

        self.stdout.write(
            f"Ventas importadas: {len(ventas)} tickets con {len(items)} renglones "
            f"(renglones omitidos: producto/cantidad/precio inválido {sin_producto}, fecha mala {sin_fecha}; "
            f"tickets fuera del límite Decimal(10,2): {tickets_fuera_rango})"
        )
