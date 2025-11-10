import discord
from discord.ext import commands
import re

# IDs fijos
CANAL_ORIGEN_ID = 1437348279107977266
CANAL_FORO_ID = 1437348404559876226

AO3_REGEX = re.compile(r"https?://archiveofourown\.org/works/\d+", re.IGNORECASE)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Extraer datos del embed
    def _parse_embed(self, embed: discord.Embed):
        titulo = (embed.title or "Título desconocido").strip()
        titulo = titulo.split(" - Chapter")[0].strip() if " - Chapter" in titulo else titulo

        desc = embed.description or ""
        autores = re.findall(r"\[([^\]]+)\]\(https://archiveofourown\.org/users/.+?\)", desc)
        autor = ", ".join(autores) if autores else None  # None si no hay autor

        rating = None
        categories = []
        relationships = []
        additional_tags = []

        for field in embed.fields:
            nombre = field.name.lower().strip(": ")
            valor = field.value.strip()

            if "rating" in nombre:
                rating = re.sub(r"^[:\w\s]*:", "", valor).strip(" :")
            elif "categories" in nombre:
                categories = [v.strip() for v in valor.split(",") if v.strip()]
            elif "relationships" in nombre:
                relationships = [v.strip() for v in valor.split(",") if v.strip()]
            elif "additional tags" in nombre:
                additional_tags = [v.strip() for v in valor.split(",") if v.strip()]

        etiquetas_principales = set()
        if rating:
            etiquetas_principales.add(rating)
        etiquetas_principales.update(categories)
        etiquetas_principales.update(relationships)

        etiquetas_adicionales = set(additional_tags)

        return titulo, autor, etiquetas_principales, etiquetas_adicionales

    @commands.command(help="Migra mensajes del bot de AO3")
    async def migrar(self, ctx, limite: int = None):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro: discord.ForumChannel = self.bot.get_channel(CANAL_FORO_ID)

        if origen is None:
            await ctx.send(f"No se encontró el canal con ID {CANAL_ORIGEN_ID}.")
            return
        if foro is None or not isinstance(foro, discord.ForumChannel):
            await ctx.send(f"No se encontró un foro válido con ID {CANAL_FORO_ID}.")
            return

        count = 0
        obras_usadas = set()

        async for msg in origen.history(limit=limite):
            if not msg.embeds:
                continue

            embed = msg.embeds[0]
            link_match = AO3_REGEX.search(msg.content) or AO3_REGEX.search(embed.url or "")
            if not link_match:
                continue

            link = link_match.group(0)  # link a la obra completa
            titulo, autor, etiquetas_principales, _ = self._parse_embed(embed)

            # Ignorar si no se detecta autor
            if not autor:
                continue

            # Evitar duplicados por obra
            if link in obras_usadas:
                continue

            nombre_post = f"{titulo} — {autor}"

            # Mapear etiquetas principales a etiquetas del foro
            etiquetas_foro = {tag.name: tag for tag in foro.available_tags}
            applied_tags = [etiquetas_foro[n] for n in etiquetas_principales if n in etiquetas_foro]

            await foro.create_thread(
                name=nombre_post,
                content=link,
                applied_tags=applied_tags
            )

            obras_usadas.add(link)
            count += 1
            print(f"📌 Migrado: {nombre_post} | Etiquetas: {', '.join([t.name for t in applied_tags]) or 'Ninguna'}")

        await ctx.send(f"✅ Migrados {count} mensajes únicos con links de AO3 al foro.")

    # Lista etiquetas principales (rating, categories, relationships)
    @commands.command(help="Lista las etiquetas principales detectadas en los mensajes de AO3")
    async def etiquetas_principales(self, ctx, limite: int = None):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        etiquetas_detectadas = set()

        async for msg in origen.history(limit=limite):
            if not msg.embeds:
                continue
            embed = msg.embeds[0]
            if not AO3_REGEX.search(msg.content) and not AO3_REGEX.search(embed.url or ""):
                continue
            _, _, etiquetas_principales, _ = self._parse_embed(embed)
            etiquetas_detectadas.update(etiquetas_principales)

        etiquetas_list = sorted(etiquetas_detectadas)
        await ctx.send(f"📊 Etiquetas principales ({len(etiquetas_list)}):\n" + (", ".join(etiquetas_list) or "—"))


    # Lista etiquetas adicionales (additional tags u otras)
    @commands.command(help="Lista las etiquetas adicionales detectadas en los mensajes de AO3")
    async def etiquetas_adicionales(self, ctx, limite: int = 100):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        etiquetas_detectadas = set()

        async for msg in origen.history(limit=limite):
            if not msg.embeds:
                continue
            embed = msg.embeds[0]
            if not AO3_REGEX.search(msg.content) and not AO3_REGEX.search(embed.url or ""):
                continue
            _, _, _, etiquetas_adicionales = self._parse_embed(embed)
            etiquetas_detectadas.update(etiquetas_adicionales)

        etiquetas_list = sorted(etiquetas_detectadas)
        await ctx.send(f"📊 Etiquetas adicionales ({len(etiquetas_list)}):\n" + (", ".join(etiquetas_list) or "—"))

async def setup(bot):
    await bot.add_cog(Moderation(bot))