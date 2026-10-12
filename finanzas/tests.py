from datetime import datetime, time, timedelta
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from core.testing import crear_negocio, crear_producto
from inventario.models import Categoria, HistorialModificacionProducto
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
