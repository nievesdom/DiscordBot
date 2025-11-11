import discord
from discord.ext import commands
import re
import asyncio

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
        """
        Construye: "Título - autor [Rel1 / Rel2]" 
        Solo añade relaciones (máx 3) o personajes (máx 5) si **cada** nuevo nombre cabe completo
        sin superar 100 caracteres en total. No recorta nombres.
        """
        base = f"{titulo} - {autor}"  # formato base solicitado

        # preparar lista de candidatos a añadir entre corchetes (relaciones preferidas)
        candidatos = relationships[:3] if relationships else characters[:5]
        if not candidatos:
            # asegurar longitud permitida
            if len(base) == 0:
                return "Sin título"
            return base[:100]  # truncar base si excede (raro)

        # vamos añadiendo items uno a uno verificando si caben completos
        items = []
        for cand in candidatos:
            # si no hay items aún, el incremento añade: " [cand]"
            if not items:
                nuevo = f"{base} [{cand}]"
            else:
                # si ya hay items, añadimos " / cand" dentro de los corchetes
                nuevo_items = " / ".join(items + [cand])
                nuevo = f"{base} [{nuevo_items}]"

            if len(nuevo) <= 100:
                items.append(cand)
            else:
                # si este candidato no cabe entero, no intentamos candidatos más largos
                # (ya que la lista viene en orden de aparición y siguientes suelen ser igual o más largos)
                break

        if items:
            nombre_post = f"{base} [{ ' / '.join(items) }]"
        else:
            nombre_post = base

        # fallback por seguridad
        if not nombre_post:
            return "Sin título"
        if len(nombre_post) > 100:
            return nombre_post[:100]
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

            if not autor:
                continue
            if link in obras_usadas:
                continue

            # formatear título en el orden exacto solicitado
            nombre_post = self._formatear_titulo(titulo, autor, relationships, characters)

            etiquetas_foro = {tag.name: tag for tag in foro.available_tags}
            applied_tags = [etiquetas_foro[n] for n in etiquetas_principales if n in etiquetas_foro]

            try:
                # Crear hilo con el link como contenido (no editamos el mensaje)
                await foro.create_thread(
                    name=nombre_post,
                    content=link,
                    applied_tags=applied_tags
                )

                obras_usadas.add(link)
                count += 1
                print(f"📌 Migrado: {nombre_post} | Etiquetas: {', '.join([t.name for t in applied_tags]) or 'Ninguna'}")

                # Pequeña pausa para que AO3 Linker procese (puedes ajustar si hace falta)
                await asyncio.sleep(0.8)

            except discord.HTTPException as e:
                print(f"❌ Error al crear post ({nombre_post}): {e}")

        await ctx.send(f"✅ Migrados {count} mensajes únicos con links de AO3 al foro.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
