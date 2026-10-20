"""
Datos con los que arranca el sistema: categorías de productos, un catálogo de abarrotes para
elegir al registrarse, proveedores comunes, categorías de gastos y los íconos de los productos.

Se cargan con `python manage.py seed_catalogo` (lo global) y, para cada tienda nueva, con
`preparar_negocio` (sus proveedores y sus categorías de gastos). Todo se puede repetir sin
duplicar nada.
"""
import re
import unicodedata

# (nombre, ícono)
CATEGORIAS = [
    ("Bebidas", "🥤"),
    ("Cervezas y licores", "🍺"),
    ("Botanas", "🍟"),
    ("Dulcería", "🍬"),
    ("Galletas", "🍪"),
    ("Panadería y tortillas", "🍞"),
    ("Abarrotes", "🍚"),
    ("Enlatados y conservas", "🥫"),
    ("Aceites, salsas y condimentos", "🧂"),
    ("Lácteos y huevo", "🥛"),
    ("Carnes frías y embutidos", "🥓"),
    ("Frutas y verduras", "🥬"),
    ("Congelados y helados", "🍦"),
    ("Cigarros", "🚬"),
    ("Limpieza del hogar", "🧴"),
    ("Higiene personal", "🧼"),
    ("Cuidado del bebé", "🍼"),
    ("Mascotas", "🐶"),
    ("Papelería y varios", "📎"),
    ("Otros", "📦"),
]

