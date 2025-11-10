import discord
from discord.ext import commands
import re

CANAL_ORIGEN_ID = 1437348279107977266
CANAL_FORO_ID = 1437348404559876226

AO3_REGEX = re.compile(r"https?://archiveofourown\.org/works/\d+", re.IGNORECASE)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Extraer datos del embed
    def _parse_embed(self, embed: discord.Embed):
        titulo = (embed.title or "Título desconocido").strip()

        # Autor(es) en la descripción
        desc = embed.description or ""
        autores = re.findall(r"\[([^\]]+)\]\(https://archiveofourown\.org/users/.+?\)", desc)
        autor = ", ".join(autores) if autores else "Autor desconocido"

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

        etiquetas_detectadas = set()
        if rating:
            etiquetas_detectadas.add(rating)
        etiquetas_detectadas.update(categories)
        etiquetas_detectadas.update(relationships)
        etiquetas_detectadas.update(additional_tags)

        return titulo, autor, etiquetas_detectadas

    @commands.command(help="Migra mensajes del bot de AO3")
    async def migrar(self, ctx, limite: int = 100):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro: discord.ForumChannel = self.bot.get_channel(CANAL_FORO_ID)

        count = 0
        titulos_usados = set()

        async for msg in origen.history(limit=limite):
            if not msg.embeds:
                continue

            # Tomar solo el embed principal de la obra completa
            embed = msg.embeds[0]
            link_match = AO3_REGEX.search(msg.content) or AO3_REGEX.search(embed.url or "")
            if not link_match:
                continue

            link = link_match.group(0)  # link original a la obra completa
            titulo, autor, etiquetas_detectadas = self._parse_embed(embed)
            nombre_post = f"{titulo} — {autor}"

            if nombre_post in titulos_usados:
                continue

            # Mapear etiquetas detectadas a etiquetas del foro
            etiquetas_foro = {tag.name: tag for tag in foro.available_tags}
            applied_tags = [etiquetas_foro[n] for n in etiquetas_detectadas if n in etiquetas_foro]

            # Crear thread en foro
            await foro.create_thread(
                name=nombre_post,
                content=link,
                applied_tags=applied_tags
            )
            titulos_usados.add(nombre_post)
            count += 1
            print(f"📌 Migrado: {nombre_post} | Etiquetas: {', '.join([t.name for t in applied_tags]) or 'Ninguna'}")

        await ctx.send(f"✅ Migrados {count} mensajes únicos con links de AO3 al foro.")

    @commands.command(help="Lista todas las etiquetas detectadas en los mensajes de AO3")
    async def listar_etiquetas(self, ctx, limite: int = 100):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        etiquetas_detectadas = set()

        async for msg in origen.history(limit=limite):
            if not msg.embeds:
                continue
            embed = msg.embeds[0]

            # Solo embeds de obras completas
            if not AO3_REGEX.search(msg.content) and not AO3_REGEX.search(embed.url or ""):
                continue

            _, _, etiq = self._parse_embed(embed)
            etiquetas_detectadas.update(etiq)

        etiquetas_list = sorted(etiquetas_detectadas)
        await ctx.send(f"📊 Etiquetas detectadas ({len(etiquetas_list)}):\n" + (", ".join(etiquetas_list) or "—"))
