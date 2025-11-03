import json
import os

# Archivo de propiedades, donde se guardan las cartas y sus propietarios
DATA_FILE = "data/propiedades.json"

# Cargar propiedades
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        propiedades = json.load(f)
else:
    propiedades = {}

# Guardar las propiedades en el archivo
def guardar_propiedades():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(propiedades, f, ensure_ascii=False, indent=2)

# Leer las cartas poseídas por un usuario
def obtener_cartas_usuario(servidor_id, usuario_id):
    return propiedades.get(servidor_id, {}).get(usuario_id, [])
