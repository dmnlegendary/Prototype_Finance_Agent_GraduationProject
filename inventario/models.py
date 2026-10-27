from decimal import Decimal

from django.conf import settings
from django.db import models

from core.models import ModeloBase


# cantidad mínima que se propone al dar de alta un producto (la alerta roja salta al llegar a ella)
MINIMO_POR_DEFECTO = Decimal("5")


class Categoria(ModeloBase):
    nombre = models.CharField(max_length=60, unique=True)
    icono = models.CharField(max_length=8, blank=True, default="📦")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Proveedor(ModeloBase):
    negocio = models.ForeignKey(
        "accounts.Negocio", on_delete=models.CASCADE, related_name="proveedores",
    )
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=30, blank=True)
    correo = models.EmailField(blank=True)
    categorias = models.ManyToManyField(Categoria, blank=True, related_name="proveedores")

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ProductoCatalogo(ModeloBase):
    """Catálogo genérico de productos que se muestra al crear una tienda nueva."""

    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, related_name="productos_catalogo",
    )
    icono = models.CharField(max_length=8, blank=True, default="📦")
    precio_sugerido = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Producto de catálogo (precargado)"
        verbose_name_plural = "Productos de catálogo (precargados)"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(ModeloBase):
    """Producto real del inventario de una tienda."""

    negocio = models.ForeignKey(
        "accounts.Negocio", on_delete=models.CASCADE, related_name="productos",
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, related_name="productos",
    )
    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.SET_NULL, null=True, blank=True, related_name="productos",
    )
    icono = models.CharField(max_length=8, blank=True, default="📦")

    costo = models.DecimalField("Costo ($)", max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField("Precio de venta ($)", max_digits=10, decimal_places=2)

    cantidad_actual = models.DecimalField("Cantidad actual", max_digits=10, decimal_places=3, default=0)
    cantidad_minima = models.DecimalField("Cantidad mínima", max_digits=10, decimal_places=3, default=0)
    # Lo que tienes cuando resurtes completo. Con este número se pintan los
    # colores del semáforo: amarillo a la mitad, naranja a un cuarto y rojo al
    # llegar al mínimo. Si se deja en 0 se usa 4 veces el mínimo.
    stock_ideal = models.DecimalField(
        "Stock ideal", max_digits=10, decimal_places=3, default=0,
        help_text="Piezas que tienes cuando resurtes completo. Déjalo en 0 si no lo sabes.",
    )

    catalogo_origen = models.ForeignKey(
        ProductoCatalogo, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )

    # Producto "a granel": se vende por peso (frijol, azúcar...). Su precio es por
    # kilo y sus existencias se guardan en kilos (125 g = 0.125). En pantalla se
    # captura en gramos.
    a_granel = models.BooleanField("Se vende a granel (por kilo)", default=False)
    # Código de barras (opcional). Un lector de códigos conectado a la compu o al
    # celular "escribe" el código como si fuera un teclado.
    codigo_barras = models.CharField("Código de barras", max_length=40, blank=True, default="")

    activo = models.BooleanField(default=True)
    # True solo para los productos creados desde "producto no encontrado" en
    # ventas, mientras el tendero no les complete los datos (categoría, stock
    # mínimo, etc.) y los dé de alta formalmente. No se debe confundir con un
    # producto dado de baja (activo=False, pendiente_validacion=False).
    pendiente_validacion = models.BooleanField(default=False)

    class Meta:
        ordering = ["nombre"]
        # Índices para que el catálogo y las alertas no se pongan lentos
        # cuando hay miles de productos (se buscan casi siempre por negocio).
        indexes = [
            models.Index(fields=["negocio", "activo"], name="producto_negocio_activo_idx"),
            models.Index(fields=["negocio", "nombre"], name="producto_negocio_nombre_idx"),
        ]
        constraints = [
            # el mismo código de barras no puede estar en dos productos de la misma tienda
            models.UniqueConstraint(
                fields=["negocio", "codigo_barras"], condition=~models.Q(codigo_barras=""),
                name="producto_codigo_unico_por_negocio",
            ),
            models.CheckConstraint(
                condition=models.Q(costo__gte=0) & models.Q(precio_venta__gte=0),
                name="producto_precios_no_negativos",
                violation_error_message="El costo y el precio de venta no pueden ser negativos.",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(cantidad_actual__gte=0)
                    & models.Q(cantidad_minima__gte=0)
                    & models.Q(stock_ideal__gte=0)
                ),
                name="producto_cantidades_no_negativas",
                violation_error_message="Las cantidades no pueden ser negativas.",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.negocio.nombre_tienda})"

    @property
    def unidad(self):
        """"kg" para los productos a granel y "pzas" para los demás."""
        return "kg" if self.a_granel else "pzas"

    @property
    def margen_porcentaje(self):
        if not self.precio_venta:
            return 0
        return round((self.precio_venta - self.costo) / self.precio_venta * 100, 1)

    @property
    def stock_ideal_efectivo(self):
        """El stock ideal que se usa para los colores: el que capturó el
        tendero, o 4 veces el mínimo si no lo capturó (o si quedó menor al mínimo)."""
        if self.stock_ideal > self.cantidad_minima:
            return self.stock_ideal
        return self.cantidad_minima * 4

    @property
    def sin_control_de_stock(self):
        """Solo el producto "no encontrado" (se crea al cobrar, inactivo y pendiente) se puede vender
        sin existencias. Los pendientes que están activos, como los que llegan del CSV de ventas,
        sí se controlan: si no hay piezas, la caja pregunta cuántas se quieren agregar."""
        return self.pendiente_validacion and not self.activo

    @property
    def nivel_stock(self):
        """Semáforo del reabastecimiento: "rojo", "naranja", "amarillo" u "ok"."""
        # un producto "no encontrado" que aún no se valida no lleva control de stock
        if self.pendiente_validacion:
            return "ok"

        actual = self.cantidad_actual
        if actual <= self.cantidad_minima:
            return "rojo"

        ideal = self.stock_ideal_efectivo
        # el naranja nunca baja del mínimo, y el amarillo nunca del naranja
        limite_naranja = max(ideal / 4, self.cantidad_minima)
        limite_amarillo = max(ideal / 2, limite_naranja)
        if actual <= limite_naranja:
            return "naranja"
        if actual <= limite_amarillo:
            return "amarillo"
        return "ok"

    @property
    def stock_critico(self):
        return self.nivel_stock == "rojo"

    @property
    def tiene_ventas(self):
        return self.items_venta.exists()


