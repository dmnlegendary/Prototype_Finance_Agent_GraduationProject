from django.db import models


class ModeloBase(models.Model):
    """Campos de fecha que comparten casi todos los modelos del proyecto."""

    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OperacionSincronizada(ModeloBase):
    """Una operación hecha sin internet (una venta, un producto dado de alta…) que ya se
    guardó en el sistema. Sirve para que, si el celular reintenta mandarla (porque la
    conexión se cortó a la mitad), no se guarde dos veces."""

    negocio = models.ForeignKey("accounts.Negocio", on_delete=models.CASCADE, related_name="operaciones_sincronizadas")
    # identificador único que genera el navegador al guardar la operación
    uuid = models.CharField(max_length=64)
    tipo = models.CharField(max_length=30)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["negocio", "uuid"], name="operacion_unica_por_negocio"),
        ]

    def __str__(self):
        return f"{self.tipo} {self.uuid[:8]}"


class LlaveIA(ModeloBase):
    """Llave de acceso a un servicio de IA (OpenAI o Google). Se guarda CIFRADA, nunca en texto plano
    (ver core/llaves.py)."""

    OPENAI = "openai"
    GEMINI = "gemini"
    PROVEEDORES = [(OPENAI, "OpenAI (ChatGPT)"), (GEMINI, "Google (Gemini)")]

    proveedor = models.CharField(max_length=20, choices=PROVEEDORES, unique=True)
    valor_cifrado = models.TextField()

    class Meta:
        verbose_name = "Llave de IA"
        verbose_name_plural = "Llaves de IA"

    def __str__(self):
        return self.get_proveedor_display()
