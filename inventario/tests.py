from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.testing import crear_negocio, crear_producto
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

    def test_el_panel_se_pagina(self):
        for numero in range(30):
            crear_producto(self.negocio, nombre=f"Producto {numero:02d}")
        respuesta = self.client.get(reverse("inventario:panel"))
        self.assertEqual(len(respuesta.context["productos"]), 25)
        self.assertEqual(respuesta.context["pagina"].paginator.num_pages, 2)

    def test_abrir_un_producto_desde_el_buscador_muestra_solo_ese(self):
        otro = crear_producto(self.negocio, nombre="Pepsi 600")
        respuesta = self.client.get(reverse("inventario:panel"), {"abrir": otro.pk})
        self.assertEqual([p.pk for p in respuesta.context["productos"]], [otro.pk])
        self.assertEqual(respuesta.context["abrir_modal_editar_pk"], otro.pk)

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
