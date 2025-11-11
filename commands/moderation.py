import discord
from discord.ext import commands
import re
import asyncio
from collections import Counter

CANAL_ORIGEN_ID = 1437348279107977266
CANAL_FORO_ID = 1437348404559876226

AO3_REGEX = re.compile(r"https?://archiveofourown\.org/works/\d+", re.IGNORECASE)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _parse_embed(self, embed: discord.Embed):
        titulo = (embed.title or "Título desconocido").strip()
        titulo = titulo.split(" - Chapter")[0].strip() if " - Chapter" in titulo else titulo

        desc = embed.description or ""
        autores = re.findall(r"\[([^\]]+)\]\(https://archiveofourown\.org/users/.+?\)", desc)
        autor = ", ".join(autores) if autores else None

        rating = None
        categories = []
        relationships = []
        characters = []
        additional_tags = []

        for field in embed.fields:
            nombre = field.name.lower().strip(": ")
            valor = field.value.strip()
            if "rating" in nombre:
                rating = re.sub(r"^[:\w\s]*:", "", valor).strip(" :")
                if rating == "Teen And Up Audiences":
                    rating = "Teen And Up"
            elif "categories" in nombre:
                categories = [v.strip() for v in valor.split(",") if v.strip()]
            elif "relationships" in nombre:
                relationships = [v.strip() for v in valor.split(",") if v.strip()]
            elif "characters" in nombre:
                characters = [v.strip() for v in valor.split(",") if v.strip()]
            elif "additional tags" in nombre:
                additional_tags = [v.strip() for v in valor.split(",") if v.strip()]

        etiquetas_principales = set()
        if rating:
            etiquetas_principales.add(rating)
        etiquetas_principales.update(categories)
        etiquetas_principales.update(relationships)

        etiquetas_adicionales = set(additional_tags)
        return titulo, autor, etiquetas_principales, etiquetas_adicionales, relationships, characters

    def _formatear_titulo(self, titulo, autor, relationships, characters):
        base = f"{titulo} - {autor}"
        candidatos = relationships[:3] if relationships else characters[:5]

        if not candidatos:
            return base[:100] if len(base) <= 100 else base[:100]

        items = []
        for cand in candidatos:
            if not items:
                nuevo = f"{base} [{cand}]"
            else:
                nuevo_items = " / ".join(items + [cand])
                nuevo = f"{base} [{nuevo_items}]"

            if len(nuevo) <= 100:
                items.append(cand)
            else:
                break

        if items:
            nombre_post = f"{base} [{' / '.join(items)}]"
        else:
            nombre_post = base

        if len(nombre_post) > 100:
            nombre_post = nombre_post[:100]

        return nombre_post

    @commands.command(help="Migra mensajes del bot de AO3")
    async def migrar(self, ctx, limite: int = None):
        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro: discord.ForumChannel = self.bot.get_channel(CANAL_FORO_ID)

        if origen is None:
            await ctx.send("No se encontró el canal de origen.")
            return
        if foro is None or not isinstance(foro, discord.ForumChannel):
            await ctx.send("No se encontró el foro de destino.")
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

            link = link_match.group(0)
            titulo, autor, etiquetas_principales, _, relationships, characters = self._parse_embed(embed)

            if not autor or link in obras_usadas:
                continue

            nombre_post = self._formatear_titulo(titulo, autor, relationships, characters)

            etiquetas_foro = {tag.name: tag for tag in foro.available_tags}
            applied_tags = [etiquetas_foro[n] for n in etiquetas_principales if n in etiquetas_foro]

            try:
                await foro.create_thread(
                    name=nombre_post,
                    content=link,
                    applied_tags=applied_tags
                )

                obras_usadas.add(link)
                count += 1
                print(f"📌 Migrado: {nombre_post} | Etiquetas: {', '.join([t.name for t in applied_tags]) or 'Ninguna'}")

                await asyncio.sleep(2)

            except discord.HTTPException as e:
                print(f"❌ Error al crear post ({nombre_post}): {e}")

        await ctx.send(f"✅ Migrados {count} mensajes únicos con links de AO3 al foro.")

    # ------------------ NUEVOS COMANDOS ------------------

    @commands.command(help="Lista relaciones y personajes usados en los mensajes AO3")
    async def etiquetas1(self, ctx, limite: int = None):
        canal = self.bot.get_channel(CANAL_ORIGEN_ID)
        if canal is None:
            await ctx.send("No se encontró el canal de origen.")
            return

        relaciones = []
        personajes = []

        async for msg in canal.history(limit=limite):
            if not msg.embeds:
                continue
            embed = msg.embeds[0]
            rels, chars, _ = self._parse_embed(embed)[4:6]
            relaciones.extend(rels)
            personajes.extend(chars)

        contador_rel = Counter(relaciones)
        contador_chars = Counter(personajes)

        texto = ["**Relaciones y Personajes encontrados:**"]
        for etiqueta, cant in contador_rel.most_common():
            texto.append(f" - {etiqueta} ({cant})")
        for etiqueta, cant in contador_chars.most_common():
            texto.append(f" - {etiqueta} ({cant})")

        if len(texto) == 1:
            texto.append(" - Ninguno encontrado.")

        await ctx.send("\n".join(texto))

    @commands.command(help="Lista tags adicionales usados en los mensajes AO3")
    async def etiquetas2(self, ctx, limite: int = None):
        canal = self.bot.get_channel(CANAL_ORIGEN_ID)
        if canal is None:
            await ctx.send("No se encontró el canal de origen.")
            return

        adicionales = []

        async for msg in canal.history(limit=limite):
            if not msg.embeds:
                continue
            embed = msg.embeds[0]
            adicionales.extend(self._parse_embed(embed)[3])

        contador = Counter(adicionales)
        texto = ["**Tags adicionales encontrados:**"]
        for etiqueta, cant in contador.most_common():
            texto.append(f" - {etiqueta} ({cant})")

        if len(texto) == 1:
            texto.append(" - Ninguno encontrado.")

        await ctx.send("\n".join(texto))

async def setup(bot):
    await bot.add_cog(Moderation(bot))
