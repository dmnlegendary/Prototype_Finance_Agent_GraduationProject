import json
from decimal import Decimal

from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from core.testing import crear_negocio, crear_producto
from finanzas.models import GastoOperativo
from ventas import carrito
from ventas.cobro import cobrar_venta
from ventas.models import ItemVenta, Venta

from .compras import agregar_existencias, registrar_alta
from .movimientos import registrar_movimiento
from .models import Categoria, HistorialModificacionProducto, MovimientoInventario, Producto


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
        self.categoria = Categoria.objects.get_or_create(nombre="Bebidas")[0]
        self.producto = crear_producto(self.negocio)
        self.client.force_login(self.usuario)

    def datos_de_edicion(self, **cambios):
        datos = {
            "nombre": "Coca 600", "descripcion": "Refresco de cola", "costo": "15", "precio_venta": "25",
            "cantidad_actual": "10", "cantidad_minima": "2", "categoria": self.categoria.pk,
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


class UrgenciaPorRitmoDeVentaTests(TestCase):
    """Dentro de un mismo color, primero va el producto que se acaba antes según lo que vende."""

    def setUp(self):
        from ventas.models import ItemVenta, Venta
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.rapido = crear_producto(self.negocio, nombre="Refresco rápido", cantidad="2", minimo="2")
        self.lento = crear_producto(self.negocio, nombre="Galleta lenta", cantidad="2", minimo="2")
        self.sin_ventas = crear_producto(self.negocio, nombre="Producto parado", cantidad="2", minimo="2")

        venta = Venta.objects.create(negocio=self.negocio, folio=1, estado=Venta.Estado.COBRADA)
        for producto, cantidad in ((self.rapido, "56"), (self.lento, "7")):  # 14 y 1.75 por semana
            ItemVenta.objects.create(venta=venta, producto=producto, cantidad=Decimal(cantidad), precio_unitario=Decimal("25"))

    def test_el_que_se_vende_mas_rapido_va_primero_y_el_que_no_se_vende_al_final(self):
        from .alertas import ordenar_por_urgencia, productos_con_alerta
        orden = [p.nombre for p in ordenar_por_urgencia(self.negocio, productos_con_alerta(self.negocio))]
        self.assertEqual(orden, ["Refresco rápido", "Galleta lenta", "Producto parado"])

    def test_se_calcula_lo_que_vende_por_semana_y_para_cuantos_dias_alcanza(self):
        from .alertas import ordenar_por_urgencia, productos_con_alerta
        lista = {p.nombre: p for p in ordenar_por_urgencia(self.negocio, productos_con_alerta(self.negocio))}
        self.assertEqual(lista["Refresco rápido"].vendidas_por_semana, Decimal("14"))
        self.assertEqual(lista["Refresco rápido"].dias_de_cobertura, 1)  # 2 piezas entre 2 al día
        self.assertIsNone(lista["Producto parado"].dias_de_cobertura)

    def test_el_color_manda_sobre_el_ritmo(self):
        from .alertas import ordenar_por_urgencia, productos_con_alerta
        crear_producto(self.negocio, nombre="Naranja", cantidad="3", minimo="2", ideal="12")
        orden = [p.nombre for p in ordenar_por_urgencia(self.negocio, productos_con_alerta(self.negocio))]
        self.assertEqual(orden[-1], "Naranja")

    def test_la_pantalla_de_alertas_muestra_el_ritmo(self):
        respuesta = self.client.get(reverse("inventario:alertas"))
        self.assertContains(respuesta, "Vende unas 14")
        self.assertContains(respuesta, "Sin ventas en las últimas 4 semanas")


class KardexTests(TestCase):
    """Todo cambio en las existencias deja un movimiento con su origen (venta, entrada, merma o ajuste)."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.categoria = Categoria.objects.get_or_create(nombre="Bebidas")[0]
        self.producto = crear_producto(self.negocio, nombre="Coca 600", cantidad="10")

    def datos(self, **cambios):
        datos = {
            "nombre": "Coca 600", "descripcion": "Refresco de cola", "costo": "15", "precio_venta": "25",
            "cantidad_actual": "10", "cantidad_minima": "2", "categoria": self.categoria.pk, "motivo": "Conteo",
        }
        datos.update(cambios)
        return datos

    def test_el_alta_con_piezas_deja_una_entrada(self):
        self.client.post(reverse("inventario:producto_alta"), self.datos(nombre="Pepsi 600", cantidad_actual="12"))
        movimiento = MovimientoInventario.objects.get(producto__nombre="Pepsi 600")
        self.assertEqual(movimiento.tipo, "ENTRADA")
        self.assertEqual(movimiento.cantidad, Decimal("12"))
        self.assertEqual(movimiento.existencia_resultante, Decimal("12"))

    def test_resurtir_deja_una_entrada(self):
        self.client.post(
            reverse("inventario:producto_resurtir", args=[self.producto.pk]),
            data='{"cantidad": 5, "costo": 16}', content_type="application/json",
        )
        movimiento = MovimientoInventario.objects.get()
        self.assertEqual((movimiento.tipo, movimiento.cantidad, movimiento.existencia_resultante), ("ENTRADA", Decimal("5"), Decimal("15")))

    def test_editar_las_existencias_deja_un_ajuste_con_su_motivo(self):
        self.client.post(
            reverse("inventario:producto_editar", args=[self.producto.pk]),
            self.datos(cantidad_actual="7", motivo="Conté y faltaban 3"),
        )
        movimiento = MovimientoInventario.objects.get()
        self.assertEqual((movimiento.tipo, movimiento.cantidad), ("AJUSTE", Decimal("-3")))
        self.assertEqual(movimiento.motivo, "Conté y faltaban 3")

    def test_se_puede_marcar_el_cambio_como_merma(self):
        self.client.post(
            reverse("inventario:producto_editar", args=[self.producto.pk]),
            self.datos(cantidad_actual="9", motivo="Se rompió una", tipo_ajuste="MERMA"),
        )
        self.assertEqual(MovimientoInventario.objects.get().tipo, "MERMA")

    def test_editar_sin_cambiar_las_existencias_no_deja_movimiento(self):
        self.client.post(reverse("inventario:producto_editar", args=[self.producto.pk]), self.datos(precio_venta="30"))
        self.assertEqual(MovimientoInventario.objects.count(), 0)

    def test_una_venta_deja_una_salida_ligada_a_su_folio(self):
        from ventas import carrito
        from ventas.cobro import cobrar_venta
        venta = carrito.venta_en_curso(self.negocio, 1, self.usuario)
        carrito.agregar_producto(venta, self.producto, Decimal("3"))
        cobrar_venta(venta)

        movimiento = MovimientoInventario.objects.get()
        self.assertEqual((movimiento.tipo, movimiento.cantidad, movimiento.existencia_resultante), ("VENTA", Decimal("-3"), Decimal("7")))
        self.assertEqual(movimiento.venta, venta)

    def test_la_pantalla_de_movimientos_filtra_por_tipo_y_producto(self):
        self.client.post(
            reverse("inventario:producto_resurtir", args=[self.producto.pk]),
            data='{"cantidad": 5}', content_type="application/json",
        )
        crear_producto(self.negocio, nombre="Galleta", cantidad="4")
        otro = crear_producto(self.negocio, nombre="Jabón", cantidad="4")
        self.client.post(
            reverse("inventario:producto_editar", args=[otro.pk]),
            self.datos(nombre="Jabón", cantidad_actual="3", motivo="Merma", tipo_ajuste="MERMA"),
        )

        todos = self.client.get(reverse("inventario:movimientos"))
        self.assertEqual(todos.status_code, 200)
        self.assertEqual(len(todos.context["pagina"].object_list), 2)
        mermas = self.client.get(reverse("inventario:movimientos"), {"tipo": "MERMA"})
        self.assertEqual([m.producto.nombre for m in mermas.context["pagina"].object_list], ["Jabón"])
        coca = self.client.get(reverse("inventario:movimientos"), {"q": "coca"})
        self.assertEqual([m.producto.nombre for m in coca.context["pagina"].object_list], ["Coca 600"])

    def test_se_puede_descargar_el_kardex_como_csv(self):
        self.client.post(
            reverse("inventario:producto_resurtir", args=[self.producto.pk]),
            data='{"cantidad": 5}', content_type="application/json",
        )
        respuesta = self.client.get(reverse("inventario:movimientos_exportar"))
        self.assertEqual(respuesta["Content-Type"], "text/csv; charset=utf-8")
        texto = respuesta.content.decode("utf-8-sig")
        self.assertIn("fecha,producto,tipo,cantidad,existencia_resultante,costo_unitario,motivo,folio_venta", texto)
        self.assertIn("Coca 600,ENTRADA,5.000,15.000", texto)

    def test_no_se_ven_los_movimientos_de_otra_tienda(self):
        self.client.post(
            reverse("inventario:producto_resurtir", args=[self.producto.pk]),
            data='{"cantidad": 5}', content_type="application/json",
        )
        otro_usuario, _ = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra")
        self.client.force_login(otro_usuario)
        respuesta = self.client.get(reverse("inventario:movimientos"))
        self.assertEqual(len(respuesta.context["pagina"].object_list), 0)


class ReglasDelProductoTests(TestCase):
    """Todo producto lleva categoría y descripción; el mínimo que se propone es 5."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.categoria = Categoria.objects.get_or_create(nombre="Bebidas")[0]

    def datos(self, **cambios):
        datos = {
            "nombre": "Pepsi", "descripcion": "Refresco de cola", "costo": "13", "precio_venta": "18",
            "cantidad_actual": "10", "cantidad_minima": "5", "categoria": self.categoria.pk,
        }
        datos.update(cambios)
        return datos

    def test_sin_categoria_no_se_da_de_alta(self):
        respuesta = self.client.post(reverse("inventario:producto_alta"), self.datos(categoria=""))
        self.assertEqual(Producto.objects.count(), 0)
        self.assertContains(respuesta, "Elige una categoría")

    def test_sin_descripcion_no_se_da_de_alta(self):
        respuesta = self.client.post(reverse("inventario:producto_alta"), self.datos(descripcion=""))
        self.assertEqual(Producto.objects.count(), 0)
        self.assertContains(respuesta, "Escribe una descripción breve")

    def test_con_todos_los_datos_si_se_da_de_alta(self):
        self.client.post(reverse("inventario:producto_alta"), self.datos())
        self.assertEqual(Producto.objects.get().categoria, self.categoria)

    def test_el_formulario_propone_un_minimo_de_5(self):
        from .forms import ProductoForm
        self.assertEqual(ProductoForm(negocio=self.negocio).fields["cantidad_minima"].initial, Decimal("5"))

    def test_las_existencias_nunca_quedan_en_negativo(self):
        from django.db import IntegrityError, transaction
        producto = crear_producto(self.negocio)
        producto.cantidad_actual = Decimal("-1")
        with self.assertRaises(IntegrityError), transaction.atomic():
            producto.save()


class CostoPorLotesTests(TestCase):
    """Cada compra tiene su costo: lo que se vende sale primero de la compra más vieja (PEPS)."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        # la coca se compró ayer a 15 y hoy a 17
        self.producto = crear_producto(self.negocio, nombre="Coca 600", costo="15", cantidad="10")
        registrar_alta(self.producto)
        agregar_existencias(self.producto, 10, costo="17")
        self.producto.refresh_from_db()

    def vender(self, cantidad):
        venta = carrito.venta_en_curso(self.negocio, 1, self.usuario)
        carrito.agregar_producto(venta, self.producto, cantidad)
        cobrar_venta(venta)
        self.producto.refresh_from_db()
        return venta.items.get()

    def test_cada_compra_abre_su_lote(self):
        lotes = list(self.producto.lotes.order_by("id").values_list("cantidad_restante", "costo_unitario"))
        self.assertEqual(lotes, [(Decimal("10"), Decimal("15")), (Decimal("10"), Decimal("17"))])

    def test_el_producto_se_queda_con_el_ultimo_costo_de_compra(self):
        self.assertEqual(self.producto.costo, Decimal("17"))

    def test_lo_que_se_vende_sale_con_el_costo_de_la_compra_mas_vieja(self):
        item = self.vender(4)
        self.assertEqual(item.costo_unitario, Decimal("15"))
        self.assertEqual(self.producto.lotes.get(costo_unitario=15).cantidad_restante, Decimal("6"))

    def test_una_venta_que_cruza_dos_lotes_usa_el_costo_promedio_de_lo_que_salio(self):
        item = self.vender(12)  # 10 a $15 y 2 a $17
        self.assertEqual(item.costo_unitario, Decimal("15.3333"))
        self.assertEqual(self.producto.lotes.get(costo_unitario=17).cantidad_restante, Decimal("8"))
        self.assertEqual(self.producto.lotes.get(costo_unitario=15).cantidad_restante, Decimal("0"))

    def test_las_ventas_de_antes_no_cambian_si_despues_sube_el_costo(self):
        primera = self.vender(3)
        agregar_existencias(self.producto, 5, costo="20")
        self.assertEqual(primera.costo_unitario, Decimal("15"))
        primera.refresh_from_db()
        self.assertEqual(primera.costo_unitario, Decimal("15"))

    def test_el_kardex_guarda_el_costo_de_cada_movimiento(self):
        self.vender(12)
        entrada, venta = MovimientoInventario.objects.filter(producto=self.producto).order_by("id")[1], MovimientoInventario.objects.filter(tipo="VENTA").get()
        self.assertEqual(entrada.costo_unitario, Decimal("17"))
        self.assertEqual(venta.costo_unitario, Decimal("15.3333"))

    def test_una_merma_se_valua_con_el_costo_de_la_compra_vieja(self):
        self.producto.cantidad_actual = Decimal("19")
        self.producto.save()
        movimiento = registrar_movimiento(self.producto, Decimal("-1"), "MERMA", motivo="Se rompió")
        self.assertEqual(movimiento.costo_unitario, Decimal("15"))

    def test_un_producto_sin_lotes_se_vende_a_su_costo(self):
        otro = crear_producto(self.negocio, nombre="Pepsi", costo="14", cantidad="5")
        venta = carrito.venta_en_curso(self.negocio, 1, self.usuario)
        carrito.agregar_producto(venta, otro, 2)
        cobrar_venta(venta)
        self.assertEqual(venta.items.get().costo_unitario, Decimal("14"))

    def test_el_gasto_de_cada_compra_respeta_su_costo(self):
        montos = list(GastoOperativo.objects.filter(tipo="MERCANCIA").order_by("id").values_list("monto", flat=True))
        self.assertEqual(montos, [Decimal("150.00"), Decimal("170.00")])


class PrecioDeVentaNoMenorAlCostoTests(TestCase):
    """Regla de negocio: nunca se vende por debajo de lo que costó."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.categoria = Categoria.objects.get_or_create(nombre="Bebidas")[0]

    def datos(self, **cambios):
        datos = {
            "nombre": "Pepsi", "descripcion": "Refresco de cola", "costo": "13", "precio_venta": "18",
            "cantidad_actual": "10", "cantidad_minima": "5", "categoria": self.categoria.pk, "motivo": "Cambio",
        }
        datos.update(cambios)
        return datos

    def test_el_alta_con_precio_menor_al_costo_se_rechaza(self):
        respuesta = self.client.post(reverse("inventario:producto_alta"), self.datos(costo="20", precio_venta="15"))
        self.assertEqual(Producto.objects.count(), 0)
        self.assertContains(respuesta, "no puede ser menor a lo que te cuesta")

    def test_vender_al_mismo_precio_que_costo_si_se_permite(self):
        self.client.post(reverse("inventario:producto_alta"), self.datos(costo="15", precio_venta="15"))
        self.assertEqual(Producto.objects.count(), 1)

    def test_editar_el_precio_por_debajo_del_costo_se_rechaza(self):
        producto = crear_producto(self.negocio, costo="15", precio="25")
        self.client.post(reverse("inventario:producto_editar", args=[producto.pk]), self.datos(costo="15", precio_venta="10"))
        producto.refresh_from_db()
        self.assertEqual(producto.precio_venta, Decimal("25"))

    def resurtir(self, producto, **datos):
        return self.client.post(
            reverse("inventario:producto_resurtir", args=[producto.pk]), data=json.dumps(datos), content_type="application/json",
        )

    def test_resurtir_con_un_costo_mayor_al_precio_de_venta_se_rechaza(self):
        producto = crear_producto(self.negocio, costo="15", precio="25", cantidad="10")
        respuesta = self.resurtir(producto, cantidad=5, costo=30)
        self.assertEqual(respuesta.status_code, 400)
        producto.refresh_from_db()
        self.assertEqual((producto.cantidad_actual, producto.costo), (Decimal("10"), Decimal("15")))

    def test_resurtir_con_costo_mayor_y_un_precio_nuevo_si_se_acepta(self):
        producto = crear_producto(self.negocio, costo="15", precio="25", cantidad="10")
        respuesta = self.resurtir(producto, cantidad=5, costo=30, precio_venta=40)
        self.assertEqual(respuesta.status_code, 200)
        producto.refresh_from_db()
        self.assertEqual((producto.costo, producto.precio_venta), (Decimal("30.00"), Decimal("40.00")))

    def test_resurtir_sin_cambiar_el_precio_deja_el_que_tenia(self):
        producto = crear_producto(self.negocio, costo="15", precio="25", cantidad="10")
        self.resurtir(producto, cantidad=5, costo=17)
        producto.refresh_from_db()
        self.assertEqual(producto.precio_venta, Decimal("25"))

    def test_una_fila_del_csv_con_precio_menor_al_costo_se_marca(self):
        from . import importacion
        filas, errores = importacion.leer_csv(b"producto,cantidad,precio_compra,precio_venta\nCoca,5,20,15\n")
        self.assertEqual(filas, [])
        self.assertIn("menor al de compra", errores[0])


class StockIdealPorPromedioTests(TestCase):
    """El stock ideal es el promedio de lo que se tuvo cada vez que se cargó mercancía."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.producto = crear_producto(self.negocio, cantidad="24", minimo="5", ideal="0")
        registrar_alta(self.producto)
        self.producto.refresh_from_db()

    def test_con_la_primera_carga_el_ideal_es_lo_que_hay(self):
        self.assertEqual(self.producto.stock_ideal, Decimal("24"))

    def test_cada_resurtido_recalcula_el_promedio(self):
        # después de resurtir quedaron 26 y luego 29: (24 + 26 + 29) / 3 = 26.3
        agregar_existencias(self.producto, 26 - 24, costo="15")
        agregar_existencias(self.producto, 29 - 26, costo="15")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_ideal, Decimal("26"))

    def test_las_ventas_y_las_mermas_no_mueven_el_ideal(self):
        registrar_movimiento(self.producto, Decimal("-4"), "MERMA")
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_ideal, Decimal("24"))

    def test_si_se_escribio_un_ideal_al_dar_de_alta_se_respeta_hasta_el_siguiente_resurtido(self):
        otro = crear_producto(self.negocio, nombre="Pepsi", cantidad="10", minimo="5", ideal="40")
        registrar_alta(otro)
        otro.refresh_from_db()
        self.assertEqual(otro.stock_ideal, Decimal("40"))
        agregar_existencias(otro, 20, costo="15")  # quedan 30
        otro.refresh_from_db()
        self.assertEqual(otro.stock_ideal, Decimal("20"))  # (10 + 30) / 2

    def test_un_producto_a_granel_guarda_el_promedio_con_decimales(self):
        granel = crear_producto(self.negocio, nombre="Frijol", cantidad="10", minimo="2", ideal="0")
        granel.a_granel = True
        granel.save()
        registrar_alta(granel)
        agregar_existencias(granel, Decimal("5.5"), costo="20")  # quedan 15.5
        granel.refresh_from_db()
        self.assertEqual(granel.stock_ideal, Decimal("12.750"))

    def test_los_productos_precargados_empiezan_con_su_ideal(self):
        from .movimientos import registrar_entradas_iniciales
        pepsi = crear_producto(self.negocio, nombre="Pepsi", cantidad="12", minimo="5", ideal="0")
        registrar_entradas_iniciales([pepsi], "Inventario inicial")
        pepsi.refresh_from_db()
        self.assertEqual(pepsi.stock_ideal, Decimal("12"))


class IconoDelProductoTests(SimpleTestCase):
    def test_el_icono_sale_de_una_palabra_del_nombre(self):
        from .datos_base import icono_para
        self.assertEqual(icono_para("Coca-Cola 600ml"), "🥤")
        self.assertEqual(icono_para("Leche Lala 1L"), "🥛")
        self.assertEqual(icono_para("Atún Dolores 140g"), "🐟")
        self.assertEqual(icono_para("Pañales Huggies"), "🍼")

    def test_una_frase_gana_sobre_una_palabra_suelta(self):
        from .datos_base import icono_para
        self.assertEqual(icono_para("Pasta dental Colgate 75ml"), "🪥")
        self.assertEqual(icono_para("Papel higiénico Regio"), "🧻")

    def test_una_palabra_corta_no_se_confunde_con_el_final_de_otra(self):
        from .datos_base import icono_para
        self.assertNotEqual(icono_para("Desodorante Colgate"), "🍵")

    def test_si_no_hay_palabra_se_usa_el_icono_de_la_categoria_y_si_no_la_caja(self):
        from .datos_base import icono_para
        categoria = Categoria(nombre="Mascotas", icono="🐾")
        self.assertEqual(icono_para("Producto raro", categoria), "🐾")
        self.assertEqual(icono_para("Producto raro"), "📦")


class DatosBaseTests(TestCase):
    """Categorías, catálogo, proveedores y categorías de gastos con los que arranca el sistema."""

    def test_el_catalogo_trae_categorias_y_muchos_productos(self):
        from .datos_base import cargar_catalogo
        from .models import ProductoCatalogo
        categorias, nuevos = cargar_catalogo()
        self.assertGreaterEqual(categorias, 15)
        self.assertGreaterEqual(nuevos, 150)
        self.assertEqual(ProductoCatalogo.objects.filter(precio_sugerido__lte=0).count(), 0)

    def test_cargar_el_catalogo_dos_veces_no_duplica_nada(self):
        from .datos_base import cargar_catalogo
        from .models import ProductoCatalogo
        cargar_catalogo()
        total = ProductoCatalogo.objects.count()
        cargar_catalogo()
        self.assertEqual(ProductoCatalogo.objects.count(), total)

    def test_ningun_producto_del_catalogo_se_repite_ni_queda_sin_categoria_valida(self):
        from .datos_base import CATEGORIAS, PRODUCTOS
        nombres = [p[0].lower() for p in PRODUCTOS]
        self.assertEqual(len(nombres), len(set(nombres)))
        validas = {c[0] for c in CATEGORIAS}
        self.assertTrue(all(p[1] in validas for p in PRODUCTOS))

    def test_los_proveedores_base_surten_categorias_que_existen(self):
        from .datos_base import CATEGORIAS, PROVEEDORES
        validas = {c[0] for c in CATEGORIAS}
        self.assertTrue(all(c in validas for _, surte in PROVEEDORES for c in surte))

    def test_preparar_una_tienda_crea_proveedores_y_categorias_de_gastos_una_sola_vez(self):
        from finanzas.models import CategoriaGasto
        from .datos_base import preparar_negocio
        from .models import Proveedor
        _, negocio = crear_negocio()
        nuevos = preparar_negocio(negocio)
        self.assertGreaterEqual(nuevos[0], 20)
        self.assertEqual(preparar_negocio(negocio), (0, 0))
        coca = Proveedor.objects.get(negocio=negocio, nombre="Coca-Cola FEMSA")
        self.assertEqual([c.nombre for c in coca.categorias.all()], ["Bebidas"])
        self.assertEqual(CategoriaGasto.objects.get(negocio=negocio, nombre="Renta del local").tipo, "FIJO")

    def test_una_tienda_no_ve_los_proveedores_de_otra(self):
        from .datos_base import preparar_negocio
        from .models import Proveedor
        _, uno = crear_negocio()
        _, dos = crear_negocio(telefono="5522223333", email="otro@ejemplo.com", nombre_tienda="Otra")
        preparar_negocio(uno)
        self.assertEqual(Proveedor.objects.filter(negocio=dos).count(), 0)

    def test_el_alta_sin_icono_le_pone_uno_segun_el_nombre(self):
        usuario, negocio = crear_negocio()
        self.client.force_login(usuario)
        bebidas = Categoria.objects.get_or_create(nombre="Bebidas")[0]
        self.client.post(reverse("inventario:producto_alta"), {
            "nombre": "Sprite 600", "descripcion": "Refresco", "costo": "12", "precio_venta": "19",
            "cantidad_actual": "10", "cantidad_minima": "5", "categoria": bebidas.pk, "icono": "",
        })
        self.assertEqual(Producto.objects.get().icono, "🥤")

    def test_el_alta_respeta_el_icono_elegido(self):
        usuario, negocio = crear_negocio()
        self.client.force_login(usuario)
        bebidas = Categoria.objects.get_or_create(nombre="Bebidas")[0]
        self.client.post(reverse("inventario:producto_alta"), {
            "nombre": "Sprite 600", "descripcion": "Refresco", "costo": "12", "precio_venta": "19",
            "cantidad_actual": "10", "cantidad_minima": "5", "categoria": bebidas.pk, "icono": "🍋",
        })
        self.assertEqual(Producto.objects.get().icono, "🍋")

    def test_el_comando_seed_catalogo_tambien_prepara_las_tiendas_existentes(self):
        from io import StringIO
        from django.core.management import call_command
        from .models import Proveedor
        _, negocio = crear_negocio()
        call_command("seed_catalogo", "--negocios", stdout=StringIO())
        self.assertGreaterEqual(Proveedor.objects.filter(negocio=negocio).count(), 20)


class ListasColapsablesTests(TestCase):
    """Las listas largas (categorías, proveedores, íconos) se muestran recogidas con "Mostrar más"."""

    def setUp(self):
        from .datos_base import preparar_negocio
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        preparar_negocio(self.negocio)

    def test_el_panel_marca_sus_listas_largas_como_colapsables(self):
        respuesta = self.client.get(reverse("inventario:panel"))
        # categoría, proveedor e ícono en el alta y en la edición, y las categorías de los dos formularios de proveedor
        self.assertGreaterEqual(respuesta.content.decode().count("data-colapsable"), 9)

    def test_el_proveedor_del_producto_se_elige_en_una_lista_con_la_opcion_sin_proveedor(self):
        respuesta = self.client.get(reverse("inventario:panel"))
        self.assertContains(respuesta, 'type="radio" name="proveedor"')
        self.assertContains(respuesta, "Sin proveedor")

    def test_se_puede_dar_de_alta_con_proveedor_y_sin_proveedor(self):
        from .models import Proveedor
        categoria = Categoria.objects.get_or_create(nombre="Bebidas")[0]
        proveedor = Proveedor.objects.get(negocio=self.negocio, nombre="Coca-Cola FEMSA")
        base = {
            "descripcion": "Refresco", "costo": "12", "precio_venta": "19", "cantidad_actual": "10",
            "cantidad_minima": "5", "categoria": categoria.pk,
        }
        self.client.post(reverse("inventario:producto_alta"), {**base, "nombre": "Sprite", "proveedor": proveedor.pk})
        self.client.post(reverse("inventario:producto_alta"), {**base, "nombre": "Fanta", "proveedor": ""})
        self.assertEqual(Producto.objects.get(nombre="Sprite").proveedor, proveedor)
        self.assertIsNone(Producto.objects.get(nombre="Fanta").proveedor)

    def test_cada_proveedor_muestra_solo_tres_categorias_y_cuantas_mas(self):
        respuesta = self.client.get(reverse("inventario:panel"))
        # Mayorista de abarrotes surte 4 categorías, así que se muestran 3 y "+1 más"
        self.assertContains(respuesta, "+1 más")

    def test_la_pagina_carga_el_script_de_las_listas_colapsables(self):
        respuesta = self.client.get(reverse("inventario:panel"))
        self.assertContains(respuesta, "colapsables.js")
        self.assertContains(respuesta, "colapsables.css")
