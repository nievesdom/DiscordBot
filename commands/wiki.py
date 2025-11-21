import discord
from discord.ext import commands
import aiohttp
import random
from discord import app_commands

class Wiki(commands.Cog):
    def categoría(nombre):
        def decorador(comando):
            comando.category = nombre
            return comando
        return decorador
    
    def __init__(self, bot):
        self.bot = bot  # Referencia al bot principal

    @app_commands.command(name="wiki", description="Searches a term in the Yakuza Wiki.")
    @app_commands.describe(termino="Term to search for in the wiki")
    async def wiki(self, interaction: discord.Interaction, *, termino: str):
        # Reemplazar espacios por "+" para formar la consulta
        termino_enc = termino.replace(' ', '+')

        # URL de la API de búsqueda de la wiki
        api_url = f"https://yakuza.fandom.com/api.php?action=query&list=search&srsearch={termino_enc}&format=json"

        # Realizar la petición HTTP a la API
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                data = await resp.json()  # Convertir la respuesta a JSON

        # Si hay resultados, enviar el enlace del más relevante
        if data["query"]["search"]:
            mejor = data["query"]["search"][0]["title"]
            enlace = f"https://yakuza.fandom.com/wiki/{mejor.replace(' ', '_')}"
            try:
                # Intentar enviar el mensaje por DM al autor
                await interaction.user.send(f"Here's the best coincidence for your search:\n{enlace}")
                await interaction.response.send_message("📬 I sent you a DM with the result!", ephemeral=True)
            except discord.Forbidden:
                # Si el usuario tiene bloqueados los DMs, avisar en el canal
                await interaction.response.send_message("⚠️ I couldn't send you a direct message. Please check your privacy settings.", ephemeral=True)
        else:
            # Si no hay resultados, enviar mensaje de error
            await interaction.response.send_message("Sorry, I couldn't find anything.", ephemeral=True)

    @app_commands.command(name="character", description="Sends a random character name.")
    async def character(self, interaction: discord.Interaction):
        # URL base de la API
        url = "https://yakuza.fandom.com/api.php"

        # Parámetros para obtener miembros de la categoría "Characters"
        parametros = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Characters",
            "cmlimit": "500",
            "format": "json"
        }

        personajes = []  # Lista para almacenar nombres de personajes

        # Peticiones paginadas a la API para obtener todos los personajes
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(url, params=parametros) as resp:
                    data = await resp.json()

                    # Filtrar solo artículos (ns == 0) y añadirlos a la lista
                    personajes += [item["title"] for item in data["query"]["categorymembers"] if item["ns"] == 0]

                    # Si hay más páginas, actualizar los parámetros
                    if "continue" in data:
                        parametros.update(data["continue"])
                    else:
                        break  # No hay más páginas

        # Elegir un personaje aleatorio de la lista
        elegido = random.choice(personajes)
        
        await interaction.response.send_message(elegido)

async def setup(bot):
    await bot.add_cog(Wiki(bot))
