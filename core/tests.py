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
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from finanzas.models import GastoOperativo
from inventario.models import Categoria, Producto
from ventas import carrito
from ventas.models import ItemVenta, Venta

from . import cache_negocio, llaves
from .models import LlaveIA
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


class ConfigurarIaTests(TestCase):
    """Las llaves de la IA se guardan cifradas en la base de datos, nunca en texto plano."""

    def correr(self, **opciones):
        salida = StringIO()
        call_command("configurar_ia", stdout=salida, **opciones)
        return salida.getvalue()

    def test_guarda_las_llaves_y_se_leen_ya_descifradas(self):
        self.correr(openai="sk-prueba-1234", gemini="AIza-prueba-5678")
        self.assertEqual(llaves.obtener("openai"), "sk-prueba-1234")
        self.assertEqual(llaves.obtener("gemini"), "AIza-prueba-5678")

    def test_en_la_base_de_datos_no_queda_el_texto_plano(self):
        self.correr(openai="sk-prueba-1234")
        guardada = LlaveIA.objects.get(proveedor="openai")
        self.assertNotIn("sk-prueba-1234", guardada.valor_cifrado)
        self.assertNotEqual(guardada.valor_cifrado, "sk-prueba-1234")

    def test_al_guardar_otra_vez_se_reemplaza_la_llave(self):
        self.correr(openai="sk-vieja")
        self.correr(openai="sk-nueva")
        self.assertEqual(LlaveIA.objects.filter(proveedor="openai").count(), 1)
        self.assertEqual(llaves.obtener("openai"), "sk-nueva")

    def test_no_escribe_el_archivo_env(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with override_settings(BASE_DIR=Path(carpeta)):
                self.correr(gemini="AIza-prueba-5678")
            self.assertEqual(list(Path(carpeta).iterdir()), [])

    def test_lee_las_llaves_de_un_archivo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            claves = Path(carpeta) / "claves.txt"
            claves.write_text("# claves del equipo\nOPENAI_API_KEY=sk-del-equipo\nOTRA_COSA=1\n", encoding="utf-8")
            self.correr(archivo=str(claves))
        self.assertEqual(llaves.obtener("openai"), "sk-del-equipo")
        self.assertEqual(LlaveIA.objects.count(), 1)

    def test_un_archivo_que_no_existe_da_error(self):
        with self.assertRaises(CommandError):
            self.correr(archivo="no_existe.txt")

    def test_pasa_a_la_base_de_datos_las_llaves_del_env(self):
        with override_settings(OPENAI_API_KEY="sk-del-env", GEMINI_API_KEY=""):
            self.correr(desde_env=True)
        self.assertEqual(llaves.obtener("openai"), "sk-del-env")
        self.assertTrue(LlaveIA.objects.filter(proveedor="openai").exists())

    def test_ver_muestra_las_llaves_tapadas(self):
        self.correr(openai="sk-prueba-1234")
        with override_settings(GEMINI_API_KEY="AIza-del-env-9999"):
            texto = self.correr(ver=True)
        self.assertIn("sk-p...1234", texto)
        self.assertNotIn("sk-prueba-1234", texto)
        self.assertIn("base de datos (cifrada)", texto)
        self.assertIn(".env", texto)


class LlavesCifradasTests(TestCase):
    def test_si_no_hay_llave_en_la_base_se_usa_la_del_env(self):
        with override_settings(OPENAI_API_KEY="sk-del-env"):
            self.assertEqual(llaves.obtener("openai"), "sk-del-env")
            self.assertEqual(llaves.origen("openai"), ".env")

    def test_la_de_la_base_de_datos_gana_sobre_la_del_env(self):
        llaves.guardar("openai", "sk-de-la-base")
        with override_settings(OPENAI_API_KEY="sk-del-env"):
            self.assertEqual(llaves.obtener("openai"), "sk-de-la-base")

    def test_sin_ninguna_llave_regresa_vacio(self):
        with override_settings(GEMINI_API_KEY=""):
            self.assertEqual(llaves.obtener("gemini"), "")
            self.assertEqual(llaves.origen("gemini"), "sin configurar")

    def test_si_cambia_la_secret_key_la_llave_no_se_puede_leer_y_no_truena(self):
        llaves.guardar("openai", "sk-de-la-base")
        with override_settings(SECRET_KEY="otra-llave-distinta", OPENAI_API_KEY=""):
            self.assertEqual(llaves.obtener("openai"), "")

    def test_un_proveedor_desconocido_se_rechaza(self):
        with self.assertRaises(ValueError):
            llaves.guardar("otro", "x")

    def test_el_asistente_usa_la_llave_guardada_en_la_base_de_datos(self):
        from avi.clients import modelos_en_orden
        with override_settings(OPENAI_API_KEY="", GEMINI_API_KEY=""):
            self.assertEqual(modelos_en_orden(), [])
            llaves.guardar("gemini", "AIza-de-la-base")
            self.assertEqual(modelos_en_orden(), ["gemini"])



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

    def test_importa_csv_de_ventas_articulos_y_crea_productos_pendientes(self):
        ventas = self.archivo(
            "ventas_articulos.csv",
            "fecha,ticket_id,producto,cantidad,precio,total\n"
            "2025-05-30 23:09:08,85,Agua 1lt,12,15,180\n"
            "2025-05-30 23:14:40,85,Agua 1lt,1,16,16\n"
            "2025-06-01 21:34:52,97,Otro producto,2,25,50\n",
        )

        self.importar(ventas=ventas, productos_desde_ventas=True)

        producto = Producto.objects.get(negocio=self.negocio, nombre="Agua 1lt")
        self.assertEqual(Producto.objects.filter(negocio=self.negocio).count(), 2)
        self.assertEqual(producto.precio_venta, Decimal("16.00"))
        self.assertEqual(producto.cantidad_actual, Decimal("0"))
        self.assertTrue(producto.pendiente_validacion)
        self.assertEqual(Venta.objects.filter(negocio=self.negocio).count(), 2)
        self.assertEqual(ItemVenta.objects.filter(venta__negocio=self.negocio).count(), 3)

    def test_productos_desde_ventas_requiere_archivo_de_ventas(self):
        with self.assertRaises(CommandError):
            self.importar(productos_desde_ventas=True)

    def test_omite_renglon_con_precio_fuera_del_limite_decimal(self):
        ventas = self.archivo(
            "precio_fuera_rango.csv",
            "fecha,folio,producto,cantidad,precio_unitario\n"
            "2026-10-01 09:15:00,A1,Coca 600,1,20\n"
            "2026-10-01 09:15:00,A1,Coca 600,1,10000000000\n"
            "2026-10-01 09:15:00,A1,Coca 600,0.0001,20\n",
        )

        self.importar(productos=self.archivo("productos.csv", self.PRODUCTOS), ventas=ventas)

        venta = Venta.objects.get(negocio=self.negocio)
        self.assertEqual(venta.total, Decimal("20.00"))
        self.assertEqual(venta.items.count(), 1)

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

    def test_una_venta_hecha_sin_internet_deja_su_salida_en_el_kardex(self):
        from inventario.models import MovimientoInventario
        self.enviar(self.venta(cantidad=3))
        movimiento = MovimientoInventario.objects.get()
        self.assertEqual((movimiento.tipo, movimiento.cantidad, movimiento.existencia_resultante), ("VENTA", Decimal("-3"), Decimal("7")))
        self.assertIn("sin internet", movimiento.motivo)

    def test_una_venta_hecha_sin_internet_guarda_el_costo_de_la_compra_mas_vieja(self):
        from inventario.compras import agregar_existencias, registrar_alta
        registrar_alta(self.coca)
        agregar_existencias(self.coca, 10, costo="17")
        self.enviar(self.venta(cantidad=4))
        self.assertEqual(Venta.objects.get().items.get().costo_unitario, Decimal("15"))

    def test_una_pieza_con_decimales_se_rechaza(self):
        resultado = self.enviar(self.venta(cantidad=1.5))[0]
        self.assertTrue(resultado["definitivo"])
        self.assertEqual(Venta.objects.count(), 0)

    def test_alta_de_un_producto_sin_internet(self):
        resultado = self.enviar({
            "uuid": "alta1", "tipo": "alta_producto",
            "datos": {
                "nombre": "Pepsi 600", "costo": "13", "precio_venta": "18", "cantidad_actual": "12",
                "cantidad_minima": "4", "a_granel": False, "descripcion": "Refresco de cola",
                "categoria": Categoria.objects.get_or_create(nombre="Bebidas")[0].pk,
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
