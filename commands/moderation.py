import discord
from discord.ext import commands
import re
import aiohttp
from bs4 import BeautifulSoup
import asyncio

TOKEN = "TU_TOKEN_DEL_BOT"
CANAL_ORIGEN_ID = 1437348279107977266  # canal de texto con mensajes antiguos
FORO_DESTINO_ID = 1437348404559876226  # canal de foro destino
AO3_LINKER_ID = 347104324255481858     # <-- ID del bot "AO3 Linker"

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Migra mensajes con links de AO3 al foro", extras={"categoria": "Moderation 👤"})
    async def mover(self, ctx):
        canal_origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro_destino = self.bot.get_channel(FORO_DESTINO_ID)

        if canal_origen is None:
            await ctx.send(f"No se encontró el canal con ID {CANAL_ORIGEN_ID}.")
            return
        if foro_destino is None or not isinstance(foro_destino, discord.ForumChannel):
            await ctx.send(f"El canal con ID {FORO_DESTINO_ID} no es un foro válido.")
            return

        patron = re.compile(r"https?://archiveofourown\.org/(?:works|series)/\d+")
        contador = 0

        await ctx.send("🔍 Buscando mensajes con links de AO3...")

        async with aiohttp.ClientSession() as session:
            async for mensaje in canal_origen.history(limit=None):
                coincidencias = re.findall(patron, mensaje.content)
                if not coincidencias:
                    continue

                for url in coincidencias:
                    titulo = None
                    autor = None

                    # Si hay un embed (por ejemplo, de AO3 Linker)
                    if mensaje.embeds:
                        for embed in mensaje.embeds:
                            # Solo usa embeds del bot AO3 Linker si existe su ID
                            if mensaje.author.id == AO3_LINKER_ID:
                                titulo = embed.title or "Sin título"
                                if embed.author:
                                    autor = embed.author.name or "Autor desconocido"
                                else:
                                    autor = "Autor desconocido"
                                break

                    # Si no hay embed o datos incompletos, intentar obtenerlos desde AO3
                    if not titulo or not autor:
                        try:
                            async with session.get(url) as resp:
                                if resp.status != 200:
                                    continue
                                html = await resp.text()

                            soup = BeautifulSoup(html, "html.parser")
                            titulo_elem = soup.find("h2", class_="title")
                            autor_elem = soup.find("a", rel="author")

                            titulo = titulo_elem.text.strip() if titulo_elem else "Sin título"
                            autor = autor_elem.text.strip() if autor_elem else "Autor desconocido"
                        except Exception as e:
                            print(f"Error obteniendo datos desde AO3: {e}")
                            continue

                    # Crear el post en el foro
                    try:
                        await foro_destino.create_thread(
                            name=f"{titulo} - {autor}",
                            content=f"{url}"
                        )
                        contador += 1
                        await asyncio.sleep(0.8)
                    except Exception as e:
                        print(f"Error creando el post en el foro: {e}")
                        continue

        await ctx.send(f"✅ Se movieron {contador} mensajes con links de AO3 al foro.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))