from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from core.testing import crear_negocio, crear_producto
from inventario.models import Categoria, HistorialModificacionProducto, Producto
from ventas.models import ItemVenta, Venta

from . import calculos
from .models import GastoOperativo


class FormulasFinancierasTests(SimpleTestCase):
    def test_punto_equilibrio_ejemplo_de_tres_categorias(self):
        # F = 30,000; w = 0.50 / 0.20 / 0.30; p = 25 / 18 / 12; cv = 15 / 12 / 8
        categorias = [
            {"nombre": "Bebidas", "ventas": Decimal("45000"), "costo": Decimal("27000"), "unidades": Decimal("1800")},
            {"nombre": "Lácteos", "ventas": Decimal("18000"), "costo": Decimal("12000"), "unidades": Decimal("1000")},
            {"nombre": "Abarrotes", "ventas": Decimal("27000"), "costo": Decimal("18000"), "unidades": Decimal("2250")},
        ]
        resultado = calculos.calcular_punto_equilibrio(Decimal("30000"), categorias)

        self.assertEqual(calculos.redondear(resultado["pe_total"]), Decimal("81818.18"))
        bebidas = resultado["filas"][0]
        self.assertEqual(bebidas["ventas_objetivo"], Decimal("40909.09"))
        self.assertEqual(bebidas["unidades_objetivo"], 1637)

    def test_sin_margen_no_hay_punto_de_equilibrio(self):
        categorias = [
            {"nombre": "Bebidas", "ventas": Decimal("100"), "costo": Decimal("120"), "unidades": Decimal("10")},
        ]
        resultado = calculos.calcular_punto_equilibrio(Decimal("500"), categorias)
        self.assertIsNone(resultado["pe_total"])

    def test_tasas_isr_resico(self):
        self.assertEqual(calculos.tasa_isr_resico(Decimal("300000")), Decimal("1.00"))
        self.assertEqual(calculos.tasa_isr_resico(Decimal("300001")), Decimal("1.10"))
        self.assertEqual(calculos.tasa_isr_resico(Decimal("600001")), Decimal("1.50"))
        self.assertEqual(calculos.tasa_isr_resico(Decimal("1000001")), Decimal("2.00"))
        self.assertEqual(calculos.tasa_isr_resico(Decimal("3500000")), Decimal("2.50"))

    def test_precio_sugerido(self):
        self.assertEqual(calculos.precio_sugerido(Decimal("15"), Decimal("40")), Decimal("25.00"))
        self.assertEqual(calculos.precio_sugerido(Decimal("18"), Decimal("30")), Decimal("25.71"))

    def test_resumen_flujo_margen_operativo_y_utilidad_neta(self):
        r = calculos.resumen_desde_sumas(
            Decimal("100000"), Decimal("60000"), Decimal("20000"), Decimal("1.00"),
        )
        self.assertEqual(r["flujo_efectivo"], Decimal("80000"))
        self.assertEqual(r["margen_operativo"], Decimal("20.0"))
        self.assertEqual(r["isr"], Decimal("1000.00"))
        self.assertEqual(r["utilidad_neta"], Decimal("19000.00"))


