import discord
from discord.ext import commands
import aiohttp
import random

# Clase que agrupa los comandos relacionados con la wiki de Yakuza
class Wiki(commands.Cog):
    def categoría(nombre):
        def decorador(comando):
            comando.category = nombre
            return comando
        return decorador
    
    def __init__(self, bot):
        self.bot = bot  # Referencia al bot principal


    @commands.command(help="Busca un término en la wiki de Yakuza", extras={"categoria": "Wiki 🌐"})
    async def wiki(self, ctx, *, termino: str):
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
            await ctx.send(f"Aquí tienes el resultado más relevante para tu búsqueda:\n{enlace}")
        else:
            # Si no hay resultados, enviar mensaje de error
            await ctx.send("Lo siento, no he encontrado nada.")


    @commands.command(help="Devuelve un personaje aleatorio de la wiki", extras={"categoria": "Wiki 🌐"})
    async def personaje(self, ctx):
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

        # Formar el enlace a su página en la wiki
        enlace = f"https://yakuza.fandom.com/wiki/{elegido.replace(' ', '_')}"
        await ctx.send(enlace)
        


async def setup(bot):
    await bot.add_cog(Wiki(bot))

