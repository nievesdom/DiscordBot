import os
import json
import shutil
import random
import cv2
import numpy as np
import easyocr
from urllib.parse import quote

# =========================
# Configuración y constantes
# =========================

CARPETA_CARTAS = "cartas"
CARPETA_NUEVAS = os.path.join(CARPETA_CARTAS, "Nuevas")
JSON_PATH = os.path.join(CARPETA_CARTAS, "cartas.json")
BOOSTS_PATH = os.path.join(CARPETA_CARTAS, "boosts_especiales.json")

# URL base para Render (para exponer imágenes por HTTP)
BASE_URL = "https://discordbot-n4ts.onrender.com/cartas/"

# Colores → atributo
COLOR_TO_TIPO = {
    "red": "heart",
    "green": "technique",
    "blue": "body",
    "yellow": "light",
    "magenta": "shadow"
}

# OCR japonés para tipo
reader = easyocr.Reader(['ja'], gpu=False)
TRADUCCIONES = {
    "攻撃": "attack",
    "防御": "defense",
    "回復": "recovery",
    "補助": "support"
}

# Rangos base por rareza
RANGOS_BASE = {
    "UR":  {"health": (900, 1200), "attack": (250, 350), "defense": (200, 300), "speed": (150, 210)},
    "SSR": {"health": (650, 850),  "attack": (170, 250), "defense": (140, 220), "speed": (110, 170)},
    "SR":  {"health": (500, 700),  "attack": (130, 200), "defense": (110, 180), "speed": (90, 150)},
    "R":   {"health": (350, 550),  "attack": (100, 160), "defense": (80, 140),  "speed": (70, 120)},
    "N":   {"health": (200, 400),  "attack": (60, 110),  "defense": (50, 100),  "speed": (50, 100)},
}

# Multiplicadores por tipo
MULTIPLICADORES = {
    "attack":   {"health": 0.95, "attack": 1.15, "defense": 1.0,  "speed": 1.05},
    "defense":  {"health": 1.1,  "attack": 0.9,  "defense": 1.2,  "speed": 0.9},
    "recovery": {"health": 1.2,  "attack": 0.85, "defense": 1.05, "speed": 1.0},
    "support":  {"health": 1.0,  "attack": 1.0,  "defense": 0.95, "speed": 1.1},
}

# Boosts especiales
BOOST_PROB = 0.05
BOOST_SINGLE_RANGE = (1.12, 1.18)
BOOST_GLOBAL_RANGE = (1.05, 1.08)
REDUCTION_RANGE = (0.95, 0.98)
SPECIAL_NAME_BONUS = (1.05, 1.08)

# =========================
# Funciones auxiliares
# =========================

def detectar_color_predominante(imagen_path):
    """Detecta el color predominante en la esquina superior izquierda (80x80) de la carta."""
    img = cv2.imread(imagen_path)
    if img is None:
        return "error"
    recorte = img[0:80, 0:80]
    hsv = cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)

    h = hsv[:, :, 0].flatten()
    s = hsv[:, :, 1].flatten()
    v = hsv[:, :, 2].flatten()

    # Filtrar píxeles para evitar grises/blancos/negros
    mask = (s > 50) & (v > 50) & (v < 205)
    h_valid = h[mask]
    if len(h_valid) == 0:
        return "unknown"

    bins = {
        "red": ((h_valid <= 10) | (h_valid >= 174)).sum(),
        "yellow": ((h_valid >= 11) & (h_valid <= 45)).sum(),
        "green": ((h_valid >= 46) & (h_valid <= 80)).sum(),
        "blue": ((h_valid >= 81) & (h_valid <= 118)).sum(),
        "magenta": ((h_valid >= 119) & (h_valid <= 173)).sum()
    }
    return max(bins, key=bins.get)

def detectar_tipo(imagen_path):
    """Usa OCR para leer el tipo japonés en la zona superior fija y traducirlo a inglés."""
    img = cv2.imread(imagen_path)
    if img is None:
        return "indeterminado"

    # Coordenadas de la zona donde está el texto del tipo (ajustadas a tu plantilla)
    x1, y1, x2, y2 = 102, 23, 176, 57
    rect_top = img[y1:y2, x1:x2]

    resultado = reader.readtext(rect_top)
    if resultado:
        for (_, texto, prob) in resultado:
            texto = texto.strip()
            if texto in TRADUCCIONES:
                return TRADUCCIONES[texto]
    return "indeterminado"

