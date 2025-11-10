import discord
from discord.ext import commands
import re

TOKEN = "TU_TOKEN_DEL_BOT"
CANAL_ORIGEN_ID = 1437348279107977266  # canal de texto con mensajes antiguos
CANAL_FORO_ID = 1437348404559876226    # canal de foro destino

AO3_REGEX = re.compile(r"(https?://archiveofourown\.org/\S+)")

class Moderation(commands.Cog):
    def categoría(nombre):
        def decorador(comando):
            comando.category = nombre
            return comando
        return decorador
    
    def __init__(self, bot):
        self.bot = bot
        
    @commands.command(help="Saluda al usuario", extras={"categoria": "Moderation 👤"})
    async def migrar(self, ctx, limite: int = 100):
        """Migra mensajes antiguos con links de AO3 al foro.
           Uso: !migrar [limite]
           Por defecto: 100 mensajes
        """
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro = self.bot.get_channel(CANAL_FORO_ID)

        count = 0
        async for msg in origen.history(limit=limite):
            match = AO3_REGEX.search(msg.content)
            if match:
                link = match.group(1)

                # Leer embed de AO3 Linker si existe
                titulo = "Título desconocido"
                autor = "Autor desconocido"
                if msg.embeds:
                    embed = msg.embeds[0]
                    if embed.title:
                        titulo = embed.title
                    if embed.author and embed.author.name:
                        autor = embed.author.name

                # Crear post en foro
                await foro.create_thread(
                    name=f"{titulo} — {autor}",
                    content=link
                )
                count += 1

        await ctx.send(f"📌 Migrados {count} mensajes con links de AO3 al foro.")
        
async def setup(bot):
    await bot.add_cog(Moderation(bot))
