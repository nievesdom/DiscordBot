import discord
from discord.ext import commands
import re

TOKEN = "TU_TOKEN_DEL_BOT"
CANAL_ORIGEN_ID = 1437348279107977266  # canal de texto con mensajes antiguos
CANAL_FORO_ID = 1437348404559876226    # canal de foro destino

AO3_REGEX = re.compile(r"(https?://archiveofourown\.org/\S+)", re.IGNORECASE)

# Regex para extraer campos desde embed.description (cuando no hay fields)
RE_AUTHOR = re.compile(r"author:\s*(.+)", re.IGNORECASE)
RE_RATING = re.compile(r"rating:\s*(.+)", re.IGNORECASE)
RE_CATEGORIES = re.compile(r"categories:\s*(.+)", re.IGNORECASE)
RE_RELATIONSHIPS = re.compile(r"relationships:\s*(.+)", re.IGNORECASE)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Utilidad: extraer datos del embed, tolerando distintas estructuras
    def _parse_embed(self, embed: discord.Embed):
        # Título (limpiar " - Chapter ...")
        raw_title = embed.title or "Título desconocido"
        titulo = raw_title.split(" - Chapter")[0].strip() if " - Chapter" in raw_title else raw_title.strip()

        autor = "Autor desconocido"
        rating = None
        categories = []
        relationships = []

        # 1️⃣ Intentar primero desde los fields
        for field in embed.fields:
            name = field.name.lower().strip()
            value = field.value.strip()
            if name.startswith("author"):
                autor = value
            elif name.startswith("rating"):
                rating = value
            elif name.startswith("categories"):
                categories = [c.strip() for c in value.split(",") if c.strip()]
            elif name.startswith("relationships"):
                relationships = [r.strip() for r in value.split(",") if r.strip()]

        # 2️⃣ Si no hay fields, usar description como respaldo
        desc = embed.description or ""
        if autor == "Autor desconocido":
            m = RE_AUTHOR.search(desc)
            if m:
                autor = m.group(1).strip()
        if not rating:
            m = RE_RATING.search(desc)
            if m:
                rating = m.group(1).strip()
        if not categories:
            m = RE_CATEGORIES.search(desc)
            if m:
                categories = [c.strip() for c in m.group(1).split(",") if c.strip()]
        if not relationships:
            m = RE_RELATIONSHIPS.search(desc)
            if m:
                relationships = [r.strip() for r in m.group(1).split(",") if r.strip()]

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

        if origen is None or foro is None:
            await ctx.send("❌ No se encontraron los canales indicados.")
            return

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
        
    
    @commands.command(help="Muestra la estructura del embed del último mensaje con link AO3")
    async def debug_ao3(self, ctx, limite: int = 10):
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
