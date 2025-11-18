import discord
from discord.ext import commands
import re
import asyncio
from collections import Counter

# Regex para detectar links de obras en AO3
AO3_REGEX = re.compile(r"https?://archiveofourown\.org/works/\d+", re.IGNORECASE)

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    # -------------------- RESTRICCIÓN GLOBAL DEL COG --------------------
    async def cog_check(self, ctx: commands.Context):
        # Solo permite ejecutar comandos del Cog si el usuario tiene "Gestionar mensajes"
        return ctx.author.guild_permissions.manage_messages

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        # Mensaje si falla por permisos al usar comandos de este Cog
        if isinstance(error, commands.CheckFailure) and ctx.command and ctx.command.cog_name == self.__class__.__name__:
            await ctx.send("🚫 You need 'Manage messages' permission to use this command.")
        # Deja que otros errores se manejen por el handler global del bot (si existe)
        

    # -------------------- PARSEO DE EMBED --------------------
    def _parse_embed(self, embed: discord.Embed):
        # Obtener el título del embed, si no existe usar "Unknown"
        titulo = (embed.title or "Unknown").strip()
        # Si el título contiene " - Chapter", eliminar esa parte para quedarse con el título base
        titulo = titulo.split(" - Chapter")[0].strip() if " - Chapter" in titulo else titulo

        # Extraer la descripción del embed
        desc = embed.description or ""
        # Buscar autores
        autores = re.findall(r"\[([^\]]+)\]\(https://archiveofourown\.org/users/.+?\)", desc)
        autor = ", ".join(autores) if autores else None

        # Inicializar variables para almacenar datos
        rating = None
        categories = []
        relationships = []
        characters = []
        additional_tags = []
        
        # Diccionarios de simplificación
        REL_SIMPLIFICACIONES = {
            "Kiryu Kazuma/Majima Goro": ["Kiryu/Majima"],
            "Dojima Daigo/Mine Yoshitaka": ["Daigo/Mine"],
            "Kiryu Kazuma & Sawamura Haruka": ["Kiryu & Haruka"],
            "Dojima Daigo & Kiryu Kazuma": ["Daigo & Kiryu"],
            "Dojima Daigo/Shinada Tatsuo": ["Daigo/Shinada"],
            "Dojima Daigo & Sawamura Haruka": ["Daigo & Haruka"],
            "Kiryu Kazuma & Nishikiyama Akira": ["Kiryu & Nishiki"],
            "Kiryu Kazuma & Majima Goro": ["Kiryu & Majima"],
            "Dojima Daigo & Majima Goro": ["Daigo & Majima"],
            "Majima Goro & Sawamura Haruka": ["Majima & Haruka"],
            "Sawamura Haruka/Usami Yuta": ["Haruka/Yuta"],
            "Kasuga Ichiban/Zhao Tianyou": ["Ichiban/Zhao"],
        }

        TAG_SIMPLIFICACIONES = {
            "Alternate Universe - Canon Divergence": ["Alternate Universe"],
            "Established Relationship": ["Established Relation"],
            "Domestic Fluff": ["Fluff", "Domestic"],
            "Angst/Fluff": ["Angst", "Fluff"],
            "Emotional Hurt/Comfort": ["Hurt/Comfort"],
            "Fluff and Angst": ["Fluff", "Angst"],
        }

        # Función genérica para simplificar listas de tags
        def simplificar(tags, reglas):
            resultado = []
            for tag in tags:
                if tag in reglas:
                    resultado.extend(reglas[tag])  # puede añadir uno o varios
                else:
                    resultado.append(tag)
            return resultado

        # Recorrer campos del embed
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
                raw_rels = [v.strip() for v in valor.split(",") if v.strip()]
                relationships = simplificar(raw_rels, REL_SIMPLIFICACIONES)
            elif "characters" in nombre:
                characters = [v.strip() for v in valor.split(",") if v.strip()]
            elif "additional tags" in nombre:
                raw_tags = [v.strip() for v in valor.split(",") if v.strip()]
                additional_tags = simplificar(raw_tags, TAG_SIMPLIFICACIONES)

        # Construir conjuntos de etiquetas principales y adicionales
        etiquetas_principales = set()
        if rating:
            etiquetas_principales.add(rating)
        etiquetas_principales.update(categories)
        etiquetas_principales.update(relationships)

        etiquetas_adicionales = set(additional_tags)

        # Devolver toda la información procesada
        return titulo, autor, etiquetas_principales, etiquetas_adicionales, relationships, characters

    # -------------------- FORMATEO DE TÍTULO --------------------
    def _formatear_titulo(self, titulo, autor, relationships, characters):
        # Crear título base con título y autor
        base = f"{titulo} - {autor}"
        # Seleccionar candidatos: hasta 3 relaciones o hasta 5 personajes
        candidatos = relationships[:3] if relationships else characters[:5]
        if not candidatos:
            # Si no hay candidatos, devolver título base truncado a 100 caracteres
            return base[:100] if len(base) <= 100 else base[:100]

        items = []
        for cand in candidatos:
            # Construir título con candidatos entre corchetes
            if not items:
                nuevo = f"{base} [{cand}]"
            else:
                nuevo_items = " / ".join(items + [cand])
                nuevo = f"{base} [{nuevo_items}]"
            # Añadir candidato si no supera los 100 caracteres
            if len(nuevo) <= 100:
                items.append(cand)
            else:
                break
        
        # Construir título final
        if items:
            nombre_post = f"{base} [{' / '.join(items)}]"
        else:
            nombre_post = base

        # Devolver título truncado a 100 caracteres si es necesario
        return nombre_post[:100] if len(nombre_post) > 100 else nombre_post


    # -------------------- MIGRACIÓN --------------------
    @commands.command(help="Migrates AO3 linker's embed messages into from the specified channel to the specified forum. Ex: `y!migrate #origin_channel #target_forum (message_limit)`.", extras={"categoria": "Moderation 🔨"})
    async def migrate(self, ctx, canal_origen: discord.TextChannel = None, foro_destino: discord.ForumChannel = None, limite: int = None):

        # Comprobar que se han pasado canal origen y foro destino
        if not canal_origen or not foro_destino:
            await ctx.send("You must mention the origin channel and the target forum. You can also choose the maximum limit of messages for me to check. Ex: `y!migrate #origin_channel #target_forum (message_limit)`.")
            return

        count = 0
        obras_usadas = set()

        # Recorrer historial de mensajes del canal origen
        async for msg in canal_origen.history(limit=limite):
            if not msg.embeds:
                continue

            embed = msg.embeds[0]
            # Buscar enlace de AO3 en el mensaje o en el embed
            link_match = AO3_REGEX.search(msg.content) or AO3_REGEX.search(embed.url or "")
            if not link_match:
                continue

            link = link_match.group(0)
            # ⚠️ IMPORTANTE: ahora también recibimos etiquetas_adicionales
            titulo, autor, etiquetas_principales, etiquetas_adicionales, relationships, characters = self._parse_embed(embed)

            # Ignorar si no hay autor o si el enlace ya fue migrado
            if not autor or link in obras_usadas:
                continue
                
            # Formatear título y preparar etiquetas
            nombre_post = self._formatear_titulo(titulo, autor, relationships, characters)

            # 🔹 Unir etiquetas principales y adicionales
            todas_etiquetas = etiquetas_principales.union(etiquetas_adicionales)

            etiquetas_foro = {tag.name: tag for tag in foro_destino.available_tags}
            applied_tags = [etiquetas_foro[n] for n in todas_etiquetas if n in etiquetas_foro]

            try:
                # Crear hilo en el foro con título, enlace y etiquetas
                await foro_destino.create_thread(
                    name=nombre_post,
                    content=link,
                    applied_tags=applied_tags
                )

                obras_usadas.add(link)
                count += 1
                print(f"📌 Migrado: {nombre_post} | Etiquetas: {', '.join([t.name for t in applied_tags]) or 'Ninguna'}")
                await asyncio.sleep(3)

            except discord.HTTPException as e:
                print(f"❌ Error al crear post ({nombre_post}): {e}")
                
        # Informar al final de cuántos mensajes se migraron
        await ctx.send(f"✅ Successfuly migrated {count} messages from {canal_origen.mention} to {foro_destino.mention}.")


    # -------------------- ETIQUETAS 1 --------------------
    @commands.command(help="Lists the most common relationship and character tags from this channel's AO3 linker embed messages.", extras={"categoria": "Moderation 🔨"})
    async def tags1(self, ctx, limite: int = None, min_cantidad: int = 1):
        relaciones = []
        personajes = []

        # Recorrer historial de mensajesdel canal actual
        async for msg in ctx.channel.history(limit=limite):
            if not msg.embeds:
                continue
            embed = msg.embeds[0]
            _, _, _, _, rels, chars = self._parse_embed(embed)
            relaciones.extend(rels)
            personajes.extend(chars)

        # Contar ocurrencias de relaciones y personajes
        contador_rel = Counter(relaciones)
        contador_chars = Counter(personajes)

        texto = ["**Relationships and characters found:**"]
        for etiqueta, cant in contador_rel.most_common():
            if cant >= min_cantidad:
                texto.append(f" - {etiqueta} ({cant})")
        for etiqueta, cant in contador_chars.most_common():
            if cant >= min_cantidad:
                texto.append(f" - {etiqueta} ({cant})")

        if len(texto) == 1:
            texto.append(" - No relevant tags found.")

        mensaje = "\n".join(texto)
        if len(mensaje) > 2000:
            mensaje = mensaje[:1997] + "..."
        await ctx.send(mensaje)


    # -------------------- ETIQUETAS 2 --------------------
    @commands.command(help="Lists the most common additional tags from this channel's AO3 linker embed messages.", extras={"categoria": "Moderation 🔨"})
    async def tags2(self, ctx, limite: int = None, min_cantidad: int = 1):
        adicionales = []

        # Recorrer historial de mensajes del canal actual
        async for msg in ctx.channel.history(limit=limite):
            if not msg.embeds:
                continue
            embed = msg.embeds[0]
            _, _, _, etiquetas_adicionales, _, _ = self._parse_embed(embed)
            adicionales.extend(etiquetas_adicionales)

        # Contar ocurrencias de etiquetas adicionales
        contador = Counter(adicionales)
        texto = ["**Additional tags found:**"]
        for etiqueta, cant in contador.most_common():
            if cant >= min_cantidad:
                texto.append(f" - {etiqueta} ({cant})")

        if len(texto) == 1:
            texto.append(" - No relevant tags found.")

        mensaje = "\n".join(texto)
        if len(mensaje) > 2000:
            mensaje = mensaje[:1997] + "..."
        await ctx.send(mensaje)


# -------------------- REGISTRO DEL COG --------------------
async def setup(bot):
    await bot.add_cog(Moderation(bot))
