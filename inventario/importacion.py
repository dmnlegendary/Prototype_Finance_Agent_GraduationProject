"""
Importar productos desde un archivo CSV (se exporta desde Excel con "Guardar como CSV").

El archivo DEBE traer estas columnas (si falta alguna, no se carga nada):

    producto, cantidad, precio_compra, precio_venta

y puede traer estas opcionales: categoria, codigo_barras, a_granel (si/no).

El proceso tiene dos pasos para no alterar la base de datos por error:
  1. se lee y se revisa el archivo (leer_csv) y cada renglón se compara con el inventario
     (clasificar): ya existe, se parece a uno que existe, o es nuevo;
  2. el usuario confirma qué hacer con cada renglón y hasta entonces se guarda (aplicar).
"""
import csv
import io
from decimal import Decimal

from django.db import transaction

from core import cache_negocio

from . import busqueda
from .compras import CantidadInvalida, a_decimal, agregar_existencias, registrar_compra
from .datos_base import icono_para
from .models import Categoria, HistorialModificacionProducto, MovimientoInventario, Producto
from .movimientos import registrar_movimiento

COLUMNAS_OBLIGATORIAS = ["producto", "cantidad", "precio_compra", "precio_venta"]
COLUMNAS_OPCIONALES = ["categoria", "codigo_barras", "a_granel"]

# nombres con los que se aceptan las columnas (ya sin acentos, en minúsculas y con guion bajo)
NOMBRES_DE_COLUMNA = {
    "producto": "producto", "nombre": "producto",
    "cantidad": "cantidad",
    "precio_compra": "precio_compra", "precio_de_compra": "precio_compra", "costo": "precio_compra",
    "precio_venta": "precio_venta", "precio_de_venta": "precio_venta",
    "categoria": "categoria",
    "codigo_barras": "codigo_barras", "codigo_de_barras": "codigo_barras", "codigo": "codigo_barras",
    "a_granel": "a_granel", "granel": "a_granel",
}

MAXIMO_DE_RENGLONES = 3000

PLANTILLA = (
    "producto,cantidad,precio_compra,precio_venta,categoria,codigo_barras,a_granel\n"
    "Coca-Cola 600ml,24,13.50,18,Bebidas,7501055300075,no\n"
    "Frijol negro,10,28,38,Abarrotes,,si\n"
)


def _decodificar(contenido):
    for codificacion in ("utf-8-sig", "cp1252"):
        try:
            return contenido.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return contenido.decode("latin-1")


def _nombre_de_columna(texto):
    limpio = busqueda.normalizar(texto).replace(" ", "_").replace("-", "_")
    return NOMBRES_DE_COLUMNA.get(limpio)


def _es_si(texto):
    return busqueda.normalizar(texto) in {"si", "s", "1", "true", "x", "granel", "kg", "kilo"}


def leer_csv(contenido):
    """Lee el archivo y lo revisa. Regresa (filas, errores).

    Si `errores` trae algo, NO se debe cargar nada: el usuario corrige el archivo y lo sube de nuevo."""
    texto = _decodificar(contenido)
    if not texto.strip():
        return [], ["El archivo está vacío."]

    primera_linea = texto.splitlines()[0]
    # Excel en español suele guardar con punto y coma
    separador = max([",", ";", "\t"], key=primera_linea.count)
    lector = csv.reader(io.StringIO(texto), delimiter=separador)

    try:
        encabezado = next(lector)
    except StopIteration:
        return [], ["El archivo está vacío."]

    posiciones = {}
    for indice, nombre in enumerate(encabezado):
        canonico = _nombre_de_columna(nombre)
        if canonico and canonico not in posiciones:
            posiciones[canonico] = indice

    faltan = [c for c in COLUMNAS_OBLIGATORIAS if c not in posiciones]
    if faltan:
        return [], [
            "Al archivo le faltan estas columnas obligatorias: " + ", ".join(faltan) + ". "
            "Debe traer: " + ", ".join(COLUMNAS_OBLIGATORIAS) + ". No se cargó nada."
        ]

    def celda(renglon, columna):
        indice = posiciones.get(columna)
        return renglon[indice].strip() if indice is not None and indice < len(renglon) else ""

    filas, errores, vistos = [], [], {}
    for numero, renglon in enumerate(lector, start=2):
        if not any(c.strip() for c in renglon):
            continue  # renglón vacío
        if len(filas) >= MAXIMO_DE_RENGLONES:
            errores.append(f"El archivo tiene más de {MAXIMO_DE_RENGLONES} productos. Divídelo en varios archivos.")
            break

        nombre = celda(renglon, "producto")
        cantidad = a_decimal(celda(renglon, "cantidad"))
        compra = a_decimal(celda(renglon, "precio_compra"))
        venta = a_decimal(celda(renglon, "precio_venta"))

        problemas = []
        if not nombre:
            problemas.append("falta el nombre del producto")
        elif len(nombre) > 150:
            problemas.append("el nombre es muy largo (máximo 150 letras)")
        if cantidad is None or cantidad < 0:
            problemas.append("la cantidad no es un número válido")
        if compra is None or compra < 0:
            problemas.append("el precio de compra no es un número válido")
        if venta is None or venta <= 0:
            problemas.append("el precio de venta debe ser un número mayor a cero")
        elif compra is not None and venta < compra:
            problemas.append("el precio de venta es menor al de compra")

        llave = busqueda.normalizar(nombre)
        if nombre and llave in vistos:
            problemas.append(f"repite el producto de la fila {vistos[llave]}")
        elif nombre:
            vistos[llave] = numero

        if problemas:
            errores.append(f"Fila {numero}: " + "; ".join(problemas) + ".")
            continue

        filas.append({
            "fila": numero,
            "producto": nombre,
            "cantidad": str(cantidad),
            "precio_compra": str(compra),
            "precio_venta": str(venta),
            "categoria": celda(renglon, "categoria"),
            "codigo_barras": celda(renglon, "codigo_barras"),
            "a_granel": _es_si(celda(renglon, "a_granel")),
        })

    if not filas and not errores:
        errores.append("El archivo no tiene productos.")
    return filas, errores


