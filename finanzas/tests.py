from datetime import date, datetime, time, timedelta
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

        respuesta = self.client.get(reverse("finanzas:pronostico_base"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["estado"], "sin_ventas")
        self.assertContains(self.client.get(reverse("finanzas:pronostico_ventas")), "estimación de apoyo")

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
        crear_producto(self.negocio)  # con precio de compra, para que lo único que falte sean las ventas
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


class PeriodoDelGastoTests(TestCase):
    """El gasto lleva el mes al que corresponde (la luz de septiembre que se paga en octubre)."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()
        self.mes_actual = self.hoy.replace(day=1)
        self.mes_pasado = calculos.mes_anterior(self.mes_actual)

    def capturar(self, **datos):
        base = {"tipo": "FIJO", "concepto": "Luz", "monto": "450", "nota": ""}
        base.update(datos)
        return self.client.post(reverse("finanzas:registrar_gastos"), base)

    def test_si_no_se_escoge_mes_el_gasto_es_de_este_mes(self):
        self.capturar()
        self.assertEqual(GastoOperativo.objects.get().periodo, self.mes_actual)

    def test_el_formulario_propone_el_mes_de_hoy(self):
        respuesta = self.client.get(reverse("finanzas:registrar_gastos"))
        self.assertContains(respuesta, 'type="month"')
        self.assertContains(respuesta, f'value="{self.mes_actual.year:04d}-{self.mes_actual.month:02d}"')

    def test_se_puede_capturar_un_gasto_de_un_mes_pasado(self):
        self.capturar(periodo=self.mes_pasado.strftime("%Y-%m"))
        gasto = GastoOperativo.objects.get()
        self.assertEqual(gasto.periodo, self.mes_pasado)
        self.assertEqual(gasto.fecha, self.hoy)  # la fecha de captura sigue siendo hoy

    def test_el_gasto_cuenta_en_el_mes_al_que_corresponde_no_en_el_que_se_capturo(self):
        self.capturar(periodo=self.mes_pasado.strftime("%Y-%m"))
        este_mes = calculos.gastos_periodo(self.negocio, self.mes_actual, calculos.mes_siguiente(self.mes_actual))
        el_otro = calculos.gastos_periodo(self.negocio, self.mes_pasado, self.mes_actual)
        self.assertEqual(este_mes, Decimal("0"))
        self.assertEqual(el_otro, Decimal("450.00"))

    def test_los_reportes_por_mes_usan_el_periodo(self):
        self.capturar(periodo=self.mes_pasado.strftime("%Y-%m"))
        meses = calculos.resumen_por_meses(self.negocio, [self.mes_pasado, self.mes_actual], Decimal("0"))
        self.assertEqual(meses[0]["gastos"], Decimal("450.00"))
        self.assertEqual(meses[1]["gastos"], Decimal("0"))

    def test_no_se_acepta_un_mes_muy_adelantado(self):
        lejano = calculos.mes_siguiente(calculos.mes_siguiente(calculos.mes_siguiente(self.mes_actual)))
        self.capturar(periodo=lejano.strftime("%Y-%m"))
        self.assertEqual(GastoOperativo.objects.count(), 0)

    def test_un_mes_mal_escrito_no_guarda_el_gasto(self):
        self.capturar(periodo="septiembre")
        self.assertEqual(GastoOperativo.objects.count(), 0)

    def test_el_historial_muestra_el_mes_de_cada_gasto(self):
        self.capturar(periodo=self.mes_pasado.strftime("%Y-%m"))
        respuesta = self.client.get(reverse("finanzas:historial_gastos"))
        self.assertContains(respuesta, "Mes")
        self.assertContains(respuesta, self.mes_pasado.strftime("%Y"))

    def test_el_resumen_del_dia_cuenta_lo_que_se_capturo_ese_dia(self):
        self.capturar(periodo=self.mes_pasado.strftime("%Y-%m"))
        capturados_hoy = calculos.gastos_capturados(self.negocio, self.hoy, self.hoy + timedelta(days=1))
        self.assertEqual(capturados_hoy, Decimal("450.00"))  # salió de la caja hoy

    def test_la_compra_de_mercancia_se_queda_en_el_mes_en_que_se_hizo(self):
        compra = GastoOperativo.objects.create(
            negocio=self.negocio, tipo=GastoOperativo.Tipo.MERCANCIA, concepto="Compra", monto=Decimal("100"),
        )
        self.assertEqual(compra.periodo, self.mes_actual)


class PeriodicidadDeGastosTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)

    def gasto_recurrente(self, periodicidad, fecha_inicio, monto="10", intervalo_meses=1):
        return GastoOperativo.objects.create(
            negocio=self.negocio,
            tipo=GastoOperativo.Tipo.FIJO,
            concepto="Servicio",
            monto=Decimal(monto),
            periodicidad=periodicidad,
            intervalo_meses=intervalo_meses,
            fecha_inicio=fecha_inicio,
            periodo=fecha_inicio.replace(day=1),
        )

    def test_cuenta_gastos_diarios_semanales_y_mensuales_en_sus_fechas(self):
        inicio = date(2024, 1, 31)
        self.gasto_recurrente(GastoOperativo.Periodicidad.DIARIA, inicio, "2")
        self.gasto_recurrente(GastoOperativo.Periodicidad.SEMANAL, inicio, "5")
        self.gasto_recurrente(GastoOperativo.Periodicidad.MENSUAL, inicio, "100")

        febrero = calculos.gastos_periodo(self.negocio, date(2024, 2, 1), date(2024, 3, 1))
        marzo = calculos.gastos_periodo(self.negocio, date(2024, 3, 1), date(2024, 4, 1))

        self.assertEqual(febrero, Decimal("178.00"))  # 29 diarios, 4 semanales y 1 mensual
        self.assertEqual(marzo, Decimal("182.00"))  # 31 diarios, 4 semanales y 1 mensual

    def test_gasto_anual_inicia_en_la_fecha_escogida_y_ajusta_anios_no_bisiestos(self):
        self.gasto_recurrente(GastoOperativo.Periodicidad.ANUAL, date(2024, 2, 29), "120")

        antes_del_inicio = calculos.gastos_periodo(
            self.negocio, date(2024, 1, 1), date(2024, 2, 29),
        )
        aniversario = calculos.gastos_periodo(
            self.negocio, date(2025, 2, 1), date(2025, 3, 1),
        )

        self.assertEqual(antes_del_inicio, Decimal("0.00"))
        self.assertEqual(aniversario, Decimal("120.00"))

    def test_periodicidad_personalizada_cuenta_cada_dos_meses_desde_la_fecha_ancla(self):
        self.gasto_recurrente(
            GastoOperativo.Periodicidad.CADA_MESES,
            date(2024, 1, 31),
            "80",
            intervalo_meses=2,
        )

        febrero = calculos.gastos_periodo(self.negocio, date(2024, 2, 1), date(2024, 3, 1))
        marzo = calculos.gastos_periodo(self.negocio, date(2024, 3, 1), date(2024, 4, 1))
        abril_y_mayo = calculos.gastos_periodo(self.negocio, date(2024, 4, 1), date(2024, 6, 1))

        self.assertEqual(febrero, Decimal("0.00"))
        self.assertEqual(marzo, Decimal("80.00"))
        self.assertEqual(abril_y_mayo, Decimal("80.00"))

    def test_resumen_mensual_incluye_recurrencias_que_comenzaron_antes(self):
        self.gasto_recurrente(GastoOperativo.Periodicidad.DIARIA, date(2024, 1, 1), "2")
        meses = calculos.resumen_por_meses(
            self.negocio, [date(2024, 2, 1), date(2024, 3, 1)], Decimal("0"),
        )

        self.assertEqual(meses[0]["gastos"], Decimal("58.00"))
        self.assertEqual(meses[1]["gastos"], Decimal("62.00"))

    def test_el_resumen_diario_cuenta_la_ocurrencia_no_el_dia_de_captura(self):
        hoy = timezone.localdate()
        ayer = hoy - timedelta(days=1)
        self.gasto_recurrente(GastoOperativo.Periodicidad.DIARIA, ayer, "25")

        self.assertEqual(
            calculos.gastos_capturados(self.negocio, hoy, hoy + timedelta(days=1)),
            Decimal("25.00"),
        )

    def test_formulario_guarda_periodicidad_y_fecha_de_inicio(self):
        fecha_inicio = date(2024, 5, 15)
        respuesta = self.client.post(reverse("finanzas:registrar_gastos"), {
            "tipo": "FIJO",
            "concepto": "Internet",
            "monto": "350",
            "periodicidad": GastoOperativo.Periodicidad.CADA_MESES,
            "intervalo_meses": "3",
            "fecha_inicio": fecha_inicio.isoformat(),
            "nota": "",
        })

        self.assertEqual(respuesta.status_code, 302)
        gasto = GastoOperativo.objects.get()
        self.assertEqual(gasto.periodicidad, GastoOperativo.Periodicidad.CADA_MESES)
        self.assertEqual(gasto.intervalo_meses, 3)
        self.assertEqual(gasto.fecha_inicio, fecha_inicio)
        self.assertEqual(gasto.periodo, date(2024, 5, 1))

    def test_un_gasto_recurrente_requiere_fecha_de_inicio(self):
        respuesta = self.client.post(reverse("finanzas:registrar_gastos"), {
            "tipo": "FIJO",
            "concepto": "Internet",
            "monto": "350",
            "periodicidad": GastoOperativo.Periodicidad.CADA_MESES,
            "intervalo_meses": "2",
            "fecha_inicio": "",
            "nota": "",
        })

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(GastoOperativo.objects.count(), 0)
        self.assertContains(respuesta, "Selecciona desde qué fecha comienza el gasto.")

    def test_un_gasto_de_cada_cierto_numero_de_meses_requiere_intervalo(self):
        respuesta = self.client.post(reverse("finanzas:registrar_gastos"), {
            "tipo": "FIJO",
            "concepto": "Mantenimiento",
            "monto": "350",
            "periodicidad": GastoOperativo.Periodicidad.CADA_MESES,
            "intervalo_meses": "",
            "fecha_inicio": "2024-05-15",
            "nota": "",
        })

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(GastoOperativo.objects.count(), 0)
        self.assertContains(respuesta, "Indica cada cuántos meses ocurre el gasto.")

    def test_las_opciones_de_periodicidad_se_muestran_en_el_formulario(self):
        respuesta = self.client.get(reverse("finanzas:registrar_gastos"))

        self.assertContains(respuesta, "Diaria")
        self.assertContains(respuesta, "Semanal")
        self.assertContains(respuesta, "Mensual")
        self.assertContains(respuesta, "Cada cierta cantidad de meses")
        self.assertContains(respuesta, "Anual")


class PreciosParaCubrirGastosTests(TestCase):
    """Sugerir precios para que las ventas alcancen a pagar los gastos del negocio."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()
        self.producto = crear_producto(self.negocio, nombre="Refresco", costo="15", precio="25")

    def vender(self, cantidad, folio=1):
        venta = Venta.objects.create(negocio=self.negocio, folio=folio, estado=Venta.Estado.COBRADA)
        ItemVenta.objects.create(
            venta=venta, producto=self.producto, cantidad=Decimal(cantidad),
            precio_unitario=self.producto.precio_venta, costo_unitario=self.producto.costo,
        )
        venta.recalcular_total()

    def gastar(self, monto):
        GastoOperativo.objects.create(
            negocio=self.negocio, tipo=GastoOperativo.Tipo.FIJO, concepto="Renta", monto=Decimal(monto),
        )

    def test_gastos_sobre_ventas(self):
        self.vender("40")  # ventas por 1,000
        self.gastar("200")
        datos = calculos.gastos_sobre_ventas(self.negocio, self.hoy)
        self.assertEqual(datos["ingresos"], Decimal("1000.00"))
        self.assertEqual(datos["gastos"], Decimal("200.00"))
        self.assertEqual(datos["porcentaje"], Decimal("20.0"))

    def test_sin_ventas_no_hay_porcentaje(self):
        self.gastar("200")
        self.assertIsNone(calculos.gastos_sobre_ventas(self.negocio, self.hoy)["porcentaje"])

    def test_el_margen_que_cubre_los_gastos_suma_la_ganancia_extra(self):
        self.assertEqual(calculos.margen_que_cubre_gastos(Decimal("20.0"), Decimal("10")), Decimal("30.0"))

    def test_el_margen_que_cubre_los_gastos_nunca_pasa_de_90(self):
        self.assertEqual(calculos.margen_que_cubre_gastos(Decimal("85"), Decimal("20")), Decimal("90"))

    def test_en_modo_gastos_el_margen_sale_de_los_gastos_mas_la_ganancia_extra(self):
        self.vender("40")
        self.gastar("200")  # 20 % de las ventas
        respuesta = self.client.get(reverse("finanzas:sugerir_precios"), {"modo": "gastos", "utilidad": "10"})
        self.assertEqual(respuesta.context["modo"], "gastos")
        self.assertEqual(respuesta.context["margen"], Decimal("30.0"))
        # costo 15 con margen de 30 %: 15 / 0.70
        self.assertEqual(respuesta.context["pagina"].object_list[0]["sugerido"], Decimal("21.43"))

    def test_si_el_tendero_cambia_la_ganancia_extra_cambia_el_precio(self):
        self.vender("40")
        self.gastar("200")
        respuesta = self.client.get(reverse("finanzas:sugerir_precios"), {"modo": "gastos", "utilidad": "20"})
        self.assertEqual(respuesta.context["margen"], Decimal("40.0"))
        self.assertEqual(respuesta.context["pagina"].object_list[0]["sugerido"], Decimal("25.00"))

    def test_sin_ventas_el_modo_gastos_regresa_al_margen_manual(self):
        respuesta = self.client.get(reverse("finanzas:sugerir_precios"), {"modo": "gastos", "margen": "30"})
        self.assertEqual(respuesta.context["modo"], "manual")
        self.assertEqual(respuesta.context["margen"], Decimal("30.0"))

    def test_un_margen_que_no_alcanza_para_los_gastos_se_avisa(self):
        self.vender("40")
        self.gastar("500")  # 50 % de las ventas
        respuesta = self.client.get(reverse("finanzas:sugerir_precios"), {"modo": "manual", "margen": "30"})
        self.assertTrue(respuesta.context["margen_ya_cubre"])
        self.assertContains(respuesta, "no alcanzas a cubrir tus gastos")

    def test_la_ganancia_extra_mal_escrita_usa_la_de_por_defecto(self):
        self.vender("40")
        self.gastar("200")
        respuesta = self.client.get(reverse("finanzas:sugerir_precios"), {"modo": "gastos", "utilidad": "abc"})
        self.assertEqual(respuesta.context["utilidad"], Decimal("10"))

    def test_aceptar_un_precio_en_modo_gastos_lo_anota_en_el_historial(self):
        self.client.post(
            reverse("finanzas:aceptar_precio_sugerido", args=[self.producto.pk]),
            {"precio": "21.43", "margen": "30", "modo": "gastos", "utilidad": "10", "page": "1"},
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio_venta, Decimal("21.43"))
        self.assertIn("cubrir gastos", HistorialModificacionProducto.objects.get().motivo)


class ReglasDelPronosticoTests(SimpleTestCase):
    def test_un_dia_que_vendio_la_mitad_de_todo_se_ajusta(self):
        dias = {f"d{n}": 4.0 for n in range(8)}  # 32 unidades en 8 días
        dias["d3"] = 40.0  # un día de 40 sobre un total de 68: más de la mitad
        limpio, corregido = calculos.limpiar_dia_atipico(dias)
        self.assertTrue(corregido)
        self.assertEqual(limpio["d3"], 4.0)

    def test_si_las_ventas_son_parejas_no_se_ajusta_nada(self):
        dias = {f"d{n}": 4.0 + n for n in range(8)}
        limpio, corregido = calculos.limpiar_dia_atipico(dias)
        self.assertFalse(corregido)
        self.assertEqual(limpio, dias)

    def test_con_muy_pocos_dias_no_se_ajusta(self):
        dias = {"a": 100.0, "b": 1.0, "c": 1.0}
        self.assertFalse(calculos.limpiar_dia_atipico(dias)[1])

    def test_nivel_de_confianza_segun_el_error_contra_lo_que_se_vende(self):
        self.assertEqual(calculos.nivel_de_confianza(2, 20), "alta")    # 10 %
        self.assertEqual(calculos.nivel_de_confianza(8, 20), "media")   # 40 %
        self.assertEqual(calculos.nivel_de_confianza(15, 20), "baja")   # 75 %
        self.assertEqual(calculos.nivel_de_confianza(None, 20), "sin datos")
        self.assertEqual(calculos.nivel_de_confianza(3, 0), "sin datos")


class PronosticoProgresivoTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.inicio = timezone.datetime(2025, 1, 6).date()

    def vender(self, producto, dia, cantidad, folio):
        venta = Venta.objects.create(negocio=self.negocio, folio=folio, estado=Venta.Estado.COBRADA)
        venta.creado_en = timezone.make_aware(datetime.combine(dia, time(12)))
        venta.save(update_fields=["creado_en"])
        ItemVenta.objects.create(venta=venta, producto=producto, cantidad=Decimal(cantidad), precio_unitario=producto.precio_venta)

    def historial(self, producto, semanas=12, folio_inicial=1, cantidad=10):
        for semana in range(semanas):
            self.vender(producto, self.inicio + timedelta(weeks=semana), cantidad + semana % 3, folio_inicial + semana)

    def test_la_pantalla_trae_el_aviso_de_que_es_una_estimacion(self):
        respuesta = self.client.get(reverse("finanzas:pronostico_ventas"))
        self.assertContains(respuesta, "estimación de apoyo")
        self.assertContains(respuesta, "Volver a calcular")

    def test_la_base_sale_sin_correr_ningun_modelo(self):
        refresco = crear_producto(self.negocio, nombre="Refresco")
        self.historial(refresco)
        datos = self.client.get(reverse("finanzas:pronostico_base")).json()
        self.assertEqual(datos["estado"], "ok")
        self.assertEqual(datos["productos"][0]["nombre"], "Refresco")
        self.assertTrue(datos["productos"][0]["suficiente"])
        self.assertEqual(datos["umbrales"], {"alta": 0.25, "media": 0.5})

    def test_cada_modelo_se_pide_por_separado(self):
        refresco = crear_producto(self.negocio, nombre="Refresco")
        self.historial(refresco)
        for clave in ("lineal", "holt_winters", "arima"):
            with self.subTest(modelo=clave):
                datos = self.client.get(reverse("finanzas:pronostico_modelo", args=[clave])).json()
                self.assertEqual(datos["clave"], clave)
                resultado = datos["resultados"][0]
                self.assertTrue(resultado["disponible"])
                self.assertIsNotNone(resultado["pronostico"])
                self.assertIsNotNone(resultado["mae"])

    def test_un_modelo_que_no_existe_da_404(self):
        self.assertEqual(self.client.get(reverse("finanzas:pronostico_modelo", args=["magia"])).status_code, 404)

    def test_un_producto_con_pocos_dias_de_historia_dice_datos_insuficientes(self):
        nuevo = crear_producto(self.negocio, nombre="Nuevo")
        self.vender(nuevo, self.inicio, 5, 1)
        self.vender(nuevo, self.inicio + timedelta(days=10), 5, 2)
        resultado = calculos.pronostico_ventas_negocio(self.negocio, semanas_historial=12)
        producto = resultado["productos"][0]
        self.assertFalse(producto["datos_suficientes"])
        self.assertIsNone(producto["mejor_pronostico"])  # nunca se inventa un cero
        self.assertEqual(producto["confianza"], "sin datos")

    def test_el_minimo_de_dias_se_puede_configurar(self):
        from django.test import override_settings
        nuevo = crear_producto(self.negocio, nombre="Nuevo")
        for semana in range(4):
            self.vender(nuevo, self.inicio + timedelta(weeks=semana), 5, semana + 1)
        with override_settings(PRONOSTICO_MINIMO_DIAS=15):
            self.assertTrue(calculos.series_de_los_mas_vendidos(self.negocio, semanas_historial=12)["productos"][0]["suficiente"])
        with override_settings(PRONOSTICO_MINIMO_DIAS=60):
            self.assertFalse(calculos.series_de_los_mas_vendidos(self.negocio, semanas_historial=12)["productos"][0]["suficiente"])

    def test_una_venta_muy_rara_se_ajusta_en_la_serie(self):
        refresco = crear_producto(self.negocio, nombre="Refresco")
        self.historial(refresco, cantidad=5)
        self.vender(refresco, self.inicio + timedelta(weeks=5, days=2), 400, 99)  # un día que vendió casi todo
        producto = calculos.series_de_los_mas_vendidos(self.negocio, semanas_historial=12)["productos"][0]
        self.assertTrue(producto["atipico_corregido"])
        self.assertLess(max(producto["serie"]), 30)

    def test_el_pronostico_trae_cambio_contra_la_ultima_semana_y_confianza(self):
        refresco = crear_producto(self.negocio, nombre="Refresco")
        self.historial(refresco)
        producto = calculos.pronostico_ventas_negocio(self.negocio, semanas_historial=12)["productos"][0]
        self.assertIn(producto["confianza"], ("alta", "media", "baja"))
        self.assertIsNotNone(producto["cambio_porcentual"])
        self.assertGreater(producto["ultima_semana_real"], 0)


class ExplicacionDelPronosticoTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)

    def test_sin_historia_suficiente_no_se_llama_a_la_ia(self):
        from unittest.mock import patch
        with patch("avi.views.generar_texto") as llamada:
            respuesta = self.client.get(reverse("avi:explicar", args=["pronostico"])).json()
        llamada.assert_not_called()
        self.assertIn("Todavía no hay suficientes días", respuesta["respuesta"])

    def test_con_historia_la_ia_explica_el_pronostico(self):
        from unittest.mock import patch
        refresco = crear_producto(self.negocio, nombre="Refresco")
        inicio = timezone.datetime(2025, 1, 6).date()
        for semana in range(12):
            venta = Venta.objects.create(negocio=self.negocio, folio=semana + 1, estado=Venta.Estado.COBRADA)
            venta.creado_en = timezone.make_aware(datetime.combine(inicio + timedelta(weeks=semana), time(12)))
            venta.save(update_fields=["creado_en"])
            ItemVenta.objects.create(venta=venta, producto=refresco, cantidad=Decimal(10 + semana % 3), precio_unitario=Decimal("25"))

        with patch("avi.views.generar_texto", return_value="Vas a vender parecido la próxima semana.") as llamada:
            respuesta = self.client.get(reverse("avi:explicar", args=["pronostico"])).json()
        self.assertEqual(respuesta["respuesta"], "Vas a vender parecido la próxima semana.")
        mensaje = llamada.call_args[0][0]
        self.assertIn("pronóstico de ventas", mensaje)
        self.assertIn("Refresco", mensaje)
        self.assertIn("la decisión de cuánto comprar es mía", mensaje)