# (nombre, categoría, ícono, precio sugerido de venta)
PRODUCTOS = [
    # Bebidas
    ("Coca-Cola 600ml", "Bebidas", "🥤", 20.00),
    ("Coca-Cola 2L", "Bebidas", "🥤", 38.00),
    ("Coca-Cola 3L", "Bebidas", "🥤", 52.00),
    ("Pepsi 600ml", "Bebidas", "🥤", 18.00),
    ("Sprite 600ml", "Bebidas", "🥤", 19.00),
    ("Fanta Naranja 600ml", "Bebidas", "🥤", 19.00),
    ("Manzanita Sol 600ml", "Bebidas", "🥤", 18.00),
    ("Sidral Mundet 600ml", "Bebidas", "🥤", 18.00),
    ("Jarritos 600ml", "Bebidas", "🥤", 17.00),
    ("Agua Ciel 600ml", "Bebidas", "💧", 12.00),
    ("Agua Ciel 1.5L", "Bebidas", "💧", 17.00),
    ("Agua Bonafont 1L", "Bebidas", "💧", 15.00),
    ("Garrafón de agua 20L", "Bebidas", "💧", 45.00),
    ("Jugo Del Valle 1L", "Bebidas", "🧃", 28.00),
    ("Jugo Jumex lata 335ml", "Bebidas", "🧃", 14.00),
    ("Boing 500ml", "Bebidas", "🧃", 16.00),
    ("Gatorade 600ml", "Bebidas", "🥤", 24.00),
    ("Powerade 600ml", "Bebidas", "🥤", 22.00),
    ("Red Bull 250ml", "Bebidas", "⚡", 42.00),
    ("Monster 473ml", "Bebidas", "⚡", 38.00),
    ("Té Lipton 600ml", "Bebidas", "🍵", 20.00),
    ("Café Nescafé Clásico 50g", "Bebidas", "☕", 52.00),
    ("Leche en polvo Nido 360g", "Bebidas", "🥛", 85.00),
    ("Electrolit 625ml", "Bebidas", "🥤", 32.00),
    # Cervezas y licores
    ("Cerveza Corona 355ml", "Cervezas y licores", "🍺", 24.00),
    ("Cerveza Victoria 355ml", "Cervezas y licores", "🍺", 23.00),
    ("Cerveza Modelo 355ml", "Cervezas y licores", "🍺", 24.00),
    ("Cerveza Tecate 355ml", "Cervezas y licores", "🍺", 23.00),
    ("Cerveza Indio 355ml", "Cervezas y licores", "🍺", 22.00),
    ("Caguama Victoria 940ml", "Cervezas y licores", "🍺", 55.00),
    ("Tequila Jimador 700ml", "Cervezas y licores", "🥃", 260.00),
    ("Ron Bacardí 750ml", "Cervezas y licores", "🥃", 230.00),
    # Botanas
    ("Sabritas Original 45g", "Botanas", "🍟", 19.00),
    ("Sabritas Adobadas 45g", "Botanas", "🍟", 19.00),
    ("Doritos Nacho 62g", "Botanas", "🍟", 21.00),
    ("Cheetos Torciditos 52g", "Botanas", "🍟", 19.00),
    ("Ruffles Queso 50g", "Botanas", "🍟", 20.00),
    ("Takis Fuego 62g", "Botanas", "🌶️", 20.00),
    ("Churrumais 40g", "Botanas", "🍟", 16.00),
    ("Cacahuates Japoneses 100g", "Botanas", "🥜", 22.00),
    ("Palomitas para microondas", "Botanas", "🍿", 18.00),
    ("Pepitas de calabaza 60g", "Botanas", "🥜", 20.00),
    # Dulcería
    ("Chicles Trident", "Dulcería", "🍬", 12.00),
    ("Paleta Payaso", "Dulcería", "🍭", 17.00),
    ("Chocolate Carlos V", "Dulcería", "🍫", 9.00),
    ("Chocolate Hershey's barra", "Dulcería", "🍫", 20.00),
    ("Gomitas Panditas 30g", "Dulcería", "🍬", 14.00),
    ("Mazapán De la Rosa", "Dulcería", "🍬", 7.00),
    ("Pulparindo", "Dulcería", "🍬", 6.00),
    ("Vero Mango", "Dulcería", "🍭", 6.00),
    ("Duvalín", "Dulcería", "🍫", 6.00),
    ("Skwinkles", "Dulcería", "🍬", 10.00),
    ("Pastillas Halls", "Dulcería", "🍬", 9.00),
    ("Alegría", "Dulcería", "🍬", 8.00),
    # Galletas
    ("Galletas Marías Gamesa", "Galletas", "🍪", 14.00),
    ("Galletas Emperador", "Galletas", "🍪", 17.00),
    ("Galletas Oreo", "Galletas", "🍪", 17.00),
    ("Galletas Saladitas", "Galletas", "🍪", 22.00),
    ("Galletas Chokis", "Galletas", "🍪", 17.00),
    ("Marinela Gansito", "Galletas", "🍰", 18.00),
    ("Marinela Pinguinos", "Galletas", "🍰", 19.00),
    ("Barritas Marinela", "Galletas", "🍪", 17.00),
    # Panadería y tortillas
    ("Pan Bimbo Blanco grande", "Panadería y tortillas", "🍞", 48.00),
    ("Pan Bimbo Integral", "Panadería y tortillas", "🍞", 52.00),
    ("Pan para hamburguesa Bimbo", "Panadería y tortillas", "🍔", 42.00),
    ("Tortillas de maíz 1kg", "Panadería y tortillas", "🫓", 24.00),
    ("Tortillas de harina Tía Rosa", "Panadería y tortillas", "🫓", 38.00),
    ("Bolillo", "Panadería y tortillas", "🥖", 3.00),
    ("Pan dulce (concha)", "Panadería y tortillas", "🥐", 9.00),
    ("Tostadas Charras 12 pzas", "Panadería y tortillas", "🫓", 28.00),
    # Abarrotes
    ("Arroz 1kg", "Abarrotes", "🍚", 30.00),
    ("Frijol negro 1kg", "Abarrotes", "🫘", 34.00),
    ("Frijol pinto 1kg", "Abarrotes", "🫘", 36.00),
    ("Azúcar 1kg", "Abarrotes", "🍬", 30.00),
    ("Sal de mesa 1kg", "Abarrotes", "🧂", 14.00),
    ("Harina de trigo 1kg", "Abarrotes", "🌾", 26.00),
    ("Harina de maíz Maseca 1kg", "Abarrotes", "🌽", 24.00),
    ("Lentejas 500g", "Abarrotes", "🫘", 24.00),
    ("Garbanzo 500g", "Abarrotes", "🫘", 30.00),
    ("Sopa de pasta (fideo) 200g", "Abarrotes", "🍝", 9.00),
    ("Espagueti 200g", "Abarrotes", "🍝", 11.00),
    ("Sopa instantánea Maruchan", "Abarrotes", "🍜", 16.00),
    ("Avena 400g", "Abarrotes", "🥣", 28.00),
    ("Cereal Zucaritas 300g", "Abarrotes", "🥣", 65.00),
    ("Café soluble 100g", "Abarrotes", "☕", 78.00),
    ("Chocolate en polvo Choco Milk 350g", "Abarrotes", "🍫", 52.00),
    ("Gelatina en polvo", "Abarrotes", "🍮", 10.00),
    ("Canela en raja", "Abarrotes", "🌿", 8.00),
    # Enlatados y conservas
    ("Atún Dolores en agua 140g", "Enlatados y conservas", "🐟", 24.00),
    ("Sardina en tomate 155g", "Enlatados y conservas", "🐟", 22.00),
    ("Chiles jalapeños La Costeña 220g", "Enlatados y conservas", "🌶️", 19.00),
    ("Chipotles La Costeña 105g", "Enlatados y conservas", "🌶️", 17.00),
    ("Frijoles refritos La Sierra 430g", "Enlatados y conservas", "🥫", 28.00),
    ("Elote en lata 220g", "Enlatados y conservas", "🌽", 20.00),
    ("Chícharos con zanahoria 220g", "Enlatados y conservas", "🥫", 18.00),
    ("Puré de tomate 210g", "Enlatados y conservas", "🍅", 11.00),
    ("Durazno en almíbar 820g", "Enlatados y conservas", "🍑", 58.00),
    ("Leche condensada La Lechera", "Enlatados y conservas", "🥫", 32.00),
    # Aceites, salsas y condimentos
    ("Aceite vegetal 1L", "Aceites, salsas y condimentos", "🛢️", 46.00),
    ("Aceite de oliva 250ml", "Aceites, salsas y condimentos", "🫒", 95.00),
    ("Mayonesa McCormick 190g", "Aceites, salsas y condimentos", "🥫", 28.00),
    ("Catsup Heinz 400g", "Aceites, salsas y condimentos", "🍅", 36.00),
    ("Salsa Valentina 370ml", "Aceites, salsas y condimentos", "🌶️", 18.00),
    ("Salsa Tabasco", "Aceites, salsas y condimentos", "🌶️", 24.00),
    ("Mostaza 215g", "Aceites, salsas y condimentos", "🥫", 20.00),
    ("Consomé de pollo Knorr", "Aceites, salsas y condimentos", "🍲", 14.00),
    ("Pimienta molida", "Aceites, salsas y condimentos", "🌿", 9.00),
    ("Vinagre blanco 1L", "Aceites, salsas y condimentos", "🧂", 24.00),
    ("Salsa de soya 150ml", "Aceites, salsas y condimentos", "🥫", 22.00),
    # Lácteos y huevo
    ("Leche Lala entera 1L", "Lácteos y huevo", "🥛", 29.00),
    ("Leche Alpura deslactosada 1L", "Lácteos y huevo", "🥛", 31.00),
    ("Yogurt Danone 1L", "Lácteos y huevo", "🥛", 38.00),
    ("Yogurt Yoplait individual", "Lácteos y huevo", "🥛", 14.00),
    ("Crema Lala 200ml", "Lácteos y huevo", "🥛", 26.00),
    ("Queso Oaxaca 400g", "Lácteos y huevo", "🧀", 85.00),
    ("Queso panela 400g", "Lácteos y huevo", "🧀", 70.00),
    ("Queso crema Philadelphia 190g", "Lácteos y huevo", "🧀", 48.00),
    ("Mantequilla 90g", "Lácteos y huevo", "🧈", 28.00),
    ("Huevo (kilo)", "Lácteos y huevo", "🥚", 48.00),
    ("Huevo (pieza)", "Lácteos y huevo", "🥚", 4.50),
    # Carnes frías y embutidos
    ("Jamón de pavo 250g", "Carnes frías y embutidos", "🥓", 58.00),
    ("Salchicha Fud 500g", "Carnes frías y embutidos", "🌭", 62.00),
    ("Chorizo 250g", "Carnes frías y embutidos", "🥓", 48.00),
    ("Tocino 200g", "Carnes frías y embutidos", "🥓", 55.00),
    ("Mortadela 250g", "Carnes frías y embutidos", "🥓", 42.00),
    # Frutas y verduras
    ("Jitomate (kilo)", "Frutas y verduras", "🍅", 28.00),
    ("Cebolla (kilo)", "Frutas y verduras", "🧅", 26.00),
    ("Papa (kilo)", "Frutas y verduras", "🥔", 32.00),
    ("Limón (kilo)", "Frutas y verduras", "🍋", 38.00),
    ("Plátano (kilo)", "Frutas y verduras", "🍌", 28.00),
    ("Manzana (kilo)", "Frutas y verduras", "🍎", 55.00),
    ("Aguacate (kilo)", "Frutas y verduras", "🥑", 85.00),
    ("Chile serrano (kilo)", "Frutas y verduras", "🌶️", 60.00),
    ("Zanahoria (kilo)", "Frutas y verduras", "🥕", 22.00),
    ("Chayote (kilo)", "Frutas y verduras", "🥬", 24.00),
    ("Cilantro (manojo)", "Frutas y verduras", "🌿", 8.00),
    ("Ajo (cabeza)", "Frutas y verduras", "🧄", 6.00),
    # Congelados y helados
    ("Helado Holanda paleta", "Congelados y helados", "🍦", 18.00),
    ("Helado Nestlé bote 1L", "Congelados y helados", "🍨", 85.00),
    ("Hielo en bolsa 3kg", "Congelados y helados", "🧊", 30.00),
    ("Nuggets de pollo 400g", "Congelados y helados", "🍗", 95.00),
    ("Paleta de hielo", "Congelados y helados", "🍧", 10.00),
    # Cigarros
    ("Cigarros Marlboro caja 20", "Cigarros", "🚬", 80.00),
    ("Cigarros Camel caja 20", "Cigarros", "🚬", 78.00),
    ("Cigarros Delicados sin filtro", "Cigarros", "🚬", 62.00),
    ("Cerillos", "Cigarros", "🔥", 4.00),
    ("Encendedor", "Cigarros", "🔥", 15.00),
    # Limpieza del hogar
    ("Cloro Cloralex 950ml", "Limpieza del hogar", "🧴", 26.00),
    ("Fabuloso 1L", "Limpieza del hogar", "🧴", 32.00),
    ("Detergente en polvo Ariel 1kg", "Limpieza del hogar", "🧺", 48.00),
    ("Detergente Roma 500g", "Limpieza del hogar", "🧺", 24.00),
    ("Jabón Zote para ropa", "Limpieza del hogar", "🧼", 16.00),
    ("Jabón de trastes Axion 400g", "Limpieza del hogar", "🧽", 30.00),
    ("Suavizante Downy 800ml", "Limpieza del hogar", "🧴", 42.00),
    ("Escoba", "Limpieza del hogar", "🧹", 65.00),
    ("Fibra para trastes", "Limpieza del hogar", "🧽", 8.00),
    ("Bolsas para basura (paquete)", "Limpieza del hogar", "🗑️", 28.00),
    ("Insecticida Raid 400ml", "Limpieza del hogar", "🪲", 75.00),
    ("Limpiador Pinol 1L", "Limpieza del hogar", "🧴", 34.00),
    # Higiene personal
    ("Papel higiénico Regio 4 rollos", "Higiene personal", "🧻", 34.00),
    ("Papel higiénico Pétalo 12 rollos", "Higiene personal", "🧻", 98.00),
    ("Jabón de tocador Palmolive", "Higiene personal", "🧼", 16.00),
    ("Shampoo Head & Shoulders 375ml", "Higiene personal", "🧴", 68.00),
    ("Shampoo sachet", "Higiene personal", "🧴", 4.00),
    ("Pasta dental Colgate 75ml", "Higiene personal", "🪥", 32.00),
    ("Cepillo de dientes", "Higiene personal", "🪥", 28.00),
    ("Desodorante Rexona", "Higiene personal", "🧴", 52.00),
    ("Toallas sanitarias Saba", "Higiene personal", "🩸", 36.00),
    ("Rastrillo desechable", "Higiene personal", "🪒", 12.00),
    ("Pañuelos desechables", "Higiene personal", "🧻", 14.00),
    # Cuidado del bebé
    ("Pañales Huggies etapa 3 (paquete)", "Cuidado del bebé", "🍼", 185.00),
    ("Pañal suelto", "Cuidado del bebé", "🍼", 8.00),
    ("Toallitas húmedas bebé", "Cuidado del bebé", "🍼", 45.00),
    ("Leche en polvo infantil NAN", "Cuidado del bebé", "🍼", 320.00),
    ("Papilla Gerber", "Cuidado del bebé", "🍼", 22.00),
    # Mascotas
    ("Croquetas para perro (kilo)", "Mascotas", "🐶", 38.00),
    ("Croquetas para gato (kilo)", "Mascotas", "🐱", 48.00),
    ("Alimento en lata para perro", "Mascotas", "🐶", 32.00),
    # Papelería y varios
    ("Cuaderno profesional", "Papelería y varios", "📓", 32.00),
    ("Pluma Bic", "Papelería y varios", "🖊️", 7.00),
    ("Lápiz", "Papelería y varios", "✏️", 5.00),
    ("Pilas AA (par)", "Papelería y varios", "🔋", 28.00),
    ("Veladora", "Papelería y varios", "🕯️", 18.00),
    ("Recarga de tiempo aire", "Papelería y varios", "📱", 20.00),
    ("Foco LED", "Papelería y varios", "💡", 45.00),
    ("Cinta adhesiva", "Papelería y varios", "📎", 15.00),
]

