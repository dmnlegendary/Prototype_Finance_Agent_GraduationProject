import json
import tempfile
from datetime import datetime
from datetime import timezone as dt_timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from finanzas.models import GastoOperativo
from inventario.models import Categoria, Producto
from ventas import carrito
from ventas.models import ItemVenta, Venta

from . import cache_negocio
from .testing import crear_negocio, crear_producto


class CacheDelNegocioTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()

    def test_solo_calcula_la_primera_vez(self):
        llamadas = []

        def calcular():
            llamadas.append(1)
            return {"valor": 5}

        cache_negocio.obtener(self.negocio, "ventas_hoy", calcular)
        resultado = cache_negocio.obtener(self.negocio, "ventas_hoy", calcular)

        self.assertEqual(resultado, {"valor": 5})
        self.assertEqual(len(llamadas), 1)

    def test_invalidar_obliga_a_calcular_de_nuevo(self):
        valores = iter([1, 2])
        cache_negocio.obtener(self.negocio, "ventas_hoy", lambda: next(valores))
        cache_negocio.invalidar(self.negocio.pk, "ventas_hoy")
        self.assertEqual(cache_negocio.obtener(self.negocio, "ventas_hoy", lambda: next(valores)), 2)

    def test_cada_negocio_tiene_su_propio_cache(self):
        _, otro = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra")
        cache_negocio.obtener(self.negocio, "ventas_hoy", lambda: "mio")
        self.assertEqual(cache_negocio.obtener(otro, "ventas_hoy", lambda: "ajeno"), "ajeno")

    def test_guardar_un_producto_borra_el_cache_del_negocio(self):
        cache_negocio.obtener(self.negocio, "alertas_conteo", lambda: {"total": 0})
        crear_producto(self.negocio)
        self.assertEqual(cache_negocio.obtener(self.negocio, "alertas_conteo", lambda: "recalculado"), "recalculado")

    def test_registrar_una_venta_borra_el_cache_del_negocio(self):
        cache_negocio.obtener(self.negocio, "ventas_hoy", lambda: "viejo")
        Venta.objects.create(negocio=self.negocio, folio=1)
        self.assertEqual(cache_negocio.obtener(self.negocio, "ventas_hoy", lambda: "nuevo"), "nuevo")


