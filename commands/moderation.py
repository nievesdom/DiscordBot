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
        
    @commands.command(help="Migra mensajes del bot de AO3", extras={"categoria": "Moderation 👤"})
    async def migrar(self, ctx, limite: int = 100):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro = self.bot.get_channel(CANAL_FORO_ID)

        count = 0
        titulos_usados = set()

        async for msg in origen.history(limit=limite):
            match = AO3_REGEX.search(msg.content)
            if match:
                link = match.group(1)

                titulo = "Título desconocido"
                autor = "Autor desconocido"

                if msg.embeds:
                    embed = msg.embeds[0]

                    # El título de AO3 Linker suele ser "Obra - Chapter X - Autor - Fandom"
                    # Nos quedamos solo con la primera parte antes de " - Chapter"
                    if embed.title:
                        raw_title = embed.title
                        # Cortar en " - Chapter" si existe
                        if " - Chapter" in raw_title:
                            titulo = raw_title.split(" - Chapter")[0].strip()
                        else:
                            titulo = raw_title.strip()

                    # El autor suele aparecer en embed.author.name como "by Nombre"
                    if embed.author and embed.author.name:
                        raw_author = embed.author.name
                        if raw_author.lower().startswith("by "):
                            autor = raw_author[3:].strip()
                        else:
                            autor = raw_author.strip()

                nombre_post = f"{titulo} — {autor}"

                # Evitar duplicados
                if nombre_post in titulos_usados:
                    print(f"⚠️ Duplicado detectado, se omite: {nombre_post}")
                    continue

                # Crear post en foro
                await foro.create_thread(
                    name=nombre_post,
                    content=link
                )
                titulos_usados.add(nombre_post)
                count += 1
                print(f"📌 Migrado: {nombre_post}")

        await ctx.send(f"✅ Migrados {count} mensajes únicos con links de AO3 al foro.")
        
    @commands.command(help="Lista todas las etiquetas de AO3 detectadas en mensajes", extras={"categoria": "Moderation 👤"})
    async def etiquetas(self, ctx, limite: int = 100):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro: discord.ForumChannel = self.bot.get_channel(CANAL_FORO_ID)

        etiquetas_detectadas = set()

        async for msg in origen.history(limit=limite):
            match = AO3_REGEX.search(msg.content)
            if match and msg.embeds:
                embed = msg.embeds[0]
                for field in embed.fields:
                    name = field.name.lower()
                    value = field.value.strip()
                    if "rating" in name:
                        etiquetas_detectadas.add(value)
                    elif "categories" in name:
                        etiquetas_detectadas.update([c.strip() for c in value.split(",")])
                    elif "relationships" in name:
                        etiquetas_detectadas.update([r.strip() for r in value.split(",")])

        etiquetas_foro = {tag.name for tag in foro.available_tags}
        faltantes = etiquetas_detectadas - etiquetas_foro

        await ctx.send("📊 **Etiquetas detectadas en AO3:**\n" + ", ".join(sorted(etiquetas_detectadas)))
        await ctx.send("🏷️ **Etiquetas ya configuradas en el foro:**\n" + ", ".join(sorted(etiquetas_foro)))
        await ctx.send("⚠️ **Etiquetas faltantes que deberías crear en el foro:**\n" + ", ".join(sorted(faltantes)) if faltantes else "✅ Todas las etiquetas ya existen en el foro.")
        
async def setup(bot):
    await bot.add_cog(Moderation(bot))