def generar_stats_y_boosts(carta):
    """Genera stats finales de la carta y devuelve, si ocurre, el registro de boost aplicado."""
    rareza = carta.get("rareza", "N")
    tipo = carta.get("tipo", "support")

    rangos = RANGOS_BASE.get(rareza, RANGOS_BASE["N"])
    mults = MULTIPLICADORES.get(tipo, MULTIPLICADORES["support"])

    # Stats base aplicando multiplicadores por tipo
    attrs = {}
    for stat, (low, high) in rangos.items():
        base = random.randint(low, high)
        attrs[stat] = int(base * mults[stat])

    stats_antes = attrs.copy()
    boost_registro = None

    # Probabilidad de boost especial
    if random.random() < BOOST_PROB:
        if random.random() < 0.6:
            # Boost único fuerte
            stat = random.choice(list(attrs.keys()))
            factor = random.uniform(*BOOST_SINGLE_RANGE)
            attrs[stat] = int(attrs[stat] * factor)
            # Reducir ligeramente los otros stats
            for s in attrs:
                if s != stat:
                    reduction = random.uniform(*REDUCTION_RANGE)
                    attrs[s] = int(attrs[s] * reduction)
            boost_registro = {"type": "single", "stat": stat, "factor": round(factor, 3)}
        else:
            # Boost global suave
            factor = random.uniform(*BOOST_GLOBAL_RANGE)
            for s in attrs:
                attrs[s] = int(attrs[s] * factor)
            boost_registro = {"type": "global", "factor": round(factor, 3)}

    # Bonus por nombre especial
    nombre = carta.get("nombre", "")
    if "Holographic" in nombre or "Black" in nombre:
        factor = random.uniform(*SPECIAL_NAME_BONUS)
        for s in attrs:
            attrs[s] = int(attrs[s] * factor)

    # Aplicar stats a la carta
    carta.update(attrs)

    # Armar registro de boost si existió
    if boost_registro:
        return {
            "id": carta.get("id", "?"),
            "nombre": carta.get("nombre", "?"),
            "stats_antes": stats_antes,
            "boost": boost_registro
        }
    return None

# =========================
# Flujo principal
# =========================

def añadir_cartas():
    """Añade nuevas cartas desde cartas/Nuevas, moviendo imágenes, asignando IDs y completando datos."""
    # Cargar cartas existentes
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            try:
                cartas = json.load(f)
            except json.JSONDecodeError:
                cartas = []
    else:
        cartas = []

    # Preparar carpeta destino
    os.makedirs(CARPETA_CARTAS, exist_ok=True)
    os.makedirs(CARPETA_NUEVAS, exist_ok=True)

    # ID inicial a partir del máximo existente
    max_id = max((c.get("id", 0) for c in cartas), default=0)

    # Listar nuevas imágenes
    nuevas_imagenes = [f for f in os.listdir(CARPETA_NUEVAS) if f.lower().endswith(".png")]
    if not nuevas_imagenes:
        print("No se encontraron nuevas imágenes en cartas/Nuevas.")
        return

    nuevas_contadas = 0
    registro_boosts = []

    for imagen in nuevas_imagenes:
        # Nombre de carta = nombre del archivo sin .png
        nombre = imagen[:-4]  # remove .png
        # Rareza = primera palabra del nombre
        partes = nombre.split(" ", 1)
        rareza = partes[0] if partes and partes[0] else "N"

        # Asignar ID consecutivo
        max_id += 1

        # Mover imagen a cartas/
        origen = os.path.join(CARPETA_NUEVAS, imagen)
        destino = os.path.join(CARPETA_CARTAS, imagen)
        shutil.move(origen, destino)

        # Construir URL pública escapando el nombre
        url_imagen = BASE_URL + quote(imagen)

        # Detectar atributo por color
        color_pred = detectar_color_predominante(destino)
        atributo = COLOR_TO_TIPO.get(color_pred, "unknown")

        # Detectar tipo por OCR
        tipo = detectar_tipo(destino)

        # Crear estructura de carta (sin tocar las existentes)
        nueva_carta = {
            "id": max_id,
            "nombre": nombre,
            "rareza": rareza,
            "imagen": url_imagen,
            "atributo": atributo,
            "tipo": tipo
        }

        # Generar stats y posible boost
        boost = generar_stats_y_boosts(nueva_carta)
        if boost:
            registro_boosts.append(boost)

        # Añadir al final del JSON en memoria
        cartas.append(nueva_carta)
        nuevas_contadas += 1
        print(f"[*] Añadida: {nombre} (ID {max_id}, Rareza {rareza}, Atributo {atributo}, Tipo {tipo})")

    # Guardar cartas.json con las nuevas al final
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(cartas, f, ensure_ascii=False, indent=2)

    # Guardar registro de boosts (si hubo)
    if registro_boosts:
        with open(BOOSTS_PATH, "w", encoding="utf-8") as f:
            json.dump(registro_boosts, f, ensure_ascii=False, indent=2)
        print(f"✅ Boosts especiales guardados en {BOOSTS_PATH} ({len(registro_boosts)} registros).")

    print(f"✅ Se han añadido {nuevas_contadas} cartas nuevas a {JSON_PATH}.")

if __name__ == "__main__":
    añadir_cartas()
