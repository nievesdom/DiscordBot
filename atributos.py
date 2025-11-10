import json
import os
import random

ARCHIVO_CARTAS = os.path.join("cartas", "cartas.json")
ARCHIVO_BOOSTS = os.path.join("cartas", "boosts_especiales.json")

# Rangos base por rareza
RANGOS_BASE = {
    "UR":  {"health": (900, 1200), "attack": (250, 350), "defense": (200, 300), "speed": (150, 210)},
    "SSR": {"health": (650, 850),  "attack": (170, 250), "defense": (140, 220), "speed": (110, 170)},
    "SR":  {"health": (500, 700),  "attack": (130, 200), "defense": (110, 180), "speed": (90, 150)},
    "R":   {"health": (350, 550),  "attack": (100, 160), "defense": (80, 140),  "speed": (70, 120)},
    "N":   {"health": (200, 400),  "attack": (60, 110),  "defense": (50, 100),  "speed": (50, 100)},
}

# Multiplicadores por tipo (diferencias más amplias entre tipos)
MULTIPLICADORES = {
    "attack":   {"health": 0.95, "attack": 1.15, "defense": 1.0,  "speed": 1.05},
    "defense":  {"health": 1.1,  "attack": 0.9,  "defense": 1.2,  "speed": 0.9},
    "recovery": {"health": 1.2,  "attack": 0.85, "defense": 1.05, "speed": 1.0},
    "support":  {"health": 1.0,  "attack": 1.0,  "defense": 0.95, "speed": 1.1},
}

# Probabilidad de boost especial
BOOST_PROB = 0.05
BOOST_SINGLE_RANGE = (1.12, 1.18)   # boost único más fuerte
BOOST_GLOBAL_RANGE = (1.05, 1.08)   # boost global más suave
REDUCTION_RANGE = (0.95, 0.98)      # reducción ligera en otros stats

# Bonus para cartas Holographic o Black
SPECIAL_NAME_BONUS = (1.05, 1.08)

# Cargar cartas
with open(ARCHIVO_CARTAS, "r", encoding="utf-8") as f:
    cartas = json.load(f)

registro_boosts = []

for carta in cartas:
    rareza = carta.get("rareza", "N")
    tipo = carta.get("tipo", "support")
    rangos = RANGOS_BASE.get(rareza, RANGOS_BASE["N"])
    mults = MULTIPLICADORES.get(tipo, MULTIPLICADORES["support"])

    # Generar stats base con menos disparidad (usar valores centrados)
    attrs = {}
    for stat, (low, high) in rangos.items():
        base = random.randint(low, high)
        attrs[stat] = int(base * mults[stat])

    stats_antes = attrs.copy()

    # Boost especial
    if random.random() < BOOST_PROB:
        if random.random() < 0.6:  # boost único
            stat = random.choice(list(attrs.keys()))
            factor = random.uniform(*BOOST_SINGLE_RANGE)
            attrs[stat] = int(attrs[stat] * factor)
            # Reducir ligeramente los demás
            for s in attrs:
                if s != stat:
                    reduction = random.uniform(*REDUCTION_RANGE)
                    attrs[s] = int(attrs[s] * reduction)
            boost_info = {"type": "single", "stat": stat, "factor": round(factor, 3)}
        else:  # boost global
            factor = random.uniform(*BOOST_GLOBAL_RANGE)
            for s in attrs:
                attrs[s] = int(attrs[s] * factor)
            boost_info = {"type": "global", "factor": round(factor, 3)}

        # Guardar registro del boost
        registro_boosts.append({
            "id": carta.get("id", "?"),
            "nombre": carta.get("nombre", "?"),
            "stats_antes": stats_antes,
            "boost": boost_info
        })

    # Bonus por nombre especial
    nombre = carta.get("nombre", "")
    if "Holographic" in nombre or "Black" in nombre:
        factor = random.uniform(*SPECIAL_NAME_BONUS)
        for s in attrs:
            attrs[s] = int(attrs[s] * factor)

    # Actualizar carta con stats finales
    carta.update(attrs)

# Guardar cartas finales
with open(ARCHIVO_CARTAS, "w", encoding="utf-8") as f:
    json.dump(cartas, f, ensure_ascii=False, indent=2)

# Guardar boosts especiales
with open(ARCHIVO_BOOSTS, "w", encoding="utf-8") as f:
    json.dump(registro_boosts, f, ensure_ascii=False, indent=2)

print("✅ Stats redistribuidos, boosts aplicados y guardados en boosts_especiales.json")