# (nombre, categorías que surte)
PROVEEDORES = [
    ("Coca-Cola FEMSA", ["Bebidas"]),
    ("Pepsi / Bebidas Pepsico", ["Bebidas"]),
    ("Sabritas (Pepsico Alimentos)", ["Botanas", "Galletas"]),
    ("Barcel", ["Botanas", "Dulcería"]),
    ("Bimbo", ["Panadería y tortillas", "Galletas"]),
    ("Marinela", ["Galletas"]),
    ("Gamesa", ["Galletas"]),
    ("Grupo Lala", ["Lácteos y huevo"]),
    ("Alpura", ["Lácteos y huevo"]),
    ("Grupo Modelo", ["Cervezas y licores"]),
    ("Heineken México", ["Cervezas y licores"]),
    ("Nestlé", ["Abarrotes", "Lácteos y huevo", "Dulcería", "Congelados y helados"]),
    ("Gruma / Maseca", ["Abarrotes", "Panadería y tortillas"]),
    ("Herdez / McCormick", ["Enlatados y conservas", "Aceites, salsas y condimentos"]),
    ("La Costeña", ["Enlatados y conservas"]),
    ("Procter & Gamble", ["Higiene personal", "Limpieza del hogar", "Cuidado del bebé"]),
    ("Unilever", ["Higiene personal", "Limpieza del hogar", "Aceites, salsas y condimentos"]),
    ("Colgate-Palmolive", ["Higiene personal", "Limpieza del hogar"]),
    ("Kimberly-Clark", ["Higiene personal", "Cuidado del bebé"]),
    ("Central de Abasto (frutas y verduras)", ["Frutas y verduras"]),
    ("Mayorista de abarrotes de la zona", ["Abarrotes", "Enlatados y conservas", "Aceites, salsas y condimentos", "Papelería y varios"]),
    ("Distribuidor de cigarros", ["Cigarros"]),
    ("Autoservicio mayorista (Costco, Makro, Chedraui)", ["Abarrotes", "Limpieza del hogar", "Higiene personal"]),
    ("Carnicería y pollería de confianza", ["Carnes frías y embutidos"]),
]

