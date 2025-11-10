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
        foro: discord.ForumChannel = self.bot.get_channel(CANAL_FORO_ID)

        count = 0
        titulos_usados = set()

        async for msg in origen.history(limit=limite):
            match = AO3_REGEX.search(msg.content)
            if not match or not msg.embeds:
                continue

            link = match.group(1)
            embed = msg.embeds[0]

            # Título limpio
            raw_title = embed.title or "Título desconocido"
            titulo = raw_title.split(" - Chapter")[0].strip() if " - Chapter" in raw_title else raw_title.strip()

            # Autor desde field "Author"
            autor = "Autor desconocido"
            for field in embed.fields:
                if field.name.lower() == "author":
                    autor = field.value.strip()
                    break

            nombre_post = f"{titulo} — {autor}"

            # Evitar duplicados
            if nombre_post in titulos_usados:
                print(f"⚠️ Duplicado detectado, se omite: {nombre_post}")
                continue

            # Extraer etiquetas
            etiquetas_detectadas = set()
            for field in embed.fields:
                name = field.name.lower()
                value = field.value.strip()
                if "rating" in name or "categories" in name or "relationships" in name:
                    etiquetas_detectadas.update([v.strip() for v in value.split(",")])

            # Mapear con etiquetas del foro
            etiquetas_foro = {tag.name: tag for tag in foro.available_tags}
            applied_tags = [etiquetas_foro[n] for n in etiquetas_detectadas if n in etiquetas_foro]

            # Crear post en foro
            await foro.create_thread(
                name=nombre_post,
                content=link,
                applied_tags=applied_tags
            )
            titulos_usados.add(nombre_post)
            count += 1
            print(f"📌 Migrado: {nombre_post} con etiquetas {', '.join([t.name for t in applied_tags])}")

        await ctx.send(f"✅ Migrados {count} mensajes únicos con links de AO3 al foro.")
    
        
    @commands.command(help="Lista todas las etiquetas de AO3 detectadas en mensajes", extras={"categoria": "Moderation 👤"})
    async def listar_etiquetas(self, ctx, limite: int = 100):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro: discord.ForumChannel = self.bot.get_channel(CANAL_FORO_ID)
    
        etiquetas_detectadas = set()
    
        async for msg in origen.history(limit=limite):
            match = AO3_REGEX.search(msg.content)
            if not match or not msg.embeds:
                continue
            
            embed = msg.embeds[0]
            for field in embed.fields:
                name = field.name.lower()
                value = field.value.strip()
                if "rating" in name or "categories" in name or "relationships" in name:
                    etiquetas_detectadas.update([v.strip() for v in value.split(",")])
    
        etiquetas_foro = {tag.name for tag in foro.available_tags}
        faltantes = etiquetas_detectadas - etiquetas_foro
    
        await ctx.send("📊 **Etiquetas detectadas en AO3:**\n" + ", ".join(sorted(etiquetas_detectadas)))
        await ctx.send("🏷️ **Etiquetas ya configuradas en el foro:**\n" + ", ".join(sorted(etiquetas_foro)))
        await ctx.send("⚠️ **Etiquetas faltantes que deberías crear en el foro:**\n" +
                       (", ".join(sorted(faltantes)) if faltantes else "✅ Todas las etiquetas ya existen en el foro."))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
