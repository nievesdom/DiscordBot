import discord
from discord.ext import commands
import re
import asyncio
from collections import Counter

# IDs fijos de canales
CANAL_ORIGEN_ID = 1437348279107977266   # Canal de texto donde están los embeds originales de AO3
CANAL_FORO_ID = 1437348404559876226     # Canal de foro donde se crearán los threads

# Regex para detectar links de obras en AO3
AO3_REGEX = re.compile(r"https?://archiveofourown\.org/works/\d+", re.IGNORECASE)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -------------------- PARSEO DE EMBED --------------------
    def _parse_embed(self, embed: discord.Embed):
        """
        Extrae datos del embed:
        - titulo
        - autor(es)
        - etiquetas principales (rating, categories, relationships)
        - etiquetas adicionales (additional tags)
        - relaciones y personajes por separado
        """

        # Título base del embed, eliminando capítulo si existe
        titulo = (embed.title or "Título desconocido").strip()
        titulo = titulo.split(" - Chapter")[0].strip() if " - Chapter" in titulo else titulo

        # Descripción del embed para extraer autores
        desc = embed.description or ""
        autores = re.findall(r"\[([^\]]+)\]\(https://archiveofourown\.org/users/.+?\)", desc)
        autor = ", ".join(autores) if autores else None

        # Inicializamos listas para cada tipo de etiqueta
        rating = None
        categories = []
        relationships = []
        characters = []
        additional_tags = []

        # Recorremos cada campo del embed y asignamos su contenido según el nombre
        for field in embed.fields:
            nombre = field.name.lower().strip(": ")  # estandarizamos el nombre del campo
            valor = field.value.strip()
            if "rating" in nombre:
                rating = re.sub(r"^[:\w\s]*:", "", valor).strip(" :")
                # Acortamos Teen And Up Audiences a Teen And Up
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

        # Conjunto de etiquetas principales que se mapearán al foro
        etiquetas_principales = set()
        if rating:
            etiquetas_principales.add(rating)
        etiquetas_principales.update(categories)
        etiquetas_principales.update(relationships)

        # Conjunto de etiquetas adicionales
        etiquetas_adicionales = set(additional_tags)

        return titulo, autor, etiquetas_principales, etiquetas_adicionales, relationships, characters

    # Formateo del título
    def _formatear_titulo(self, titulo, autor, relationships, characters):
        """
        Construye el título final del post en el foro:
        Formato: "Título - autor [Rel1 / Rel2]"
        - Añade hasta 3 relaciones o 5 personajes, solo si caben completos
        - Nunca recorta nombres dentro de los corchetes
        - Respeta el límite máximo de 100 caracteres de Discord
        """

        base = f"{titulo} - {autor}"  # formato base solicitado

        # Prioridad: relaciones, si no hay, usamos personajes
        candidatos = relationships[:3] if relationships else characters[:5]

        # Si no hay relaciones ni personajes, devolvemos solo el título base
        if not candidatos:
            return base[:100] if len(base) <= 100 else base[:100]

        items = []  # Lista de elementos que se van a añadir entre corchetes
        for cand in candidatos:
            if not items:
                nuevo = f"{base} [{cand}]"
            else:
                nuevo_items = " / ".join(items + [cand])
                nuevo = f"{base} [{nuevo_items}]"

            # Solo añadimos si el nuevo título completo no supera 100 caracteres
            if len(nuevo) <= 100:
                items.append(cand)
            else:
                break

        # Construimos el nombre final con los elementos añadidos
        if items:
            nombre_post = f"{base} [{' / '.join(items)}]"
        else:
            nombre_post = base

        # Garantizamos que nunca supere 100 caracteres
        if len(nombre_post) > 100:
            nombre_post = nombre_post[:100]

        return nombre_post


    @commands.command(help="Migra mensajes del bot de AO3")
    async def migrar(self, ctx, limite: int = None):
        """
        Recorre los mensajes del canal de origen
        - Detecta solo mensajes con embeds de AO3
        - Evita duplicados por link
        - Formatea título correctamente
        - Mapea etiquetas principales a las del foro
        - Crea threads en el foro con link original (AO3 Linker se activa automáticamente)
        """

        origen = self.bot.get_channel(CANAL_ORIGEN_ID)
        foro: discord.ForumChannel = self.bot.get_channel(CANAL_FORO_ID)

        if origen is None:
            await ctx.send("No se encontró el canal de origen.")
            return
        if foro is None or not isinstance(foro, discord.ForumChannel):
            await ctx.send("No se encontró el foro de destino.")
            return

        count = 0
        obras_usadas = set()  # Evita duplicados por link

        async for msg in origen.history(limit=limite):
            if not msg.embeds:
                continue

            embed = msg.embeds[0]
            link_match = AO3_REGEX.search(msg.content) or AO3_REGEX.search(embed.url or "")
            if not link_match:
                continue

            link = link_match.group(0)
            titulo, autor, etiquetas_principales, _, relationships, characters = self._parse_embed(embed)

            # Ignoramos si no se detecta autor o si ya se migró esta obra
            if not autor or link in obras_usadas:
                continue

            # Formateamos título según el orden exacto solicitado
            nombre_post = self._formatear_titulo(titulo, autor, relationships, characters)

            # Mapear etiquetas principales a etiquetas disponibles en el foro
            etiquetas_foro = {tag.name: tag for tag in foro.available_tags}
            applied_tags = [etiquetas_foro[n] for n in etiquetas_principales if n in etiquetas_foro]

            try:
                # Crear thread con el link
                await foro.create_thread(
                    name=nombre_post,
                    content=link,
                    applied_tags=applied_tags
                )

                obras_usadas.add(link)
                count += 1
                print(f"📌 Migrado: {nombre_post} | Etiquetas: {', '.join([t.name for t in applied_tags]) or 'Ninguna'}")

                # Pequeña pausa para asegurar que AO3 Linker genere el embed
                await asyncio.sleep(2)

            except discord.HTTPException as e:
                print(f"❌ Error al crear post ({nombre_post}): {e}")

        await ctx.send(f"✅ Migrados {count} mensajes únicos con links de AO3 al foro.")


    @commands.command(help="Lista relaciones y personajes usados en los mensajes AO3")
    async def etiquetas1(self, ctx, limite: int = None):
        """
        Recorre los embeds del canal de origen y lista:
        - Relaciones
        - Personajes
        Muestra la cantidad de veces que aparece cada etiqueta
        """
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

            # Desempaquetamos todos los valores de _parse_embed y tomamos solo relaciones y personajes
            _, _, _, _, rels, chars = self._parse_embed(embed)
            relaciones.extend(rels)
            personajes.extend(chars)

        # Contamos la cantidad de veces que aparece cada etiqueta
        contador_rel = Counter(relaciones)
        contador_chars = Counter(personajes)

        texto = ["**Relaciones y Personajes encontrados:**"]
        # Ordenamos por cantidad descendente
        for etiqueta, cant in contador_rel.most_common():
            texto.append(f" - {etiqueta} ({cant})")
        for etiqueta, cant in contador_chars.most_common():
            texto.append(f" - {etiqueta} ({cant})")

        if len(texto) == 1:
            texto.append(" - Ninguno encontrado.")

        await ctx.send("\n".join(texto))


    @commands.command(help="Lista tags adicionales usados en los mensajes AO3")
    async def etiquetas2(self, ctx, limite: int = None):
        """
        Recorre los embeds del canal de origen y lista los tags adicionales (additional tags)
        Muestra la cantidad de veces que aparece cada tag
        """
        canal = self.bot.get_channel(CANAL_ORIGEN_ID)
        if canal is None:
            await ctx.send("No se encontró el canal de origen.")
            return

        adicionales = []

        async for msg in canal.history(limit=limite):
            if not msg.embeds:
                continue
            embed = msg.embeds[0]

            # Extraemos etiquetas adicionales desempaquetando todos los valores
            _, _, _, etiquetas_adicionales, _, _ = self._parse_embed(embed)
            adicionales.extend(etiquetas_adicionales)

        # Contamos y ordenamos por frecuencia
        contador = Counter(adicionales)
        texto = ["**Tags adicionales encontrados:**"]
        for etiqueta, cant in contador.most_common():
            texto.append(f" - {etiqueta} ({cant})")

        if len(texto) == 1:
            texto.append(" - Ninguno encontrado.")

        await ctx.send("\n".join(texto))


# -------------------- REGISTRO DEL COG --------------------
async def setup(bot):
    await bot.add_cog(Moderation(bot))
