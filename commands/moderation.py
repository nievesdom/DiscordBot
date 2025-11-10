import discord
from discord.ext import commands
import re
import asyncio
import aiohttp

TOKEN = "TU_TOKEN_DEL_BOT"
CANAL_ORIGEN_ID = 1437348279107977266  # canal de texto con mensajes antiguos
CANAL_FORO_ID = 1437348404559876226    # canal de foro destino

AO3_REGEX = re.compile(r"(https?://archiveofourown\.org/\S+)", re.IGNORECASE)

# Regex y utilidades para parsear AO3 HTML
RE_TITLE = re.compile(r'<h2[^>]*class="title heading"[^>]*>\s*(.*?)\s*</h2>', re.IGNORECASE | re.DOTALL)
RE_AUTHOR = re.compile(r'<a[^>]*rel="author"[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
RE_RATING = re.compile(r'<dt[^>]*>Rating:</dt>\s*<dd[^>]*>\s*<a[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
RE_CATEGORIES = re.compile(r'<dt[^>]*>Category:</dt>\s*<dd[^>]*>(.*?)</dd>', re.IGNORECASE | re.DOTALL)
RE_RELATIONSHIPS = re.compile(r'<dt[^>]*>Relationship[s]?:</dt>\s*<dd[^>]*>(.*?)</dd>', re.IGNORECASE | re.DOTALL)
RE_ANCHORS = re.compile(r'<a[^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)

async def fetch_ao3_fields(session: aiohttp.ClientSession, url: str):
    # Normalizar URL a la página principal del work (evitar /chapters)
    base_url = url.split("?")[0]
    if "/chapters/" in base_url:
        base_url = base_url.split("/chapters/")[0]
    # Aceptar cookies adult (- sideload simple sin cookie de sesión)
    headers = {"User-Agent": "Mozilla/5.0"}
    async with session.get(base_url, headers=headers) as resp:
        html = await resp.text()

    # Título
    m_title = RE_TITLE.search(html)
    titulo = (m_title.group(1).strip() if m_title else "Título desconocido")
    # Autor (primer rel="author")
    m_author = RE_AUTHOR.search(html)
    autor = (m_author.group(1).strip() if m_author else "Autor desconocido")
    # Rating
    m_rating = RE_RATING.search(html)
    rating = m_rating.group(1).strip() if m_rating else None
    # Categorías (puede haber varias dentro del dd)
    cats_block = RE_CATEGORIES.search(html)
    categories = []
    if cats_block:
        categories = [c.strip() for c in RE_ANCHORS.findall(cats_block.group(1)) if c.strip()]
    # Relationships (varios anchors dentro del dd)
    rels_block = RE_RELATIONSHIPS.search(html)
    relationships = []
    if rels_block:
        relationships = [r.strip() for r in RE_ANCHORS.findall(rels_block.group(1)) if r.strip()]

    etiquetas_detectadas = set()
    if rating:
        etiquetas_detectadas.add(rating)
    etiquetas_detectadas.update(categories)
    etiquetas_detectadas.update(relationships)

    # AO3 a veces incluye “- Chapter …” en el título del embed; aquí usamos el título del HTML directamente.
    # Aseguramos limpieza mínima:
    titulo = re.sub(r"\s+", " ", titulo).strip()
    autor = re.sub(r"\s+", " ", autor).strip()

    return titulo, autor, etiquetas_detectadas, base_url

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Migra mensajes del bot de AO3", extras={"categoria": "Moderation 👤"})
    async def migrar(self, ctx, limite: int = 100):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro: discord.ForumChannel = self.bot.get_channel(CANAL_FORO_ID)

        count = 0
        titulos_usados = set()

        async with aiohttp.ClientSession() as session:
            async for msg in origen.history(limit=limite):
                # Debe contener link AO3
                link_match = AO3_REGEX.search(msg.content)
                if not link_match:
                    continue

                link = link_match.group(1)

                # Parsear desde la página de AO3
                try:
                    titulo, autor, etiquetas_detectadas, work_url = await fetch_ao3_fields(session, link)
                except Exception as e:
                    print(f"⚠️ Error al parsear {link}: {e}")
                    continue

                nombre_post = f"{titulo} — {autor}"

                # Evitar duplicados por título-autor
                if nombre_post in titulos_usados:
                    print(f"⚠️ Duplicado detectado, se omite: {nombre_post}")
                    continue

                # Mapear etiquetas detectadas a etiquetas del foro
                etiquetas_foro = {tag.name: tag for tag in foro.available_tags}
                applied_tags = [etiquetas_foro[n] for n in etiquetas_detectadas if n in etiquetas_foro]

                # Crear post en foro (usamos la URL normalizada del work)
                await foro.create_thread(
                    name=nombre_post,
                    content=work_url,
                    applied_tags=applied_tags
                )
                titulos_usados.add(nombre_post)
                count += 1
                print(f"📌 Migrado: {nombre_post} | Etiquetas: {', '.join([t.name for t in applied_tags]) or 'Ninguna'}")

        await ctx.send(f"✅ Migrados {count} mensajes únicos con links de AO3 al foro.")

    @commands.command(help="Lista etiquetas AO3 encontradas y compara con las del foro", extras={"categoria": "Moderation 👤"})
    async def listar_etiquetas(self, ctx, limite: int = 100):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro: discord.ForumChannel = self.bot.get_channel(CANAL_FORO_ID)

        etiquetas_detectadas = set()

        async with aiohttp.ClientSession() as session:
            async for msg in origen.history(limit=limite):
                link_match = AO3_REGEX.search(msg.content)
                if not link_match:
                    continue
                link = link_match.group(1)
                try:
                    _, _, etiq, _ = await fetch_ao3_fields(session, link)
                    etiquetas_detectadas.update(etiq)
                except Exception as e:
                    print(f"⚠️ Error al parsear {link}: {e}")
                    continue

        etiquetas_foro = {tag.name for tag in foro.available_tags}
        faltantes = etiquetas_detectadas - etiquetas_foro

        await ctx.send("📊 Etiquetas detectadas en AO3:\n" + (", ".join(sorted(etiquetas_detectadas)) or "—"))
        await ctx.send("🏷️ Etiquetas ya configuradas en el foro:\n" + (", ".join(sorted(etiquetas_foro)) or "—"))
        await ctx.send("⚠️ Etiquetas faltantes que deberías crear en el foro:\n" +
                       (", ".join(sorted(faltantes)) if faltantes else "✅ Todas las etiquetas ya existen en el foro."))

async def setup(bot):
    await bot.add_cog(Moderation(bot))
