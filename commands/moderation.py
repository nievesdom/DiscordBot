import discord
from discord.ext import commands
import re
import aiohttp
from bs4 import BeautifulSoup
import asyncio

TOKEN = "TU_TOKEN_DEL_BOT"
CANAL_ORIGEN_ID = 1437348279107977266  # canal de texto con mensajes antiguos
FORO_DESTINO_ID = 1437348404559876226    # canal de foro destino

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Migra mensajes del bot de AO3", extras={"categoria": "Moderation 👤"})
    async def mover(self, ctx):
        canal_origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro_destino = self.bot.get_channel(FORO_DESTINO_ID)
    
        if canal_origen is None:
            await ctx.send(f"No se encontró el canal con ID {CANAL_ORIGEN_ID}.")
            return
        if foro_destino is None or not isinstance(foro_destino, discord.ForumChannel):
            await ctx.send(f"El canal con ID {FORO_DESTINO_ID} no es un foro válido.")
            return
    
        patron = re.compile(r"https?://archiveofourown\.org/(works|series)/\d+")
        contador = 0
    
        async for mensaje in canal_origen.history(limit=None):
            links = re.findall(patron, mensaje.content)
            if not links:
                continue
            
            for coincidencia in re.finditer(patron, mensaje.content):
                url = coincidencia.group(0)
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            continue
                        html = await resp.text()
    
                soup = BeautifulSoup(html, "html.parser")
    
                # Extraer título y autor
                titulo_elem = soup.find("h2", class_="title")
                autor_elem = soup.find("a", rel="author")
    
                titulo = titulo_elem.text.strip() if titulo_elem else "Sin título"
                autor = autor_elem.text.strip() if autor_elem else "Autor desconocido"
    
                # Crear post en el foro con el título formateado
                await foro_destino.create_thread(
                    name=f"{titulo} - {autor}",
                    content=f"{url}"
                )
    
                contador += 1
                # Pequeña pausa para no saturar AO3
                await asyncio.sleep(0.8)
    
    
        await ctx.send(f"✅ Se movieron {contador} mensajes con links de AO3 al foro.")
        
async def setup(bot):
    await bot.add_cog(Moderation(bot))
