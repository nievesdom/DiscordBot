import json
import random
import os
from collections import defaultdict

RANGOS_BASE = {
    "UR":  {"health": (850, 1300), "attack": (230, 370), "defense": (180, 320), "speed": (140, 220)},
    "KSR": {"health": (750, 1100), "attack": (200, 320), "defense": (160, 280), "speed": (120, 200)},
    "SSR": {"health": (600, 900),  "attack": (160, 270), "defense": (130, 240), "speed": (100, 180)},
    "SR":  {"health": (450, 750),  "attack": (120, 220), "defense": (100, 200), "speed": (80, 160)},
    "R":   {"health": (300, 600),  "attack": (90, 170),  "defense": (70, 150),  "speed": (60, 130)},
    "N":   {"health": (150, 450),  "attack": (50, 120),  "defense": (40, 110),  "speed": (40, 110)},
}

MULTIPLICADORES = {
    "attack":   {"health": 0.9,  "attack": 1.2,  "defense": 1.0, "speed": 1.0},
    "defense":  {"health": 1.1,  "attack": 0.9,  "defense": 1.2, "speed": 0.9},
    "recovery": {"health": 1.2,  "attack": 0.85, "defense": 1.0, "speed": 1.0},
    "support":  {"health": 1.0,  "attack": 1.0,  "defense": 0.9, "speed": 1.1},
}

BOOST_PROB = 0.05
BOOST_SINGLE_RANGE = (1.10, 1.15)   # +10% a +15% en un stat
REDUCTION_RANGE = (0.95, 0.98)      # −2% a −5% en los demás
BOOST_GLOBAL_RANGE = (1.03, 1.05)   # +3% a +5% en todos
BOOST_CAP = 1.20                    # nunca más de +20%

ARCHIVO_CARTAS = os.path.join("cartas", "cartas.json")

with open(ARCHIVO_CARTAS, "r", encoding="utf-8") as f:
    cartas = json.load(f)

# Estadísticas por tipo
stats_por_tipo = defaultdict(lambda: {
    "health":0,"attack":0,"defense":0,"speed":0,"count":0,
    "mejor":{"nombre":None,"total":-1,"stats":{}},
    "peor":{"nombre":None,"total":10**9,"stats":{}}
})

for carta in cartas:
    rareza = carta.get("rareza", "N")
    tipo = carta.get("tipo", "support")
    rangos = RANGOS_BASE.get(rareza, RANGOS_BASE["N"])
    mults = MULTIPLICADORES.get(tipo, MULTIPLICADORES["support"])

    # Base aleatoria
    attrs = {
        "health": int(random.randint(*rangos["health"]) * mults["health"]),
        "attack": int(random.randint(*rangos["attack"]) * mults["attack"]),
        "defense": int(random.randint(*rangos["defense"]) * mults["defense"]),
        "speed": int(random.randint(*rangos["speed"]) * mults["speed"]),
    }

    # Boost aleatorio
    if random.random() < BOOST_PROB:
        if random.random() < 0.6:  # boost único
            stat = random.choice(list(attrs.keys()))
            factor = random.uniform(*BOOST_SINGLE_RANGE)
            attrs[stat] = min(int(attrs[stat] * factor), int(attrs[stat] * BOOST_CAP))
            for s in attrs:
                if s != stat:
                    reduction = random.uniform(*REDUCTION_RANGE)
                    attrs[s] = int(attrs[s] * reduction)
            carta["boost"] = {"type": "single", "stat": stat, "factor": round(factor, 3)}
        else:  # boost global
            factor = random.uniform(*BOOST_GLOBAL_RANGE)
            for s in attrs:
                attrs[s] = min(int(attrs[s] * factor), int(attrs[s] * BOOST_CAP))
            carta["boost"] = {"type": "global", "factor": round(factor, 3)}

    carta.update(attrs)

    # Actualizar estadísticas por tipo
    stats_por_tipo[tipo]["health"] += attrs["health"]
    stats_por_tipo[tipo]["attack"] += attrs["attack"]
    stats_por_tipo[tipo]["defense"] += attrs["defense"]
    stats_por_tipo[tipo]["speed"] += attrs["speed"]
    stats_por_tipo[tipo]["count"] += 1

    # Calcular total de stats
    total = attrs["health"] + attrs["attack"] + attrs["defense"] + attrs["speed"]

    # Mejor y peor carta dentro del tipo
    if total > stats_por_tipo[tipo]["mejor"]["total"]:
        stats_por_tipo[tipo]["mejor"] = {"nombre": carta["nombre"], "total": total, "stats": attrs.copy()}
    if total < stats_por_tipo[tipo]["peor"]["total"]:
        stats_por_tipo[tipo]["peor"] = {"nombre": carta["nombre"], "total": total, "stats": attrs.copy()}

# Guardar cambios
with open(ARCHIVO_CARTAS, "w", encoding="utf-8") as f:
    json.dump(cartas, f, ensure_ascii=False, indent=2)

# Mostrar resumen
print("\n📊 Medias de stats por tipo:")
for tipo, datos in stats_por_tipo.items():
    if datos["count"] > 0:
        print(f"- {tipo.capitalize()}: "
              f"Health {datos['health']//datos['count']}, "
              f"Attack {datos['attack']//datos['count']}, "
              f"Defense {datos['defense']//datos['count']}, "
              f"Speed {datos['speed']//datos['count']}")
        print(f"   🏆 Mejor carta: {datos['mejor']['nombre']} → Total {datos['mejor']['total']} → {datos['mejor']['stats']}")
        print(f"   💀 Peor carta: {datos['peor']['nombre']} → Total {datos['peor']['total']} → {datos['peor']['stats']}")
