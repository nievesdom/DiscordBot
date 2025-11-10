import discord
from discord.ext import commands
import re

TOKEN = "TU_TOKEN_DEL_BOT"
CANAL_ORIGEN_ID = 1437348279107977266  # canal de texto con mensajes antiguos
CANAL_FORO_ID = 1437348404559876226    # canal de foro destino

AO3_REGEX = re.compile(r"(https?://archiveofourown\.org/\S+)", re.IGNORECASE)

# Regex para extraer campos desde embed.description (líneas tipo "Author: Jollyjane")
RE_AUTHOR = re.compile(r"^author:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
RE_RATING = re.compile(r"^rating:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
RE_CATEGORIES = re.compile(r"^categories:\s*(.+)$", re.IGNORECASE | re.MULTILINE)
RE_RELATIONSHIPS = re.compile(r"^relationships:\s*(.+)$", re.IGNORECASE | re.MULTILINE)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Utilidad: extraer datos del embed
    def _parse_embed(self, embed: discord.Embed):
        # Título (limpiar " - Chapter ...")
        raw_title = embed.title or "Título desconocido"
        titulo = raw_title.split(" - Chapter")[0].strip() if " - Chapter" in raw_title else raw_title.strip()

        desc = embed.description or ""

        # Autor
        m_author = RE_AUTHOR.search(desc)
        autor = m_author.group(1).strip() if m_author else "Autor desconocido"

        # Rating
        m_rating = RE_RATING.search(desc)
        rating = m_rating.group(1).strip() if m_rating else None

        # Categories (lista)
        m_cats = RE_CATEGORIES.search(desc)
        categories = []
        if m_cats:
            categories = [c.strip() for c in m_cats.group(1).split(",") if c.strip()]

        # Relationships (lista)
        m_rels = RE_RELATIONSHIPS.search(desc)
        relationships = []
        if m_rels:
            relationships = [r.strip() for r in m_rels.group(1).split(",") if r.strip()]

        # Conjunto de etiquetas detectadas (rating + categories + relationships)
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
            # Solo mensajes con link AO3 y con embed
            if not msg.embeds:
                continue
            link_match = AO3_REGEX.search(msg.content) or (msg.embeds and AO3_REGEX.search(msg.embeds[0].url or ""))
            if not link_match:
                continue

            link = link_match.group(1)
            embed = msg.embeds[0]

            titulo, autor, etiquetas_detectadas = self._parse_embed(embed)
            nombre_post = f"{titulo} — {autor}"

            # Evitar duplicados
            if nombre_post in titulos_usados:
                print(f"⚠️ Duplicado detectado, se omite: {nombre_post}")
                continue

            # Mapear etiquetas detectadas a etiquetas del foro
            etiquetas_foro = {tag.name: tag for tag in foro.available_tags}
            applied_tags = [etiquetas_foro[n] for n in etiquetas_detectadas if n in etiquetas_foro]

            # Crear post en foro con etiquetas
            await foro.create_thread(
                name=nombre_post,
                content=link,
                applied_tags=applied_tags
            )
            titulos_usados.add(nombre_post)
            count += 1
            print(f"📌 Migrado: {nombre_post} | Etiquetas: {', '.join([t.name for t in applied_tags]) or 'Ninguna'}")

        await ctx.send(f"✅ Migrados {count} mensajes únicos con links de AO3 al foro.")

    @commands.command(help="Lista todas las etiquetas de AO3 detectadas en mensajes", extras={"categoria": "Moderation 👤"})
    async def listar_etiquetas(self, ctx, limite: int = 100):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro: discord.ForumChannel = self.bot.get_channel(CANAL_FORO_ID)

        etiquetas_detectadas = set()

        async for msg in origen.history(limit=limite):
            if not msg.embeds:
                continue
            embed = msg.embeds[0]

            # Intentar obtener link (para filtrar solo embeds de AO3 si quieres)
            link_present = AO3_REGEX.search(msg.content) or (embed and AO3_REGEX.search(embed.url or ""))
            if not link_present:
                continue

            _, _, etiq = self._parse_embed(embed)
            etiquetas_detectadas.update(etiq)

        etiquetas_foro = {tag.name for tag in foro.available_tags}
        faltantes = etiquetas_detectadas - etiquetas_foro

        await ctx.send("📊 Etiquetas detectadas en AO3:\n" + (", ".join(sorted(etiquetas_detectadas)) or "—"))
        await ctx.send("🏷️ Etiquetas ya configuradas en el foro:\n" + (", ".join(sorted(etiquetas_foro)) or "—"))
        await ctx.send("⚠️ Etiquetas faltantes que deberías crear en el foro:\n" +
                       (", ".join(sorted(faltantes)) if faltantes else "✅ Todas las etiquetas ya existen en el foro."))

async def setup(bot):
    await bot.add_cog(Moderation(bot))