def clasificar(negocio, filas):
    """Compara cada renglón con el inventario. Cada renglón queda con un `tipo`:

      existente  -> ya hay un producto con ese nombre (o ese código de barras)
      pendiente  -> es un producto "no encontrado" que se vendió y falta completarlo
      parecido   -> no hay uno igual, pero hay productos parecidos (el usuario elige)
      nuevo      -> no se parece a nada; solo se agrega si el usuario confirma
    """
    existentes = {busqueda.normalizar(p["nombre"]): p for p in busqueda.catalogo(negocio)}
    por_codigo = {p["codigo"]: p for p in busqueda.catalogo(negocio) if p["codigo"]}
    pendientes = {
        busqueda.normalizar(p.nombre): p
        for p in Producto.objects.filter(negocio=negocio, pendiente_validacion=True)
    }

    resultado = []
    for fila in filas:
        fila = dict(fila, tipo="nuevo", coincide_id=None, coincide_nombre="", candidatos=[])
        llave = busqueda.normalizar(fila["producto"])

        if fila["codigo_barras"] and fila["codigo_barras"] in por_codigo:
            coincide = por_codigo[fila["codigo_barras"]]
            fila.update(tipo="existente", coincide_id=coincide["id"], coincide_nombre=coincide["nombre"])
        elif llave in existentes:
            coincide = existentes[llave]
            fila.update(tipo="existente", coincide_id=coincide["id"], coincide_nombre=coincide["nombre"])
        elif llave in pendientes:
            coincide = pendientes[llave]
            fila.update(tipo="pendiente", coincide_id=coincide.pk, coincide_nombre=coincide.nombre)
        else:
            parecidos = busqueda.buscar(negocio, fila["producto"], limite=3)
            if parecidos:
                fila.update(
                    tipo="parecido",
                    candidatos=[{"id": p["id"], "nombre": p["nombre"]} for p in parecidos],
                )
        resultado.append(fila)
    return resultado


