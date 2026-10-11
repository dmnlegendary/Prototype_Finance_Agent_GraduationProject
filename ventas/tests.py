from decimal import Decimal

from django.contrib.messages import get_messages
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.testing import crear_negocio, crear_producto
from inventario.models import Producto

from .models import ItemVenta, Venta


class CalculosDeVentaTests(SimpleTestCase):
    def test_subtotal_se_redondea_a_dos_decimales(self):
        item = ItemVenta(cantidad=Decimal("1.5"), precio_unitario=Decimal("12.99"))
        self.assertEqual(item.subtotal, Decimal("19.49"))


class FlujoDeVentaTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.producto = crear_producto(self.negocio)
        self.client.force_login(self.usuario)

    def test_la_pantalla_de_ventas_abre(self):
        respuesta = self.client.get(reverse("ventas:punto_de_venta"))
        self.assertEqual(respuesta.status_code, 200)

    def test_total_de_la_venta_se_guarda_con_dos_decimales(self):
        venta = Venta.objects.create(negocio=self.negocio, folio=1)
        ItemVenta.objects.create(
            venta=venta, producto=self.producto, cantidad=Decimal("1.5"), precio_unitario=Decimal("12.99"),
        )
        venta.recalcular_total()
        venta.refresh_from_db()
        self.assertEqual(venta.total, Decimal("19.49"))

    def test_cobrar_descuenta_inventario_y_cierra_la_venta(self):
        self.client.post(reverse("ventas:agregar_item", args=[self.producto.pk]))
        item = ItemVenta.objects.get()
        self.client.post(reverse("ventas:item_incrementar", args=[item.pk]))
        self.client.post(reverse("ventas:cobrar"))

        self.producto.refresh_from_db()
        venta = Venta.objects.get()
        self.assertEqual(self.producto.cantidad_actual, Decimal("8"))
        self.assertEqual(venta.estado, Venta.Estado.COBRADA)
        self.assertEqual(venta.total, Decimal("50.00"))

    def test_cancelar_no_mueve_el_inventario(self):
        self.client.post(reverse("ventas:agregar_item", args=[self.producto.pk]))
        self.client.post(reverse("ventas:cancelar_venta"))

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.cantidad_actual, Decimal("10"))
        self.assertEqual(Venta.objects.get().estado, Venta.Estado.CANCELADA)

    def test_quitar_producto_del_carrito_de_una_vez(self):
        self.client.post(reverse("ventas:agregar_item", args=[self.producto.pk]))
        item = ItemVenta.objects.get()
        self.client.post(reverse("ventas:item_incrementar", args=[item.pk]))
        self.client.post(reverse("ventas:item_eliminar", args=[item.pk]))

        self.assertEqual(ItemVenta.objects.count(), 0)
        self.assertEqual(Venta.objects.get().total, Decimal("0.00"))

    def test_bajar_la_cantidad_a_cero_quita_el_producto(self):
        self.client.post(reverse("ventas:agregar_item", args=[self.producto.pk]))
        item = ItemVenta.objects.get()
        self.client.post(reverse("ventas:item_decrementar", args=[item.pk]))
        self.assertEqual(ItemVenta.objects.count(), 0)

    def test_producto_no_encontrado_queda_pendiente_de_validar(self):
        self.client.post(reverse("ventas:agregar_no_encontrado"), {"nombre": "Bolsa de hielo", "precio": "20"})

        producto = Producto.objects.get(nombre="Bolsa de hielo")
        self.assertTrue(producto.pendiente_validacion)
        self.assertFalse(producto.activo)
        self.assertEqual(ItemVenta.objects.count(), 1)

    def test_la_busqueda_instantanea_encuentra_por_nombre(self):
        respuesta = self.client.get(reverse("ventas:buscar_productos_json"), {"q": "coca"})
        nombres = [p["nombre"] for p in respuesta.json()["resultados"]]
        self.assertEqual(nombres, ["Coca 600"])

    def test_otro_negocio_no_puede_tocar_mi_carrito(self):
        self.client.post(reverse("ventas:agregar_item", args=[self.producto.pk]))
        item = ItemVenta.objects.get()

        otro_usuario, _ = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra tienda")
        self.client.force_login(otro_usuario)
        respuesta = self.client.post(reverse("ventas:item_eliminar", args=[item.pk]))

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(ItemVenta.objects.count(), 1)

    def test_el_ticket_muestra_nombre_y_ubicacion_del_negocio(self):
        venta = Venta.objects.create(negocio=self.negocio, folio=1, estado=Venta.Estado.COBRADA)
        ItemVenta.objects.create(
            venta=venta, producto=self.producto, cantidad=Decimal("1"), precio_unitario=Decimal("25"),
        )
        respuesta = self.client.get(reverse("ventas:ticket", args=[venta.pk]))
        self.assertContains(respuesta, "Abarrotes Prueba")
        self.assertContains(respuesta, "Iztapalapa")


class AvisoDeReabastecimientoAlCobrarTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        # ideal 20 y mínimo 2: amarillo desde 10, naranja desde 5, rojo desde 2
        self.producto = crear_producto(self.negocio, cantidad="11", minimo="2", ideal="20")
        self.client.force_login(self.usuario)

    def cobrar(self, piezas):
        self.client.post(reverse("ventas:agregar_item", args=[self.producto.pk]))
        item = ItemVenta.objects.get()
        item.cantidad = Decimal(piezas)
        item.save()
        respuesta = self.client.post(reverse("ventas:cobrar"))
        return [str(m) for m in get_messages(respuesta.wsgi_request)]

    def test_avisa_cuando_el_producto_pasa_a_amarillo(self):
        avisos = self.cobrar("2")  # quedan 9
        self.assertTrue(any("mitad" in aviso for aviso in avisos))

    def test_avisa_cuando_el_producto_llega_al_minimo(self):
        avisos = self.cobrar("9")  # quedan 2
        self.assertTrue(any("mínimo" in aviso for aviso in avisos))

    def test_en_el_limite_de_la_mitad_ya_cuenta_como_amarillo(self):
        self.cobrar("1")  # quedan 10, justo la mitad del ideal
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nivel_stock, "amarillo")

    def test_el_historial_de_ventas_se_pagina(self):
        for folio in range(1, 31):
            Venta.objects.create(negocio=self.negocio, folio=folio, estado=Venta.Estado.COBRADA)
        respuesta = self.client.get(reverse("ventas:historial"))
        self.assertEqual(len(respuesta.context["ventas"]), 25)
        self.assertEqual(respuesta.context["pagina"].paginator.num_pages, 2)
