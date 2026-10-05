from django.contrib.auth.models import AbstractUser
from django.db import models

from core.models import ModeloBase


class Usuario(AbstractUser):
    """Cuenta autenticable del sistema, basada en el usuario de Django.

    Django conserva credenciales y permisos heredados de `AbstractUser`; los
    campos adicionales guardan datos de contacto. `telefono` es unico cuando
    tiene valor, y el registro lo usa tambien como `username`.
    """

    nombre_completo = models.CharField("Nombre completo", max_length=150, blank=True)
    telefono = models.CharField("Teléfono celular", max_length=20, unique=True, null=True, blank=True)
    email = models.EmailField("Correo electrónico", blank=True)

    def __str__(self):
        return self.nombre_completo or self.username


class Negocio(ModeloBase):
    """Perfil de tienda con relacion uno-a-uno con su cuenta propietaria.

    La llave foranea inversa `usuario.negocio` permite obtener la tienda de la
    sesion actual. Al borrar el usuario, Django elimina tambien su negocio; las
    tablas de inventario, ventas y gastos lo referencian para aislar sus datos.
    """

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

    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name="negocio")
    nombre_tienda = models.CharField("Nombre de tu tienda", max_length=150)
    alcaldia = models.CharField("Alcaldía", max_length=30, choices=Alcaldia.choices, blank=True)
    anios_operacion = models.CharField(
        "Años de operación", max_length=20,
        choices=AniosOperacion.choices, default=AniosOperacion.DE_3_A_10,
    )
    regimen_resico = models.BooleanField("Régimen RESICO", default=True)
    rfc = models.CharField("RFC", max_length=13, blank=True)

    def __str__(self):
        return self.nombre_tienda
