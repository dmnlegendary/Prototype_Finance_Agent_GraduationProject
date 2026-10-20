import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core import cache_negocio
from core.testing import crear_negocio, crear_producto
from finanzas.models import GastoOperativo
from inventario.models import Categoria, HistorialModificacionProducto, Producto, Proveedor
from ventas.models import ItemVenta, Venta

from . import services
from .clients import (
    MENSAJE_SIN_LLAVE, SinLlaveError, con_reintentos, generar_texto, mensaje_de_error, modelos_en_orden, preguntar_ia,
)
from .models import ExplicacionIA, HistorialConversacion, ResumenDiario


@override_settings(OPENAI_API_KEY="llave-de-prueba", GEMINI_API_KEY="llave-de-prueba")
class ChatDelAsistenteTests(TestCase):
    """Las llamadas a ChatGPT/Gemini se simulan para no gastar saldo ni necesitar internet."""

    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)

    def mandar(self, mensaje):
        return self.client.post(
            reverse("avi:chat"),
            data=json.dumps({"mensaje": mensaje}),
            content_type="application/json",
        )

    @patch("avi.views.preguntar_ia", return_value=("Listo, agregué 2 pepsis.", ["agregar_al_carrito"]))
    def test_guarda_el_historial_y_pide_refrescar_la_pantalla(self, _llamada):
        respuesta = self.mandar("agrega 2 pepsis").json()

        self.assertEqual(respuesta["respuesta"], "Listo, agregué 2 pepsis.")
        self.assertTrue(respuesta["refrescar"])
        self.assertEqual(HistorialConversacion.objects.count(), 2)

    @patch("avi.views.preguntar_ia", return_value=("Hoy vendiste poco.", ["consultar_ventas_hoy"]))
    def test_una_consulta_no_refresca_la_pantalla(self, _llamada):
        respuesta = self.mandar("¿cuánto vendí hoy?").json()
        self.assertFalse(respuesta["refrescar"])

    def test_un_mensaje_vacio_no_llama_al_modelo(self):
        with patch("avi.views.preguntar_ia") as llamada:
            respuesta = self.mandar("   ").json()
        self.assertEqual(llamada.call_count, 0)
        self.assertIn("Escribe algo", respuesta["respuesta"])

    @patch("avi.views.generar_texto", return_value="Resumen de ayer")
    def test_el_resumen_se_pide_a_la_ia_una_sola_vez_por_dia(self, llamada):
        self.client.get(reverse("avi:resumen_diario"))
        self.client.get(reverse("avi:resumen_diario"))

        self.assertEqual(llamada.call_count, 1)
        self.assertEqual(ResumenDiario.objects.count(), 1)

    @patch("avi.views.generar_texto", side_effect=SinLlaveError("sin llave"))
    def test_si_no_hay_llave_el_resumen_no_se_guarda(self, _llamada):
        respuesta = self.client.get(reverse("avi:resumen_diario")).json()
        self.assertEqual(respuesta["respuesta"], MENSAJE_SIN_LLAVE)
        self.assertEqual(ResumenDiario.objects.count(), 0)

    @patch("avi.views.generar_texto", return_value="Así van tus números")
    def test_la_explicacion_se_reutiliza_si_los_numeros_no_cambiaron(self, llamada):
        self.client.get(reverse("avi:explicar", args=["dashboard"]))
        segunda = self.client.get(reverse("avi:explicar", args=["dashboard"])).json()

        self.assertEqual(llamada.call_count, 1)
        self.assertTrue(segunda["guardada"])
        self.assertEqual(ExplicacionIA.objects.count(), 1)

    @patch("avi.views.generar_texto", return_value="Así van tus números")
    def test_la_explicacion_se_pide_de_nuevo_si_cambian_los_numeros(self, llamada):
        self.client.get(reverse("avi:explicar", args=["reportes"]))
        Venta.objects.create(negocio=self.negocio, folio=1, estado=Venta.Estado.COBRADA, total=Decimal("80"))
        self.client.get(reverse("avi:explicar", args=["reportes"]))

        self.assertEqual(llamada.call_count, 2)
        self.assertEqual(ExplicacionIA.objects.count(), 1)

    def test_un_tipo_de_explicacion_que_no_existe_da_404(self):
        self.assertEqual(self.client.get(reverse("avi:explicar", args=["otra-cosa"])).status_code, 404)

    @patch("avi.views.generar_texto", side_effect=SinLlaveError("sin llave"))
    def test_sin_llave_la_explicacion_no_se_guarda(self, _llamada):
        respuesta = self.client.get(reverse("avi:explicar", args=["dashboard"])).json()
        self.assertEqual(respuesta["respuesta"], MENSAJE_SIN_LLAVE)
        self.assertEqual(ExplicacionIA.objects.count(), 0)

    def test_el_chat_pide_sesion(self):
        self.client.logout()
        respuesta = self.mandar("hola")
        self.assertEqual(respuesta.status_code, 302)


class MemoriaDeLaConversacionTests(TestCase):
    def test_el_historial_reciente_va_del_mas_viejo_al_mas_nuevo(self):
        usuario, negocio = crear_negocio()
        for numero in range(12):
            HistorialConversacion.objects.create(
                negocio=negocio, usuario=usuario, rol=HistorialConversacion.Rol.USUARIO, mensaje=f"mensaje {numero}",
            )

        mensajes = services.historial_reciente(negocio)

        self.assertEqual(len(mensajes), 10)
        self.assertEqual(mensajes[0].mensaje, "mensaje 2")
        self.assertEqual(mensajes[-1].mensaje, "mensaje 11")


class FuncionesDelAsistenteTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()
        Venta.objects.create(negocio=self.negocio, folio=1)

    def test_si_hay_varios_productos_parecidos_pide_elegir(self):
        crear_producto(self.negocio, nombre="Coca 600")
        crear_producto(self.negocio, nombre="Coca 2L")

        resultado = services.agregar_al_carrito(self.negocio, "Coca")

        self.assertFalse(resultado["ok"])
        self.assertTrue(resultado["ambiguo"])
        self.assertEqual(ItemVenta.objects.count(), 0)

    def test_si_hay_un_solo_producto_lo_agrega(self):
        crear_producto(self.negocio, nombre="Pepsi 600")

        resultado = services.agregar_al_carrito(self.negocio, "pepsi", 2)

        self.assertTrue(resultado["ok"])
        self.assertEqual(ItemVenta.objects.get().cantidad, Decimal("2"))

    def test_si_no_existe_el_producto_avisa(self):
        resultado = services.agregar_al_carrito(self.negocio, "caviar")
        self.assertFalse(resultado["ok"])

    def test_una_funcion_que_no_existe_regresa_un_error(self):
        resultado = services.ejecutar_funcion("borrar_todo", {}, self.negocio)
        self.assertIn("error", resultado)

    def test_registrar_gasto_por_el_asistente(self):
        resultado = services.ejecutar_funcion(
            "registrar_gasto", {"concepto": "Luz", "monto": 450, "tipo": "FIJO"}, self.negocio,
        )
        self.assertTrue(resultado["ok"])


class ElegirModeloTests(SimpleTestCase):
    @override_settings(OPENAI_API_KEY="", GEMINI_API_KEY="llave-de-gemini")
    def test_si_solo_hay_llave_de_gemini_se_usa_solo_gemini(self):
        self.assertEqual(modelos_en_orden(), ["gemini"])

    @override_settings(OPENAI_API_KEY="llave-de-openai", GEMINI_API_KEY="llave-de-gemini")
    def test_si_hay_las_dos_primero_va_gemini_y_luego_chatgpt(self):
        self.assertEqual(modelos_en_orden(), ["gemini", "chatgpt"])

    @override_settings(OPENAI_API_KEY="llave-de-openai", GEMINI_API_KEY="")
    def test_si_solo_hay_llave_de_openai_se_usa_chatgpt(self):
        self.assertEqual(modelos_en_orden(), ["chatgpt"])

    @override_settings(OPENAI_API_KEY="", GEMINI_API_KEY="")
    def test_si_no_hay_ninguna_el_chat_avisa_que_falta_la_llave(self):
        self.assertEqual(preguntar_ia("hola", None), (MENSAJE_SIN_LLAVE, []))
        with self.assertRaises(SinLlaveError):
            generar_texto("hola")


@override_settings(OPENAI_API_KEY="llave-de-openai", GEMINI_API_KEY="llave-de-gemini")
class RespaldoEntreModelosTests(SimpleTestCase):
    @patch("avi.clients.preguntar_chatgpt")
    @patch("avi.clients.preguntar_gemini", return_value=("Contestó Gemini", []))
    def test_si_gemini_contesta_no_se_llama_a_chatgpt(self, _gemini, chatgpt):
        self.assertEqual(preguntar_ia("hola", None), ("Contestó Gemini", []))
        chatgpt.assert_not_called()

    @patch("avi.clients.preguntar_chatgpt", return_value=("Contestó ChatGPT", []))
    @patch("avi.clients.preguntar_gemini", side_effect=Exception("503 overloaded"))
    def test_si_gemini_falla_contesta_chatgpt(self, _gemini, _chatgpt):
        self.assertEqual(preguntar_ia("hola", None), ("Contestó ChatGPT", []))

    @patch("avi.clients.preguntar_chatgpt", side_effect=Exception("sin saldo"))
    @patch("avi.clients.preguntar_gemini", side_effect=Exception("503 overloaded"))
    def test_si_fallan_los_dos_se_avisa_del_ultimo_error(self, _gemini, _chatgpt):
        with self.assertRaisesMessage(Exception, "sin saldo"):
            preguntar_ia("hola", None)

    @patch("avi.clients.preguntar_chatgpt")
    def test_si_gemini_ya_hizo_una_accion_y_falla_no_se_repite_con_chatgpt(self, chatgpt):
        def gemini_a_medias(mensaje, negocio, pantalla, ejecutadas):
            ejecutadas.append("agregar_al_carrito")
            raise Exception("503 overloaded")

        with patch("avi.clients.preguntar_gemini", side_effect=gemini_a_medias):
            with self.assertRaises(Exception):
                preguntar_ia("agrega 2 cocas", None)
        chatgpt.assert_not_called()

    @patch("avi.clients._texto_con_chatgpt", return_value="Resumen de ChatGPT")
    @patch("avi.clients._texto_con_gemini", side_effect=Exception("429 quota"))
    def test_los_resumenes_tambien_pasan_a_chatgpt(self, _gemini, _chatgpt):
        self.assertEqual(generar_texto("explica"), "Resumen de ChatGPT")


class RespuestaDirectaTests(SimpleTestCase):
    def test_si_solo_hubo_acciones_se_contesta_sin_otra_llamada_a_la_ia(self):
        ejecuciones = [
            ("agregar_al_carrito", {"ok": True, "mensaje": "Agregué 2 pepsis."}),
            ("agregar_al_carrito", {"ok": True, "mensaje": "Agregué 1 coca."}),
        ]
        self.assertEqual(services.respuesta_directa(ejecuciones), "Agregué 2 pepsis. Agregué 1 coca.")

    def test_una_consulta_si_necesita_que_la_ia_la_explique(self):
        ejecuciones = [("consultar_ventas_hoy", {"total": 100, "numero_ventas": 3})]
        self.assertIsNone(services.respuesta_directa(ejecuciones))

    def test_si_se_mezclan_acciones_y_consultas_tambien_la_explica_la_ia(self):
        ejecuciones = [
            ("agregar_al_carrito", {"ok": True, "mensaje": "Agregué 2 pepsis."}),
            ("consultar_ventas_hoy", {"total": 100, "numero_ventas": 3}),
        ]
        self.assertIsNone(services.respuesta_directa(ejecuciones))

    def test_sin_funciones_no_hay_respuesta_directa(self):
        self.assertIsNone(services.respuesta_directa([]))


class BusquedaDelAsistenteTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()
        crear_producto(self.negocio, nombre="Jabón Zote")
        crear_producto(self.negocio, nombre="Coca-Cola 600ml")

    def nombres(self, texto):
        return [p["nombre"] for p in services.buscar_en_catalogo(self.negocio, texto)]

    def test_no_importan_los_acentos(self):
        self.assertEqual(self.nombres("jabon"), ["Jabón Zote"])

    def test_no_importa_el_orden_de_las_palabras(self):
        self.assertEqual(self.nombres("600ml coca"), ["Coca-Cola 600ml"])

    def test_el_plural_tambien_encuentra(self):
        self.assertEqual(self.nombres("cocas"), ["Coca-Cola 600ml"])

    def test_el_catalogo_en_cache_se_renueva_al_dar_de_alta_un_producto(self):
        self.assertEqual(self.nombres("pepsi"), [])
        crear_producto(self.negocio, nombre="Pepsi 600")
        self.assertEqual(self.nombres("pepsi"), ["Pepsi 600"])

    def test_el_catalogo_en_cache_se_renueva_al_dar_de_baja_un_producto(self):
        self.assertEqual(self.nombres("zote"), ["Jabón Zote"])
        producto = Producto.objects.get(negocio=self.negocio, nombre="Jabón Zote")
        producto.activo = False
        producto.save()
        self.assertEqual(self.nombres("zote"), [])

    def test_un_cambio_masivo_necesita_invalidar_el_cache_a_mano(self):
        self.assertEqual(self.nombres("zote"), ["Jabón Zote"])
        Producto.objects.filter(negocio=self.negocio, nombre="Jabón Zote").update(activo=False)
        # update() no dispara señales, por eso quien lo use debe avisar
        cache_negocio.invalidar(self.negocio.pk)
        self.assertEqual(self.nombres("zote"), [])


class FuncionesDeVentaDelAsistenteTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()
        self.coca = crear_producto(self.negocio, nombre="Coca 600", cantidad="10", minimo="2", ideal="20")
        self.pepsi = crear_producto(self.negocio, nombre="Pepsi 600", cantidad="10", minimo="2")

    def ejecutar(self, funcion, **argumentos):
        return services.ejecutar_funcion(funcion, argumentos, self.negocio)

    def test_agregar_crea_la_venta_si_todavia_no_hay(self):
        resultado = self.ejecutar("agregar_al_carrito", nombre_producto="coca", cantidad=3)
        self.assertTrue(resultado["ok"])
        self.assertEqual(ItemVenta.objects.get().cantidad, Decimal("3"))

    def test_avisa_si_se_agrega_mas_de_lo_que_hay(self):
        resultado = self.ejecutar("agregar_al_carrito", nombre_producto="coca", cantidad=15)
        self.assertIn("solo hay", resultado["mensaje"])

    def test_quitar_del_carrito(self):
        self.ejecutar("agregar_al_carrito", nombre_producto="coca")
        resultado = self.ejecutar("quitar_del_carrito", nombre_producto="coca")
        self.assertTrue(resultado["ok"])
        self.assertEqual(ItemVenta.objects.count(), 0)

    def test_quitar_algo_que_no_esta_en_el_carrito_avisa(self):
        self.ejecutar("agregar_al_carrito", nombre_producto="coca")
        self.assertFalse(self.ejecutar("quitar_del_carrito", nombre_producto="pepsi")["ok"])

    def test_cambiar_la_cantidad_del_carrito(self):
        self.ejecutar("agregar_al_carrito", nombre_producto="coca")
        self.ejecutar("cambiar_cantidad_carrito", nombre_producto="coca", cantidad=5)
        self.assertEqual(ItemVenta.objects.get().cantidad, Decimal("5"))
        self.assertEqual(Venta.objects.get().total, Decimal("125.00"))

    def test_cambiar_la_cantidad_a_cero_lo_quita(self):
        self.ejecutar("agregar_al_carrito", nombre_producto="coca")
        self.ejecutar("cambiar_cantidad_carrito", nombre_producto="coca", cantidad=0)
        self.assertEqual(ItemVenta.objects.count(), 0)

    def test_ver_el_carrito(self):
        self.ejecutar("agregar_al_carrito", nombre_producto="coca", cantidad=2)
        carrito = self.ejecutar("ver_carrito")
        self.assertEqual(carrito["total"], 50.0)
        self.assertEqual(carrito["productos"][0]["nombre"], "Coca 600")

    def test_cobrar_descuenta_el_inventario_y_avisa_del_semaforo(self):
        self.ejecutar("agregar_al_carrito", nombre_producto="pepsi", cantidad=9)
        resultado = self.ejecutar("cobrar_carrito")

        self.assertTrue(resultado["ok"])
        self.assertIn("mínimo", resultado["mensaje"])
        self.pepsi.refresh_from_db()
        self.assertEqual(self.pepsi.cantidad_actual, Decimal("1"))
        self.assertEqual(Venta.objects.get().estado, Venta.Estado.COBRADA)

    def test_cobrar_un_carrito_vacio_avisa(self):
        self.assertFalse(self.ejecutar("cobrar_carrito")["ok"])

    def test_cancelar_pide_confirmacion(self):
        self.ejecutar("agregar_al_carrito", nombre_producto="coca")
        sin_confirmar = self.ejecutar("cancelar_venta")
        self.assertTrue(sin_confirmar["requiere_confirmacion"])
        self.assertEqual(Venta.objects.get().estado, Venta.Estado.EN_CURSO)

        self.ejecutar("cancelar_venta", confirmar=True)
        self.assertEqual(Venta.objects.get().estado, Venta.Estado.CANCELADA)

    def test_producto_no_encontrado_queda_pendiente_de_validar(self):
        resultado = self.ejecutar("agregar_producto_no_encontrado", nombre="Bolsa de hielo", precio=20)
        self.assertTrue(resultado["ok"])
        pendiente = Producto.objects.get(nombre="Bolsa de hielo")
        self.assertTrue(pendiente.pendiente_validacion)
        self.assertFalse(pendiente.activo)
        self.assertEqual(ItemVenta.objects.get().producto, pendiente)

    def test_ventas_de_hoy_se_actualizan_despues_de_cobrar(self):
        self.assertEqual(self.ejecutar("consultar_ventas_hoy")["numero_ventas"], 0)
        self.ejecutar("agregar_al_carrito", nombre_producto="coca")
        self.ejecutar("cobrar_carrito")
        resultado = self.ejecutar("consultar_ventas_hoy")
        self.assertEqual(resultado["numero_ventas"], 1)
        self.assertEqual(resultado["total"], 25.0)

    def test_ultimas_ventas(self):
        self.ejecutar("agregar_al_carrito", nombre_producto="coca")
        self.ejecutar("cobrar_carrito")
        ventas = self.ejecutar("ultimas_ventas")["ventas"]
        self.assertEqual(len(ventas), 1)
        self.assertEqual(ventas[0]["total"], 25.0)


class FuncionesDeInventarioDelAsistenteTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()
        self.coca = crear_producto(self.negocio, nombre="Coca 600", cantidad="10", minimo="2")
        Categoria.objects.create(nombre="Bebidas")

    def ejecutar(self, funcion, **argumentos):
        return services.ejecutar_funcion(funcion, argumentos, self.negocio)

    def test_dar_de_alta_un_producto(self):
        resultado = self.ejecutar(
            "dar_de_alta_producto", nombre="Pepsi 600", precio_venta=18, costo=13, cantidad_actual=12,
            cantidad_minima=4, categoria="bebidas",
        )
        self.assertTrue(resultado["ok"])
        pepsi = Producto.objects.get(nombre="Pepsi 600")
        self.assertEqual(pepsi.precio_venta, Decimal("18.00"))
        self.assertEqual(pepsi.categoria.nombre, "Bebidas")
        self.assertTrue(pepsi.activo)

    def test_dar_de_alta_sin_costo_pregunta_el_costo(self):
        resultado = self.ejecutar("dar_de_alta_producto", nombre="Pepsi 600", precio_venta=18, costo=None)
        self.assertFalse(resultado["ok"])
        self.assertIn("cuesta", resultado["mensaje"])
        self.assertFalse(Producto.objects.filter(nombre="Pepsi 600").exists())

    def test_dar_de_alta_un_producto_repetido_avisa(self):
        resultado = self.ejecutar("dar_de_alta_producto", nombre="coca 600", precio_venta=25, costo=15)
        self.assertFalse(resultado["ok"])

    def test_dar_de_alta_con_una_categoria_que_no_existe_avisa(self):
        resultado = self.ejecutar(
            "dar_de_alta_producto", nombre="Pepsi 600", precio_venta=18, costo=13, categoria="Ferretería",
        )
        self.assertFalse(resultado["ok"])
        self.assertIn("Bebidas", resultado["mensaje"])

    def test_modificar_el_precio_guarda_el_historial(self):
        resultado = self.ejecutar("modificar_producto", nombre_producto="coca", precio_venta=30, motivo="Subió el proveedor")
        self.assertTrue(resultado["ok"])
        self.coca.refresh_from_db()
        self.assertEqual(self.coca.precio_venta, Decimal("30.00"))
        self.assertEqual(HistorialModificacionProducto.objects.get().motivo, "Subió el proveedor")

    def test_modificar_sin_decir_que_cambiar_avisa(self):
        self.assertFalse(self.ejecutar("modificar_producto", nombre_producto="coca")["ok"])

    def test_sumar_existencias(self):
        resultado = self.ejecutar("ajustar_existencias", nombre_producto="coca", cantidad=20, modo="sumar")
        self.assertTrue(resultado["ok"])
        self.coca.refresh_from_db()
        self.assertEqual(self.coca.cantidad_actual, Decimal("30"))

    def test_no_se_pueden_restar_mas_piezas_de_las_que_hay(self):
        resultado = self.ejecutar("ajustar_existencias", nombre_producto="coca", cantidad=50, modo="restar")
        self.assertFalse(resultado["ok"])
        self.coca.refresh_from_db()
        self.assertEqual(self.coca.cantidad_actual, Decimal("10"))

    def test_establecer_existencias_y_avisar_si_queda_en_rojo(self):
        resultado = self.ejecutar("ajustar_existencias", nombre_producto="coca", cantidad=1, modo="establecer")
        self.assertIn("mínimo", resultado["mensaje"])

    def test_dar_de_baja_pide_confirmacion(self):
        sin_confirmar = self.ejecutar("dar_de_baja_producto", nombre_producto="coca")
        self.assertTrue(sin_confirmar["requiere_confirmacion"])
        self.coca.refresh_from_db()
        self.assertTrue(self.coca.activo)

        self.ejecutar("dar_de_baja_producto", nombre_producto="coca", confirmar=True)
        self.coca.refresh_from_db()
        self.assertFalse(self.coca.activo)

    def test_crear_categoria_y_proveedor(self):
        self.assertTrue(self.ejecutar("crear_categoria", nombre="Panadería")["ok"])
        self.assertTrue(Categoria.objects.filter(nombre="Panadería").exists())

        self.assertTrue(self.ejecutar("alta_proveedor", nombre="FEMSA", telefono="5511223344")["ok"])
        self.assertFalse(self.ejecutar("alta_proveedor", nombre="femsa")["ok"])
        self.assertEqual(self.ejecutar("consultar_proveedores")["proveedores"][0]["nombre"], "FEMSA")

    def test_las_alertas_del_asistente_traen_el_color(self):
        crear_producto(self.negocio, nombre="Casi sin stock", cantidad="1", minimo="5")
        resultado = self.ejecutar("consultar_alertas_stock")
        self.assertEqual(resultado["conteo"]["rojo"], 1)
        self.assertEqual(resultado["productos"][0]["color"], "rojo")


class FuncionesDeFinanzasDelAsistenteTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()

    def ejecutar(self, funcion, **argumentos):
        return services.ejecutar_funcion(funcion, argumentos, self.negocio)

    def test_registrar_gasto_con_categoria(self):
        resultado = self.ejecutar("registrar_gasto", concepto="Recibo de luz", monto=450, tipo="fijo", categoria="Luz")
        self.assertTrue(resultado["ok"])
        gasto = GastoOperativo.objects.get()
        self.assertEqual(gasto.monto, Decimal("450.00"))
        self.assertEqual(gasto.tipo, "FIJO")
        self.assertEqual(gasto.categoria.nombre, "Luz")

    def test_el_gasto_lleva_el_mes_que_dice_el_tendero(self):
        resultado = self.ejecutar("registrar_gasto", concepto="Luz", monto=450, tipo="FIJO", mes=9, anio=2026)
        self.assertTrue(resultado["ok"])
        self.assertIn("09/2026", resultado["mensaje"])
        self.assertEqual(GastoOperativo.objects.get().periodo.isoformat(), "2026-09-01")

    def test_sin_mes_el_gasto_es_de_este_mes(self):
        self.ejecutar("registrar_gasto", concepto="Luz", monto=450, tipo="FIJO")
        self.assertEqual(GastoOperativo.objects.get().periodo, timezone.localdate().replace(day=1))

    def test_un_mes_que_no_existe_no_registra_el_gasto(self):
        resultado = self.ejecutar("registrar_gasto", concepto="Luz", monto=450, tipo="FIJO", mes=13)
        self.assertFalse(resultado["ok"])
        self.assertEqual(GastoOperativo.objects.count(), 0)

    def test_un_gasto_sin_monto_valido_no_se_registra(self):
        self.assertFalse(self.ejecutar("registrar_gasto", concepto="Luz", monto=0, tipo="FIJO")["ok"])
        self.assertEqual(GastoOperativo.objects.count(), 0)

    def test_consultar_gastos_del_mes(self):
        self.ejecutar("registrar_gasto", concepto="Renta", monto=3000, tipo="FIJO")
        self.ejecutar("registrar_gasto", concepto="Bolsas", monto=200, tipo="VARIABLE")
        resultado = self.ejecutar("consultar_gastos_mes")
        self.assertEqual(resultado["total_fijos"], 3000.0)
        self.assertEqual(resultado["total_variables"], 200.0)
        self.assertEqual(len(resultado["ultimos_gastos"]), 2)

    def test_sugerir_precio(self):
        crear_producto(self.negocio, nombre="Coca 600", costo="14")
        resultado = self.ejecutar("sugerir_precio", nombre_producto="coca", margen_deseado=30)
        self.assertEqual(resultado["precio_sugerido"], 20.0)

    def test_el_resumen_financiero_se_actualiza_despues_de_un_gasto(self):
        self.assertEqual(self.ejecutar("consultar_resumen_financiero")["gastos"], 0.0)
        self.ejecutar("registrar_gasto", concepto="Renta", monto=3000, tipo="FIJO")
        self.assertEqual(self.ejecutar("consultar_resumen_financiero")["gastos"], 3000.0)


class ContextoDelAsistenteTests(TestCase):
    def test_el_contexto_resume_la_tienda_y_se_renueva(self):
        _, negocio = crear_negocio()
        crear_producto(negocio, nombre="Coca 600", cantidad="1", minimo="5")

        contexto = services.contexto_negocio(negocio)
        self.assertIn("Abarrotes Prueba", contexto)
        self.assertIn("1 en rojo", contexto)

        services.agregar_al_carrito(negocio, "coca")
        self.assertIn("Caja 1: 1 Coca 600", services.contexto_negocio(negocio))
        self.assertIn("Caja 2: vacía", services.contexto_negocio(negocio))


@override_settings(OPENAI_API_KEY="llave-de-prueba", GEMINI_API_KEY="llave-de-prueba")
class PersistenciaDelChatTests(TestCase):
    def setUp(self):
        self.usuario, self.negocio = crear_negocio()
        self.client.force_login(self.usuario)

    def guardar(self, texto, rol=HistorialConversacion.Rol.USUARIO, negocio=None, horas_atras=0):
        mensaje = HistorialConversacion.objects.create(
            negocio=negocio or self.negocio, usuario=self.usuario, rol=rol, mensaje=texto,
        )
        if horas_atras:
            # creado_en es auto_now_add; con update() sí se puede mover la fecha
            HistorialConversacion.objects.filter(pk=mensaje.pk).update(
                creado_en=timezone.now() - timedelta(hours=horas_atras),
            )
        return mensaje

    def test_el_historial_trae_las_ultimas_24_horas_en_orden(self):
        self.guardar("mensaje de antier", horas_atras=48)
        self.guardar("pregunta de ayer", horas_atras=20)
        self.guardar("respuesta de ayer", rol=HistorialConversacion.Rol.ASISTENTE, horas_atras=19)
        self.guardar("pregunta de hoy")

        mensajes = self.client.get(reverse("avi:historial")).json()["mensajes"]

        self.assertEqual([m["texto"] for m in mensajes], ["pregunta de ayer", "respuesta de ayer", "pregunta de hoy"])
        self.assertEqual([m["rol"] for m in mensajes], ["usuario", "asistente", "usuario"])

    def test_el_historial_no_mezcla_tiendas(self):
        _, otro_negocio = crear_negocio(telefono="5599999999", email="otro@ejemplo.com", nombre_tienda="Otra")
        self.guardar("mensaje de la otra tienda", negocio=otro_negocio)
        self.assertEqual(self.client.get(reverse("avi:historial")).json()["mensajes"], [])

    def test_la_memoria_de_la_ia_tambien_olvida_lo_de_hace_mas_de_un_dia(self):
        self.guardar("mensaje viejo", horas_atras=30)
        self.guardar("mensaje reciente")
        self.assertEqual([m.mensaje for m in services.historial_reciente(self.negocio)], ["mensaje reciente"])

    def test_vaciar_el_chat_borra_la_conversacion(self):
        self.guardar("hola")
        self.client.post(reverse("avi:limpiar"))
        self.assertEqual(HistorialConversacion.objects.count(), 0)

    def test_vaciar_el_chat_pide_post(self):
        self.guardar("hola")
        self.assertEqual(self.client.get(reverse("avi:limpiar")).status_code, 405)
        self.assertEqual(HistorialConversacion.objects.count(), 1)

    @patch("avi.views.preguntar_ia", side_effect=Exception("Error 503: the model is overloaded"))
    def test_un_mensaje_que_fallo_no_se_guarda_y_el_aviso_dice_la_causa(self, _llamada):
        respuesta = self.client.post(
            reverse("avi:chat"), data=json.dumps({"mensaje": "hola"}), content_type="application/json",
        ).json()
        self.assertIn("saturada", respuesta["respuesta"])
        self.assertEqual(HistorialConversacion.objects.count(), 0)


