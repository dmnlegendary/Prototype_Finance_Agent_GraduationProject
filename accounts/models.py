"""
Modelos de la app `accounts`.

Alinea con las pantallas ya maquetadas:
  - sistema_configuracion/registro.html      -> Usuario (paso 1: Cuenta)
  - sistema_configuracion/datos_negocio.html -> Negocio (paso 2: Negocio)
  - sistema_configuracion/productos_precargados.html -> usa el catálogo de
    `inventario.ProductoCatalogo` (paso 3: Productos), no un modelo nuevo.

IMPORTANTE (léase antes de poblar datos): todavía no existe una base de
artículos/productos real. Los choices de catálogos (alcaldías, años de
operación, categorías) se tomaron LITERALMENTE de las opciones que ya
existen en los <select> de los HTML proporcionados, para no inventar datos
de negocio. Si el negocio real necesita más opciones, hay que actualizarlas
aquí antes de generar las migraciones definitivas.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import ModeloBase


class Usuario(AbstractUser):
    """
    Usuario del sistema (dueño de la tienda o cajero).

    Se extiende `AbstractUser` (en vez de reescribir autenticación desde
    cero) para heredar gratis: hashing de contraseña, permisos, integración
    con el admin de Django y con `django.contrib.auth` (login/logout,
    `login_required`, etc.).

    TODO de diseño (pendiente de definir con el equipo, no asumido aquí):
    actualmente el login sigue usando `username` (heredado de AbstractUser),
    pero registro.html no pide "usuario", pide Teléfono. Si el login final
    debe hacerse por teléfono en vez de username, hace falta:
      1) un backend de autenticación custom (`AUTHENTICATION_BACKENDS`), o
      2) cambiar `USERNAME_FIELD` a "telefono" (requiere una migración
         limpia, mejor hacerlo ahora que el proyecto está vacío que después).
    Por ahora se deja `username` funcional para no bloquear el resto del
    sistema, y se guarda el teléfono como dato de perfil.
    """

    nombre_completo = models.CharField(
        "Nombre completo", max_length=150, blank=True,
        help_text="Tal como se captura en un solo campo en registro.html.",
    )
    telefono = models.CharField(
        "Teléfono celular", max_length=20, unique=True, null=True, blank=True,
    )
    # AbstractUser ya trae `email`; aquí se relaja a opcional porque en
    # registro.html el correo está marcado explícitamente como "(opcional)".
    email = models.EmailField("Correo electrónico", blank=True)

    def __str__(self):
        return self.nombre_completo or self.username


class Negocio(ModeloBase):
    """
    Perfil de negocio (la tienda) asociado 1 a 1 con un Usuario dueño.
    Corresponde al paso 2 del onboarding (datos_negocio.html).
    """

    # Opciones tomadas literalmente del <select> de datos_negocio.html.
    # TODO: si el negocio opera fuera de CDMX, ampliar este catálogo.
    class Alcaldia(models.TextChoices):
        IZTAPALAPA = "IZTAPALAPA", "Iztapalapa"
        GUSTAVO_A_MADERO = "GAM", "Gustavo A. Madero"
        ALVARO_OBREGON = "ALVARO_OBREGON", "Álvaro Obregón"
        TLALPAN = "TLALPAN", "Tlalpan"
        COYOACAN = "COYOACAN", "Coyoacán"
        XOCHIMILCO = "XOCHIMILCO", "Xochimilco"
        OTRA = "OTRA", "Otra"

    class AniosOperacion(models.TextChoices):
        MENOS_DE_1 = "MENOS_DE_1", "Menos de 1 año"
        DE_1_A_3 = "DE_1_A_3", "1 a 3 años"
        DE_3_A_10 = "DE_3_A_10", "3 a 10 años"
        MAS_DE_10 = "MAS_DE_10", "Más de 10 años"

    usuario = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, related_name="negocio",
    )
    nombre_tienda = models.CharField("Nombre de tu tienda", max_length=150)

    # NOTA: el <label> del mockup dice "Alcaldía / Colonia" pero el <select>
    # solo lista alcaldías (no hay un campo de colonia independiente en el
    # HTML). Se modela solo `alcaldia` por fidelidad a lo que existe hoy.
    # TODO: preguntar si falta un campo `colonia` de texto libre.
    alcaldia = models.CharField(
        "Alcaldía", max_length=30, choices=Alcaldia.choices, blank=True,
    )
    anios_operacion = models.CharField(
        "Años de operación", max_length=20,
        choices=AniosOperacion.choices, default=AniosOperacion.DE_3_A_10,
    )

    # Switch "¿Estás en el régimen RESICO?" — activado por default en el mockup.
    regimen_resico = models.BooleanField("Régimen RESICO", default=True)
    rfc = models.CharField("RFC", max_length=13, blank=True)

    def __str__(self):
        return self.nombre_tienda
