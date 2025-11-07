import json
import random
import os

# Rangos de atributos por rareza
RANGOS = {
    "UR":  {"health": (900, 1200), "attack": (250, 350), "defense": (200, 300), "speed": (150, 200)},
    "KSR": {"health": (800, 1000), "attack": (220, 300), "defense": (180, 260), "speed": (130, 180)},
    "SSR": {"health": (650, 850),  "attack": (180, 250), "defense": (150, 220), "speed": (110, 160)},
    "SR":  {"health": (500, 700),  "attack": (140, 200), "defense": (120, 180), "speed": (90, 140)},
    "R":   {"health": (350, 550),  "attack": (100, 150), "defense": (80, 130),  "speed": (70, 110)},
    "N":   {"health": (200, 400),  "attack": (60, 100),  "defense": (50, 90),   "speed": (50, 90)},
}

# Ruta del archivo cartas.json
ARCHIVO_CARTAS = os.path.join("cartas", "cartas.json")

# Cargar cartas
with open(ARCHIVO_CARTAS, "r", encoding="utf-8") as f:
    cartas = json.load(f)

# Asignar atributos directamente al mismo nivel
for carta in cartas:
    rareza = carta.get("rareza", "N")
    rangos = RANGOS.get(rareza, RANGOS["N"])
    carta["health"] = random.randint(*rangos["health"])
    carta["attack"] = random.randint(*rangos["attack"])
    carta["defense"] = random.randint(*rangos["defense"])
    carta["speed"] = random.randint(*rangos["speed"])

# Guardar cambios directamente en cartas.json
with open(ARCHIVO_CARTAS, "w", encoding="utf-8") as f:
    json.dump(cartas, f, ensure_ascii=False, indent=2)

print("✅ Atributos añadidos directamente en cartas.json al mismo nivel")
