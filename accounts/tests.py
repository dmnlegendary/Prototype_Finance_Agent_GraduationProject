from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from core.testing import CLAVE, crear_negocio, crear_producto
from ventas.models import ItemVenta, Venta
from finanzas.models import GastoOperativo
from inventario.alertas import conteo_alertas
from inventario.models import Categoria, Producto, ProductoCatalogo

from .models import Negocio, Usuario


class InicioDeSesionTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()

    def iniciar_sesion(self, usuario, clave):
        return self.client.post(reverse("accounts:login"), {"username": usuario, "password": clave})

    def test_entra_con_el_correo(self):
        self.iniciar_sesion("tendero@ejemplo.com", CLAVE)
        self.assertIn("_auth_user_id", self.client.session)

    def test_el_correo_no_distingue_mayusculas(self):
        self.iniciar_sesion("TENDERO@EJEMPLO.COM", CLAVE)
        self.assertIn("_auth_user_id", self.client.session)

    def test_entra_con_el_telefono(self):
        self.iniciar_sesion("5512345678", CLAVE)
        self.assertIn("_auth_user_id", self.client.session)

    def test_contrasena_incorrecta_no_entra(self):
        self.iniciar_sesion("tendero@ejemplo.com", "otra-clave")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_las_pantallas_del_sistema_piden_sesion(self):
        respuesta = self.client.get(reverse("ventas:punto_de_venta"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn(reverse("accounts:login"), respuesta.url)


class RegistroTests(TestCase):
    def datos(self, **cambios):
        datos = {
            "nombre_completo": "Raúl Martínez", "telefono": "5511112222",
            "email": "raul@ejemplo.com", "password": "Tiend1ta-Segura-2026",
        }
        datos.update(cambios)
        return datos

    def test_registro_correcto_crea_la_cuenta(self):
        respuesta = self.client.post(reverse("accounts:registro"), self.datos())
        self.assertEqual(Usuario.objects.count(), 1)
        self.assertRedirects(respuesta, reverse("accounts:datos_negocio"))

    def test_el_correo_es_obligatorio(self):
        self.client.post(reverse("accounts:registro"), self.datos(email=""))
        self.assertEqual(Usuario.objects.count(), 0)

    def test_no_se_repite_el_correo(self):
        crear_negocio(telefono="5599999999", email="raul@ejemplo.com")
        self.client.post(reverse("accounts:registro"), self.datos())
        self.assertEqual(Usuario.objects.count(), 1)

    def test_no_se_repite_el_telefono(self):
        crear_negocio(telefono="5511112222", email="otro@ejemplo.com")
        self.client.post(reverse("accounts:registro"), self.datos())
        self.assertEqual(Usuario.objects.count(), 1)


class RecuperarContrasenaTests(TestCase):
    def test_se_manda_el_enlace_de_recuperacion(self):
        crear_negocio()
        self.client.post(reverse("accounts:password_reset"), {"email": "tendero@ejemplo.com"})

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("password-reset/confirmar", mail.outbox[0].body)

    def test_con_un_correo_que_no_existe_no_se_manda_nada(self):
        self.client.post(reverse("accounts:password_reset"), {"email": "nadie@ejemplo.com"})
        self.assertEqual(len(mail.outbox), 0)


class EliminarCuentaTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        producto = crear_producto(self.negocio)
        venta = Venta.objects.create(negocio=self.negocio, folio=1, estado=Venta.Estado.COBRADA)
        ItemVenta.objects.create(venta=venta, producto=producto, cantidad=Decimal("2"), precio_unitario=Decimal("25"))
        self.client.force_login(self.usuario)

    def test_con_la_contrasena_correcta_se_borra_todo(self):
        self.client.post(reverse("accounts:eliminar_cuenta"), {"password": CLAVE})

        self.assertEqual(Usuario.objects.count(), 0)
        self.assertEqual(Producto.objects.count(), 0)
        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(ItemVenta.objects.count(), 0)

    def test_con_la_contrasena_incorrecta_no_se_borra_nada(self):
        self.client.post(reverse("accounts:eliminar_cuenta"), {"password": "otra-clave"})

        self.assertEqual(Usuario.objects.count(), 1)
        self.assertEqual(Producto.objects.count(), 1)
        self.assertEqual(ItemVenta.objects.count(), 1)


class DatosDelNegocioTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username="5512345678", password=CLAVE, email="t@ejemplo.com", telefono="5512345678", nombre_completo="Tendero",
        )
        self.client.force_login(self.usuario)

    def datos(self, **cambios):
        datos = {
            "nombre_tienda": "Abarrotes Prueba", "alcaldia": "TLALPAN", "alcaldia_otra": "",
            "anios_operacion": "DE_3_A_10", "regimen_resico": "on", "rfc": "",
        }
        datos.update(cambios)
        return datos

    def test_la_tienda_nueva_arranca_con_proveedores_y_categorias_de_gastos(self):
        from finanzas.models import CategoriaGasto
        from inventario.models import Proveedor
        self.client.post(reverse("accounts:datos_negocio"), self.datos())
        negocio = self.usuario.negocio
        self.assertGreaterEqual(Proveedor.objects.filter(negocio=negocio).count(), 20)
        self.assertEqual(CategoriaGasto.objects.get(negocio=negocio, nombre="Luz").tipo, "FIJO")
        self.assertEqual(CategoriaGasto.objects.get(negocio=negocio, nombre="Bolsas y empaques").tipo, "VARIABLE")

    def test_al_editar_los_datos_de_la_tienda_no_se_duplican_proveedores(self):
        from inventario.models import Proveedor
        self.client.post(reverse("accounts:datos_negocio"), self.datos())
        antes = Proveedor.objects.count()
        self.client.post(reverse("accounts:datos_negocio"), self.datos(nombre_tienda="Otro nombre"))
        self.assertEqual(Proveedor.objects.count(), antes)

    def test_con_una_alcaldia_de_la_lista_el_ticket_dice_cdmx(self):
        self.client.post(reverse("accounts:datos_negocio"), self.datos())
        self.assertEqual(self.usuario.negocio.ubicacion, "Tlalpan, CDMX")

    def test_si_elige_otra_hay_que_escribir_el_nombre_del_lugar(self):
        respuesta = self.client.post(reverse("accounts:datos_negocio"), self.datos(alcaldia="OTRA"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Negocio.objects.filter(usuario=self.usuario).exists())

    def test_el_lugar_escrito_es_el_que_sale_en_el_ticket_y_sin_decir_cdmx(self):
        self.client.post(
            reverse("accounts:datos_negocio"), self.datos(alcaldia="OTRA", alcaldia_otra="Naucalpan, Estado de México"),
        )
        self.assertEqual(self.usuario.negocio.ubicacion, "Naucalpan, Estado de México")

    def test_si_cambia_a_una_alcaldia_de_la_lista_se_borra_el_lugar_escrito(self):
        self.client.post(reverse("accounts:datos_negocio"), self.datos(alcaldia="OTRA", alcaldia_otra="Naucalpan"))
        self.client.post(reverse("accounts:datos_negocio"), self.datos(alcaldia="COYOACAN"))
        self.usuario.negocio.refresh_from_db()
        self.assertEqual(self.usuario.negocio.alcaldia_otra, "")
        self.assertEqual(self.usuario.negocio.ubicacion, "Coyoacán, CDMX")


class ProductosPrecargadosTests(TestCase):
    """Paso 3 del registro: ahora se piden las piezas y los precios de cada producto elegido."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)
        categoria = Categoria.objects.create(nombre="Bebidas")
        self.coca = ProductoCatalogo.objects.create(nombre="Coca-Cola 600ml", categoria=categoria, precio_sugerido=Decimal("18"))
        self.agua = ProductoCatalogo.objects.create(nombre="Agua Ciel", categoria=categoria, precio_sugerido=Decimal("12"))

    def enviar(self, **campos):
        return self.client.post(reverse("accounts:productos_precargados"), campos)

    def test_se_crean_con_sus_piezas_costo_y_precio(self):
        respuesta = self.enviar(
            productos_catalogo=[self.coca.pk, self.agua.pk],
            **{
                f"piezas_{self.coca.pk}": "24", f"costo_{self.coca.pk}": "13.5", f"precio_{self.coca.pk}": "18",
                f"piezas_{self.agua.pk}": "10", f"costo_{self.agua.pk}": "8", f"precio_{self.agua.pk}": "12",
            },
        )

        self.assertRedirects(respuesta, reverse("ventas:punto_de_venta"), fetch_redirect_response=False)
        coca = Producto.objects.get(nombre="Coca-Cola 600ml")
        self.assertEqual(coca.cantidad_actual, Decimal("24"))
        self.assertEqual(coca.costo, Decimal("13.50"))
        self.assertNotEqual(coca.costo, coca.precio_venta)

    def test_el_inventario_inicial_se_registra_como_una_compra_de_mercancia(self):
        self.enviar(
            productos_catalogo=[self.coca.pk],
            **{f"piezas_{self.coca.pk}": "24", f"costo_{self.coca.pk}": "13.5", f"precio_{self.coca.pk}": "18"},
        )
        compra = GastoOperativo.objects.get()
        self.assertEqual(compra.tipo, GastoOperativo.Tipo.MERCANCIA)
        self.assertEqual(compra.monto, Decimal("324.00"))

    def test_si_faltan_las_piezas_no_se_crea_nada_y_se_avisa(self):
        respuesta = self.enviar(
            productos_catalogo=[self.coca.pk], **{f"costo_{self.coca.pk}": "13", f"precio_{self.coca.pk}": "18"},
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "cuántas piezas tienes")
        self.assertEqual(Producto.objects.filter(negocio=self.negocio).count(), 0)

    def test_si_falta_el_costo_se_avisa(self):
        respuesta = self.enviar(
            productos_catalogo=[self.coca.pk], **{f"piezas_{self.coca.pk}": "5", f"precio_{self.coca.pk}": "18"},
        )
        self.assertContains(respuesta, "cuánto te costó")

    def test_las_piezas_deben_ser_enteras(self):
        respuesta = self.enviar(
            productos_catalogo=[self.coca.pk],
            **{f"piezas_{self.coca.pk}": "2.5", f"costo_{self.coca.pk}": "13", f"precio_{self.coca.pk}": "18"},
        )
        self.assertContains(respuesta, "número entero")
        self.assertEqual(Producto.objects.filter(negocio=self.negocio).count(), 0)

    def test_se_puede_continuar_sin_elegir_productos(self):
        respuesta = self.enviar()
        self.assertRedirects(respuesta, reverse("ventas:punto_de_venta"), fetch_redirect_response=False)

    def test_los_productos_nuevos_no_quedan_todos_en_rojo_por_costo_igual_al_precio(self):
        self.enviar(
            productos_catalogo=[self.coca.pk],
            **{f"piezas_{self.coca.pk}": "24", f"costo_{self.coca.pk}": "13.5", f"precio_{self.coca.pk}": "18"},
        )
        # con 24 piezas y mínimo 0 no hay alerta
        self.assertEqual(conteo_alertas(self.negocio)["total"], 0)


class VideoDeBienvenidaTests(TestCase):
    """RF-S05: el video de presentación se muestra solo la primera vez que alguien entra."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)

    def test_sin_enlace_configurado_no_se_muestra_nada(self):
        from django.test import override_settings
        with override_settings(VIDEO_INTRODUCTORIO_URL=""):
            self.assertNotContains(self.client.get(reverse("ventas:punto_de_venta")), "modal-video-bienvenida")

    def test_la_primera_vez_se_muestra_el_video(self):
        from django.test import override_settings
        with override_settings(VIDEO_INTRODUCTORIO_URL="https://www.youtube.com/embed/abc123"):
            respuesta = self.client.get(reverse("ventas:punto_de_venta"))
        self.assertContains(respuesta, "modal-video-bienvenida")
        self.assertContains(respuesta, "https://www.youtube.com/embed/abc123")

    def test_despues_de_verlo_ya_no_vuelve_a_salir(self):
        from django.test import override_settings
        self.assertEqual(self.client.post(reverse("accounts:video_visto")).status_code, 200)
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.video_visto)
        with override_settings(VIDEO_INTRODUCTORIO_URL="https://www.youtube.com/embed/abc123"):
            self.assertNotContains(self.client.get(reverse("ventas:punto_de_venta")), "modal-video-bienvenida")

    def test_marcar_el_video_como_visto_pide_post_y_sesion(self):
        self.assertEqual(self.client.get(reverse("accounts:video_visto")).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.post(reverse("accounts:video_visto")).status_code, 302)


class PreferenciasDelNegocioTests(TestCase):
    def test_las_preferencias_se_guardan_y_se_leen(self):
        _, negocio = crear_negocio()
        self.assertEqual(negocio.preferencia("margen_deseado", 30), 30)
        negocio.guardar_preferencias(margen_deseado="35")
        negocio.refresh_from_db()
        self.assertEqual(negocio.preferencia("margen_deseado"), "35")

    def test_guardar_lo_mismo_no_escribe_otra_vez(self):
        _, negocio = crear_negocio()
        negocio.guardar_preferencias(meses_reportes=3)
        antes = Negocio.objects.get(pk=negocio.pk).actualizado_en
        negocio.guardar_preferencias(meses_reportes=3)
        self.assertEqual(Negocio.objects.get(pk=negocio.pk).actualizado_en, antes)
