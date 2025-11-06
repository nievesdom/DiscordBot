import os
import json
from github import Github

# Cargar las variables de entorno
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GIST_ID = os.getenv("GIST_ID")

def cargar_propiedades():
    """Descarga el archivo propiedades.json desde el Gist."""
    if not GITHUB_TOKEN or not GIST_ID:
        raise ValueError("Faltan las variables de entorno GITHUB_TOKEN o GIST_ID")

    g = Github(GITHUB_TOKEN)
    gist = g.get_gist(GIST_ID)
    contenido = gist.files["propiedades.json"].content
    return json.loads(contenido)

def guardar_propiedades(propiedades):
    """Guarda el diccionario de propiedades en el Gist."""
    if not GITHUB_TOKEN or not GIST_ID:
        raise ValueError("Faltan las variables de entorno GITHUB_TOKEN o GIST_ID")

    g = Github(GITHUB_TOKEN)
    gist = g.get_gist(GIST_ID)
    nuevo_contenido = json.dumps(propiedades, ensure_ascii=False, indent=2)
    gist.edit(files={"propiedades.json": {"content": nuevo_contenido}})
