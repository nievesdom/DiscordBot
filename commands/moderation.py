import discord
from discord.ext import commands
import re

TOKEN = "TU_TOKEN_DEL_BOT"
CANAL_ORIGEN_ID = 1437348279107977266  # canal de texto con mensajes antiguos
CANAL_FORO_ID = 1437348404559876226    # canal de foro destino

AO3_REGEX = re.compile(r"(https?://archiveofourown\.org/\S+)", re.IGNORECASE)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Nueva versión adaptada al formato real del embed
    def _parse_embed(self, embed: discord.Embed):
        titulo = (embed.title or "Título desconocido").strip()

        # Autor(es): vienen en la descripción con formato "by [autor1](url), [autor2](url)"
        desc = embed.description or ""
        autores = re.findall(r"\[([^\]]+)\]\(https://archiveofourown\.org/users/.+?\)", desc)
        autor = ", ".join(autores) if autores else "Autor desconocido"

        rating = None
        categories = []
        relationships = []

        for field in embed.fields:
            nombre = field.name.lower().strip(": ")
            valor = field.value.strip()

            if "rating" in nombre:
                rating = re.sub(r"^[:\w\s]*:", "", valor).strip(" :")
            elif "categories" in nombre:
                categories = [v.strip() for v in valor.split(",") if v.strip()]
            elif "relationships" in nombre:
                relationships = [v.strip() for v in valor.split(",") if v.strip()]

        etiquetas_detectadas = set()
        if rating:
            etiquetas_detectadas.add(rating)
        etiquetas_detectadas.update(categories)
        etiquetas_detectadas.update(relationships)

        return titulo, autor, etiquetas_detectadas

    @commands.command(help="Migra mensajes del bot de AO3", extras={"categoria": "Moderation 👤"})
    async def migrar(self, ctx, limite: int = 100):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro: discord.ForumChannel = self.bot.get_channel(CANAL_FORO_ID)

        count = 0
        titulos_usados = set()

        async for msg in origen.history(limit=limite):
            if not msg.embeds:
                continue

            link_match = AO3_REGEX.search(msg.content) or (msg.embeds and AO3_REGEX.search(msg.embeds[0].url or ""))
            if not link_match:
                continue

            link = link_match.group(1)
            embed = msg.embeds[0]

            titulo, autor, etiquetas_detectadas = self._parse_embed(embed)
            nombre_post = f"{titulo} — {autor}"

            if nombre_post in titulos_usados:
                continue

            etiquetas_foro = {tag.name: tag for tag in foro.available_tags}
            applied_tags = [etiquetas_foro[n] for n in etiquetas_detectadas if n in etiquetas_foro]

            await foro.create_thread(
                name=nombre_post,
                content=link,
                applied_tags=applied_tags
            )

            titulos_usados.add(nombre_post)
            count += 1
            print(f"📌 Migrado: {nombre_post} | Etiquetas: {', '.join([t.name for t in applied_tags]) or 'Ninguna'}")

        await ctx.send(f"✅ Migrados {count} mensajes únicos con links de AO3 al foro.")
        
    
    @commands.command(help="Muestra la estructura del embed del último mensaje con link AO3")
    async def debug_ao3(self, ctx, limite: int = 200):
        canal = self.bot.get_channel(CANAL_ORIGEN_ID)
        async for msg in canal.history(limit=limite):
            if not msg.embeds:
                continue
            embed = msg.embeds[0]
            if "archiveofourown.org" not in (msg.content or "") and "archiveofourown.org" not in (embed.url or ""):
                continue

            info = f"**Título:** {embed.title}\n"
            info += f"**Descripción:**\n{embed.description}\n\n"
            info += f"**Campos:**\n"
            for f in embed.fields:
                info += f"- {f.name}: {f.value}\n"
            info += f"**Autor embed.author.name:** {getattr(embed.author, 'name', None)}\n"
            info += f"**Footer:** {getattr(embed.footer, 'text', None)}\n"
            info += f"**URL:** {embed.url}\n"

            await ctx.send(f"```{info}```")
            return

        await ctx.send("No se encontraron mensajes con embeds de AO3 en el rango dado.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