# (nombre, tipo) del gasto: así se propone fijo o variable al elegir la categoría
CATEGORIAS_DE_GASTO = [
    ("Renta del local", "FIJO"),
    ("Luz", "FIJO"),
    ("Agua", "FIJO"),
    ("Gas", "FIJO"),
    ("Internet y teléfono", "FIJO"),
    ("Sueldos y ayudantes", "FIJO"),
    ("Contador e impuestos", "FIJO"),
    ("Permisos y licencias", "FIJO"),
    ("Seguridad y vigilancia", "FIJO"),
    ("Sistema o aplicaciones", "FIJO"),
    ("Bolsas y empaques", "VARIABLE"),
    ("Transporte y fletes", "VARIABLE"),
    ("Limpieza del local", "VARIABLE"),
    ("Mantenimiento y reparaciones", "VARIABLE"),
    ("Publicidad y volantes", "VARIABLE"),
    ("Comisión de terminal bancaria", "VARIABLE"),
    ("Mermas y caducados", "VARIABLE"),
    ("Papelería", "VARIABLE"),
    ("Imprevistos", "VARIABLE"),
]

# íconos que se ofrecen al dar de alta un producto
ICONOS = [
    "🥤", "💧", "🧃", "☕", "🍵", "🥛", "🍺", "🥃", "🍷", "⚡", "🍟", "🌶️", "🍿", "🥜", "🍬", "🍭", "🍫", "🍪",
    "🍰", "🍞", "🥖", "🥐", "🫓", "🍚", "🫘", "🌾", "🌽", "🍝", "🍜", "🥣", "🍲", "🥫", "🐟", "🛢️", "🧂", "🫒",
    "🧀", "🧈", "🥚", "🥓", "🌭", "🍗", "🥩", "🍅", "🧅", "🥔", "🍋", "🍌", "🍎", "🥑", "🥕", "🥬", "🧄", "🍦",
    "🍨", "🧊", "🚬", "🔥", "🧴", "🧼", "🧽", "🧹", "🧺", "🗑️", "🧻", "🪥", "🪒", "🍼", "🐶", "🐱", "📓", "🖊️",
    "🔋", "🕯️", "💡", "📱", "📎", "📦",
]