def aplicar(negocio, filas, decisiones):
    """Guarda lo que el usuario confirmó. `decisiones` es {número de fila: acción} con:

      "actualizar"  (existente o pendiente): suma las piezas y actualiza los precios
      "usar:<id>"   (parecido): lo trata como ese producto del inventario
      "agregar"     (nuevo o parecido): crea el producto
      cualquier otra cosa: se omite

    Todo ocurre en una sola transacción y la compra se registra como un solo gasto."""
    resumen = {
        "actualizados": 0, "agregados": 0, "activados": 0, "omitidos": 0, "errores": [], "compra_total": Decimal("0"),
    }
    categorias = {busqueda.normalizar(c.nombre): c for c in Categoria.objects.all()}
    por_id = {p.pk: p for p in Producto.objects.filter(negocio=negocio)}

    with transaction.atomic():
        for fila in filas:
            accion = decisiones.get(fila["fila"], "omitir")
            cantidad = Decimal(fila["cantidad"])
            compra = Decimal(fila["precio_compra"])
            venta = Decimal(fila["precio_venta"])

            producto = None
            if accion == "actualizar" and fila["coincide_id"] in por_id:
                producto = por_id[fila["coincide_id"]]
            elif accion.startswith("usar:") and accion[5:].isdigit() and int(accion[5:]) in por_id:
                producto = por_id[int(accion[5:])]

            if producto is not None:
                era_pendiente = producto.pendiente_validacion
                try:
                    resumen["compra_total"] += _actualizar(producto, fila, cantidad, compra, venta)
                except CantidadInvalida as error:
                    resumen["errores"].append(f"Fila {fila['fila']}: {error}")
                    resumen["omitidos"] += 1
                    continue
                if era_pendiente:
                    resumen["activados"] += 1
                else:
                    resumen["actualizados"] += 1
            elif accion == "agregar":
                nuevo = _crear(negocio, fila, cantidad, compra, venta, categorias)
                resumen["compra_total"] += nuevo.cantidad_actual * nuevo.costo
                resumen["agregados"] += 1
            else:
                resumen["omitidos"] += 1

        registrar_compra(
            negocio, f"Compra de mercancía (importación de {resumen['actualizados'] + resumen['agregados'] + resumen['activados']} productos)",
            resumen["compra_total"],
        )

    cache_negocio.invalidar(negocio.pk)
    return resumen


def _actualizar(producto, fila, cantidad, compra, venta):
    """Suma las piezas y deja los precios del archivo. Regresa lo que costó la mercancía."""
    era_pendiente = producto.pendiente_validacion
    # se revisa antes de guardar nada, para no dejar el producto a medias
    es_granel = fila["a_granel"] if era_pendiente else producto.a_granel
    if cantidad > 0 and not es_granel and cantidad != cantidad.to_integral_value():
        raise CantidadInvalida(f'"{producto.nombre}" se vende por pieza: la cantidad debe ser un número entero.')

    if era_pendiente:
        producto.activo = True
        producto.pendiente_validacion = False
        producto.a_granel = fila["a_granel"]
        if producto.categoria_id is None:
            # un producto validado ya lleva categoría: si no la tenía, va en "Otros"
            producto.categoria, _ = Categoria.objects.get_or_create(nombre="Otros", defaults={"icono": "📦"})
        # las ventas que se hicieron sin saber el costo se completan con este precio de compra
        producto.items_venta.filter(costo_unitario=0).update(costo_unitario=compra)

    producto.precio_venta = venta
    codigo = fila["codigo_barras"]
    if codigo and not producto.codigo_barras and not Producto.objects.filter(
        negocio=producto.negocio, codigo_barras=codigo,
    ).exists():
        producto.codigo_barras = codigo
    producto.costo = compra
    producto.save()

    HistorialModificacionProducto.objects.create(
        producto=producto, usuario=producto.negocio.usuario,
        motivo="Importación de CSV: precios actualizados" + (" y producto validado" if era_pendiente else ""),
    )
    if cantidad > 0:
        return agregar_existencias(producto, cantidad, costo=compra, motivo="Importación de CSV", registrar_gasto=False)
    return Decimal("0")


def _crear(negocio, fila, cantidad, compra, venta, categorias):
    categoria = None
    nombre_categoria = fila["categoria"].strip()
    if nombre_categoria:
        categoria = categorias.get(busqueda.normalizar(nombre_categoria))
        if categoria is None:
            categoria = Categoria.objects.create(nombre=nombre_categoria[:60])
            categorias[busqueda.normalizar(nombre_categoria)] = categoria
    if categoria is None:
        # todo producto lleva una categoría válida: si el archivo no la trae, va en "Otros"
        categoria, _ = Categoria.objects.get_or_create(nombre="Otros", defaults={"icono": "📦"})

    codigo = fila["codigo_barras"]
    if codigo and Producto.objects.filter(negocio=negocio, codigo_barras=codigo).exists():
        codigo = ""  # ese código ya lo tiene otro producto: se agrega sin código

    a_granel = fila["a_granel"]
    if not a_granel:
        cantidad = cantidad.to_integral_value()  # por pieza: solo enteros
    nuevo = Producto.objects.create(
        negocio=negocio, nombre=fila["producto"], costo=compra, precio_venta=venta,
        cantidad_actual=cantidad, categoria=categoria, a_granel=a_granel, codigo_barras=codigo,
        icono=icono_para(fila["producto"], categoria),
    )
    registrar_movimiento(nuevo, nuevo.cantidad_actual, MovimientoInventario.Tipo.ENTRADA, motivo="Importación de CSV")
    return nuevo
