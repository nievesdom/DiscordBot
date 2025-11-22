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

    # ---------------------------
    # WIKI
    # ---------------------------
    @app_commands.command(name="wiki", description="Searches a term in the Yakuza Wiki.")
    @app_commands.describe(termino="Term to search for in the wiki")
    async def wiki_slash(self, interaction: discord.Interaction, *, termino: str):
        termino_enc = termino.replace(' ', '+')
        api_url = f"https://yakuza.fandom.com/api.php?action=query&list=search&srsearch={termino_enc}&format=json"

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                data = await resp.json()

        if data["query"]["search"]:
            mejor = data["query"]["search"][0]["title"]
            enlace = f"https://yakuza.fandom.com/wiki/{mejor.replace(' ', '_')}"
            try:
                await interaction.user.send(f"Here's the best coincidence for your search:\n{enlace}")
                await interaction.response.send_message("📬 I sent you a DM with the result!", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("⚠️ I couldn't send you a direct message. Please check your privacy settings.", ephemeral=True)
        else:
            await interaction.response.send_message("Sorry, I couldn't find anything.")

    @commands.command(name="wiki")
    async def wiki_prefix(self, ctx: commands.Context, *, termino: str):
        termino_enc = termino.replace(' ', '+')
        api_url = f"https://yakuza.fandom.com/api.php?action=query&list=search&srsearch={termino_enc}&format=json"

        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as resp:
                data = await resp.json()

        if data["query"]["search"]:
            mejor = data["query"]["search"][0]["title"]
            enlace = f"https://yakuza.fandom.com/wiki/{mejor.replace(' ', '_')}"
            try:
                await ctx.author.send(f"Here's the best coincidence for your search:\n{enlace}")
                await ctx.send("📬 I sent you a DM with the result!", ephemeral=True)
            except discord.Forbidden:
                await ctx.send("⚠️ I couldn't send you a direct message. Please check your privacy settings.", ephemeral=True)
        else:
            await ctx.send("Sorry, I couldn't find anything.")

    # ---------------------------
    # CHARACTER
    # ---------------------------
    @app_commands.command(name="character", description="Sends a random character name.")
    async def character_slash(self, interaction: discord.Interaction):
        url = "https://yakuza.fandom.com/api.php"
        parametros = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Characters",
            "cmlimit": "500",
            "format": "json"
        }

        personajes = []
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(url, params=parametros) as resp:
                    data = await resp.json()
                    personajes += [item["title"] for item in data["query"]["categorymembers"] if item["ns"] == 0]
                    if "continue" in data:
                        parametros.update(data["continue"])
                    else:
                        break

        elegido = random.choice(personajes)
        await interaction.response.send_message(elegido)

    @commands.command(name="character")
    async def character_prefix(self, ctx: commands.Context):
        url = "https://yakuza.fandom.com/api.php"
        parametros = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Characters",
            "cmlimit": "500",
            "format": "json"
        }

        personajes = []
        async with aiohttp.ClientSession() as session:
            while True:
                async with session.get(url, params=parametros) as resp:
                    data = await resp.json()
                    personajes += [item["title"] for item in data["query"]["categorymembers"] if item["ns"] == 0]
                    if "continue" in data:
                        parametros.update(data["continue"])
                    else:
                        break

        elegido = random.choice(personajes)
        await ctx.send(elegido)

async def setup(bot):
    await bot.add_cog(Wiki(bot))