class ConfigurarIaTests(SimpleTestCase):
    def correr(self, ruta_env, **opciones):
        with patch("avi.management.commands.configurar_ia.RUTA_ENV", ruta_env):
            call_command("configurar_ia", stdout=StringIO(), **opciones)

    def test_guarda_las_llaves_sin_borrar_lo_demas(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / ".env"
            ruta.write_text("DB_NAME=maria_db\nOPENAI_API_KEY=\n", encoding="utf-8")

            self.correr(ruta, openai="sk-prueba-1234", gemini="AIza-prueba-5678")
            lineas = ruta.read_text(encoding="utf-8").splitlines()

        self.assertIn("DB_NAME=maria_db", lineas)
        self.assertIn("OPENAI_API_KEY=sk-prueba-1234", lineas)
        self.assertIn("GEMINI_API_KEY=AIza-prueba-5678", lineas)
        self.assertEqual(sum(1 for linea in lineas if linea.startswith("OPENAI_API_KEY=")), 1)

    def test_crea_el_archivo_si_no_existe(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / ".env"
            self.correr(ruta, gemini="AIza-prueba-5678")
            self.assertEqual(ruta.read_text(encoding="utf-8").strip(), "GEMINI_API_KEY=AIza-prueba-5678")

    def test_lee_las_llaves_de_un_archivo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / ".env"
            claves = Path(carpeta) / "claves.txt"
            claves.write_text("# claves del equipo\nOPENAI_API_KEY=sk-del-equipo\nOTRA_COSA=1\n", encoding="utf-8")

            self.correr(ruta, archivo=str(claves))
            texto = ruta.read_text(encoding="utf-8")

        self.assertIn("OPENAI_API_KEY=sk-del-equipo", texto)
        self.assertNotIn("OTRA_COSA", texto)

    def test_un_archivo_que_no_existe_da_error(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with self.assertRaises(CommandError):
                self.correr(Path(carpeta) / ".env", archivo=str(Path(carpeta) / "no_existe.txt"))


class ImportarCsvTests(TestCase):
    PRODUCTOS = (
        "nombre,categoria,costo,precio_venta,cantidad_actual,cantidad_minima\n"
        "Coca 600,Bebidas,14,20,10,2\n"
        "Jabón Zote,Limpieza,10,14,5,2\n"
        "Sabritas,Botanas,13,18,8,2\n"
        "Producto sin precio,Botanas,5,,3,1\n"
    )
    VENTAS = (
        "fecha,folio,producto,cantidad,precio_unitario\n"
        "2026-10-01 09:15:00,A1,Coca 600,2,20\n"
        "2026-10-01 09:15:00,A1,jabon zote,1,14\n"
        "2026-10-02 10:00:00,A2,Sabritas,3,18\n"
        "2026-10-02 10:30:00,A3,Un producto que no existe,1,10\n"
    )

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.carpeta = tempfile.TemporaryDirectory()
        self.addCleanup(self.carpeta.cleanup)

    def archivo(self, nombre, contenido):
        ruta = Path(self.carpeta.name) / nombre
        ruta.write_text(contenido, encoding="utf-8")
        return str(ruta)

    def importar(self, **archivos):
        call_command("importar_csv", usuario="tendero@ejemplo.com", stdout=StringIO(), **archivos)

    def test_importa_productos_y_omite_los_que_traen_datos_malos(self):
        self.importar(productos=self.archivo("productos.csv", self.PRODUCTOS))

        self.assertEqual(Producto.objects.filter(negocio=self.negocio).count(), 3)
        self.assertEqual(Categoria.objects.count(), 3)
        coca = Producto.objects.get(nombre="Coca 600")
        self.assertEqual(coca.precio_venta, Decimal("20.00"))
        self.assertEqual(coca.categoria.nombre, "Bebidas")

    def test_importar_dos_veces_no_duplica_productos(self):
        ruta = self.archivo("productos.csv", self.PRODUCTOS)
        self.importar(productos=ruta)
        self.importar(productos=ruta)
        self.assertEqual(Producto.objects.filter(negocio=self.negocio).count(), 3)

    def test_importa_ventas_agrupadas_por_folio_con_su_fecha(self):
        self.importar(
            productos=self.archivo("productos.csv", self.PRODUCTOS),
            ventas=self.archivo("ventas.csv", self.VENTAS),
        )

        ventas = list(Venta.objects.filter(negocio=self.negocio).order_by("folio"))
        self.assertEqual(len(ventas), 2)
        self.assertEqual(ItemVenta.objects.count(), 3)
        self.assertTrue(all(v.estado == Venta.Estado.COBRADA for v in ventas))
        self.assertEqual(ventas[0].total, Decimal("54.00"))
        self.assertEqual(ventas[1].total, Decimal("54.00"))
        self.assertEqual(timezone.localtime(ventas[0].creado_en).date().isoformat(), "2026-10-01")
        self.assertEqual(timezone.localtime(ventas[1].creado_en).date().isoformat(), "2026-10-02")

    def test_un_csv_sin_las_columnas_necesarias_da_error(self):
        with self.assertRaises(CommandError):
            self.importar(productos=self.archivo("malo.csv", "color,talla\nrojo,M\n"))

    def test_un_usuario_que_no_existe_da_error(self):
        with self.assertRaises(CommandError):
            call_command(
                "importar_csv", usuario="nadie@ejemplo.com",
                productos=self.archivo("productos.csv", self.PRODUCTOS), stdout=StringIO(),
            )

    def test_despues_de_importar_las_alertas_ya_cuentan_los_productos_nuevos(self):
        from inventario.alertas import conteo_alertas

        self.assertEqual(conteo_alertas(self.negocio)["total"], 0)
        self.importar(productos=self.archivo(
            "productos.csv", "nombre,precio_venta,cantidad_actual,cantidad_minima\nPepsi,18,1,5\n",
        ))
        self.assertEqual(conteo_alertas(self.negocio)["rojo"], 1)


class SincronizacionSinInternetTests(TestCase):
    """Lo que se hizo sin internet llega al servidor cuando regresa la conexión."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        self.coca = crear_producto(self.negocio, nombre="Coca 600", cantidad="10", costo="15", precio="25")

    def enviar(self, *operaciones):
        respuesta = self.client.post(
            reverse("core:sincronizar"), data=json.dumps({"operaciones": list(operaciones)}), content_type="application/json",
        )
        return respuesta.json()["resultados"]

    def venta(self, uuid="v1", cantidad=2, **extra):
        datos = {
            "carrito": 1, "fecha": "2026-01-05T15:30:00Z", "limpiar_carrito": False,
            "renglones": [{"producto_id": self.coca.pk, "cantidad": cantidad, "precio_unitario": 25}],
        }
        datos.update(extra)
        return {"uuid": uuid, "tipo": "venta", "datos": datos}

    def test_una_venta_hecha_sin_internet_se_guarda_con_su_fecha_y_descuenta_el_inventario(self):
        resultado = self.enviar(self.venta())[0]

        self.assertTrue(resultado["ok"])
        venta = Venta.objects.get()
        self.assertEqual(venta.estado, Venta.Estado.COBRADA)
        self.assertEqual(venta.total, Decimal("50.00"))
        self.assertEqual(venta.creado_en, datetime(2026, 1, 5, 15, 30, tzinfo=dt_timezone.utc))
        self.assertEqual(ItemVenta.objects.get().costo_unitario, Decimal("15.00"))
        self.coca.refresh_from_db()
        self.assertEqual(self.coca.cantidad_actual, Decimal("8"))

    def test_mandar_dos_veces_la_misma_operacion_no_la_duplica(self):
        self.enviar(self.venta(uuid="repetida"))
        resultado = self.enviar(self.venta(uuid="repetida"))[0]

        self.assertTrue(resultado["ok"])
        self.assertEqual(Venta.objects.count(), 1)
        self.coca.refresh_from_db()
        self.assertEqual(self.coca.cantidad_actual, Decimal("8"))

    def test_las_operaciones_se_aplican_en_orden_y_cada_una_responde_por_separado(self):
        resultados = self.enviar(self.venta(uuid="a", cantidad=1), self.venta(uuid="b", cantidad=3))
        self.assertEqual([r["uuid"] for r in resultados], ["a", "b"])
        self.assertEqual(Venta.objects.count(), 2)
        self.coca.refresh_from_db()
        self.assertEqual(self.coca.cantidad_actual, Decimal("6"))

    def test_una_venta_de_un_producto_que_ya_no_existe_se_rechaza_para_siempre(self):
        operacion = self.venta()
        operacion["datos"]["renglones"][0]["producto_id"] = 99999
        resultado = self.enviar(operacion)[0]

        self.assertFalse(resultado["ok"])
        self.assertTrue(resultado["definitivo"])
        self.assertEqual(Venta.objects.count(), 0)

    def test_si_ya_no_alcanzaban_las_existencias_la_venta_se_guarda_y_se_avisa(self):
        resultado = self.enviar(self.venta(cantidad=15))[0]

        self.assertTrue(resultado["ok"])
        self.assertIn("no alcanzaban", resultado["mensaje"])
        self.coca.refresh_from_db()
        self.assertEqual(self.coca.cantidad_actual, Decimal("0"))  # nunca queda en negativo

    def test_si_la_venta_venia_de_un_carrito_del_servidor_se_vacia_ese_carrito(self):
        abierto = carrito.venta_en_curso(self.negocio, 1)
        ItemVenta.objects.create(venta=abierto, producto=self.coca, cantidad=Decimal("2"), precio_unitario=Decimal("25"))

        self.enviar(self.venta(limpiar_carrito=True))
        abierto.refresh_from_db()
        self.assertEqual(abierto.items.count(), 0)
        self.assertEqual(abierto.estado, Venta.Estado.EN_CURSO)

    def test_un_producto_no_encontrado_vendido_sin_internet_queda_pendiente(self):
        operacion = self.venta()
        operacion["datos"]["renglones"] = [{"no_encontrado": True, "nombre": "Bolsa de hielo", "cantidad": 1, "precio_unitario": 20}]
        self.enviar(operacion)

        pendiente = Producto.objects.get(nombre="Bolsa de hielo")
        self.assertTrue(pendiente.pendiente_validacion)
        self.assertEqual(Venta.objects.get().total, Decimal("20.00"))

    def test_una_pieza_con_decimales_se_rechaza(self):
        resultado = self.enviar(self.venta(cantidad=1.5))[0]
        self.assertTrue(resultado["definitivo"])
        self.assertEqual(Venta.objects.count(), 0)

    def test_alta_de_un_producto_sin_internet(self):
        resultado = self.enviar({
            "uuid": "alta1", "tipo": "alta_producto",
            "datos": {
                "nombre": "Pepsi 600", "costo": "13", "precio_venta": "18", "cantidad_actual": "12",
                "cantidad_minima": "4", "a_granel": False, "descripcion": "",
            },
        })[0]

        self.assertTrue(resultado["ok"])
        self.assertEqual(Producto.objects.get(nombre="Pepsi 600").cantidad_actual, Decimal("12"))
        self.assertEqual(GastoOperativo.objects.get().monto, Decimal("156.00"))

    def test_un_alta_con_datos_malos_se_rechaza(self):
        resultado = self.enviar({"uuid": "alta2", "tipo": "alta_producto", "datos": {"nombre": "Sin precios"}})[0]
        self.assertFalse(resultado["ok"])
        self.assertTrue(resultado["definitivo"])
        self.assertFalse(Producto.objects.filter(nombre="Sin precios").exists())

    def test_resurtir_sin_internet_suma_las_piezas_y_registra_la_compra(self):
        self.enviar({"uuid": "r1", "tipo": "resurtir", "datos": {"producto_id": self.coca.pk, "cantidad": "20", "costo": "16"}})
        self.coca.refresh_from_db()
        self.assertEqual(self.coca.cantidad_actual, Decimal("30"))
        self.assertEqual(GastoOperativo.objects.get().monto, Decimal("320.00"))

    def test_una_operacion_desconocida_se_descarta(self):
        resultado = self.enviar({"uuid": "x", "tipo": "borrar_todo", "datos": {}})[0]
        self.assertFalse(resultado["ok"])
        self.assertTrue(resultado["definitivo"])

    def test_no_se_pueden_tocar_productos_de_otra_tienda(self):
        otro_usuario, otro_negocio = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra")
        ajeno = crear_producto(otro_negocio, nombre="Ajeno", cantidad="5")
        resultado = self.enviar({"uuid": "r2", "tipo": "resurtir", "datos": {"producto_id": ajeno.pk, "cantidad": "5"}})[0]
        self.assertFalse(resultado["ok"])
        ajeno.refresh_from_db()
        self.assertEqual(ajeno.cantidad_actual, Decimal("5"))

    def test_pide_sesion(self):
        self.client.logout()
        respuesta = self.client.post(reverse("core:sincronizar"), data="{}", content_type="application/json")
        self.assertEqual(respuesta.status_code, 302)

    def test_un_envio_mal_armado_da_error_400(self):
        respuesta = self.client.post(reverse("core:sincronizar"), data=json.dumps({"operaciones": "no"}), content_type="application/json")
        self.assertEqual(respuesta.status_code, 400)

    def test_el_navegador_puede_preguntar_si_ya_hay_conexion(self):
        self.assertTrue(self.client.get(reverse("core:estado_de_la_conexion")).json()["ok"])

    def test_el_service_worker_se_sirve_desde_la_raiz(self):
        respuesta = self.client.get("/sw.js")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta["Service-Worker-Allowed"], "/")
        self.assertIn("addEventListener('fetch'", respuesta.content.decode())