class HistorialModificacionProducto(ModeloBase):
    """El motivo que el tendero da cada vez que edita un producto."""

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="historial_cambios")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+",
    )
    motivo = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Historial de modificación de producto"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"{self.producto.nombre}: {self.motivo[:40]}"


class MovimientoInventario(ModeloBase):
    """El kardex: un renglón por cada cambio en las existencias de un producto, con su origen
    (venta, entrada de mercancía, merma o ajuste). Nunca se edita ni se borra; así queda la
    evidencia de por qué cambió cada cifra y sirve como dataset para el análisis."""

    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada de mercancía"
        VENTA = "VENTA", "Venta"
        MERMA = "MERMA", "Merma"
        AJUSTE = "AJUSTE", "Ajuste de conteo"

    negocio = models.ForeignKey("accounts.Negocio", on_delete=models.CASCADE, related_name="movimientos_inventario")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    # lo que cambió: positivo si entraron piezas, negativo si salieron
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    existencia_resultante = models.DecimalField(max_digits=10, decimal_places=3)
    motivo = models.CharField(max_length=255, blank=True)
    # a cuánto costó cada pieza de este movimiento (en las ventas y mermas es el costo de los lotes de los que salió)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    venta = models.ForeignKey("ventas.Venta", on_delete=models.SET_NULL, null=True, blank=True, related_name="movimientos")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")

    class Meta:
        verbose_name = "Movimiento de inventario"
        verbose_name_plural = "Movimientos de inventario"
        ordering = ["-creado_en", "-id"]
        indexes = [
            models.Index(fields=["negocio", "creado_en"], name="movimiento_negocio_fecha_idx"),
            models.Index(fields=["producto", "creado_en"], name="movimiento_producto_fecha_idx"),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.producto.nombre}: {self.cantidad}"


class LoteInventario(ModeloBase):
    """Una compra de mercancía que todavía no se acaba. Cada vez que entran piezas se abre un lote
    con lo que costó esa compra y, al vender, se gastan primero los lotes más viejos (PEPS).
    Así, si la coca costó 15 ayer y 17 hoy, las de ayer se venden con costo de 15 y las de hoy de 17."""

    negocio = models.ForeignKey("accounts.Negocio", on_delete=models.CASCADE, related_name="lotes_inventario")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="lotes")
    cantidad_inicial = models.DecimalField(max_digits=10, decimal_places=3)
    cantidad_restante = models.DecimalField(max_digits=10, decimal_places=3)
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4)

    class Meta:
        verbose_name = "Lote de inventario"
        verbose_name_plural = "Lotes de inventario"
        ordering = ["creado_en", "id"]
        indexes = [models.Index(fields=["producto", "cantidad_restante"], name="lote_producto_restante_idx")]

    def __str__(self):
        return f"{self.producto.nombre}: {self.cantidad_restante} a ${self.costo_unitario}"
