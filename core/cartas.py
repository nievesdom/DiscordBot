import json
import os

# Cargar cartas desde cartas.json
def cargar_cartas():
    ruta = os.path.join("cartas", "cartas.json")
    # Verifica si el archivo existe; si no, devuelve una lista vacía
    if not os.path.exists(ruta):
        return []
    # Abre el archivo y carga su contenido como una lista de diccionarios
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)

# Devuelve un diccionario de cartas indexadas por su ID
def cartas_por_id():
    cartas = cargar_cartas()
    return {str(c["id"]): c for c in cartas}