class ErroresDeLaIaTests(SimpleTestCase):
    def test_cada_error_tiene_un_aviso_claro(self):
        self.assertIn("límite", mensaje_de_error(Exception("429 Too Many Requests")))
        self.assertIn("llave", mensaje_de_error(Exception("Incorrect API key provided")))
        self.assertIn("tardó", mensaje_de_error(Exception("Request timed out")))
        self.assertIn("saturada", mensaje_de_error(Exception("503 Service Unavailable")))
        self.assertIn("No pude conectarme", mensaje_de_error(Exception("algo raro")))

    @patch("avi.clients.time.sleep")
    def test_reintenta_las_fallas_pasajeras(self, _espera):
        intentos = []

        def llamada():
            intentos.append(1)
            if len(intentos) < 3:
                raise Exception("503 overloaded")
            return "respuesta"

        self.assertEqual(con_reintentos(llamada), "respuesta")
        self.assertEqual(len(intentos), 3)

    @patch("avi.clients.time.sleep")
    def test_no_reintenta_si_la_llave_es_mala(self, _espera):
        intentos = []

        def llamada():
            intentos.append(1)
            raise Exception("401 Incorrect API key")

        with self.assertRaises(Exception):
            con_reintentos(llamada)
        self.assertEqual(len(intentos), 1)


class ProveedoresYBusquedaDelAsistenteTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()

    def ejecutar(self, funcion, **argumentos):
        return services.ejecutar_funcion(funcion, argumentos, self.negocio)

    def test_agregar_el_correo_a_un_proveedor_que_ya_existe(self):
        self.ejecutar("alta_proveedor", nombre="Coca-cola")
        resultado = self.ejecutar("modificar_proveedor", nombre_proveedor="coca cola", correo="coca-cola arroba coca-cola.com.mx")

        self.assertTrue(resultado["ok"])
        self.assertEqual(Proveedor.objects.get().correo, "coca-cola@coca-cola.com.mx")

    def test_un_correo_invalido_no_se_guarda(self):
        self.ejecutar("alta_proveedor", nombre="Coca-cola")
        resultado = self.ejecutar("modificar_proveedor", nombre_proveedor="coca", correo="no es un correo")
        self.assertFalse(resultado["ok"])
        self.assertEqual(Proveedor.objects.get().correo, "")

    def test_modificar_un_proveedor_que_no_existe_avisa(self):
        self.assertFalse(self.ejecutar("modificar_proveedor", nombre_proveedor="Bimbo", telefono="5511")["ok"])

    def test_dar_de_alta_con_el_correo_dictado(self):
        self.ejecutar("alta_proveedor", nombre="Bimbo", correo="ventas arroba bimbo punto com")
        self.assertEqual(Proveedor.objects.get().correo, "ventas@bimbo.com")

    def test_el_alta_repetida_sugiere_cambiar_los_datos(self):
        self.ejecutar("alta_proveedor", nombre="Coca-cola")
        resultado = self.ejecutar("alta_proveedor", nombre="coca-cola")
        self.assertFalse(resultado["ok"])
        self.assertIn("cambiarle", resultado["mensaje"])

    def test_buscar_encuentra_aunque_digan_de_y_litros(self):
        crear_producto(self.negocio, nombre="Agua Ciel 1.5L")
        crear_producto(self.negocio, nombre="Agua Ciel 600ml")
        encontrados = [p["nombre"] for p in services.buscar_en_catalogo(self.negocio, "Agua Ciel de 1.5 litros")]
        self.assertEqual(encontrados, ["Agua Ciel 1.5L"])

    def test_buscar_agua_cuenta_todos_los_tipos(self):
        for nombre in ("Agua Ciel 1.5L", "Agua Bonafont 1L", "Agua de Jamaica", "Leche Lala"):
            crear_producto(self.negocio, nombre=nombre)
        resultado = self.ejecutar("buscar_producto", nombre="agua")
        self.assertEqual(resultado["total_encontrados"], 3)

    def test_consultar_inventario_cuenta_por_categoria(self):
        bebidas = Categoria.objects.create(nombre="Bebidas")
        for nombre in ("Coca 600", "Pepsi 600"):
            producto = crear_producto(self.negocio, nombre=nombre)
            producto.categoria = bebidas
            producto.save()
        crear_producto(self.negocio, nombre="Jabón")

        resultado = self.ejecutar("consultar_inventario")
        self.assertEqual(resultado["total_productos"], 3)
        categorias = {fila["categoria"]: fila["productos"] for fila in resultado["por_categoria"]}
        self.assertEqual(categorias, {"Bebidas": 2, "Sin categoría": 1})

        solo_bebidas = self.ejecutar("consultar_inventario", categoria="bebidas")
        self.assertEqual([p["nombre"] for p in solo_bebidas["productos"]], ["Coca 600", "Pepsi 600"])


class ReglaDeOroDelAsistenteTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()
        Categoria.objects.get_or_create(nombre="Bebidas")
        self.coca = crear_producto(self.negocio, nombre="Coca 600", cantidad="3", costo="15")

    def ejecutar(self, funcion, **argumentos):
        return services.ejecutar_funcion(funcion, argumentos, self.negocio)

    def test_si_no_hay_piezas_pregunta_cuantas_agregar_y_el_precio_de_compra(self):
        resultado = self.ejecutar("agregar_al_carrito", nombre_producto="coca", cantidad=5)

        self.assertFalse(resultado["ok"])
        self.assertTrue(resultado["sin_existencias"])
        self.assertIn("precio de compra", resultado["mensaje"])
        self.assertEqual(ItemVenta.objects.count(), 0)

    def test_el_flujo_completo_agrega_mercancia_registra_la_compra_y_vende(self):
        self.ejecutar("agregar_al_carrito", nombre_producto="coca", cantidad=5)
        self.ejecutar("ajustar_existencias", nombre_producto="coca", cantidad=10, modo="sumar", costo=16)
        resultado = self.ejecutar("agregar_al_carrito", nombre_producto="coca", cantidad=5)

        self.assertTrue(resultado["ok"])
        compra = GastoOperativo.objects.get()
        self.assertEqual(compra.tipo, GastoOperativo.Tipo.MERCANCIA)
        self.assertEqual(compra.monto, Decimal("160.00"))
        self.coca.refresh_from_db()
        self.assertEqual(self.coca.costo, Decimal("16.00"))

    def test_para_un_producto_a_granel_pide_kilos(self):
        frijol = crear_producto(self.negocio, nombre="Frijol", cantidad="1")
        frijol.a_granel = True
        frijol.save()
        resultado = self.ejecutar("agregar_al_carrito", nombre_producto="frijol", cantidad=3)
        self.assertIn("kilos", resultado["mensaje"])

    def test_se_vende_por_kilos_con_decimales(self):
        frijol = crear_producto(self.negocio, nombre="Frijol", cantidad="5", precio="40")
        frijol.a_granel = True
        frijol.save()
        resultado = self.ejecutar("agregar_al_carrito", nombre_producto="frijol", cantidad=0.25)
        self.assertTrue(resultado["ok"])
        self.assertEqual(ItemVenta.objects.get().cantidad, Decimal("0.250"))

    def test_las_piezas_no_aceptan_decimales(self):
        resultado = self.ejecutar("agregar_al_carrito", nombre_producto="coca", cantidad=1.5)
        self.assertFalse(resultado["ok"])

    def test_cobrar_con_el_carrito_sin_existencias_avisa(self):
        ItemVenta.objects.create(
            venta=services.carrito.venta_en_curso(self.negocio, 1), producto=self.coca,
            cantidad=Decimal("9"), precio_unitario=Decimal("25"),
        )
        resultado = self.ejecutar("cobrar_carrito")
        self.assertFalse(resultado["ok"])
        self.assertTrue(resultado["sin_existencias"])

    def test_dar_de_alta_con_piezas_registra_la_compra(self):
        self.ejecutar("dar_de_alta_producto", nombre="Pepsi", precio_venta=18, costo=13, cantidad_actual=10, categoria="bebidas")
        self.assertEqual(GastoOperativo.objects.get().monto, Decimal("130.00"))

    def test_dar_de_alta_un_producto_a_granel(self):
        resultado = self.ejecutar(
            "dar_de_alta_producto", nombre="Azúcar", precio_venta=30, costo=24, cantidad_actual=2.5, a_granel=True,
            categoria="bebidas",
        )
        self.assertTrue(resultado["ok"])
        self.assertTrue(Producto.objects.get(nombre="Azúcar").a_granel)

    def test_restar_o_establecer_no_registra_compras(self):
        self.ejecutar("ajustar_existencias", nombre_producto="coca", cantidad=1, modo="restar")
        self.ejecutar("ajustar_existencias", nombre_producto="coca", cantidad=9, modo="establecer")
        self.assertEqual(GastoOperativo.objects.count(), 0)


class CarritoActivoDelAsistenteTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()
        crear_producto(self.negocio, nombre="Coca 600")

    def tearDown(self):
        services.CARRITO_ACTIVO.set(1)

    def test_agrega_al_carrito_en_el_que_esta_la_persona(self):
        services.CARRITO_ACTIVO.set(2)
        services.agregar_al_carrito(self.negocio, "coca")
        self.assertEqual(Venta.objects.get().carrito, 2)

    @override_settings(OPENAI_API_KEY="llave-de-prueba", GEMINI_API_KEY="llave-de-prueba")
    def test_el_chat_manda_la_pantalla_y_el_carrito_a_la_ia(self):
        usuario = self.negocio.usuario
        self.client.force_login(usuario)
        with patch("avi.views.preguntar_ia", return_value=("Listo", [])) as llamada:
            self.client.post(
                reverse("avi:chat"),
                data=json.dumps({"mensaje": "hola", "pantalla": "ventas", "carrito": 2}),
                content_type="application/json",
            )
        self.assertEqual(llamada.call_args[0][2], "ventas")
        self.assertEqual(services.CARRITO_ACTIVO.get(), 2)


class HerramientasPorPantallaTests(SimpleTestCase):
    def nombres(self, pantalla):
        return {f["name"] for f in services.funciones_de(pantalla)}

    def test_cada_pantalla_recibe_solo_sus_acciones(self):
        ventas = self.nombres("ventas")
        self.assertIn("cobrar_carrito", ventas)
        self.assertNotIn("registrar_gasto", ventas)
        self.assertNotIn("dar_de_alta_producto", ventas)

        self.assertIn("dar_de_alta_producto", self.nombres("inventario"))
        self.assertNotIn("cobrar_carrito", self.nombres("inventario"))
        self.assertIn("registrar_gasto", self.nombres("finanzas"))

    def test_las_consultas_cruzadas_se_pueden_hacer_desde_cualquier_pantalla(self):
        consultas = {"consultar_alertas_stock", "consultar_gastos_mes", "consultar_resumen_financiero", "consultar_inventario", "consultar_punto_equilibrio"}
        for pantalla in ("ventas", "inventario", "finanzas"):
            self.assertTrue(consultas <= self.nombres(pantalla), pantalla)

    def test_ninguna_accion_viene_en_todas_las_pantallas_por_ser_comun(self):
        self.assertFalse(services.HERRAMIENTAS_COMUNES & services.ACCIONES)

    def test_hay_herramientas_comunes_en_todas_las_pantallas(self):
        for pantalla in ("ventas", "inventario", "finanzas"):
            self.assertIn("buscar_producto", self.nombres(pantalla))

    def test_sin_pantalla_se_mandan_todas(self):
        self.assertEqual(len(services.funciones_de(None)), len(services.FUNCIONES))
        self.assertEqual(len(services.funciones_de("otra")), len(services.FUNCIONES))

    def test_mandar_solo_las_de_la_pantalla_baja_el_tamano_de_la_peticion(self):
        completo = len(json.dumps(services.tools_openai()))
        ventas = len(json.dumps(services.tools_openai("ventas")))
        self.assertLess(ventas, completo * 0.85)

    def test_toda_funcion_declarada_esta_en_el_despachador_y_en_alguna_pantalla(self):
        en_pantallas = set(services.HERRAMIENTAS_COMUNES)
        for conjunto in services.HERRAMIENTAS_POR_PANTALLA.values():
            en_pantallas |= conjunto
        for funcion in services.FUNCIONES:
            self.assertIn(funcion["name"], services.DESPACHADOR)
            self.assertIn(funcion["name"], en_pantallas)


class ReglasDelAsistenteTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()
        Categoria.objects.get_or_create(nombre="Bebidas")

    def ejecutar(self, funcion, **argumentos):
        return services.ejecutar_funcion(funcion, argumentos, self.negocio)

    def test_el_prompt_tiene_el_mensaje_estandar_para_temas_fuera_de_la_tienda(self):
        from .clients import SYSTEM_PROMPT
        self.assertIn("Solo puedo ayudarte con las ventas, el inventario y las finanzas de tu tienda", SYSTEM_PROMPT)

    def test_dar_de_alta_sin_categoria_la_pide(self):
        resultado = self.ejecutar("dar_de_alta_producto", nombre="Pepsi", precio_venta=18, costo=13)
        self.assertFalse(resultado["ok"])
        self.assertIn("categoría", resultado["mensaje"])
        self.assertFalse(Producto.objects.filter(nombre="Pepsi").exists())

    def test_la_categoria_es_obligatoria_en_la_herramienta(self):
        herramienta = next(f for f in services.FUNCIONES if f["name"] == "dar_de_alta_producto")
        self.assertIn("categoria", herramienta["parameters"]["required"])

    def test_el_minimo_que_se_propone_es_5(self):
        self.ejecutar("dar_de_alta_producto", nombre="Pepsi", precio_venta=18, costo=13, categoria="bebidas")
        self.assertEqual(Producto.objects.get(nombre="Pepsi").cantidad_minima, Decimal("5"))

    def test_el_alta_con_el_asistente_deja_su_entrada_en_el_kardex(self):
        from inventario.models import MovimientoInventario
        self.ejecutar("dar_de_alta_producto", nombre="Pepsi", precio_venta=18, costo=13, cantidad_actual=10, categoria="bebidas")
        self.assertEqual(MovimientoInventario.objects.get().tipo, "ENTRADA")

    def test_ajustar_existencias_con_el_asistente_deja_un_ajuste_en_el_kardex(self):
        from inventario.models import MovimientoInventario
        crear_producto(self.negocio, nombre="Coca 600", cantidad="10")
        self.ejecutar("ajustar_existencias", nombre_producto="coca", cantidad=4, modo="establecer")
        movimiento = MovimientoInventario.objects.get()
        self.assertEqual((movimiento.tipo, movimiento.cantidad), ("AJUSTE", Decimal("-6")))

    def test_sugerir_precio_usa_el_margen_que_el_tendero_ya_escogio(self):
        crear_producto(self.negocio, nombre="Coca 600", costo="15")
        self.negocio.guardar_preferencias(margen_deseado="40")
        resultado = self.ejecutar("sugerir_precio", nombre_producto="coca")
        self.assertEqual(resultado["margen_deseado"], 40.0)
        self.assertEqual(resultado["precio_sugerido"], 25.0)

    def test_si_el_usuario_dice_el_margen_se_usa_ese(self):
        crear_producto(self.negocio, nombre="Coca 600", costo="15")
        self.negocio.guardar_preferencias(margen_deseado="40")
        resultado = self.ejecutar("sugerir_precio", nombre_producto="coca", margen_deseado=25)
        self.assertEqual(resultado["margen_deseado"], 25.0)


class PrecioNoMenorAlCostoDelAsistenteTests(TestCase):
    def setUp(self):
        _, self.negocio = crear_negocio()
        Categoria.objects.create(nombre="Bebidas")
        self.producto = crear_producto(self.negocio, nombre="Coca 600", costo="15", precio="25")

    def ejecutar(self, funcion, **argumentos):
        return services.ejecutar_funcion(funcion, argumentos, self.negocio)

    def test_no_da_de_alta_un_producto_que_se_vende_por_debajo_de_su_costo(self):
        resultado = self.ejecutar(
            "dar_de_alta_producto", nombre="Pepsi 600", precio_venta=10, costo=13, cantidad_actual=5, categoria="bebidas",
        )
        self.assertFalse(resultado["ok"])
        self.assertIn("no puede ser menor", resultado["mensaje"])
        self.assertFalse(Producto.objects.filter(nombre="Pepsi 600").exists())

    def test_no_baja_el_precio_por_debajo_del_costo(self):
        resultado = self.ejecutar("modificar_producto", nombre_producto="coca", precio_venta=10)
        self.assertFalse(resultado["ok"])
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio_venta, Decimal("25"))

    def test_no_sube_el_costo_por_encima_del_precio(self):
        resultado = self.ejecutar("modificar_producto", nombre_producto="coca", costo=40)
        self.assertFalse(resultado["ok"])

    def test_al_dar_de_alta_le_pone_un_icono_segun_el_nombre(self):
        self.ejecutar("dar_de_alta_producto", nombre="Sprite 600", precio_venta=19, costo=12, cantidad_actual=5, categoria="bebidas")
        self.assertEqual(Producto.objects.get(nombre="Sprite 600").icono, "🥤")

    def test_la_categoria_de_gasto_no_se_duplica_por_las_mayusculas(self):
        from finanzas.models import CategoriaGasto
        CategoriaGasto.objects.create(negocio=self.negocio, nombre="Luz", tipo="FIJO")
        self.ejecutar("registrar_gasto", tipo="FIJO", concepto="Luz de octubre", monto=450, categoria="luz")
        self.assertEqual(CategoriaGasto.objects.filter(negocio=self.negocio).count(), 1)