class ReportesConfigurablesTests(TestCase):
    """Reportes financieros en el periodo que el tendero elija, con alertas y sugerencias concretas."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()
        self.mes_actual = self.hoy.replace(day=1)
        self.producto = crear_producto(self.negocio, nombre="Refresco", costo="15", precio="25", cantidad="500")

    def vender(self, cantidad, folio, dia=None):
        venta = Venta.objects.create(negocio=self.negocio, folio=folio, estado=Venta.Estado.COBRADA)
        ItemVenta.objects.create(
            venta=venta, producto=self.producto, cantidad=Decimal(cantidad),
            precio_unitario=Decimal("25"), costo_unitario=Decimal("15"),
        )
        venta.recalcular_total()
        if dia:
            venta.creado_en = timezone.make_aware(datetime.combine(dia, time(12)))
            venta.save(update_fields=["creado_en"])
        return venta

    def test_se_puede_ver_el_reporte_de_1_3_6_o_12_meses(self):
        for meses in (1, 3, 6, 12):
            with self.subTest(meses=meses):
                respuesta = self.client.get(reverse("finanzas:reportes_financieros"), {"periodo": meses})
                self.assertEqual(len(respuesta.context["datos_meses"]), meses)

    def test_se_puede_escoger_un_rango_de_meses(self):
        desde = calculos.mes_anterior(calculos.mes_anterior(self.mes_actual))
        respuesta = self.client.get(reverse("finanzas:reportes_financieros"), {
            "desde": desde.strftime("%Y-%m"), "hasta": self.mes_actual.strftime("%Y-%m"),
        })
        self.assertEqual(len(respuesta.context["datos_meses"]), 3)
        self.assertEqual(respuesta.context["desde_mes"], desde.strftime("%Y-%m"))

    def test_un_rango_al_reves_o_en_el_futuro_se_acomoda(self):
        futuro = calculos.mes_siguiente(calculos.mes_siguiente(self.mes_actual))
        respuesta = self.client.get(reverse("finanzas:reportes_financieros"), {
            "desde": futuro.strftime("%Y-%m"), "hasta": self.mes_actual.strftime("%Y-%m"),
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["hasta_mes"], self.mes_actual.strftime("%Y-%m"))

    def test_un_rango_muy_largo_se_limita_a_24_meses(self):
        respuesta = self.client.get(reverse("finanzas:reportes_financieros"), {"desde": "2000-01", "hasta": self.mes_actual.strftime("%Y-%m")})
        self.assertEqual(len(respuesta.context["datos_meses"]), 24)

    def test_el_ultimo_periodo_escogido_se_recuerda(self):
        self.client.get(reverse("finanzas:reportes_financieros"), {"periodo": 3})
        respuesta = self.client.get(reverse("finanzas:reportes_financieros"))
        self.assertEqual(respuesta.context["periodo_meses"], 3)
        self.negocio.refresh_from_db()
        self.assertEqual(self.negocio.preferencia("meses_reportes"), 3)

    def test_sugerencia_cuando_un_mes_se_pierde_dinero(self):
        self.vender("2", 1)  # ventas por 50
        GastoOperativo.objects.create(negocio=self.negocio, tipo=GastoOperativo.Tipo.FIJO, concepto="Renta", monto=Decimal("900"))
        respuesta = self.client.get(reverse("finanzas:reportes_financieros"), {"periodo": 1})
        textos = " ".join(s["texto"] for s in respuesta.context["sugerencias"])
        self.assertIn("perdiste dinero", textos)

    def test_sugerencia_cuando_los_gastos_suben_mucho(self):
        anterior = calculos.mes_anterior(self.mes_actual)
        GastoOperativo.objects.create(negocio=self.negocio, tipo=GastoOperativo.Tipo.FIJO, concepto="Luz", monto=Decimal("100"), periodo=anterior)
        GastoOperativo.objects.create(negocio=self.negocio, tipo=GastoOperativo.Tipo.FIJO, concepto="Luz", monto=Decimal("300"), periodo=self.mes_actual)
        respuesta = self.client.get(reverse("finanzas:reportes_financieros"), {"periodo": 3})
        textos = " ".join(s["texto"] for s in respuesta.context["sugerencias"])
        self.assertIn("subieron 200%", textos)

    def test_sin_problemas_no_hay_sugerencias(self):
        respuesta = self.client.get(reverse("finanzas:reportes_financieros"))
        self.assertEqual(respuesta.context["sugerencias"], [])
        self.assertContains(respuesta, "no hay alertas en este periodo")


class ReporteDeVentasTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.hoy = timezone.localdate()
        self.coca = crear_producto(self.negocio, nombre="Coca", costo="15", precio="25", cantidad="500")
        self.galleta = crear_producto(self.negocio, nombre="Galleta", costo="8", precio="10", cantidad="500")
        categoria = Categoria.objects.create(nombre="Bebidas")
        self.coca.categoria = categoria
        self.coca.save()

    def vender(self, renglones, folio, dia=None):
        venta = Venta.objects.create(negocio=self.negocio, folio=folio, estado=Venta.Estado.COBRADA)
        for producto, cantidad in renglones:
            ItemVenta.objects.create(
                venta=venta, producto=producto, cantidad=Decimal(cantidad),
                precio_unitario=producto.precio_venta, costo_unitario=producto.costo,
            )
        venta.recalcular_total()
        if dia:
            venta.creado_en = timezone.make_aware(datetime.combine(dia, time(12)))
            venta.save(update_fields=["creado_en"])

    def test_la_pantalla_abre_sin_ventas(self):
        respuesta = self.client.get(reverse("finanzas:reporte_ventas"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No hay ventas cobradas en estas fechas")

    def test_ventas_ganancia_tickets_y_ticket_promedio(self):
        self.vender([(self.coca, "4"), (self.galleta, "5")], 1)  # 100 + 50 = 150; costo 60 + 40 = 100
        self.vender([(self.coca, "2")], 2)                       # 50; costo 30
        reporte = calculos.reporte_de_ventas(self.negocio, self.hoy, self.hoy)
        self.assertEqual(reporte["ingresos"], Decimal("200.00"))
        self.assertEqual(reporte["costo"], Decimal("130.00"))
        self.assertEqual(reporte["ganancia"], Decimal("70.00"))
        self.assertEqual(reporte["margen_bruto"], Decimal("35.0"))
        self.assertEqual(reporte["tickets"], 2)
        self.assertEqual(reporte["ticket_promedio"], Decimal("100.00"))

    def test_productos_mas_vendidos_y_con_mas_ganancia(self):
        self.vender([(self.coca, "2"), (self.galleta, "30")], 1)  # galleta: 30 piezas, 60 de ganancia; coca: 2 piezas, 20 de ganancia
        reporte = calculos.reporte_de_ventas(self.negocio, self.hoy, self.hoy)
        self.assertEqual(reporte["mas_vendidos"][0]["nombre"], "Galleta")
        self.assertEqual(reporte["mas_ganancia"][0]["nombre"], "Galleta")
        self.assertEqual(reporte["mas_ganancia"][1]["ganancia"], Decimal("20.00"))

    def test_por_categoria(self):
        self.vender([(self.coca, "2"), (self.galleta, "5")], 1)
        nombres = {c["nombre"]: c["ventas"] for c in calculos.reporte_de_ventas(self.negocio, self.hoy, self.hoy)["por_categoria"]}
        self.assertEqual(nombres, {"Bebidas": Decimal("50.00"), "Sin categoría": Decimal("50.00")})

    def test_el_filtro_por_fechas_deja_fuera_lo_demas(self):
        self.vender([(self.coca, "2")], 1, dia=self.hoy - timedelta(days=40))
        self.vender([(self.coca, "1")], 2)
        respuesta = self.client.get(reverse("finanzas:reporte_ventas"), {"dias": "30"})
        self.assertEqual(respuesta.context["reporte"]["tickets"], 1)
        todo = self.client.get(reverse("finanzas:reporte_ventas"), {
            "desde": (self.hoy - timedelta(days=60)).isoformat(), "hasta": self.hoy.isoformat(),
        })
        self.assertEqual(todo.context["reporte"]["tickets"], 2)

    def test_no_se_mezclan_las_ventas_de_otra_tienda(self):
        otro_usuario, otro_negocio = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra")
        otro = crear_producto(otro_negocio, nombre="Ajeno")
        venta = Venta.objects.create(negocio=otro_negocio, folio=1, estado=Venta.Estado.COBRADA)
        ItemVenta.objects.create(venta=venta, producto=otro, cantidad=Decimal("1"), precio_unitario=Decimal("25"))
        venta.recalcular_total()
        self.assertEqual(self.client.get(reverse("finanzas:reporte_ventas")).context["reporte"]["tickets"], 0)

    def test_fechas_mal_escritas_usan_los_ultimos_30_dias(self):
        respuesta = self.client.get(reverse("finanzas:reporte_ventas"), {"desde": "ayer", "hasta": "hoy"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["dias"], "30")


class ReglasFinancierasTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)

    def test_el_punto_de_equilibrio_necesita_el_costo_de_los_productos(self):
        GastoOperativo.objects.create(negocio=self.negocio, tipo=GastoOperativo.Tipo.FIJO, concepto="Renta", monto=Decimal("500"))
        crear_producto(self.negocio, nombre="Sin costo", costo="0")
        datos = calculos.punto_equilibrio_negocio(self.negocio, timezone.localdate())
        self.assertEqual(datos["estado"], "sin_costos")
        self.assertContains(self.client.get(reverse("finanzas:punto_equilibrio")), "cuánto te cuesta cada producto")

    def test_el_precio_sugerido_nunca_baja_del_costo(self):
        self.assertGreaterEqual(calculos.precio_sugerido(Decimal("15"), Decimal("0")), Decimal("15.00"))
        self.assertGreaterEqual(calculos.precio_sugerido(Decimal("15"), Decimal("-20")), Decimal("15.00"))

    def test_los_precios_sugeridos_muestran_la_ganancia_por_pieza(self):
        crear_producto(self.negocio, nombre="Refresco")  # costo 15
        respuesta = self.client.get(reverse("finanzas:sugerir_precios"), {"modo": "manual", "margen": "30"})
        self.assertEqual(respuesta.context["pagina"].object_list[0]["ganancia"], Decimal("6.43"))
        self.assertContains(respuesta, "Ganancia por pieza")

    def test_lo_que_escoge_en_precios_se_recuerda_entre_sesiones(self):
        self.client.get(reverse("finanzas:sugerir_precios"), {"modo": "manual", "margen": "42", "utilidad": "15"})
        respuesta = self.client.get(reverse("finanzas:sugerir_precios"))
        self.assertEqual(respuesta.context["margen"], Decimal("42.0"))
        self.assertEqual(respuesta.context["utilidad"], Decimal("15.0"))
        self.negocio.refresh_from_db()
        self.assertEqual(self.negocio.preferencia("margen_deseado"), "42.0")


class CategoriasDeGastoTests(TestCase):
    """Las categorías de gasto vienen con su tipo (fijo o variable) para proponerlo al elegirlas."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)

    def test_la_pantalla_de_gastos_manda_el_tipo_de_cada_categoria(self):
        from .models import CategoriaGasto
        CategoriaGasto.objects.create(negocio=self.negocio, nombre="Luz", tipo="FIJO")
        CategoriaGasto.objects.create(negocio=self.negocio, nombre="Bolsas", tipo="VARIABLE")
        respuesta = self.client.get(reverse("finanzas:registrar_gastos"))
        self.assertContains(respuesta, 'data-tipo="FIJO"')
        self.assertContains(respuesta, 'data-tipo="VARIABLE"')

    def test_una_categoria_nueva_guarda_el_tipo_que_se_eligio(self):
        from .models import CategoriaGasto
        self.client.post(reverse("finanzas:categoria_gasto_alta"), {"nombre": "Fletes", "tipo": "VARIABLE"})
        self.assertEqual(CategoriaGasto.objects.get(nombre="Fletes").tipo, "VARIABLE")

    def test_no_se_duplica_una_categoria_aunque_cambien_las_mayusculas(self):
        from .models import CategoriaGasto
        CategoriaGasto.objects.create(negocio=self.negocio, nombre="Luz", tipo="FIJO")
        self.client.post(reverse("finanzas:categoria_gasto_alta"), {"nombre": "luz", "tipo": "FIJO"})
        self.assertEqual(CategoriaGasto.objects.count(), 1)

    def test_el_precio_de_compra_de_un_no_encontrado_no_puede_superar_su_precio_de_venta(self):
        producto = crear_producto(self.negocio, nombre="Cosa rara", costo="0", precio="20", cantidad="0")
        producto.pendiente_validacion = True
        producto.save()
        self.client.post(reverse("finanzas:completar_no_encontrado", args=[producto.pk]), {"precio_compra": "30"})
        producto.refresh_from_db()
        self.assertEqual(producto.costo, Decimal("0"))

    def test_las_categorias_de_gasto_se_ven_recogidas_con_mostrar_mas(self):
        respuesta = self.client.get(reverse("finanzas:registrar_gastos"))
        self.assertContains(respuesta, "data-colapsable")
        self.assertContains(respuesta, "data-siempre")  # el botón "Nueva" nunca se esconde