# palabras del nombre -> ícono (se busca la primera que aparezca)
ICONOS_POR_PALABRA = [
    # primero las frases, para que no las gane una palabra suelta
    ("pasta dental", "🪥"), ("papel higienico", "🧻"), ("jabon de trastes", "🧽"), ("red bull", "⚡"),
    ("leche en polvo", "🥛"), ("cigarros", "🚬"),
    ("coca", "🥤"), ("pepsi", "🥤"), ("sprite", "🥤"), ("fanta", "🥤"), ("refresco", "🥤"), ("sidral", "🥤"),
    ("jarritos", "🥤"), ("manzanita", "🥤"), ("gatorade", "🥤"), ("electrolit", "🥤"),
    ("agua", "💧"), ("garrafon", "💧"), ("jugo", "🧃"), ("boing", "🧃"),
    ("monster", "⚡"), ("cafe", "☕"), ("te ", "🍵"),
    ("cerveza", "🍺"), ("caguama", "🍺"), ("corona", "🍺"), ("victoria", "🍺"), ("modelo", "🍺"),
    ("tequila", "🥃"), ("ron ", "🥃"), ("whisky", "🥃"), ("vodka", "🥃"), ("vino", "🍷"),
    ("cigarro", "🚬"), ("encendedor", "🔥"), ("cerillo", "🔥"),
    ("sabritas", "🍟"), ("papas", "🍟"), ("doritos", "🍟"), ("cheetos", "🍟"), ("ruffles", "🍟"), ("takis", "🌶️"),
    ("palomitas", "🍿"), ("cacahuate", "🥜"), ("pepita", "🥜"),
    ("chicle", "🍬"), ("dulce", "🍬"), ("gomita", "🍬"), ("paleta", "🍭"), ("chocolate", "🍫"), ("mazapan", "🍬"),
    ("galleta", "🍪"), ("oreo", "🍪"), ("gansito", "🍰"), ("pastel", "🍰"),
    ("pan ", "🍞"), ("bolillo", "🥖"), ("concha", "🥐"), ("tortilla", "🫓"), ("tostada", "🫓"),
    ("arroz", "🍚"), ("frijol", "🫘"), ("lenteja", "🫘"), ("garbanzo", "🫘"), ("harina", "🌾"), ("maiz", "🌽"),
    ("sopa", "🍜"), ("espagueti", "🍝"), ("pasta ", "🍝"), ("avena", "🥣"), ("cereal", "🥣"),
    ("atun", "🐟"), ("sardina", "🐟"), ("lata", "🥫"), ("enlatado", "🥫"), ("mayonesa", "🥫"),
    ("aceite", "🛢️"), ("sal ", "🧂"), ("azucar", "🍬"), ("pimienta", "🧂"), ("vinagre", "🧂"),
    ("salsa", "🌶️"), ("chile", "🌶️"), ("catsup", "🍅"),
    ("leche", "🥛"), ("yogurt", "🥛"), ("crema", "🥛"), ("queso", "🧀"), ("mantequilla", "🧈"), ("huevo", "🥚"),
    ("jamon", "🥓"), ("salchicha", "🌭"), ("chorizo", "🥓"), ("tocino", "🥓"), ("pollo", "🍗"), ("carne", "🥩"),
    ("jitomate", "🍅"), ("tomate", "🍅"), ("cebolla", "🧅"), ("papa ", "🥔"), ("limon", "🍋"), ("platano", "🍌"),
    ("manzana", "🍎"), ("aguacate", "🥑"), ("zanahoria", "🥕"), ("ajo", "🧄"), ("verdura", "🥬"),
    ("helado", "🍦"), ("hielo", "🧊"),
    ("cloro", "🧴"), ("fabuloso", "🧴"), ("pinol", "🧴"), ("suavizante", "🧴"), ("detergente", "🧺"),
    ("jabon", "🧼"), ("fibra", "🧽"), ("escoba", "🧹"), ("basura", "🗑️"),
    ("panuelo", "🧻"), ("shampoo", "🧴"), ("desodorante", "🧴"),
    ("cepillo", "🪥"), ("rastrillo", "🪒"),
    ("panal", "🍼"), ("bebe", "🍼"), ("gerber", "🍼"),
    ("perro", "🐶"), ("croqueta", "🐶"), ("gato", "🐱"),
    ("cuaderno", "📓"), ("pluma", "🖊️"), ("lapiz", "✏️"), ("pila", "🔋"), ("veladora", "🕯️"), ("foco", "💡"),
    ("recarga", "📱"),
]


