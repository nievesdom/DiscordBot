import json
import os

# Archivo de propiedades, donde se guardan las cartas y sus propietarios
DATA_FILE = "data/propiedades.json"

# Cargar propiedades
def cargar_propiedades():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {}

# Guardar las propiedades en el archivo (o gist remoto)
def guardar_propiedades(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Leer las cartas poseídas por un usuario
def obtener_cartas_usuario(servidor_id, usuario_id):
    propiedades = cargar_propiedades()
    return propiedades.get(servidor_id, {}).get(usuario_id, [])
