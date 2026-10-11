from decimal import Decimal

from django.core import mail
from django.test import TestCase
from django.urls import reverse

from core.testing import CLAVE, crear_negocio, crear_producto
from ventas.models import ItemVenta, Venta
from inventario.models import Producto

from .models import Usuario


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
