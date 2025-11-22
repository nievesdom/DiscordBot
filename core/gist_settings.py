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

# Guardar settings en el Gist remoto
async def guardar_settings(datos, bot=None, guild_id=None, channel_id=None):
    """
    Sube los cambios al Gist, actualizando settings.json.
    Si se excede el límite de la API, se avisa en el canal configurado del servidor.
    """
    try:
        print("[INFO] Iniciando guardado de settings en Gist...")
        gist = get_gist()
        nuevo_contenido = json.dumps(datos, indent=2, ensure_ascii=False)
        gist.edit(files={"settings.json": InputFileContent(nuevo_contenido)})
        print("[OK] Settings actualizados correctamente en el Gist.")
    except RateLimitExceededException as e:
        print("[ERROR] Rate limit excedido:", e)

        # Avisar en el servidor si tenemos contexto
        if bot and guild_id and channel_id:
            guild = bot.get_guild(int(guild_id))
            if guild:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    try:
                        await channel.send(
                            "⚠️ Se ha alcanzado el límite de peticiones a GitHub. "
                            "Los cambios no se guardarán hasta que se libere el límite."
                        )
                    except Exception as send_error:
                        print(f"[ERROR] No se pudo enviar aviso en guild {guild_id}: {send_error}")
    except Exception as e:
        import traceback
        print("[ERROR] guardar_settings:", e)
        traceback.print_exc()