class FinanzasConDatosRealesTests(TestCase):
    """Usan la base de datos de pruebas: ventas, gastos y productos de verdad."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)

    def vender(self, producto, cantidad, folio=1):
        venta = Venta.objects.create(negocio=self.negocio, folio=folio, estado=Venta.Estado.COBRADA)
        ItemVenta.objects.create(
            venta=venta, producto=producto, cantidad=Decimal(cantidad), precio_unitario=producto.precio_venta,
        )
        venta.recalcular_total()
        return venta

    def gastar(self, monto, tipo=GastoOperativo.Tipo.FIJO):
        return GastoOperativo.objects.create(
            negocio=self.negocio, tipo=tipo, concepto="Renta", monto=Decimal(monto),
        )

    def test_todas_las_pantallas_abren_sin_datos(self):
        nombres = (
            "finanzas:inicio", "finanzas:registrar_gastos", "finanzas:historial_gastos",
            "finanzas:punto_equilibrio", "finanzas:sugerir_precios", "finanzas:pronostico_ventas",
            "finanzas:reportes_financieros",
        )
        for nombre in nombres:
            with self.subTest(pantalla=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)

    def test_todas_las_pantallas_abren_con_datos(self):
        categoria = Categoria.objects.create(nombre="Bebidas")
        producto = crear_producto(self.negocio, nombre="Refresco")
        producto.categoria = categoria
        producto.save()
        self.vender(producto, "10")
        self.gastar("400")

        for nombre in ("finanzas:inicio", "finanzas:punto_equilibrio", "finanzas:sugerir_precios", "finanzas:reportes_financieros"):
            with self.subTest(pantalla=nombre):
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200)

    def test_pronostico_compara_tres_modelos_para_los_diez_mas_vendidos(self):
        productos = [
            crear_producto(self.negocio, nombre=f"Producto {indice:02d}")
            for indice in range(11)
        ]
        inicio = timezone.datetime(2025, 1, 6).date()
        for semana in range(12):
            venta = Venta.objects.create(
                negocio=self.negocio, folio=semana + 1, estado=Venta.Estado.COBRADA,
            )
            venta.creado_en = timezone.make_aware(datetime.combine(
                inicio + timedelta(weeks=semana), time(12),
            ))
            venta.save(update_fields=["creado_en"])
            ItemVenta.objects.bulk_create([
                ItemVenta(
                    venta=venta,
                    producto=producto,
                    cantidad=Decimal(20 - indice + semana % 3),
                    precio_unitario=producto.precio_venta,
                )
                for indice, producto in enumerate(productos)
            ])

        resultado = calculos.pronostico_ventas_negocio(self.negocio, semanas_historial=12)

        self.assertEqual(resultado["estado"], "ok")
        self.assertEqual(len(resultado["productos"]), 10)
        self.assertEqual(resultado["productos"][0]["nombre"], "Producto 00")
        self.assertNotIn("Producto 10", [producto["nombre"] for producto in resultado["productos"]])
        for producto in resultado["productos"]:
            self.assertEqual(set(producto["modelos"]), {"arima", "lineal", "holt_winters"})
            self.assertTrue(all(modelo["disponible"] for modelo in producto["modelos"].values()))
            self.assertTrue(all(modelo["mae"] is not None for modelo in producto["modelos"].values()))
        self.assertEqual(resultado["semana_pronostico"], inicio + timedelta(weeks=12))

    def test_pronostico_sin_ventas_indica_que_no_hay_datos(self):
        resultado = calculos.pronostico_ventas_negocio(self.negocio)
        self.assertEqual(resultado["estado"], "sin_ventas")
        self.assertEqual(resultado["productos"], [])

        respuesta = self.client.get(reverse("finanzas:pronostico_ventas"), {"generar": "1"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["pronostico"]["estado"], "sin_ventas")
        self.assertContains(respuesta, "Aún no hay ventas cobradas")

    def test_punto_de_equilibrio_con_ventas_y_gastos_reales(self):
        categoria = Categoria.objects.create(nombre="Bebidas")
        producto = crear_producto(self.negocio, nombre="Refresco")  # costo 15, precio 25
        producto.categoria = categoria
        producto.save()
        self.vender(producto, "10")  # ventas 250, costo 150, margen de contribucion 40 %
        self.gastar("400")

        datos = calculos.punto_equilibrio_negocio(self.negocio, timezone.localdate())

        self.assertEqual(datos["estado"], "ok")
        self.assertEqual(calculos.redondear(datos["pe_total"]), Decimal("1000.00"))

    def test_sin_gastos_fijos_explica_que_falta(self):
        producto = crear_producto(self.negocio)
        self.vender(producto, "10")
        datos = calculos.punto_equilibrio_negocio(self.negocio, timezone.localdate())
        self.assertEqual(datos["estado"], "sin_fijos")

    def test_sin_ventas_explica_que_falta(self):
        self.gastar("400")
        datos = calculos.punto_equilibrio_negocio(self.negocio, timezone.localdate())
        self.assertEqual(datos["estado"], "sin_ventas")

    def test_resumen_financiero_del_mes(self):
        producto = crear_producto(self.negocio)
        self.vender(producto, "10")  # ingresos 250, costo de ventas 150
        self.gastar("400")
        hoy = timezone.localdate()

        resumen = calculos.resumen_financiero(
            self.negocio, calculos.primer_dia_del_mes(hoy), hoy + timedelta(days=1), Decimal("1.00"),
        )

        self.assertEqual(resumen["ingresos"], Decimal("250.00"))
        self.assertEqual(resumen["costo_ventas"], Decimal("150.00"))
        self.assertEqual(resumen["gastos"], Decimal("400.00"))
        self.assertEqual(resumen["flujo_efectivo"], Decimal("-150.00"))
        self.assertEqual(resumen["isr"], Decimal("2.50"))
        self.assertEqual(resumen["utilidad_neta"], Decimal("-302.50"))

    def test_la_tasa_de_isr_depende_del_regimen(self):
        producto = crear_producto(self.negocio)
        self.vender(producto, "10")
        hoy = timezone.localdate()
        self.assertEqual(calculos.tasa_isr_del_negocio(self.negocio, hoy), Decimal("1.00"))

        self.negocio.regimen_resico = False
        self.negocio.save()
        self.assertEqual(calculos.tasa_isr_del_negocio(self.negocio, hoy), Decimal("0"))

    def test_precio_sugerido_en_pantalla(self):
        crear_producto(self.negocio, nombre="Refresco")  # costo 15
        respuesta = self.client.get(reverse("finanzas:sugerir_precios"), {"margen": "30"})
        fila = respuesta.context["pagina"].object_list[0]
        self.assertEqual(fila["sugerido"], Decimal("21.43"))

    def test_aceptar_un_precio_sugerido_cambia_el_precio_y_guarda_el_historial(self):
        producto = crear_producto(self.negocio)
        self.client.post(
            reverse("finanzas:aceptar_precio_sugerido", args=[producto.pk]),
            {"precio": "26.50", "margen": "30", "page": "1"},
        )

        producto.refresh_from_db()
        self.assertEqual(producto.precio_venta, Decimal("26.50"))
        self.assertEqual(HistorialModificacionProducto.objects.count(), 1)

    def test_un_precio_invalido_no_cambia_nada(self):
        producto = crear_producto(self.negocio)
        self.client.post(
            reverse("finanzas:aceptar_precio_sugerido", args=[producto.pk]),
            {"precio": "abc", "margen": "30", "page": "1"},
        )

        producto.refresh_from_db()
        self.assertEqual(producto.precio_venta, Decimal("25.00"))
        self.assertEqual(HistorialModificacionProducto.objects.count(), 0)

    def test_registrar_un_gasto_con_categoria_nueva(self):
        self.client.post(reverse("finanzas:categoria_gasto_alta"), {"nombre": "Luz"})
        self.assertEqual(self.negocio.categorias_gasto.count(), 1)

        categoria = self.negocio.categorias_gasto.get()
        self.client.post(reverse("finanzas:registrar_gastos"), {
            "tipo": "FIJO", "categoria": categoria.pk, "concepto": "Recibo de luz", "monto": "450", "nota": "",
        })
        gasto = GastoOperativo.objects.get()
        self.assertEqual(gasto.categoria, categoria)
        self.assertEqual(gasto.monto, Decimal("450.00"))


class UtilidadConfiableTests(TestCase):
    """La mercancía que se compra no debe contarse dos veces en la utilidad."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()
        self.manana = self.hoy + timedelta(days=1)
        self.inicio_mes = calculos.primer_dia_del_mes(self.hoy)

    def vender(self, producto, cantidad, folio=1):
        venta = Venta.objects.create(negocio=self.negocio, folio=folio, estado=Venta.Estado.COBRADA)
        ItemVenta.objects.create(venta=venta, producto=producto, cantidad=Decimal(cantidad), precio_unitario=producto.precio_venta)
        venta.recalcular_total()

    def resumen(self):
        return calculos.resumen_financiero(self.negocio, self.inicio_mes, self.manana, Decimal("1"))

    def test_la_compra_de_mercancia_no_cambia_la_utilidad_pero_si_el_flujo_de_efectivo(self):
        producto = crear_producto(self.negocio, costo="15", precio="25", cantidad="100")
        self.vender(producto, "10")  # ingresos 250, costo de ventas 150
        sin_compra = self.resumen()

        GastoOperativo.objects.create(
            negocio=self.negocio, tipo=GastoOperativo.Tipo.MERCANCIA, concepto="Compra", monto=Decimal("1500"),
        )
        con_compra = self.resumen()

        self.assertEqual(con_compra["utilidad_neta"], sin_compra["utilidad_neta"])
        self.assertEqual(con_compra["margen_operativo"], sin_compra["margen_operativo"])
        self.assertEqual(con_compra["gastos"], Decimal("0.00"))
        self.assertEqual(con_compra["compras"], Decimal("1500.00"))
        self.assertEqual(con_compra["flujo_efectivo"], Decimal("250.00") - Decimal("1500.00"))

    def test_los_gastos_fijos_y_variables_si_restan_utilidad(self):
        producto = crear_producto(self.negocio, costo="15", precio="25", cantidad="100")
        self.vender(producto, "10")
        antes = self.resumen()["utilidad_neta"]
        GastoOperativo.objects.create(negocio=self.negocio, tipo=GastoOperativo.Tipo.FIJO, concepto="Renta", monto=Decimal("50"))
        self.assertEqual(self.resumen()["utilidad_neta"], antes - Decimal("50"))

    def test_el_costo_de_ventas_usa_el_costo_de_cuando_se_vendio(self):
        producto = crear_producto(self.negocio, costo="15", precio="25", cantidad="100")
        self.vender(producto, "10")
        antes = self.resumen()["costo_ventas"]

        producto.costo = Decimal("40")
        producto.save()

        self.assertEqual(self.resumen()["costo_ventas"], antes)
        self.assertEqual(antes, Decimal("150.00"))

    def test_el_punto_de_equilibrio_no_cuenta_la_mercancia_como_gasto_fijo(self):
        GastoOperativo.objects.create(
            negocio=self.negocio, tipo=GastoOperativo.Tipo.MERCANCIA, concepto="Compra", monto=Decimal("9999"),
        )
        datos = calculos.punto_equilibrio_negocio(self.negocio, self.hoy)
        self.assertEqual(datos["estado"], "sin_fijos")

    def test_las_ventas_sin_precio_de_compra_se_cuentan(self):
        sin_costo = crear_producto(self.negocio, nombre="Sin costo", costo="0", precio="20", cantidad="5")
        con_costo = crear_producto(self.negocio, nombre="Con costo", costo="8", precio="20", cantidad="5")
        self.vender(sin_costo, "2", folio=1)
        self.vender(con_costo, "2", folio=2)
        self.assertEqual(calculos.renglones_sin_costo(self.negocio, self.inicio_mes, self.manana), 1)

    def test_el_reporte_por_meses_da_lo_mismo_que_calcular_mes_por_mes(self):
        producto = crear_producto(self.negocio, costo="15", precio="25", cantidad="100")
        self.vender(producto, "4")
        GastoOperativo.objects.create(negocio=self.negocio, tipo=GastoOperativo.Tipo.FIJO, concepto="Luz", monto=Decimal("30"))
        GastoOperativo.objects.create(
            negocio=self.negocio, tipo=GastoOperativo.Tipo.MERCANCIA, concepto="Compra", monto=Decimal("200"),
        )

        mes_anterior = calculos.mes_anterior(self.inicio_mes)
        por_meses = calculos.resumen_por_meses(self.negocio, [mes_anterior, self.inicio_mes], Decimal("1"))
        self.assertEqual(por_meses[0]["ingresos"], Decimal("0.00"))
        self.assertEqual(por_meses[1], self.resumen())

    def test_el_reporte_usa_pocas_consultas(self):
        producto = crear_producto(self.negocio, costo="15", precio="25", cantidad="100")
        self.vender(producto, "4")
        self.client.get(reverse("finanzas:reportes_financieros"))  # calienta
        with CaptureQueriesContext(connection) as consultas:
            self.client.get(reverse("finanzas:reportes_financieros"))
        self.assertLess(len(consultas), 16)

    def test_el_aviso_de_utilidad_inflada_aparece(self):
        sin_costo = crear_producto(self.negocio, costo="0", precio="20", cantidad="5")
        self.vender(sin_costo, "2")
        respuesta = self.client.get(reverse("finanzas:reportes_financieros"))
        self.assertContains(respuesta, "no tienen precio de compra")

    def test_no_se_puede_registrar_a_mano_una_compra_de_mercancia(self):
        respuesta = self.client.post(reverse("finanzas:registrar_gastos"), {
            "tipo": "MERCANCIA", "concepto": "Compra", "monto": "500", "nota": "",
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(GastoOperativo.objects.count(), 0)

    def test_la_pantalla_de_gastos_ya_no_dice_que_el_inventario_es_un_gasto(self):
        respuesta = self.client.get(reverse("finanzas:registrar_gastos"))
        self.assertNotContains(respuesta, "(inventario, merma, bolsas)")
        self.assertContains(respuesta, "No registres aquí la mercancía")

    def test_el_historial_de_gastos_muestra_las_compras_de_mercancia(self):
        GastoOperativo.objects.create(
            negocio=self.negocio, tipo=GastoOperativo.Tipo.MERCANCIA, concepto="Compra de mercancía: Coca", monto=Decimal("90"),
        )
        self.assertContains(self.client.get(reverse("finanzas:historial_gastos")), "Mercancía")


class ProductosNoEncontradosEnGastosTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.pendiente = Producto.objects.create(
            negocio=self.negocio, nombre="Bolsa de hielo", costo=0, precio_venta=20, activo=False, pendiente_validacion=True,
        )
        venta = Venta.objects.create(negocio=self.negocio, folio=1, estado=Venta.Estado.COBRADA)
        self.item = ItemVenta.objects.create(venta=venta, producto=self.pendiente, cantidad=Decimal("3"), precio_unitario=Decimal("20"))

    def test_aparece_en_la_pantalla_de_gastos_con_lo_que_se_vendio(self):
        respuesta = self.client.get(reverse("finanzas:registrar_gastos"))
        self.assertContains(respuesta, "Productos no encontrados")
        self.assertContains(respuesta, "Bolsa de hielo")

    def test_ponerle_precio_de_compra_completa_el_costo_y_registra_la_compra(self):
        self.client.post(reverse("finanzas:completar_no_encontrado", args=[self.pendiente.pk]), {"precio_compra": "8"})

        self.item.refresh_from_db()
        self.pendiente.refresh_from_db()
        self.assertEqual(self.item.costo_unitario, Decimal("8.00"))
        self.assertEqual(self.pendiente.costo, Decimal("8.00"))
        compra = GastoOperativo.objects.get()
        self.assertEqual(compra.tipo, GastoOperativo.Tipo.MERCANCIA)
        self.assertEqual(compra.monto, Decimal("24.00"))  # 3 vendidas x $8

    def test_ya_con_precio_no_vuelve_a_aparecer_ni_se_puede_registrar_dos_veces(self):
        url = reverse("finanzas:completar_no_encontrado", args=[self.pendiente.pk])
        self.client.post(url, {"precio_compra": "8"})
        self.assertEqual(self.client.post(url, {"precio_compra": "9"}).status_code, 404)
        self.assertEqual(GastoOperativo.objects.count(), 1)
        self.assertNotContains(self.client.get(reverse("finanzas:registrar_gastos")), "Productos no encontrados")

    def test_un_precio_malo_no_cambia_nada(self):
        self.client.post(reverse("finanzas:completar_no_encontrado", args=[self.pendiente.pk]), {"precio_compra": "-5"})
        self.pendiente.refresh_from_db()
        self.assertEqual(self.pendiente.costo, Decimal("0"))
        self.assertEqual(GastoOperativo.objects.count(), 0)

    def test_no_se_puede_tocar_un_producto_de_otra_tienda(self):
        otro_usuario, _ = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra")
        self.client.force_login(otro_usuario)
        respuesta = self.client.post(reverse("finanzas:completar_no_encontrado", args=[self.pendiente.pk]), {"precio_compra": "8"})
        self.assertEqual(respuesta.status_code, 404)


class BajaRotacionPorLotesTests(TestCase):
    def test_los_productos_sin_ventas_se_piden_por_lotes_de_diez(self):
        usuario, negocio = crear_negocio()
        self.client.force_login(usuario)
        for numero in range(25):
            crear_producto(negocio, nombre=f"Producto {numero:02d}")

        respuesta = self.client.get(reverse("finanzas:baja_rotacion"), {"desde": "2020-01-01", "page": 1}).json()
        self.assertEqual(respuesta["html"].count("baja-rotacion-item"), 10)
        self.assertTrue(respuesta["hay_mas"])
        self.assertEqual(respuesta["total"], 25)

        ultimo = self.client.get(reverse("finanzas:baja_rotacion"), {"desde": "2020-01-01", "page": 3}).json()
        self.assertFalse(ultimo["hay_mas"])
