"""
Búsqueda de productos. La usan la caja (búsqueda manual) y el asistente, así los dos
encuentran lo mismo. Entiende:

  * mayúsculas y acentos ("jabon" encuentra "Jabón Zote")
  * palabras en otro orden ("600 coca" encuentra "Coca-Cola 600ml")
  * plurales ("cocas")
  * errores de dedo ("jbon" o "sabrtas" encuentran Jabón y Sabritas)

El catálogo del negocio se guarda en el cache (ver core/cache_negocio.py), así que
buscar no consulta la base de datos en cada letra.
"""
import unicodedata
from difflib import SequenceMatcher

from core import cache_negocio

from .models import Producto

# palabras que no ayudan a encontrar un producto ("agua DE 1.5 litros")
PALABRAS_VACIAS = {"de", "del", "la", "el", "los", "las", "un", "una", "unos", "unas", "para", "con", "y", "en", "por", "al"}

# qué tan parecida debe ser una palabra mal escrita para aceptarla (0 a 1)
PARECIDO_MINIMO = 0.8


def normalizar(texto):
    """Minúsculas y sin acentos, para que 'jabon' encuentre 'Jabón'."""
    descompuesto = unicodedata.normalize("NFD", str(texto))
    sin_acentos = "".join(letra for letra in descompuesto if unicodedata.category(letra) != "Mn")
    return sin_acentos.lower().strip()


def catalogo(negocio):
    """Lista de productos activos del negocio, guardada en el cache."""
    def armar():
        productos = Producto.objects.filter(negocio=negocio, activo=True).values(
            "id", "nombre", "icono", "precio_venta", "cantidad_actual", "cantidad_minima", "a_granel", "codigo_barras",
        )
        lista = []
        for p in productos:
            buscable = normalizar(p["nombre"])
            lista.append({
                "id": p["id"],
                "nombre": p["nombre"],
                "icono": p["icono"],
                "buscable": buscable,
                "palabras": buscable.replace("-", " ").split(),
                "precio": float(p["precio_venta"]),
                "stock": float(p["cantidad_actual"]),
                "minimo": float(p["cantidad_minima"]),
                "a_granel": p["a_granel"],
                "codigo": p["codigo_barras"],
            })
        return lista
    return cache_negocio.obtener(negocio, "catalogo", armar)


def _coincidencias(productos, palabras):
    return [p for p in productos if all(palabra in p["buscable"] for palabra in palabras)]


def _parece_a(consulta, palabra):
    """True si `consulta` parece una palabra mal escrita de `palabra` (o del inicio de la palabra)."""
    if len(consulta) < 4:
        return False
    # para ahorrar tiempo solo se comparan palabras de largo parecido que empiecen con la misma letra
    # (o cuya segunda letra coincida, por si el error está en la primera)
    if abs(len(consulta) - len(palabra)) > 4:
        return False
    if consulta[0] != palabra[0] and consulta[1:2] != palabra[1:2]:
        return False
    for candidata in (palabra, palabra[:len(consulta)], palabra[:len(consulta) + 1]):
        if SequenceMatcher(None, consulta, candidata).ratio() >= PARECIDO_MINIMO:
            return True
    return False


def _con_errores_de_dedo(productos, palabras):
    """Productos donde cada palabra buscada aparece (aunque sea mal escrita). Los que
    tienen más palabras escritas bien van primero."""
    vocabulario = {palabra for p in productos for palabra in p["palabras"]}
    equivalentes = []
    for buscada in palabras:
        iguales = {v for v in vocabulario if buscada in v or _parece_a(buscada, v)}
        if not iguales:
            return []
        equivalentes.append((buscada, iguales))

    encontrados = []
    for p in productos:
        conjunto = set(p["palabras"])
        if all(conjunto & iguales for _, iguales in equivalentes):
            exactas = sum(1 for buscada, _ in equivalentes if buscada in p["buscable"])
            encontrados.append((-exactas, p["nombre"], p))
    encontrados.sort(key=lambda fila: (fila[0], fila[1]))
    return [fila[2] for fila in encontrados]


def encontrar(negocio, texto):
    """Todos los productos que coinciden con `texto`, los más parecidos primero."""
    palabras = normalizar(texto).split()
    # se quitan las palabras vacías, salvo que sea lo único que escribieron
    palabras = [p for p in palabras if p not in PALABRAS_VACIAS] or palabras
    if not palabras:
        return []

    productos = catalogo(negocio)
    encontrados = _coincidencias(productos, palabras)

    # "cocas" -> "coca": si no salió nada, se prueba con las palabras en singular
    if not encontrados:
        singulares = [p[:-1] if len(p) > 3 and p.endswith("s") else p for p in palabras]
        encontrados = _coincidencias(productos, singulares)

    # "agua ciel 1.5 litros" -> "Agua Ciel 1.5L": si no salió nada, se acepta que falte una palabra
    if not encontrados and len(palabras) >= 3:
        puntos = [(sum(1 for p in palabras if p in prod["buscable"]), prod) for prod in productos]
        mejor = max((punto for punto, _ in puntos), default=0)
        if mejor >= len(palabras) - 1:
            encontrados = [prod for punto, prod in puntos if punto == mejor]

    # "jbon", "sabrtas": por último se toleran errores de dedo
    if not encontrados:
        encontrados = _con_errores_de_dedo(productos, palabras)

    exactos = [p for p in encontrados if p["buscable"] == " ".join(palabras)]
    return exactos or encontrados


def buscar(negocio, texto, limite=5):
    return encontrar(negocio, texto)[:limite]


def por_codigo(negocio, codigo):
    """El producto cuyo código de barras es `codigo`, o None."""
    codigo = str(codigo).strip()
    if not codigo:
        return None
    for p in catalogo(negocio):
        if p["codigo"] == codigo:
            return p
    return None
