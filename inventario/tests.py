from decimal import Decimal

from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.testing import crear_negocio, crear_producto
from finanzas.models import GastoOperativo
from ventas.models import ItemVenta, Venta

from .models import HistorialModificacionProducto, Producto


class CalculosDeProductoTests(SimpleTestCase):
    def test_margen_bruto(self):
        producto = Producto(costo=Decimal("15"), precio_venta=Decimal("25"))
        self.assertEqual(producto.margen_porcentaje, Decimal("40.0"))

    def test_stock_critico_cuando_llega_al_minimo(self):
        en_el_minimo = Producto(cantidad_actual=Decimal("2"), cantidad_minima=Decimal("2"))
        arriba_del_minimo = Producto(cantidad_actual=Decimal("3"), cantidad_minima=Decimal("2"))
        self.assertTrue(en_el_minimo.stock_critico)
        self.assertFalse(arriba_del_minimo.stock_critico)


class SemaforoDeReabastecimientoTests(SimpleTestCase):
    """Con ideal 20 y mínimo 2: amarillo hasta 10, naranja hasta 5, rojo hasta 2."""

    def producto(self, actual, minimo="2", ideal="20", pendiente=False):
        return Producto(
            cantidad_actual=Decimal(actual), cantidad_minima=Decimal(minimo),
            stock_ideal=Decimal(ideal), pendiente_validacion=pendiente,
        )

    def test_verde_cuando_hay_mas_de_la_mitad(self):
        self.assertEqual(self.producto("11").nivel_stock, "ok")

    def test_amarillo_a_la_mitad(self):
        self.assertEqual(self.producto("10").nivel_stock, "amarillo")

    def test_naranja_a_un_cuarto(self):
        self.assertEqual(self.producto("5").nivel_stock, "naranja")
        self.assertEqual(self.producto("6").nivel_stock, "amarillo")

    def test_rojo_al_llegar_al_minimo(self):
        self.assertEqual(self.producto("2").nivel_stock, "rojo")
        self.assertEqual(self.producto("0").nivel_stock, "rojo")

    def test_sin_stock_ideal_se_usan_4_veces_el_minimo(self):
        producto = self.producto("4", minimo="2", ideal="0")
        self.assertEqual(producto.stock_ideal_efectivo, Decimal("8"))
        self.assertEqual(producto.nivel_stock, "amarillo")

    def test_si_el_cuarto_queda_debajo_del_minimo_no_hay_naranja(self):
        # ideal 6 y mínimo 3: un cuarto serían 1.5, pero rojo ya llega hasta 3
        self.assertEqual(self.producto("4", minimo="3", ideal="6").nivel_stock, "ok")
        self.assertEqual(self.producto("3", minimo="3", ideal="6").nivel_stock, "rojo")

    def test_un_producto_pendiente_de_validar_no_lleva_semaforo(self):
        self.assertEqual(self.producto("0", minimo="0", ideal="0", pendiente=True).nivel_stock, "ok")


class InventarioTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.producto = crear_producto(self.negocio)
        self.client.force_login(self.usuario)

    def datos_de_edicion(self, **cambios):
        datos = {
            "nombre": "Coca 600", "descripcion": "", "costo": "15", "precio_venta": "25",
            "cantidad_actual": "10", "cantidad_minima": "2",
        }
        datos.update(cambios)
        return datos

    def test_las_pantallas_abren(self):
        for nombre in ("inventario:panel", "inventario:alertas"):
            with self.subTest(pantalla=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)

    def test_alta_de_producto(self):
        datos = self.datos_de_edicion(nombre="Pepsi 600")
        self.client.post(reverse("inventario:producto_alta"), datos)
        self.assertTrue(Producto.objects.filter(negocio=self.negocio, nombre="Pepsi 600").exists())

    def test_editar_sin_motivo_no_cambia_nada(self):
        url = reverse("inventario:producto_editar", args=[self.producto.pk])
        self.client.post(url, self.datos_de_edicion(precio_venta="30"))

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio_venta, Decimal("25.00"))
        self.assertEqual(HistorialModificacionProducto.objects.count(), 0)

    def test_editar_con_motivo_guarda_el_cambio_y_el_historial(self):
        url = reverse("inventario:producto_editar", args=[self.producto.pk])
        self.client.post(url, self.datos_de_edicion(precio_venta="30", motivo="Subió el proveedor"))

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio_venta, Decimal("30.00"))
        self.assertEqual(HistorialModificacionProducto.objects.get().motivo, "Subió el proveedor")

    def test_baja_conserva_las_ventas_anteriores(self):
        venta = Venta.objects.create(negocio=self.negocio, folio=1, estado=Venta.Estado.COBRADA)
        ItemVenta.objects.create(
            venta=venta, producto=self.producto, cantidad=Decimal("1"), precio_unitario=Decimal("25"),
        )
        self.client.post(reverse("inventario:producto_eliminar", args=[self.producto.pk]))

        self.producto.refresh_from_db()
        self.assertFalse(self.producto.activo)
        self.assertTrue(self.producto.tiene_ventas)
        self.assertEqual(ItemVenta.objects.count(), 1)

    def test_producto_pendiente_se_activa_al_completarlo(self):
        pendiente = Producto.objects.create(
            negocio=self.negocio, nombre="Bolsa de hielo", costo=Decimal("0"), precio_venta=Decimal("20"),
            activo=False, pendiente_validacion=True,
        )
        datos = self.datos_de_edicion(nombre="Bolsa de hielo", costo="8", precio_venta="20", motivo="Completar datos")
        self.client.post(reverse("inventario:producto_editar", args=[pendiente.pk]), datos)

        pendiente.refresh_from_db()
        self.assertTrue(pendiente.activo)
        self.assertFalse(pendiente.pendiente_validacion)

    def test_las_alertas_ponen_primero_el_producto_mas_critico(self):
        crear_producto(self.negocio, nombre="Justo en el minimo", cantidad="5", minimo="5")
        crear_producto(self.negocio, nombre="Casi sin stock", cantidad="1", minimo="5")

        respuesta = self.client.get(reverse("inventario:alertas"))
        nombres = [p.nombre for p in respuesta.context["alertas"]]
        self.assertEqual(nombres, ["Casi sin stock", "Justo en el minimo"])
        self.assertEqual(respuesta.context["conteo"]["rojo"], 2)

    def test_las_alertas_se_ordenan_por_color(self):
        # ideal 20, mínimo 2 -> rojo en 2 o menos, naranja hasta 5, amarillo hasta 10
        crear_producto(self.negocio, nombre="Amarillo", cantidad="9", minimo="2", ideal="20")
        crear_producto(self.negocio, nombre="Rojo", cantidad="2", minimo="2", ideal="20")
        crear_producto(self.negocio, nombre="Naranja", cantidad="4", minimo="2", ideal="20")
        crear_producto(self.negocio, nombre="Verde", cantidad="15", minimo="2", ideal="20")

        respuesta = self.client.get(reverse("inventario:alertas"))
        self.assertEqual([p.nombre for p in respuesta.context["alertas"]], ["Rojo", "Naranja", "Amarillo"])
        self.assertEqual(respuesta.context["conteo"], {"rojo": 1, "naranja": 1, "amarillo": 1, "total": 3})

    def test_el_panel_carga_pocos_productos_y_el_resto_con_ver_mas(self):
        for numero in range(30):
            crear_producto(self.negocio, nombre=f"Producto {numero:02d}")
        respuesta = self.client.get(reverse("inventario:panel"))
        self.assertEqual(len(respuesta.context["productos"]), 20)
        self.assertTrue(respuesta.context["hay_mas"])
        self.assertEqual(respuesta.context["total_productos"], 31)

        siguiente = self.client.get(reverse("inventario:panel_filas"), {"page": 2}).json()
        self.assertFalse(siguiente["hay_mas"])
        self.assertEqual(siguiente["html"].count("<tr"), 11)

    def test_el_panel_no_hace_una_consulta_por_producto(self):
        for numero in range(20):
            crear_producto(self.negocio, nombre=f"Producto {numero:02d}")
        self.client.get(reverse("inventario:panel"))  # calienta el cache
        with CaptureQueriesContext(connection) as consultas:
            self.client.get(reverse("inventario:panel"))
        # antes eran más de 90 (un formulario por producto); ahora no dependen de cuántos productos haya
        self.assertLess(len(consultas), 16)

    def test_abrir_un_producto_desde_el_buscador_abre_su_edicion(self):
        otro = crear_producto(self.negocio, nombre="Pepsi 600")
        respuesta = self.client.get(reverse("inventario:panel"), {"abrir": otro.pk})
        self.assertEqual(respuesta.context["abrir_edicion_pk"], otro.pk)

    def test_los_datos_del_producto_llenan_el_formulario_de_edicion(self):
        datos = self.client.get(reverse("inventario:producto_datos", args=[self.producto.pk])).json()
        self.assertEqual(datos["nombre"], "Coca 600")
        self.assertEqual(datos["precio_venta"], "25.00")
        self.assertEqual(datos["cantidad_actual"], "10")
        self.assertFalse(datos["a_granel"])

    def test_los_datos_de_un_producto_ajeno_no_se_ven(self):
        otro_usuario, otro_negocio = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra")
        ajeno = crear_producto(otro_negocio, nombre="Ajeno")
        self.assertEqual(self.client.get(reverse("inventario:producto_datos", args=[ajeno.pk])).status_code, 404)

    def test_la_busqueda_del_catalogo_ignora_acentos(self):
        crear_producto(self.negocio, nombre="Jabón Zote")
        respuesta = self.client.get(reverse("inventario:panel"), {"q": "jabon"})
        self.assertEqual([p.nombre for p in respuesta.context["productos"]], ["Jabón Zote"])

    def test_el_alta_con_piezas_registra_la_compra_de_mercancia(self):
        datos = self.datos_de_edicion(nombre="Pepsi 600", costo="13", cantidad_actual="12")
        self.client.post(reverse("inventario:producto_alta"), datos)

        compra = GastoOperativo.objects.get()
        self.assertEqual(compra.tipo, GastoOperativo.Tipo.MERCANCIA)
        self.assertEqual(compra.monto, Decimal("156.00"))

    def test_el_alta_sin_piezas_no_registra_compra(self):
        datos = self.datos_de_edicion(nombre="Pepsi 600", cantidad_actual="0")
        self.client.post(reverse("inventario:producto_alta"), datos)
        self.assertEqual(GastoOperativo.objects.count(), 0)

    def test_dar_de_alta_un_producto_a_granel_con_decimales(self):
        datos = self.datos_de_edicion(nombre="Frijol", cantidad_actual="2.5", a_granel="on")
        self.client.post(reverse("inventario:producto_alta"), datos)

        frijol = Producto.objects.get(nombre="Frijol")
        self.assertTrue(frijol.a_granel)
        self.assertEqual(frijol.cantidad_actual, Decimal("2.5"))

    def test_un_producto_por_pieza_no_acepta_decimales(self):
        datos = self.datos_de_edicion(nombre="Pepsi 600", cantidad_actual="2.5")
        self.client.post(reverse("inventario:producto_alta"), datos)
        self.assertFalse(Producto.objects.filter(nombre="Pepsi 600").exists())

    def test_el_codigo_de_barras_no_se_repite(self):
        self.client.post(reverse("inventario:producto_alta"), self.datos_de_edicion(nombre="Uno", codigo_barras="123456789"))
        self.client.post(reverse("inventario:producto_alta"), self.datos_de_edicion(nombre="Dos", codigo_barras="123456789"))
        self.assertEqual(Producto.objects.filter(codigo_barras="123456789").count(), 1)

    def test_editar_las_existencias_es_una_correccion_y_no_una_compra(self):
        url = reverse("inventario:producto_editar", args=[self.producto.pk])
        self.client.post(url, self.datos_de_edicion(cantidad_actual="40", motivo="Conteo"))
        self.assertEqual(GastoOperativo.objects.count(), 0)

    def test_la_busqueda_instantanea_regresa_json(self):
        crear_producto(self.negocio, nombre="Pepsi 600")
        respuesta = self.client.get(reverse("inventario:buscar_json"), {"q": "pep"})
        self.assertEqual([r["nombre"] for r in respuesta.json()["resultados"]], ["Pepsi 600"])

    def test_la_busqueda_no_regresa_productos_de_otra_tienda(self):
        otro_usuario, otro_negocio = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra")
        crear_producto(otro_negocio, nombre="Pepsi ajena")
        respuesta = self.client.get(reverse("inventario:buscar_json"), {"q": "pepsi"})
        self.assertEqual(respuesta.json()["resultados"], [])

    def test_el_stock_ideal_no_puede_ser_menor_al_minimo(self):
        datos = self.datos_de_edicion(nombre="Pepsi 600", cantidad_minima="10", stock_ideal="5")
        self.client.post(reverse("inventario:producto_alta"), datos)
        self.assertFalse(Producto.objects.filter(nombre="Pepsi 600").exists())

    def test_otro_negocio_no_puede_editar_mi_producto(self):
        otro_usuario, _ = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra tienda")
        self.client.force_login(otro_usuario)
        url = reverse("inventario:producto_editar", args=[self.producto.pk])

        respuesta = self.client.post(url, self.datos_de_edicion(precio_venta="1", motivo="Intento"))
        self.assertEqual(respuesta.status_code, 404)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio_venta, Decimal("25.00"))


class AlertasPorLotesTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        for numero in range(25):
            crear_producto(self.negocio, nombre=f"Agotado {numero:02d}", cantidad="0", minimo="2")
        crear_producto(self.negocio, nombre="Jabón Zote", cantidad="1", minimo="2")
        crear_producto(self.negocio, nombre="Bien surtido", cantidad="100", minimo="2")

    def pedir(self, **filtros):
        return self.client.get(reverse("inventario:alertas_filas"), filtros).json()

    def test_la_pantalla_trae_solo_el_primer_lote(self):
        respuesta = self.client.get(reverse("inventario:alertas"))
        self.assertEqual(len(respuesta.context["alertas"]), 20)
        self.assertTrue(respuesta.context["hay_mas"])
        self.assertEqual(respuesta.context["conteo"]["total"], 26)

    def test_ver_mas_regresa_el_siguiente_lote(self):
        segunda = self.pedir(page=2)
        self.assertEqual(segunda["html"].count("alert-item"), 6)
        self.assertFalse(segunda["hay_mas"])

    def test_la_busqueda_instantanea_ignora_acentos_y_tolera_errores_de_dedo(self):
        self.assertEqual(self.pedir(q="jabon")["total"], 1)
        self.assertEqual(self.pedir(q="jbon")["total"], 1)
        self.assertIn("Jabón Zote", self.pedir(q="jabon")["html"])

    def test_el_filtro_por_color(self):
        self.assertEqual(self.pedir(nivel="rojo")["total"], 26)
        self.assertEqual(self.pedir(nivel="amarillo")["total"], 0)

    def test_lo_que_esta_bien_surtido_no_aparece(self):
        self.assertNotIn("Bien surtido", self.pedir(page=1)["html"] + self.pedir(page=2)["html"])

    def test_no_se_ven_las_alertas_de_otra_tienda(self):
        otro_usuario, otro_negocio = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra")
        crear_producto(otro_negocio, nombre="Ajeno agotado", cantidad="0", minimo="2")
        self.assertEqual(self.pedir(q="ajeno")["total"], 0)


class EdicionConErroresTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.producto = crear_producto(self.negocio)
        self.client.force_login(self.usuario)

    def test_un_error_regresa_al_panel_con_el_modal_de_edicion_abierto_y_lo_escrito(self):
        datos = {
            "nombre": "Coca 600", "descripcion": "", "costo": "15", "precio_venta": "99",
            "cantidad_actual": "10", "cantidad_minima": "2",
        }  # sin "motivo"
        respuesta = self.client.post(reverse("inventario:producto_editar", args=[self.producto.pk]), datos)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["abrir_edicion_pk"], self.producto.pk)
        self.assertTrue(respuesta.context["edicion_con_errores"])
        self.assertContains(respuesta, "Indica el motivo del cambio")
        self.assertContains(respuesta, 'value="99"')
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio_venta, Decimal("25.00"))

    def test_el_panel_abre_el_alta_con_el_codigo_que_no_se_encontro_en_caja(self):
        respuesta = self.client.get(reverse("inventario:panel"), {"nuevo_codigo": "7501055300075"})
        self.assertTrue(respuesta.context["abrir_modal_alta"])
        self.assertContains(respuesta, 'value="7501055300075"')

    def test_los_productos_a_granel_se_ven_con_kilos_en_la_tabla(self):
        frijol = crear_producto(self.negocio, nombre="Frijol", cantidad="2")
        frijol.a_granel = True
        frijol.save()
        respuesta = self.client.get(reverse("inventario:panel"))
        self.assertContains(respuesta, "A granel")
        self.assertContains(respuesta, "2 kg")
