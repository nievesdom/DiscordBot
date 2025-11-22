import os
import json
from github import Github, InputFileContent
from github.GithubException import RateLimitExceededException

# Obtener el gist remoto
def get_gist():
    token = os.getenv("GITHUB_TOKEN")
    gist_id = os.getenv("SETTINGS_ID")

    if not token or not gist_id:
        raise ValueError("Faltan las variables de entorno GITHUB_TOKEN o SETTINGS_ID.")

    g = Github(token)
    return g.get_gist(gist_id)

# Cargar settings desde el Gist remoto
def cargar_settings():
    """Descarga y devuelve los settings guardados en el gist remoto."""
    try:
        print("[INFO] Cargando settings desde Gist...")
        gist = get_gist()
        contenido = gist.files["settings.json"].content
        datos = json.loads(contenido)
        print("[OK] Settings cargados correctamente.")
        return datos
    except Exception as e:
        print("[ERROR] cargar_settings:", e)
        return {}

# Guardar settings en el Gist remoto (función síncrona)
def guardar_settings(datos):
    """Sube los cambios al Gist, actualizando settings.json."""
    try:
        print("[INFO] Iniciando guardado de settings en Gist...")
        gist = get_gist()
        nuevo_contenido = json.dumps(datos, indent=2, ensure_ascii=False)
        gist.edit(files={"settings.json": InputFileContent(nuevo_contenido)})
        print("[OK] Settings actualizados correctamente en el Gist.")
    except RateLimitExceededException as e:
        # Lanzamos la excepción para que el cog la capture y avise en el servidor
        raise e
    except Exception as e:
        import traceback
        print("[ERROR] guardar_settings:", e)
        traceback.print_exc()
