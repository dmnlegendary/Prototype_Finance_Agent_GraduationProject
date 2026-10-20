import json
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.testing import crear_negocio, crear_producto
from finanzas.models import GastoOperativo
from inventario.models import Producto

from . import carrito
from .cobro import SinExistencias, cobrar_venta
from .models import ItemVenta, Venta


class CalculosDeVentaTests(SimpleTestCase):
    def test_subtotal_se_redondea_a_dos_decimales(self):
        item = ItemVenta(cantidad=Decimal("1.5"), precio_unitario=Decimal("12.99"))
        self.assertEqual(item.subtotal, Decimal("19.49"))

    def test_subtotal_de_un_producto_a_granel(self):
        item = ItemVenta(cantidad=Decimal("0.250"), precio_unitario=Decimal("38"))
        self.assertEqual(item.subtotal, Decimal("9.50"))


class ApiDeVentasBase(TestCase):
    """Ayudas para llamar a la API JSON del punto de venta."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.producto = crear_producto(self.negocio)
        self.client.force_login(self.usuario)

    def post(self, nombre_url, argumentos=None, datos=None):
        return self.client.post(
            reverse(nombre_url, args=argumentos or []), data=json.dumps(datos or {}), content_type="application/json",
        )

    def agregar(self, producto=None, cantidad=1, numero=1):
        producto = producto or self.producto
        return self.post("ventas:api_agregar", [numero], {"producto_id": producto.pk, "cantidad": cantidad})


class FlujoDeVentaTests(ApiDeVentasBase):
    def test_la_pantalla_de_ventas_abre(self):
        respuesta = self.client.get(reverse("ventas:punto_de_venta"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["estado_inicial"]["carrito"], 1)

    def test_en_pantalla_se_les_dice_cajas_y_no_carritos(self):
        respuesta = self.client.get(reverse("ventas:punto_de_venta"))
        self.assertContains(respuesta, "Caja 1")
        self.assertContains(respuesta, "Caja 2")
        self.assertNotContains(respuesta, "Carrito 1")
        self.assertNotContains(respuesta, "al carrito")

    def test_total_de_la_venta_se_guarda_con_dos_decimales(self):
        venta = Venta.objects.create(negocio=self.negocio, folio=1)
        ItemVenta.objects.create(
            venta=venta, producto=self.producto, cantidad=Decimal("1.5"), precio_unitario=Decimal("12.99"),
        )
        venta.recalcular_total()
        venta.refresh_from_db()
        self.assertEqual(venta.total, Decimal("19.49"))

    def test_agregar_cambiar_cantidad_y_cobrar(self):
        self.agregar()
        item = ItemVenta.objects.get()
        # la cantidad se puede escribir (en el ejemplo, 8 piezas)
        respuesta = self.post("ventas:api_cantidad", [item.pk], {"cantidad": 8}).json()
        self.assertEqual(respuesta["total"], "200.00")

        resultado = self.post("ventas:api_cobrar", [1]).json()
        self.producto.refresh_from_db()
        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["ticket"]["total"], "200.00")
        self.assertEqual(self.producto.cantidad_actual, Decimal("2"))
        self.assertEqual(Venta.objects.get(estado=Venta.Estado.COBRADA).total, Decimal("200.00"))

    def test_cancelar_no_mueve_el_inventario(self):
        self.agregar()
        self.post("ventas:api_cancelar", [1])

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.cantidad_actual, Decimal("10"))
        self.assertEqual(Venta.objects.get(estado=Venta.Estado.CANCELADA).total, Decimal("25.00"))

    def test_quitar_producto_del_carrito(self):
        self.agregar(cantidad=3)
        item = ItemVenta.objects.get()
        respuesta = self.post("ventas:api_quitar", [item.pk]).json()

        self.assertEqual(respuesta["renglones"], [])
        self.assertEqual(Venta.objects.get().total, Decimal("0.00"))

    def test_escribir_cero_quita_el_producto(self):
        self.agregar()
        item = ItemVenta.objects.get()
        self.post("ventas:api_cantidad", [item.pk], {"cantidad": 0})
        self.assertEqual(ItemVenta.objects.count(), 0)

    def test_otro_negocio_no_puede_tocar_mi_carrito(self):
        self.agregar()
        item = ItemVenta.objects.get()

        otro_usuario, _ = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra tienda")
        self.client.force_login(otro_usuario)
        respuesta = self.post("ventas:api_quitar", [item.pk])

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(ItemVenta.objects.count(), 1)

    def test_el_ticket_muestra_nombre_y_ubicacion_del_negocio(self):
        venta = Venta.objects.create(negocio=self.negocio, folio=1, estado=Venta.Estado.COBRADA)
        ItemVenta.objects.create(
            venta=venta, producto=self.producto, cantidad=Decimal("1"), precio_unitario=Decimal("25"),
        )
        respuesta = self.client.get(reverse("ventas:ticket", args=[venta.pk]))
        self.assertContains(respuesta, "Abarrotes Prueba")
        self.assertContains(respuesta, "Iztapalapa, CDMX")

    def test_el_historial_de_ventas_se_pagina(self):
        for folio in range(1, 31):
            Venta.objects.create(negocio=self.negocio, folio=folio, estado=Venta.Estado.COBRADA)
        respuesta = self.client.get(reverse("ventas:historial"))
        self.assertEqual(len(respuesta.context["ventas"]), 25)
        self.assertEqual(respuesta.context["pagina"].paginator.num_pages, 2)


class ReglaDeOroDeExistenciasTests(ApiDeVentasBase):
    """No se puede vender lo que no hay en el inventario."""

    def test_no_se_agrega_mas_de_lo_que_hay(self):
        respuesta = self.agregar(cantidad=11)  # hay 10
        datos = respuesta.json()

        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(datos["error"], "sin_existencias")
        self.assertEqual(datos["disponible"], "10")
        self.assertFalse(datos["producto"]["a_granel"])
        self.assertEqual(ItemVenta.objects.count(), 0)

    def test_un_producto_en_cero_no_se_puede_vender(self):
        agotado = crear_producto(self.negocio, nombre="Agotado", cantidad="0")
        respuesta = self.agregar(producto=agotado)
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("No hay existencias", respuesta.json()["mensaje"])

    def test_tampoco_se_puede_subir_la_cantidad_del_carrito_mas_alla_de_lo_que_hay(self):
        self.agregar(cantidad=5)
        item = ItemVenta.objects.get()
        respuesta = self.post("ventas:api_cantidad", [item.pk], {"cantidad": 90})

        self.assertEqual(respuesta.status_code, 409)
        item.refresh_from_db()
        self.assertEqual(item.cantidad, Decimal("5"))

    def test_si_agrega_mas_piezas_al_inventario_ya_se_puede_vender(self):
        agotado = crear_producto(self.negocio, nombre="Agotado", cantidad="0", costo="10")
        self.assertEqual(self.agregar(producto=agotado).status_code, 409)

        resultado = self.post("inventario:producto_resurtir", [agotado.pk], {"cantidad": 20, "costo": "12"}).json()
        self.assertTrue(resultado["ok"])
        self.assertEqual(self.agregar(producto=agotado, cantidad=3).status_code, 200)

        agotado.refresh_from_db()
        self.assertEqual(agotado.cantidad_actual, Decimal("20"))
        self.assertEqual(agotado.costo, Decimal("12.00"))

    def test_resurtir_registra_la_compra_en_los_gastos(self):
        self.post("inventario:producto_resurtir", [self.producto.pk], {"cantidad": 10, "costo": "15"})
        compra = GastoOperativo.objects.get()
        self.assertEqual(compra.tipo, GastoOperativo.Tipo.MERCANCIA)
        self.assertEqual(compra.monto, Decimal("150.00"))

    def test_resurtir_una_cantidad_mala_no_cambia_nada(self):
        respuesta = self.post("inventario:producto_resurtir", [self.producto.pk], {"cantidad": -4})
        self.assertEqual(respuesta.status_code, 400)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.cantidad_actual, Decimal("10"))

    def test_al_cobrar_se_revisa_otra_vez(self):
        # el otro carrito vende la última pieza antes de cobrar este
        self.agregar(cantidad=8, numero=1)
        self.agregar(cantidad=2, numero=2)
        self.post("ventas:api_cobrar", [2])
        self.producto.cantidad_actual = Decimal("1")
        self.producto.save()

        respuesta = self.post("ventas:api_cobrar", [1])
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(Venta.objects.filter(estado=Venta.Estado.COBRADA).count(), 1)

    def test_un_producto_no_encontrado_si_se_puede_vender(self):
        respuesta = self.post("ventas:api_no_encontrado", [1], {"nombre": "Bolsa de hielo", "precio": "20"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.post("ventas:api_cobrar", [1]).status_code, 200)


class ProductosAGranelTests(ApiDeVentasBase):
    def setUp(self):
        super().setUp()
        self.frijol = crear_producto(self.negocio, nombre="Frijol", costo="28", precio="40", cantidad="5")
        self.frijol.a_granel = True
        self.frijol.save()

    def test_se_vende_por_gramos(self):
        respuesta = self.agregar(producto=self.frijol, cantidad="0.250").json()
        self.assertEqual(respuesta["renglones"][0]["cantidad"], "0.25")
        self.assertEqual(respuesta["total"], "10.00")

        self.post("ventas:api_cobrar", [1])
        self.frijol.refresh_from_db()
        self.assertEqual(self.frijol.cantidad_actual, Decimal("4.750"))

    def test_un_producto_por_pieza_no_acepta_decimales(self):
        respuesta = self.agregar(producto=self.producto, cantidad="1.5")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(ItemVenta.objects.count(), 0)

    def test_el_granel_tambien_respeta_las_existencias(self):
        respuesta = self.agregar(producto=self.frijol, cantidad="5.5")
        self.assertEqual(respuesta.status_code, 409)
        self.assertTrue(respuesta.json()["producto"]["a_granel"])


class DosCarritosTests(ApiDeVentasBase):
    def test_cada_carrito_tiene_sus_productos(self):
        otro = crear_producto(self.negocio, nombre="Pepsi")
        self.agregar(numero=1)
        self.agregar(producto=otro, numero=2)

        uno = self.client.get(reverse("ventas:api_carrito", args=[1])).json()
        dos = self.client.get(reverse("ventas:api_carrito", args=[2])).json()
        self.assertEqual([r["nombre"] for r in uno["renglones"]], ["Coca 600"])
        self.assertEqual([r["nombre"] for r in dos["renglones"]], ["Pepsi"])
        self.assertEqual(dos["contadores"], {"1": 1, "2": 1})

    def test_se_puede_cobrar_un_carrito_sin_tocar_el_otro(self):
        self.agregar(numero=1)
        self.agregar(numero=2)
        self.post("ventas:api_cobrar", [1])

        self.assertEqual(Venta.objects.filter(estado=Venta.Estado.COBRADA, carrito=1).count(), 1)
        dos = self.client.get(reverse("ventas:api_carrito", args=[2])).json()
        self.assertEqual(len(dos["renglones"]), 1)

    def test_un_numero_de_carrito_inventado_cae_en_el_primero(self):
        self.assertEqual(carrito.numero_de_carrito_valido(7), 1)
        self.assertEqual(carrito.numero_de_carrito_valido("hola"), 1)

    def test_no_puede_haber_dos_carritos_abiertos_con_el_mismo_numero(self):
        carrito.venta_en_curso(self.negocio, 1)
        carrito.venta_en_curso(self.negocio, 1)
        self.assertEqual(Venta.objects.filter(estado=Venta.Estado.EN_CURSO).count(), 1)


class PrecioYCostoGuardadosEnLaVentaTests(ApiDeVentasBase):
    def test_cambiar_el_precio_no_cambia_las_ventas_de_antes(self):
        self.agregar(cantidad=4)
        self.post("ventas:api_cobrar", [1])

        self.producto.precio_venta = Decimal("23")
        self.producto.costo = Decimal("19")
        self.producto.save()

        item = ItemVenta.objects.get()
        venta = Venta.objects.get(estado=Venta.Estado.COBRADA)
        self.assertEqual(item.precio_unitario, Decimal("25.00"))
        self.assertEqual(item.costo_unitario, Decimal("15.00"))
        self.assertEqual(venta.total, Decimal("100.00"))

    def test_una_venta_nueva_usa_el_precio_nuevo(self):
        self.producto.precio_venta = Decimal("23")
        self.producto.save()
        self.agregar()
        self.assertEqual(ItemVenta.objects.get().precio_unitario, Decimal("23.00"))


class BusquedaYCodigoDeBarrasTests(ApiDeVentasBase):
    def buscar(self, texto):
        return [r["nombre"] for r in self.client.get(reverse("ventas:buscar_productos_json"), {"q": texto}).json()["resultados"]]

    def test_la_busqueda_manual_ignora_los_acentos(self):
        crear_producto(self.negocio, nombre="Jabón Zote")
        self.assertEqual(self.buscar("jabon"), ["Jabón Zote"])

    def test_la_busqueda_manual_tolera_un_error_de_dedo(self):
        crear_producto(self.negocio, nombre="Jabón Zote")
        crear_producto(self.negocio, nombre="Sabritas Original")
        self.assertEqual(self.buscar("jbon"), ["Jabón Zote"])
        self.assertEqual(self.buscar("sabrtas"), ["Sabritas Original"])

    def test_la_busqueda_manual_no_importa_el_orden(self):
        crear_producto(self.negocio, nombre="Coca-Cola 600ml")
        self.assertIn("Coca-Cola 600ml", self.buscar("600 coca"))

    def test_encuentra_un_producto_por_su_codigo_de_barras(self):
        self.producto.codigo_barras = "7501055300075"
        self.producto.save()

        encontrado = self.client.get(reverse("ventas:api_codigo"), {"c": "7501055300075"}).json()
        self.assertTrue(encontrado["encontrado"])
        self.assertEqual(encontrado["producto"]["nombre"], "Coca 600")

        self.assertFalse(self.client.get(reverse("ventas:api_codigo"), {"c": "000"}).json()["encontrado"])

    def test_el_catalogo_para_vender_sin_internet_trae_los_productos_activos(self):
        baja = crear_producto(self.negocio, nombre="Baja")
        baja.activo = False
        baja.save()

        nombres = [p["nombre"] for p in self.client.get(reverse("ventas:api_catalogo")).json()["productos"]]
        self.assertIn("Coca 600", nombres)
        self.assertNotIn("Baja", nombres)


class ProductosNoEncontradosTests(ApiDeVentasBase):
    def test_se_reutiliza_el_mismo_producto_pendiente(self):
        self.post("ventas:api_no_encontrado", [1], {"nombre": "Bolsa de hielo", "precio": "20"})
        self.post("ventas:api_cobrar", [1])
        self.post("ventas:api_no_encontrado", [1], {"nombre": "bolsa de hielo", "precio": "20"})

        self.assertEqual(Producto.objects.filter(pendiente_validacion=True).count(), 1)

    def test_un_precio_malo_no_agrega_nada(self):
        respuesta = self.post("ventas:api_no_encontrado", [1], {"nombre": "Hielo", "precio": "0"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(Producto.objects.filter(pendiente_validacion=True).count(), 0)


class AvisoDeReabastecimientoAlCobrarTests(ApiDeVentasBase):
    def setUp(self):
        super().setUp()
        # ideal 20 y mínimo 2: amarillo desde 10, naranja desde 5, rojo desde 2
        self.producto = crear_producto(self.negocio, nombre="Con semáforo", cantidad="11", minimo="2", ideal="20")

    def cobrar(self, piezas):
        self.agregar(producto=self.producto, cantidad=piezas)
        return self.post("ventas:api_cobrar", [1]).json()["avisos"]

    def test_avisa_cuando_el_producto_pasa_a_amarillo(self):
        avisos = self.cobrar(2)  # quedan 9
        self.assertTrue(any("mitad" in aviso["texto"] and aviso["nivel"] == "amarillo" for aviso in avisos))

    def test_avisa_cuando_el_producto_llega_al_minimo(self):
        avisos = self.cobrar(9)  # quedan 2
        self.assertTrue(any("mínimo" in aviso["texto"] and aviso["nivel"] == "rojo" for aviso in avisos))

    def test_en_el_limite_de_la_mitad_ya_cuenta_como_amarillo(self):
        self.cobrar(1)  # quedan 10, justo la mitad del ideal
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nivel_stock, "amarillo")

    def test_si_no_cambia_de_color_no_avisa(self):
        crear = crear_producto(self.negocio, nombre="Con mucho", cantidad="100", minimo="2", ideal="100")
        self.agregar(producto=crear, cantidad=1)
        self.assertEqual(self.post("ventas:api_cobrar", [1]).json()["avisos"], [])


class CobroDirectoTests(TestCase):
    def test_cobrar_venta_lanza_sin_existencias_y_no_mueve_nada(self):
        _, negocio = crear_negocio()
        producto = crear_producto(negocio, cantidad="2")
        venta = carrito.venta_en_curso(negocio, 1)
        ItemVenta.objects.create(venta=venta, producto=producto, cantidad=Decimal("5"), precio_unitario=Decimal("25"))

        with self.assertRaises(SinExistencias):
            cobrar_venta(venta)

        producto.refresh_from_db()
        venta.refresh_from_db()
        self.assertEqual(producto.cantidad_actual, Decimal("2"))
        self.assertEqual(venta.estado, Venta.Estado.EN_CURSO)


class CobroDuplicadoTests(TestCase):
    """Un doble clic con internet lento no debe registrar la misma venta dos veces."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.producto = crear_producto(self.negocio, cantidad="10")
        self.venta = carrito.venta_en_curso(self.negocio, 1, self.usuario)
        ItemVenta.objects.create(venta=self.venta, producto=self.producto, cantidad=Decimal("2"), precio_unitario=Decimal("25"))

    def test_cobrar_dos_veces_la_misma_venta_solo_descuenta_una_vez(self):
        from .cobro import VentaYaCobrada
        cobrar_venta(self.venta)
        with self.assertRaises(VentaYaCobrada):
            cobrar_venta(self.venta)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.cantidad_actual, Decimal("8"))
        self.assertEqual(Venta.objects.filter(estado=Venta.Estado.COBRADA).count(), 1)

    def test_el_segundo_cobro_por_la_api_se_rechaza_con_un_aviso(self):
        # la primera petición cobra el carrito; la segunda llega con una venta que ya no está en curso
        from unittest.mock import patch
        self.client.post(reverse("ventas:api_cobrar", args=[1]), data="{}", content_type="application/json")
        with patch("ventas.views.carrito.venta_en_curso", return_value=self.venta):
            respuesta = self.client.post(reverse("ventas:api_cobrar", args=[1]), data="{}", content_type="application/json")
        self.assertEqual(respuesta.status_code, 409)
        self.assertEqual(respuesta.json()["error"], "ya_cobrada")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.cantidad_actual, Decimal("8"))
