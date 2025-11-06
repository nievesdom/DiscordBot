import os
import json
from github import Github

# Variables de entorno que debes tener configuradas en Render
# GITHUB_TOKEN = tu token personal
# GIST_ID = el id del gist donde se guarda propiedades.json

def get_client():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("No se encontró la variable de entorno GITHUB_TOKEN.")
    return Github(token)

def get_gist():
    gist_id = os.getenv("GIST_ID")
    if not gist_id:
        raise ValueError("No se encontró la variable de entorno GIST_ID.")
    g = get_client()
    gist = g.get_gist(gist_id)
    return gist

# -------------------------------------------------------

def cargar_propiedades():
    """Descarga el contenido del gist y lo devuelve como dict."""
    try:
        gist = get_gist()
        contenido = gist.files["propiedades.json"].content
        return json.loads(contenido)
    except Exception as e:
        print(f"[ERROR] cargar_propiedades: {e}")
        return {}  # Devuelve un dict vacío si no puede cargar

def guardar_propiedades(datos):
    """Sube los cambios al gist, actualizando propiedades.json."""
    try:
        print("[INFO] Iniciando guardado en Gist...")  # visible en logs
        gist = get_gist()
        nuevo_contenido = json.dumps(datos, indent=2, ensure_ascii=False)
        gist.edit(files={"propiedades.json": {"content": nuevo_contenido}})
        print("[OK] Propiedades actualizadas correctamente en el Gist.")
    except Exception as e:
        import traceback
        print("[ERROR] guardar_propiedades:", e)
        traceback.print_exc()


# -------------------------------------------------------

def obtener_cartas_usuario(servidor_id, usuario_id):
    """Devuelve lista de IDs de cartas del usuario."""
    propiedades = cargar_propiedades()
    if servidor_id in propiedades and usuario_id in propiedades[servidor_id]:
        return propiedades[servidor_id][usuario_id]
    return []
