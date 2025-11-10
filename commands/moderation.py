import discord
from discord.ext import commands
import re
import aiohttp
from bs4 import BeautifulSoup

TOKEN = "TU_TOKEN_DEL_BOT"
CANAL_ORIGEN_ID = 1437348279107977266  # canal de texto con mensajes antiguos
CANAL_FORO_ID = 1437348404559876226    # canal de foro destino

AO3_REGEX = re.compile(r"(https?://archiveofourown\.org/\S+)", re.IGNORECASE)

async def fetch_ao3_fields(session, url: str):
    # Normalizar URL al work principal
    base_url = url.split("?")[0]
    if "/chapters/" in base_url:
        base_url = base_url.split("/chapters/")[0]

    headers = {"User-Agent": "Mozilla/5.0"}
    async with session.get(base_url, headers=headers) as resp:
        html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")

    # Título
    titulo_tag = soup.find("h2", class_="title")
    titulo = titulo_tag.get_text(strip=True) if titulo_tag else "Título desconocido"

    # Autor
    autor_tag = soup.find("a", rel="author")
    autor = autor_tag.get_text(strip=True) if autor_tag else "Autor desconocido"

    etiquetas_detectadas = set()

    # Rating
    rating_dd = soup.find("dd", class_="rating tags")
    if rating_dd:
        etiquetas_detectadas.update([a.get_text(strip=True) for a in rating_dd.find_all("a", class_="tag")])

    # Categories
    cat_dd = soup.find("dd", class_="category tags")
    if cat_dd:
        etiquetas_detectadas.update([a.get_text(strip=True) for a in cat_dd.find_all("a", class_="tag")])

    # Relationships
    rel_dd = soup.find("dd", class_="relationship tags")
    if rel_dd:
        etiquetas_detectadas.update([a.get_text(strip=True) for a in rel_dd.find_all("a", class_="tag")])

    # Characters
    char_dd = soup.find("dd", class_="character tags")
    if char_dd:
        etiquetas_detectadas.update([a.get_text(strip=True) for a in char_dd.find_all("a", class_="tag")])

    # Additional Tags
    free_dd = soup.find("dd", class_="freeform tags")
    if free_dd:
        etiquetas_detectadas.update([a.get_text(strip=True) for a in free_dd.find_all("a", class_="tag")])

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
                match = AO3_REGEX.search(msg.content)
                if not match:
                    continue

                link = match.group(1)
                try:
                    titulo, autor, etiquetas_detectadas, work_url = await fetch_ao3_fields(session, link)
                except Exception as e:
                    print(f"⚠️ Error al parsear {link}: {e}")
                    continue

                nombre_post = f"{titulo} — {autor}"
                if nombre_post in titulos_usados:
                    print(f"⚠️ Duplicado detectado, se omite: {nombre_post}")
                    continue

                etiquetas_foro = {tag.name: tag for tag in foro.available_tags}
                applied_tags = [etiquetas_foro[n] for n in etiquetas_detectadas if n in etiquetas_foro]

                await foro.create_thread(
                    name=nombre_post,
                    content=work_url,
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

        async with aiohttp.ClientSession() as session:
            async for msg in origen.history(limit=limite):
                match = AO3_REGEX.search(msg.content)
                if not match:
                    continue
                link = match.group(1)
                try:
                    _, _, etiq, _ = await fetch_ao3_fields(session, link)
                    etiquetas_detectadas.update(etiq)
                except Exception as e:
                    print(f"⚠️ Error al parsear {link}: {e}")
                    continue

        etiquetas_foro = {tag.name for tag in foro.available_tags}
        faltantes = etiquetas_detectadas - etiquetas_foro

        await ctx.send("📊 **Etiquetas detectadas en AO3:**\n" + (", ".join(sorted(etiquetas_detectadas)) or "—"))
        await ctx.send("🏷️ **Etiquetas ya configuradas en el foro:**\n" + (", ".join(sorted(etiquetas_foro)) or "—"))
        await ctx.send("⚠️ **Etiquetas faltantes que deberías crear en el foro:**\n" +
                       (", ".join(sorted(faltantes)) if faltantes else "✅ Todas las etiquetas ya existen en el foro."))


async def setup(bot):
    await bot.add_cog(Moderation(bot))
