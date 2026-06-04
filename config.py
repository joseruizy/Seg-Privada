"""
Configuración del monitor de Mercado Público — Equipos de Seguridad (Mitosis).

Foco: licitaciones de equipos y personal de seguridad, agrupadas en 3
categorías temáticas. El correo presenta una sección por categoría con
las licitaciones nuevas que matchearon.

Keywords de múltiples palabras (ej. "chalecos antibalas") se evalúan
como frase exacta (substring con espacios). Keywords de una palabra se
buscan como substring simple.

Una misma licitación puede aparecer en más de una sección si matchea
keywords de distintas categorías.
"""

# Tipos de licitación monitoreados
TIPOS_ACTIVOS = {"LS", "L1", "LE", "LP"}

# Categorías y sus keywords (lógica OR dentro de cada categoría)
CATEGORIAS = [
    {
        "nombre": "1. Guardias y vigilantes",
        "keywords": ["guardias", "vigilantes"],
    },
    {
        "nombre": "2. Elementos defensivos y de protección",
        "keywords": ["elementos defensivos", "elementos de protección"],
    },
    {
        "nombre": "3. Chalecos de protección",
        "keywords": ["chalecos anticortes", "chalecos antibalas"],
    },
]
