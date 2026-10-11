import json
from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from core import cache_negocio
from core.testing import crear_negocio, crear_producto
from finanzas.models import GastoOperativo
from inventario.models import Categoria, HistorialModificacionProducto, Producto
from ventas.models import ItemVenta, Venta

from . import services
from .clients import MENSAJE_SIN_LLAVE, SinLlaveError, modelo_disponible
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
            data=json.dumps({"mensaje": mensaje, "modelo": "chatgpt"}),
            content_type="application/json",
        )

    @patch("avi.views.preguntar_chatgpt", return_value=("Listo, agregué 2 pepsis.", ["agregar_al_carrito"]))
    def test_guarda_el_historial_y_pide_refrescar_la_pantalla(self, _llamada):
        respuesta = self.mandar("agrega 2 pepsis").json()

        self.assertEqual(respuesta["respuesta"], "Listo, agregué 2 pepsis.")
        self.assertTrue(respuesta["refrescar"])
        self.assertEqual(HistorialConversacion.objects.count(), 2)

    @patch("avi.views.preguntar_chatgpt", return_value=("Hoy vendiste poco.", ["consultar_ventas_hoy"]))
    def test_una_consulta_no_refresca_la_pantalla(self, _llamada):
        respuesta = self.mandar("¿cuánto vendí hoy?").json()
        self.assertFalse(respuesta["refrescar"])

    def test_un_mensaje_vacio_no_llama_al_modelo(self):
        with patch("avi.views.preguntar_chatgpt") as llamada:
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
    def test_si_solo_hay_llave_de_gemini_se_usa_gemini(self):
        self.assertEqual(modelo_disponible("chatgpt"), "gemini")

    @override_settings(OPENAI_API_KEY="llave-de-openai", GEMINI_API_KEY="llave-de-gemini")
    def test_si_hay_las_dos_se_respeta_la_elegida(self):
        self.assertEqual(modelo_disponible("gemini"), "gemini")
        self.assertEqual(modelo_disponible("chatgpt"), "chatgpt")

    @override_settings(OPENAI_API_KEY="", GEMINI_API_KEY="")
    def test_si_no_hay_ninguna_se_queda_con_la_elegida(self):
        self.assertEqual(modelo_disponible("gemini"), "gemini")


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
        self.assertIn("Carrito actual: 1 Coca 600", services.contexto_negocio(negocio))
