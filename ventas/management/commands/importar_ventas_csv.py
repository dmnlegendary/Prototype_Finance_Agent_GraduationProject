import csv
from collections import OrderedDict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from inventario.models import Producto
from ventas.models import ItemVenta, Venta


class Command(BaseCommand):
    help = "Importa tickets históricos desde un CSV con fecha, ticket_id, producto, cantidad y precio."

    def add_arguments(self, parser):
        parser.add_argument("--archivo", default="ventas_articulos_completo.csv")
        parser.add_argument("--usuario", required=True, help="Usuario o nombre de la persona dueña del negocio.")
        parser.add_argument("--dry-run", action="store_true", help="Valida y resume sin escribir en la base.")
        parser.add_argument(
            "--reparar-fechas", action="store_true",
            help="Restaura las fechas del CSV en un lote ya importado, verificando antes sus conteos.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["archivo"]).expanduser()
        if not csv_path.is_absolute():
            csv_path = Path.cwd() / csv_path
        if not csv_path.is_file():
            raise CommandError(f"No se encontró el archivo: {csv_path}")

        User = get_user_model()
        selector = options["usuario"].strip()
        users = list(
            User.objects.filter(
                Q(username__iexact=selector) | Q(nombre_completo__icontains=selector)
            ).distinct()[:2]
        )
        if not users:
            raise CommandError(
                f'No se encontró una cuenta para "{selector}" en esta base de datos. '
                "Regístralo y completa los datos de su negocio antes de importar."
            )
        if len(users) > 1:
            raise CommandError(
                f'"{selector}" coincide con varias cuentas. Usa el teléfono/usuario exacto de la cuenta.'
            )
        user = users[0]
        negocio = getattr(user, "negocio", None)
        if negocio is None:
            raise CommandError("El usuario todavía no tiene un negocio configurado.")

        tickets, product_prices, row_count = self._read_csv(csv_path)
        if not tickets:
            raise CommandError("El CSV no contiene renglones de venta.")

        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS(
                f"Simulación válida: {row_count} renglones, {len(tickets)} tickets y "
                f"{len(product_prices)} productos para {negocio.nombre_tienda}. No se guardaron cambios."
            ))
            return

        if options["reparar_fechas"]:
            self._repair_historical_timestamps(negocio, tickets, row_count)
            self.stdout.write(self.style.SUCCESS(
                f"Fechas históricas restauradas en {len(tickets)} tickets y {row_count} renglones."
            ))
            return

        has_existing_sales = Venta.objects.filter(negocio=negocio).filter(
            Q(estado=Venta.Estado.COBRADA) | Q(items__isnull=False)
        ).exists()
        if has_existing_sales:
            raise CommandError(
                "El negocio ya tiene ventas con artículos. La importación requiere un negocio de pruebas sin historial "
                "para evitar duplicados o mezclar ventas reales con el histórico."
            )

        self._import(negocio, user, tickets, product_prices)
        self.stdout.write(self.style.SUCCESS(
            f"Importación terminada: {row_count} renglones, {len(tickets)} tickets y "
            f"{len(product_prices)} productos en {negocio.nombre_tienda}."
        ))

    def _read_csv(self, csv_path):
        tickets = OrderedDict()
        product_prices = OrderedDict()
        row_count = 0

        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                required = {"fecha", "ticket_id", "producto", "cantidad", "precio"}
                if reader.fieldnames is None or not required.issubset(reader.fieldnames):
                    raise CommandError(
                        "El CSV debe incluir las columnas: fecha, ticket_id, producto, cantidad y precio."
                    )

                for line_number, row in enumerate(reader, start=2):
                    try:
                        sold_at = datetime.fromisoformat(row["fecha"].strip())
                        if timezone.is_naive(sold_at):
                            sold_at = timezone.make_aware(sold_at, timezone.get_current_timezone())
                        ticket_id = row["ticket_id"].strip()
                        product_name = row["producto"].strip()
                        quantity = Decimal(row["cantidad"].strip())
                        price = Decimal(row["precio"].strip())
                        if not ticket_id or not product_name or quantity <= 0 or price < 0:
                            raise ValueError("ticket/producto vacío o cantidad/precio fuera de rango")
                    except (AttributeError, InvalidOperation, ValueError) as error:
                        raise CommandError(f"Fila {line_number} inválida: {error}") from error

                    ticket_key = (ticket_id, sold_at.date())
                    ticket = tickets.setdefault(ticket_key, {"fecha": sold_at, "items": []})
                    ticket["fecha"] = min(ticket["fecha"], sold_at)
                    ticket["items"].append({
                        "producto": product_name,
                        "cantidad": quantity,
                        "precio": price,
                    })
                    product_prices[product_name] = price
                    row_count += 1
        except UnicodeDecodeError as error:
            raise CommandError("No se pudo leer el CSV como UTF-8. Guarda el archivo en UTF-8 e inténtalo de nuevo.") from error

        return tickets, product_prices, row_count

    @transaction.atomic
    def _import(self, negocio, user, tickets, product_prices):
        products = {
            product.nombre: product
            for product in Producto.objects.filter(negocio=negocio, nombre__in=product_prices)
        }
        new_products = [
            Producto(
                negocio=negocio,
                nombre=name,
                descripcion="Importado del histórico; costo de compra no disponible.",
                costo=Decimal("0"),
                precio_venta=price,
                cantidad_actual=Decimal("0"),
                cantidad_minima=Decimal("0"),
            )
            for name, price in product_prices.items()
            if name not in products
        ]
        Producto.objects.bulk_create(new_products, batch_size=1000)
        products.update({
            product.nombre: product
            for product in Producto.objects.filter(negocio=negocio, nombre__in=product_prices)
        })

        first_folio = (Venta.objects.filter(negocio=negocio).order_by("-folio").values_list("folio", flat=True).first() or 0) + 1
        sales = []
        ticket_items = []
        for offset, ticket in enumerate(tickets.values()):
            sale = Venta(
                negocio=negocio,
                cajero=user,
                folio=first_folio + offset,
                estado=Venta.Estado.COBRADA,
                total=sum((item["cantidad"] * item["precio"] for item in ticket["items"]), Decimal("0")),
                creado_en=ticket["fecha"],
            )
            sales.append(sale)

        Venta.objects.bulk_create(sales, batch_size=1000)
        for sale, ticket in zip(sales, tickets.values()):
            sale.creado_en = ticket["fecha"]
        Venta.objects.bulk_update(sales, ["creado_en"], batch_size=1000)

        for sale, ticket in zip(sales, tickets.values()):
            ticket_items.extend(
                ItemVenta(
                    venta=sale,
                    producto=products[item["producto"]],
                    cantidad=item["cantidad"],
                    precio_unitario=item["precio"],
                    creado_en=ticket["fecha"],
                )
                for item in ticket["items"]
            )
        ItemVenta.objects.bulk_create(ticket_items, batch_size=2000)

        sale_dates = {
            sale.pk: ticket["fecha"]
            for sale, ticket in zip(sales, tickets.values())
        }
        for item in ticket_items:
            item.creado_en = sale_dates[item.venta_id]
        ItemVenta.objects.bulk_update(ticket_items, ["creado_en"], batch_size=2000)

    @transaction.atomic
    def _repair_historical_timestamps(self, negocio, tickets, row_count):
        sales = list(
            Venta.objects.filter(negocio=negocio, estado=Venta.Estado.COBRADA)
            .only("id", "folio", "creado_en")
            .annotate(item_count=Count("items"))
            .order_by("folio")
        )
        expected_tickets = list(tickets.values())
        if len(sales) != len(expected_tickets) or sum(sale.item_count for sale in sales) != row_count:
            raise CommandError(
                "El lote guardado no coincide con el CSV (cantidad de tickets o renglones); no se modificaron fechas."
            )
        if any(sale.item_count != len(ticket["items"]) for sale, ticket in zip(sales, expected_tickets)):
            raise CommandError(
                "La distribución de artículos por ticket no coincide con el CSV; no se modificaron fechas."
            )

        for sale, ticket in zip(sales, expected_tickets):
            sale.creado_en = ticket["fecha"]
        Venta.objects.bulk_update(sales, ["creado_en"], batch_size=1000)

        sale_dates = {sale.pk: sale.creado_en for sale in sales}
        items = list(ItemVenta.objects.filter(venta__in=sales).only("id", "venta_id", "creado_en"))
        for item in items:
            item.creado_en = sale_dates[item.venta_id]
        ItemVenta.objects.bulk_update(items, ["creado_en"], batch_size=2000)