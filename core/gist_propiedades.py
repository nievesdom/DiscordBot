import os
import json
from github import Github

# Carga el token y el ID del Gist desde variables de entorno
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GIST_ID = os.getenv("GIST_ID")

if not GITHUB_TOKEN or not GIST_ID:
    raise ValueError("Faltan variables de entorno: GITHUB_TOKEN o GIST_ID")

# Cliente de GitHub
g = Github(GITHUB_TOKEN)
gist = g.get_gist(GIST_ID)


# Cargar las propiedades desde el Gist remoto
def cargar_propiedades():
    try:
        contenido = gist.files["propiedades.json"].content
        return json.loads(contenido)
    except Exception as e:
        print(f"[ERROR] No se pudo cargar propiedades desde el Gist: {type(e).__name__} - {e}")
        return {}


# Guardar propiedades en el Gist remoto
def guardar_propiedades(propiedades=None):
    try:
        if propiedades is None:
            propiedades = cargar_propiedades()

        nuevo_contenido = json.dumps(propiedades, ensure_ascii=False, indent=2)
        gist.edit(
            files={"propiedades.json": {"content": nuevo_contenido}}
        )
        print("[OK] Propiedades actualizadas en el Gist remoto.")
    except Exception as e:
        print(f"[ERROR] No se pudo guardar propiedades en el Gist: {type(e).__name__} - {e}")


# Obtener las cartas de un usuario específico en un servidor
def obtener_cartas_usuario(servidor_id, usuario_id):
    propiedades = cargar_propiedades()
    if servidor_id in propiedades and usuario_id in propiedades[servidor_id]:
        return propiedades[servidor_id][usuario_id]
    return []
