import os
import json
from github import Github, InputFileContent

# Cargar el gist remoto
def get_gist():
    token = os.getenv("GITHUB_TOKEN")
    gist_id = os.getenv("GIST_ID")

    if not token or not gist_id:
        raise ValueError("Faltan las variables de entorno GITHUB_TOKEN o GIST_ID.")

    g = Github(token)
    return g.get_gist(gist_id)

# Cargar propiedades desde el Gist remoto
def cargar_propiedades():
    """Descarga y devuelve las propiedades guardadas en el gist remoto."""
    try:
        print("[INFO] Cargando propiedades desde Gist...")
        gist = get_gist()
        contenido = gist.files["propiedades.json"].content
        datos = json.loads(contenido)
        print("[OK] Propiedades cargadas correctamente.")
        return datos
    except Exception as e:
        print("[ERROR] cargar_propiedades:", e)
        return {}

# Guardar propiedades en el Gist remoto
def guardar_propiedades(datos):
    """Sube los cambios al Gist, actualizando propiedades.json."""
    try:
        print("[INFO] Iniciando guardado en Gist...")
        gist = get_gist()
        nuevo_contenido = json.dumps(datos, indent=2, ensure_ascii=False)
        gist.edit(files={"propiedades.json": InputFileContent(nuevo_contenido)})
        print("[OK] Propiedades actualizadas correctamente en el Gist.")
    except Exception as e:
        import traceback
        print("[ERROR] guardar_propiedades:", e)
        traceback.print_exc()
