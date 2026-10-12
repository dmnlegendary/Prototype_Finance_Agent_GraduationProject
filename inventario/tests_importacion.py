from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from core.testing import crear_negocio, crear_producto
from finanzas.models import GastoOperativo
from ventas.models import ItemVenta, Venta

from . import importacion
from .models import Categoria, Producto

ARCHIVO_BUENO = (
    "producto,cantidad,precio_compra,precio_venta,categoria,codigo_barras,a_granel\n"
    "Coca 600,24,13.50,18,Bebidas,7501055300075,no\n"
    "Frijol negro,10,28,38,Abarrotes,,si\n"
).encode("utf-8")


class LecturaDelCsvTests(SimpleTestCase):
    def test_un_archivo_correcto_se_lee_completo(self):
        filas, errores = importacion.leer_csv(ARCHIVO_BUENO)
        self.assertEqual(errores, [])
        self.assertEqual([f["producto"] for f in filas], ["Coca 600", "Frijol negro"])
        self.assertTrue(filas[1]["a_granel"])
        self.assertFalse(filas[0]["a_granel"])

    def test_si_falta_una_columna_obligatoria_no_se_carga_nada(self):
        filas, errores = importacion.leer_csv(b"producto,cantidad,precio_venta\nCoca,5,18\n")
        self.assertEqual(filas, [])
        self.assertIn("precio_compra", errores[0])
        self.assertIn("No se cargó nada", errores[0])

    def test_acepta_otros_nombres_de_las_columnas_sin_acentos_ni_mayusculas(self):
        archivo = "Producto;Cantidad;Precio de compra;Precio de venta\nCoca;5;13,5;18\n".encode("utf-8")
        filas, errores = importacion.leer_csv(archivo)
        self.assertEqual(errores, [])
        self.assertEqual(filas[0]["precio_compra"], "135")  # la coma se toma como separador de miles

    def test_un_precio_con_signo_de_pesos_y_comas_se_entiende(self):
        archivo = b'producto,cantidad,precio_compra,precio_venta\nTV,2,"$1,500.50","$2,000"\n'
        filas, errores = importacion.leer_csv(archivo)
        self.assertEqual(errores, [])
        self.assertEqual(filas[0]["precio_compra"], "1500.50")

    def test_un_renglon_malo_bloquea_todo_el_archivo(self):
        archivo = (
            "producto,cantidad,precio_compra,precio_venta\n"
            "Coca,5,13,18\n"
            ",5,13,18\n"
            "Pepsi,abc,13,18\n"
            "Sprite,5,13,0\n"
        ).encode("utf-8")
        filas, errores = importacion.leer_csv(archivo)
        self.assertEqual(len(errores), 3)
        self.assertIn("Fila 3", errores[0])
        self.assertIn("cantidad", errores[1])
        self.assertIn("precio de venta", errores[2])

    def test_un_producto_repetido_en_el_archivo_es_un_error(self):
        archivo = b"producto,cantidad,precio_compra,precio_venta\nCoca,5,13,18\ncoca,2,13,18\n"
        _, errores = importacion.leer_csv(archivo)
        self.assertIn("repite", errores[0])

    def test_archivos_vacios_o_sin_productos(self):
        self.assertTrue(importacion.leer_csv(b"")[1])
        self.assertTrue(importacion.leer_csv(b"producto,cantidad,precio_compra,precio_venta\n")[1])

    def test_lee_archivos_guardados_por_excel_con_acentos(self):
        archivo = "producto,cantidad,precio_compra,precio_venta\nJabón Zote,5,10,14\n".encode("cp1252")
        filas, _ = importacion.leer_csv(archivo)
        self.assertEqual(filas[0]["producto"], "Jabón Zote")


class ClasificacionDeRenglonesTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()
        crear_producto(self.negocio, nombre="Jabón Zote")
        crear_producto(self.negocio, nombre="Coca-Cola 600ml")

    def clasificar(self, nombre, codigo=""):
        fila = {
            "fila": 2, "producto": nombre, "cantidad": "5", "precio_compra": "10", "precio_venta": "14",
            "categoria": "", "codigo_barras": codigo, "a_granel": False,
        }
        return importacion.clasificar(self.negocio, [fila])[0]

    def test_un_nombre_igual_ya_existe_aunque_cambien_acentos_y_mayusculas(self):
        fila = self.clasificar("jabon zote")
        self.assertEqual(fila["tipo"], "existente")
        self.assertEqual(fila["coincide_nombre"], "Jabón Zote")

    def test_un_nombre_parecido_se_ofrece_para_que_el_usuario_elija(self):
        fila = self.clasificar("jbon")
        self.assertEqual(fila["tipo"], "parecido")
        self.assertEqual(fila["candidatos"][0]["nombre"], "Jabón Zote")

    def test_algo_que_no_se_parece_a_nada_es_nuevo(self):
        self.assertEqual(self.clasificar("Escoba de mijo")["tipo"], "nuevo")

    def test_el_codigo_de_barras_identifica_al_producto(self):
        Producto.objects.filter(nombre="Coca-Cola 600ml").update(codigo_barras="750")
        fila = self.clasificar("Refresco de cola", codigo="750")
        self.assertEqual(fila["tipo"], "existente")

    def test_un_producto_no_encontrado_que_se_vendio_se_reconoce(self):
        Producto.objects.create(
            negocio=self.negocio, nombre="Bolsa de hielo", costo=0, precio_venta=20, activo=False, pendiente_validacion=True,
        )
        self.assertEqual(self.clasificar("Bolsa de hielo")["tipo"], "pendiente")


class ImportarDesdeLaPantallaTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.coca = crear_producto(self.negocio, nombre="Coca 600", cantidad="10", costo="15", precio="25")
        self.client.force_login(self.usuario)

    def subir(self, contenido, nombre="productos.csv"):
        return self.client.post(
            reverse("inventario:importar"), {"archivo": SimpleUploadedFile(nombre, contenido, content_type="text/csv")},
        )

    def confirmar(self, **decisiones):
        return self.client.post(reverse("inventario:importar_revisar"), decisiones)

    def test_las_pantallas_abren_y_la_plantilla_se_descarga(self):
        self.assertEqual(self.client.get(reverse("inventario:importar")).status_code, 200)
        plantilla = self.client.get(reverse("inventario:importar_plantilla"))
        self.assertIn("producto,cantidad,precio_compra,precio_venta", plantilla.content.decode())

    def test_un_archivo_sin_las_columnas_no_toca_la_base_de_datos(self):
        respuesta = self.subir(b"nombre,color\nCoca,rojo\n")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No se pudo cargar el archivo")
        self.assertEqual(Producto.objects.count(), 1)
        self.assertEqual(GastoOperativo.objects.count(), 0)

    def test_subir_el_archivo_solo_revisa_y_no_guarda_nada(self):
        respuesta = self.subir(ARCHIVO_BUENO)
        self.assertRedirects(respuesta, reverse("inventario:importar_revisar"))
        self.assertEqual(Producto.objects.count(), 1)
        self.assertEqual(GastoOperativo.objects.count(), 0)

    def test_los_productos_nuevos_solo_se_agregan_si_el_usuario_confirma(self):
        self.subir(ARCHIVO_BUENO)
        self.confirmar()  # no marcó ninguno
        self.assertEqual(Producto.objects.count(), 1)

        self.subir(ARCHIVO_BUENO)
        self.confirmar(accion_3="agregar")  # solo el frijol (fila 3)
        frijol = Producto.objects.get(nombre="Frijol negro")
        self.assertTrue(frijol.a_granel)
        self.assertEqual(frijol.cantidad_actual, Decimal("10"))
        self.assertEqual(frijol.costo, Decimal("28.00"))
        self.assertEqual(Producto.objects.count(), 2)

    def test_los_que_ya_existen_suman_piezas_y_actualizan_precios(self):
        self.subir(b"producto,cantidad,precio_compra,precio_venta\ncoca 600,24,13.50,18\n")
        self.confirmar()

        self.coca.refresh_from_db()
        self.assertEqual(self.coca.cantidad_actual, Decimal("34"))
        self.assertEqual(self.coca.costo, Decimal("13.50"))
        self.assertEqual(self.coca.precio_venta, Decimal("18.00"))

    def test_la_compra_se_registra_como_un_solo_gasto_de_mercancia(self):
        self.subir(
            b"producto,cantidad,precio_compra,precio_venta\ncoca 600,10,10,18\nEscoba,5,20,35\n",
        )
        self.confirmar(accion_3="agregar")

        compra = GastoOperativo.objects.get()
        self.assertEqual(compra.tipo, GastoOperativo.Tipo.MERCANCIA)
        self.assertEqual(compra.monto, Decimal("200.00"))  # 10 x 10 + 5 x 20

    def test_un_producto_parecido_puede_tratarse_como_uno_existente(self):
        self.subir(b"producto,cantidad,precio_compra,precio_venta\nCoca 6,5,13,18\n")
        self.confirmar(**{"accion_2": f"usar:{self.coca.pk}"})

        self.coca.refresh_from_db()
        self.assertEqual(self.coca.cantidad_actual, Decimal("15"))

    def test_un_producto_parecido_tambien_puede_agregarse_como_nuevo_o_dejarse_fuera(self):
        self.subir(b"producto,cantidad,precio_compra,precio_venta\nCoca 6,5,13,18\n")
        self.confirmar(accion_2="agregar")
        self.assertTrue(Producto.objects.filter(nombre="Coca 6").exists())

        self.subir(b"producto,cantidad,precio_compra,precio_venta\nCoca 7,5,13,18\n")
        self.confirmar(accion_2="omitir")
        self.assertFalse(Producto.objects.filter(nombre="Coca 7").exists())

    def test_un_producto_no_encontrado_se_completa_con_los_datos_del_archivo(self):
        pendiente = Producto.objects.create(
            negocio=self.negocio, nombre="Bolsa de hielo", costo=0, precio_venta=20, activo=False, pendiente_validacion=True,
        )
        venta = Venta.objects.create(negocio=self.negocio, folio=1, estado=Venta.Estado.COBRADA)
        item = ItemVenta.objects.create(venta=venta, producto=pendiente, cantidad=Decimal("2"), precio_unitario=Decimal("20"))
        self.assertEqual(item.costo_unitario, Decimal("0"))

        self.subir(b"producto,cantidad,precio_compra,precio_venta\nBolsa de hielo,10,8,20\n")
        self.confirmar()

        pendiente.refresh_from_db()
        item.refresh_from_db()
        self.assertTrue(pendiente.activo)
        self.assertFalse(pendiente.pendiente_validacion)
        self.assertEqual(pendiente.cantidad_actual, Decimal("10"))
        self.assertEqual(item.costo_unitario, Decimal("8.00"))  # las ventas viejas completan su costo

    def test_cantidad_con_decimales_en_un_producto_por_pieza_se_omite_con_aviso(self):
        self.subir(b"producto,cantidad,precio_compra,precio_venta\ncoca 600,2.5,13,18\n")
        self.confirmar()

        self.coca.refresh_from_db()
        self.assertEqual(self.coca.cantidad_actual, Decimal("10"))
        self.assertEqual(self.coca.precio_venta, Decimal("25.00"))

    def test_cancelar_borra_la_importacion_en_proceso(self):
        self.subir(ARCHIVO_BUENO)
        self.client.get(reverse("inventario:importar_cancelar"))
        respuesta = self.client.get(reverse("inventario:importar_revisar"))
        self.assertRedirects(respuesta, reverse("inventario:importar"))

    def test_las_categorias_nuevas_del_archivo_se_crean(self):
        self.subir(ARCHIVO_BUENO)
        self.confirmar(accion_3="agregar")
        self.assertTrue(Categoria.objects.filter(nombre="Abarrotes").exists())

    def test_la_pantalla_de_revision_muestra_los_tres_grupos(self):
        self.subir(
            b"producto,cantidad,precio_compra,precio_venta\n"
            b"coca 600,5,13,18\n"
            b"Coca 6,5,13,18\n"
            b"Escoba de mijo,2,20,35\n"
        )
        respuesta = self.client.get(reverse("inventario:importar_revisar"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ya están en tu inventario (1)")
        self.assertContains(respuesta, "Se parecen a productos que ya tienes (1)")
        self.assertContains(respuesta, "No están en tu inventario (1)")
        self.assertContains(respuesta, "Todavía no se guardó nada")
