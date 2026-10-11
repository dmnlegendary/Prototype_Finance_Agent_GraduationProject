import tempfile
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from inventario.models import Categoria, Producto
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
