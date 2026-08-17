"""
Modelos de la app `inventario`.

Alinea con:
  - auxiliar_de_inventario/inventario.html          -> Producto, Categoria, Proveedor
  - sistema_configuracion/productos_precargados.html -> Categoria, ProductoCatalogo

Diseño clave: se separan dos conceptos que en el mockup de onboarding se
ven parecidos pero son distintos:
  - `ProductoCatalogo`: catálogo GENÉRICO y compartido (ej. "Coca-Cola
    600ml", "$18.00") que administra el equipo/ admin del sistema. Es la
    fuente de productos_precargados.html.
  - `Producto`: el inventario REAL de una tienda (`Negocio`) específica,
    con su propio costo, precio, stock y mínimo. Se crea cuando el dueño
    selecciona productos del catálogo (o los da de alta manualmente, como
    en el panel "Alta de producto" de inventario.html).

Esto evita que, si dos tiendas venden "Coca-Cola 600ml", compartan el mismo
registro de stock/costo — cada tienda tiene su propia fila en `Producto`.

Aún no hay una base de artículos real: `ProductoCatalogo` se deja vacío por
ahora (se puebla después vía admin de Django o un fixture), y las vistas de
onboarding usan datos de ejemplo hasta entonces (ver accounts/views.py).
"""
from django.conf import settings
from django.db import models

from core.models import ModeloBase


class Categoria(ModeloBase):
    """
    Categorías vistas en los mockups: Bebidas, Abarrotes, Limpieza,
    Dulcería, Lácteos, Botanas, Verduras, Panadería (recopiladas de
    inventario.html y productos_precargados.html).
    """

    nombre = models.CharField(max_length=60, unique=True)
    # Emoji usado como ícono en las tarjetas de producto (🥤, 🍞, 🧴, ...).
    # Se modela como texto simple en vez de una tabla de íconos para no
    # sobre-diseñar algo que hoy es solo un emoji en el HTML.
    icono = models.CharField(max_length=8, blank=True, default="📦")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Proveedor(ModeloBase):
    """Panel "Gestión de proveedores" de inventario.html."""

    negocio = models.ForeignKey(
        "accounts.Negocio", on_delete=models.CASCADE, related_name="proveedores",
    )
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=30, blank=True)
    correo = models.EmailField(blank=True)
    categorias = models.ManyToManyField(
        Categoria, blank=True, related_name="proveedores",
        help_text="Categorías que surte este proveedor (etiquetas de colores en el mockup).",
    )

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class ProductoCatalogo(ModeloBase):
    """
    Catálogo genérico/precargado (productos_precargados.html). No pertenece
    a ninguna tienda: es el "menú" del que un negocio nuevo elige sus
    primeros productos durante el onboarding.
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
    """
    Inventario real de una tienda. Corresponde a las tarjetas y al panel
    "Alta de producto" / "Modificar producto" de inventario.html.
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

    cantidad_actual = models.DecimalField(
        "Cantidad actual", max_digits=10, decimal_places=2, default=0,
        help_text="Decimal para soportar productos a granel (ej. 1.5 kg de jitomate).",
    )
    cantidad_minima = models.DecimalField(
        "Cantidad mínima", max_digits=10, decimal_places=2, default=0,
        help_text="Umbral para las alertas de reabastecimiento (panel 'Alertas inteligentes').",
    )

    # De qué producto de catálogo se originó (si vino del onboarding).
    # Queda nulo si el producto se dio de alta manualmente.
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
        """Margen estimado, usado en el panel 'Modificar producto'."""
        if not self.precio_venta:
            return 0
        return round((self.precio_venta - self.costo) / self.precio_venta * 100, 1)

    @property
    def stock_critico(self):
        """True si la cantidad actual ya tocó (o cruzó) la cantidad mínima."""
        return self.cantidad_actual <= self.cantidad_minima