def _sin_acentos(texto):
    texto = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in texto if unicodedata.category(c) != "Mn").lower()


def icono_para(nombre, categoria=None):
    """El ícono de un producto: por una palabra de su nombre (coca, leche, jabón…); si ninguna
    aparece, el de su categoría; y si tampoco hay, la caja 📦."""
    texto = " " + _sin_acentos(nombre) + " "
    for palabra, icono in ICONOS_POR_PALABRA:
        # la palabra tiene que empezar donde empieza una palabra del nombre (así "te " no cae en "colgate")
        if re.search(r"(?<![a-z0-9])" + re.escape(palabra), texto):
            return icono
    if categoria is not None and getattr(categoria, "icono", ""):
        return categoria.icono
    return "📦"


def cargar_categorias():
    """Crea las categorías de productos que falten. Regresa {nombre: categoría}."""
    from .models import Categoria

    categorias = {}
    for nombre, icono in CATEGORIAS:
        categorias[nombre], _ = Categoria.objects.get_or_create(nombre=nombre, defaults={"icono": icono})
    return categorias


def cargar_catalogo():
    """Crea las categorías y los productos del catálogo que se ofrece al registrar una tienda.
    Regresa (categorías, productos nuevos)."""
    from .models import ProductoCatalogo

    categorias = cargar_categorias()
    nuevos = 0
    for nombre, categoria, icono, precio in PRODUCTOS:
        _, creado = ProductoCatalogo.objects.get_or_create(
            nombre=nombre, defaults={"categoria": categorias[categoria], "icono": icono, "precio_sugerido": precio},
        )
        nuevos += int(creado)
    return len(categorias), nuevos


def preparar_negocio(negocio):
    """Deja lista una tienda nueva: sus proveedores más comunes y sus categorías de gastos.
    No toca lo que la tienda ya tenga. Regresa (proveedores nuevos, categorías de gasto nuevas)."""
    from finanzas.models import CategoriaGasto

    from .models import Proveedor

    categorias = cargar_categorias()
    proveedores_nuevos = 0
    for nombre, surte in PROVEEDORES:
        proveedor, creado = Proveedor.objects.get_or_create(negocio=negocio, nombre=nombre)
        if creado:
            proveedores_nuevos += 1
            proveedor.categorias.set([categorias[c] for c in surte])

    gastos_nuevos = 0
    for nombre, tipo in CATEGORIAS_DE_GASTO:
        _, creada = CategoriaGasto.objects.get_or_create(negocio=negocio, nombre=nombre, defaults={"tipo": tipo})
        gastos_nuevos += int(creada)
    return proveedores_nuevos, gastos_nuevos
