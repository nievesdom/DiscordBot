import json
import os

ARCHIVO_CARTAS = os.path.join("cartas", "cartas.json")

# Pedir datos al usuario
try:
    x = int(input("¿Cuántas cartas quieres ver en el ranking? "))
    rareza_objetivo = input("¿Qué rareza quieres analizar? (ej: UR, SSR, SR, R, N) ").strip()
except ValueError:
    print("Entrada inválida. Debes introducir un número para la cantidad.")
    exit()

# Cargar cartas
with open(ARCHIVO_CARTAS, "r", encoding="utf-8") as f:
    cartas = json.load(f)

# Filtrar por rareza
cartas_filtradas = [c for c in cartas if c.get("rareza") == rareza_objetivo]

if not cartas_filtradas:
    print(f"No se encontraron cartas con rareza {rareza_objetivo}")
    exit()

# Calcular total de stats
for c in cartas_filtradas:
    c["total_stats"] = c["health"] + c["attack"] + c["defense"] + c["speed"]

# Ordenar por total
cartas_ordenadas = sorted(cartas_filtradas, key=lambda c: c["total_stats"], reverse=True)

print(f"\n🏆 Top {x} cartas con mejores stats totales en rareza {rareza_objetivo}:")
for c in cartas_ordenadas[:x]:
    print(f"- {c['nombre']} (ID {c.get('id','?')}) → Total {c['total_stats']} → "
          f"H:{c['health']} A:{c['attack']} D:{c['defense']} S:{c['speed']}")

print(f"\n💀 Top {x} cartas con peores stats totales en rareza {rareza_objetivo}:")
for c in cartas_ordenadas[-x:]:
    print(f"- {c['nombre']} (ID {c.get('id','?')}) → Total {c['total_stats']} → "
          f"H:{c['health']} A:{c['attack']} D:{c['defense']} S:{c['speed']}")

# Mejor y peor carta por tipo
print(f"\n📊 Mejor y peor carta por tipo en rareza {rareza_objetivo}:")
for tipo in ["attack", "defense", "recovery", "support"]:
    cartas_tipo = [c for c in cartas_filtradas if c.get("tipo") == tipo]
    if cartas_tipo:
        mejor = max(cartas_tipo, key=lambda c: c["total_stats"])
        peor = min(cartas_tipo, key=lambda c: c["total_stats"])
        print(f"- {tipo.capitalize()}:")
        print(f"   🏆 Mejor: {mejor['nombre']} (ID {mejor.get('id','?')}) → Total {mejor['total_stats']} → "
              f"H:{mejor['health']} A:{mejor['attack']} D:{mejor['defense']} S:{mejor['speed']}")
        print(f"   💀 Peor: {peor['nombre']} (ID {peor.get('id','?')}) → Total {peor['total_stats']} → "
              f"H:{peor['health']} A:{peor['attack']} D:{peor['defense']} S:{peor['speed']}")

# Mejor y peor carta en cada stat individual
print(f"\n📊 Mejor y peor carta en cada stat dentro de rareza {rareza_objetivo}:")
for stat in ["health", "attack", "defense", "speed"]:
    mejor = max(cartas_filtradas, key=lambda c: c[stat])
    peor = min(cartas_filtradas, key=lambda c: c[stat])
    print(f"- {stat.capitalize()}:")
    print(f"   🏆 Mejor: {mejor['nombre']} (ID {mejor.get('id','?')}) → {stat.capitalize()} {mejor[stat]}")
    print(f"   💀 Peor: {peor['nombre']} (ID {peor.get('id','?')}) → {stat.capitalize()} {peor[stat]}")
