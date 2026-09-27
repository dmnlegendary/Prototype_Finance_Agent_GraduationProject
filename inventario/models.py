from django.db import models

from core.models import ModeloBase


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

    cantidad_actual = models.DecimalField("Cantidad actual", max_digits=10, decimal_places=2, default=0)
    cantidad_minima = models.DecimalField("Cantidad mínima", max_digits=10, decimal_places=2, default=0)

    catalogo_origen = models.ForeignKey(
        ProductoCatalogo, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )

    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.negocio.nombre_tienda})"

    @property
    def margen_porcentaje(self):
        if not self.precio_venta:
            return 0
        return round((self.precio_venta - self.costo) / self.precio_venta * 100, 1)

    @property
    def stock_critico(self):
        return self.cantidad_actual <= self.cantidad_minima
