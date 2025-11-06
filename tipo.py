import cv2
import numpy as np
import os
import json
from collections import Counter

CARPETA_CARTAS = "cartas"
JSON_PATH = os.path.join(CARPETA_CARTAS, "cartas.json")

COLOR_TO_TIPO = {
    "red": "heart",
    "green": "technique",
    "blue": "body",
    "yellow": "yang",
    "magenta": "yin"
}

def detectar_color_predominante(imagen_path):
    img = cv2.imread(imagen_path)
    if img is None:
        return "error"

    # Recorte 80x80 en esquina superior izquierda
    recorte = img[0:80, 0:80]
    hsv = cv2.cvtColor(recorte, cv2.COLOR_BGR2HSV)

    h = hsv[:, :, 0].flatten()
    s = hsv[:, :, 1].flatten()
    v = hsv[:, :, 2].flatten()

    # Filtrar píxeles válidos (evitar grises/blancos/negros)
    mask = (s > 50) & (v > 50) & (v < 205)
    h_valid = h[mask]

    if len(h_valid) == 0:
        return "unknown"

    # Rangos más agresivos para balancear proporciones
    bins = {
        "red": ((h_valid <= 10) | (h_valid >= 174)).sum(),       # más estrecho
        "yellow": ((h_valid >= 11) & (h_valid <= 45)).sum(),     # ampliado
        "green": ((h_valid >= 46) & (h_valid <= 80)).sum(),      # estable
        "blue": ((h_valid >= 81) & (h_valid <= 118)).sum(),      # recortado
        "magenta": ((h_valid >= 119) & (h_valid <= 173)).sum()   # recortado
    }

    color = max(bins, key=bins.get)
    return color

def actualizar_json():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        cartas = json.load(f)

    tipos_detectados = []
    cartas_unknown = []

    for carta in cartas:
        nombre_archivo = f"{carta['nombre']}.png"
        ruta_img = os.path.join(CARPETA_CARTAS, nombre_archivo)

        if os.path.exists(ruta_img):
            color = detectar_color_predominante(ruta_img)
            tipo = COLOR_TO_TIPO.get(color, "unknown")
            carta["tipo"] = tipo
            if tipo != "unknown" and tipo is not None:
                tipos_detectados.append(tipo)
            else:
                cartas_unknown.append(carta["nombre"])
        else:
            carta["tipo"] = None
            cartas_unknown.append(carta["nombre"])

    # Guardar cambios en cartas.json
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(cartas, f, indent=2, ensure_ascii=False)

    # Resumen
    conteo = Counter(tipos_detectados)
    print("📊 Resumen de tipos detectados:")
    for tipo, cantidad in conteo.items():
        print(f"   {tipo}: {cantidad} cartas")

    # Mostrar cartas desconocidas
    if cartas_unknown:
        print("\n⚠️ Cartas sin tipo detectado (unknown o no encontradas):")
        for nombre in cartas_unknown:
            print(f"   - {nombre}")

if __name__ == "__main__":
    actualizar_json()
    print("✅ cartas.json actualizado con propiedad 'tipo' usando histograma de Hue ajustado")
