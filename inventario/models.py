from django.db import models

from core.models import ModeloBase


class Categoria(ModeloBase):
    """Categoria compartida por productos y proveedores del sistema."""

    nombre = models.CharField(max_length=60, unique=True)
    icono = models.CharField(max_length=8, blank=True, default="📦")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Proveedor(ModeloBase):
    """Proveedor perteneciente a una tienda y relacionado con categorias.

    `categorias` es una relacion muchos-a-muchos que Django guarda en una
    tabla intermedia. Borrar el negocio elimina sus proveedores; quitar una
    categoria de la relacion no elimina la categoria compartida.
    """

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
    """Referencia global usada para precargar inventarios durante el registro.

    No pertenece a un negocio. Al copiarlo a una tienda se crea un `Producto`
    propio y se conserva este registro como `catalogo_origen`.
    """

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
    """Producto persistido en el inventario de un negocio concreto.

    `negocio` determina a que tienda pertenece; categoria, proveedor y
    catalogo_origen son referencias opcionales o compartidas. Las ventas
    conservan una referencia al producto y su precio historico en `ItemVenta`,
    por eso las vistas dan de baja productos desactivandolos en vez de
    eliminarlos fisicamente.
    """

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
