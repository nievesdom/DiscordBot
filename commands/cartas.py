import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import datetime
from core.firebase_client import db

# Core: carga/guardado en Gist y acceso a la base de cartas
from core.firebase_storage import cargar_settings, guardar_settings
from core.firebase_storage import cargar_packs, guardar_packs, cargar_propiedades, guardar_propiedades

from core.cartas import cargar_cartas, cartas_por_id

# Views: componentes interactivos
from views.navegador import Navegador
from views.reclamar import ReclamarCarta
from views.navegador_paquete import NavegadorPaquete
from views.navegador_trade import TradeView

# ID del dueño (ocultamos /carta solo para él)
OWNER_ID = 182920174276575232

def backup_settings(settings: dict) -> None:
    """Guarda una copia completa de settings en la colección settings_backup."""
    timestamp = datetime.datetime.now().isoformat()
    db.collection("settings_backup").document(timestamp).set(settings)
    
class Cartas(commands.Cog):
    """Cog principal para gestionar cartas y comandos del sistema RGGO."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.bloqueados = set()  # Conjunto opcional para bloquear usuarios en flujos

    async def _safe_defer(self, interaction: discord.Interaction, ephemeral: bool = False):
        """Hace defer seguro para evitar errores si ya se respondió."""
        try:
            await interaction.response.defer(ephemeral=ephemeral)
        except discord.InteractionResponded:
            pass
        
        

    # -----------------------------
    # SOLO OWNER
    # -----------------------------
    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(
        name="servers_info",
        description="(Owner only) Shows the servers where the bot is and their member counts."
    )
    async def servers_info(self, interaction: discord.Interaction):
        """Muestra información de todos los servidores donde está el bot."""
        # Ya no es ephemeral
        await interaction.response.defer(ephemeral=False)
    
        guilds = self.bot.guilds
        total_servers = len(guilds)
        info_lines = [
            f"• **{g.name}** (ID: {g.id}) → 👥 {g.member_count} members"
            for g in guilds
        ]
        listado = "\n".join(info_lines)
    
        embed = discord.Embed(
            title="🌐 Servers where the bot is present",
            description=f"Currently in **{total_servers} servers**:\n\n{listado}",
            color=discord.Color.green()
        )
    
        # Mensaje visible para todos en el canal
        await interaction.followup.send(embed=embed)
        
    # Decorador para restringir el comando solo a ti
    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(
        name="migrar_packs",
        description="(Owner only) Migra los datos de packs desde settings a la nueva colección packs."
    )
    async def migrar_packs(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        settings = cargar_settings()
        packs = {}

        # Recorremos todos los servidores en settings
        for servidor_id, servidor_data in settings.items():
            if servidor_id == "guilds":  # saltar config de auto_cards
                continue

            packs[servidor_id] = {}
            for usuario_id, usuario_data in servidor_data.items():
                ultimo = usuario_data.get("ultimo_paquete")
                if ultimo:
                    packs[servidor_id][usuario_id] = {"ultimo_paquete": ultimo}

        # Guardar en la nueva colección
        guardar_packs(packs)

        # Resumen de migración
        servidores = len(packs)
        usuarios = sum(len(u) for u in packs.values())

        await interaction.followup.send(
            f"✅ Migración completada.\n"
            f"- Servidores migrados: {servidores}\n"
            f"- Usuarios migrados: {usuarios}",
            ephemeral=True
        )
        
    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(
        name="borrar_packs_settings",
        description="(Owner only) Borra la información de paquetes desde settings."
    )
    async def borrar_packs_settings(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        settings = cargar_settings()

        # ✅ Guardar copia de seguridad antes de borrar
        backup_settings(settings)

        borrados = 0
        for servidor_id, servidor_data in settings.items():
            if servidor_id == "guilds":  # saltar config de auto_cards
                continue

            for usuario_id in list(servidor_data.keys()):
                if "ultimo_paquete" in servidor_data[usuario_id]:
                    servidor_data[usuario_id].pop("ultimo_paquete", None)
                    borrados += 1

        # Guardar cambios en settings (merge=True ya aplicado en guardar_settings)
        guardar_settings(settings)

        await interaction.followup.send(
            f"🗑️ Se han borrado {borrados} registros de 'ultimo_paquete' en settings.\n"
            f"📦 Copia de seguridad guardada en 'settings_backup'.",
            ephemeral=True
        )

    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(name="avisar_update", description="**[Bot owner only]** Send update notice to all servers with auto_cards enabled.")
    async def avisar_update(self, interaction: discord.Interaction):
        """Envía aviso de actualización a todos los servidores con auto_cards activado."""
        await interaction.response.defer(ephemeral=True)
        message = (
            "🚀 **The bot has been updated to version 1.1 and now supports slash commands!**\n"
            "Use `/help` to see the full list of available commands or `/update` in order to see a more detailed description of all the changes.\n"
            "Sorry for the downtime and if you experienced any issues before."
        )
        sent, failed = 0, 0
        cartas_cog = self.bot.get_cog("CartasAuto")
        if not cartas_cog:
            await interaction.followup.send("❌ CartasAuto cog not found.", ephemeral=True)
            return
        for gid, config in cartas_cog.settings.get("guilds", {}).items():
            if config.get("enabled"):
                guild = self.bot.get_guild(int(gid))
                if not guild:
                    continue
                channel = guild.get_channel(config["channel_id"])
                if not channel:
                    continue
                try:
                    await channel.send(message)
                    sent += 1
                except Exception as e:
                    print(f"[ERROR] No se pudo enviar aviso en guild {gid}: {e}")
                    failed += 1
        await interaction.followup.send(f"✅ Aviso enviado a {sent} servidores. ❌ Fallos: {failed}.", ephemeral=True)

    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(name="carta", description="Draws a random RGGO card")
    async def carta(self, interaction: discord.Interaction):
        """Muestra una carta aleatoria (solo owner)."""
        await interaction.response.defer()
        cartas = cargar_cartas()
        if not cartas:
            return await interaction.followup.send("No cards available.", ephemeral=True)
        elegida = random.choice(cartas)
        # Diccionarios de formato visual
        colores = {"UR": 0x8841f2, "KSR": 0xabfbff, "SSR": 0x57ffae, "SR": 0xfcb63d, "R": 0xfc3d3d, "N": 0x8c8c8c}
        atributos = {"heart": "心", "technique": "技", "body": "体", "light": "陽", "shadow": "陰"}
        tipos = {"attack": "⚔️ Attack", "defense": "🛡️ Defense", "recovery": "❤️ Recovery", "support": "✨ Support"}
        rareza = elegida.get("rareza", "N")
        color = colores.get(rareza, 0x8c8c8c)
        attr_raw = str(elegida.get("atributo", "—")).lower()
        tipo_raw = str(elegida.get("tipo", "—")).lower()
        attr_symbol = atributos.get(attr_raw, "")
        attr_name = attr_raw.capitalize() if attr_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
        tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")
        embed = discord.Embed(
            title=f"{elegida.get('nombre', 'Carta')}",
            color=color,
            description=(f"**Attribute:** {atributo_fmt}\n"
                         f"**Type:** {tipo_fmt}\n"
                         f"❤️ {elegida.get('health', '—')} | ⚔️ {elegida.get('attack', '—')} | "
                         f"🛡️ {elegida.get('defense', '—')} | 💨 {elegida.get('speed', '—')}")
        )
        ruta = elegida.get("imagen")
        archivo = None
        if ruta and ruta.startswith("http"):
            embed.set_image(url=ruta)
        elif ruta and os.path.exists(ruta):
            archivo = discord.File(ruta, filename="carta.png")
            embed.set_image(url="attachment://carta.png")
        vista = ReclamarCarta(elegida["id"], embed, ruta)
        
        if archivo:
            await interaction.followup.send(file=archivo, embed=embed, view=vista)
        else:
            await interaction.followup.send(embed=embed, view=vista)

    # -----------------------------
    # COMANDOS PÚBLICOS (slash + prefijo)
    # -----------------------------
    @app_commands.command(name="album", description="Shows a user's card collection in a visual format")
    async def album(self, interaction: discord.Interaction, user: discord.Member = None):
        """Muestra la galería navegable de un usuario (slash)."""
        await self._safe_defer(interaction)
        objetivo = user or interaction.user
        servidor_id, usuario_id = str(interaction.guild.id), str(objetivo.id)
        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await interaction.followup.send(f"{objetivo.display_name} has no cards yet.")
            return
        cartas_info = cartas_por_id()
        vista = Navegador(interaction, cartas_ids, cartas_info, objetivo)
        await vista.enviar()

    @commands.command(name="album")
    async def album_prefix(self, ctx: commands.Context, user: discord.Member = None):
        """Muestra la galería navegable de un usuario (prefijo)."""
        objetivo = user or ctx.author
        servidor_id, usuario_id = str(ctx.guild.id), str(objetivo.id)
        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await ctx.send(f"{objetivo.display_name} has no cards yet.")
            return
        cartas_info = cartas_por_id()
        vista = Navegador(ctx, cartas_ids, cartas_info, objetivo)
        await vista.enviar()
        
        
    # -----------------------------
    # /collection (texto)
    # -----------------------------
    @app_commands.command(name="collection", description="Shows a user's card collection in text mode")
    async def collection(self, interaction: discord.Interaction, user: discord.Member = None):
        """Muestra la colección como lista de nombres en texto plano (slash)."""
        await self._safe_defer(interaction, ephemeral=True)

        objetivo = user or interaction.user
        servidor_id, usuario_id = str(interaction.guild.id), str(objetivo.id)

        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await interaction.followup.send(f"{objetivo.display_name} has no cards yet.")
            return

        cartas_info = cartas_por_id()
        nombres = [cartas_info.get(str(cid), {}).get("nombre", f"ID {cid}") for cid in cartas_ids]
        nombres = sorted(nombres, key=lambda s: s.lower())

        texto = f"{objetivo.mention}, these are your cards ({len(nombres)}):\n" + "\n".join(nombres)
        # Fragmentar si excede el límite de Discord
        bloques = [texto[i:i+1900] for i in range(0, len(texto), 1900)]
        for b in bloques:
            await interaction.followup.send(b)

    @commands.command(name="collection")
    async def collection_prefix(self, ctx: commands.Context, user: discord.Member = None):
        """Muestra la colección como lista de nombres en texto plano (prefijo)."""
        objetivo = user or ctx.author
        servidor_id, usuario_id = str(ctx.guild.id), str(objetivo.id)

        propiedades = cargar_propiedades()
        cartas_ids = propiedades.get(servidor_id, {}).get(usuario_id, [])
        if not cartas_ids:
            await ctx.send(f"{objetivo.display_name} has no cards yet.")
            return

        cartas_info = cartas_por_id()
        nombres = [cartas_info.get(str(cid), {}).get("nombre", f"ID {cid}") for cid in cartas_ids]
        nombres = sorted(nombres, key=lambda s: s.lower())

        texto = f"{objetivo.mention}, these are your cards ({len(nombres)}):\n" + "\n".join(nombres)
        bloques = [texto[i:i+1900] for i in range(0, len(texto), 1900)]
        for b in bloques:
            await ctx.send(b)

    # -----------------------------
    # /search
    # -----------------------------
    @app_commands.command(name="search", description="Searches RGGO cards containing a term")
    async def search(self, interaction: discord.Interaction, term: str):
        """Busca cartas que contengan el término en su nombre (slash)."""
        await self._safe_defer(interaction, ephemeral=True)

        if not term:
            await interaction.followup.send("You must provide a search term. Example: /search Yamai", ephemeral=True)
            return

        cartas = cargar_cartas()
        coincidencias = [c for c in cartas if term.lower() in c["nombre"].lower()]
        coincidencias = sorted(coincidencias, key=lambda x: x["nombre"])

        if not coincidencias:
            await interaction.followup.send(f"No cards found containing '{term}'.")
            return

        propiedades = cargar_propiedades()
        cartas_usuario = propiedades.get(str(interaction.guild.id), {}).get(str(interaction.user.id), [])

        mensaje = "```diff\n"
        for c in coincidencias:
            cid = str(c["id"])
            nombre = c["nombre"]
            if cid in map(str, cartas_usuario):
                mensaje += f"+ {nombre}\n"
            else:
                mensaje += f"- {nombre}\n"
        mensaje += "```"

        await interaction.followup.send(mensaje)
        await interaction.followup.send(f"{len(coincidencias)} cards found containing '{term}'.")

    @commands.command(name="search")
    async def search_prefix(self, ctx: commands.Context, *, term: str):
        """Busca cartas que contengan el término en su nombre (prefijo)."""
        if not term:
            await ctx.send("You must provide a search term. Example: y!search Yamai")
            return

        cartas = cargar_cartas()
        coincidencias = [c for c in cartas if term.lower() in c["nombre"].lower()]
        coincidencias = sorted(coincidencias, key=lambda x: x["nombre"])

        if not coincidencias:
            await ctx.send(f"No cards found containing '{term}'.")
            return

        propiedades = cargar_propiedades()
        cartas_usuario = propiedades.get(str(ctx.guild.id), {}).get(str(ctx.author.id), [])

        mensaje = "```diff\n"
        for c in coincidencias:
            cid = str(c["id"])
            nombre = c["nombre"]
            if cid in map(str, cartas_usuario):
                mensaje += f"+ {nombre}\n"
            else:
                mensaje += f"- {nombre}\n"
        mensaje += "```"

        await ctx.send(mensaje)
        await ctx.send(f"{len(coincidencias)} cards found containing '{term}'.")

    # -----------------------------
    # /pack (diario)
    # -----------------------------

    @app_commands.command(name="pack", description="Opens a daily pack of 5 cards")
    async def pack(self, interaction: discord.Interaction):
        """Allows opening a daily pack of 5 cards (slash)."""
        await interaction.response.defer(ephemeral=False)
        # Diferimos la respuesta para poder responder luego con followup
    
        # Validar que el comando se ejecuta en un servidor
        if interaction.guild is None:
            await interaction.followup.send("🚫 This command can only be used in servers.")
            return
    
        # Identificadores del servidor y del usuario
        servidor_id = str(interaction.guild.id)
        usuario_id = str(interaction.user.id)
    
        # Cargar la estructura de packs
        try:
            packs = cargar_packs()
        except Exception as e:
            # Si fallan los datos, informar y salir
            await interaction.followup.send("❌ Could not load packs data. Please try again later.")
            print(f"[ERROR] cargar_packs failed: {e}")
            return
    
        servidor_packs = packs.setdefault(servidor_id, {})  # Diccionario de packs por servidor
        usuario_packs = servidor_packs.setdefault(usuario_id, {})  # Diccionario de packs por usuario
    
        # Obtener configuración del servidor desde settings
        # Si no existe pack_limit, se asume 1 pack/día por defecto (24h, único intervalo)
        servidor_settings = self.settings["guilds"].setdefault(servidor_id, {})
        packs_diarios = servidor_settings.get("pack_limit", 1)
    
        # Cada día tiene 24h → se divide en intervalos según packs_diarios
        # Para 5 packs: 24*3600/5 = 17280s (4h48m), etc.
        intervalo_segundos = int(24 * 3600 / packs_diarios)
    
        # Hora actual y comienzo del día (medianoche)
        ahora = datetime.datetime.now()
        inicio_dia = datetime.datetime.combine(ahora.date(), datetime.time.min)
    
        # Segundos transcurridos desde medianoche
        segundos_actual = (ahora - inicio_dia).total_seconds()
    
        # Franja actual en la que estamos (ej: 0=00:00–11:59 si son 2 packs/día)
        franja_actual = int(segundos_actual // intervalo_segundos)
    
        # Recuperar la última vez que el usuario abrió un pack
        ultimo_str = usuario_packs.get("ultimo_paquete")
        if ultimo_str:
            try:
                # Intentar parsear con fecha y hora exacta
                ultimo_dt = datetime.datetime.fromisoformat(ultimo_str)
            except ValueError:
                # Si solo se guardó la fecha (YYYY-MM-DD), asumir medianoche
                try:
                    ultimo_dt = datetime.datetime.fromisoformat(ultimo_str + "T00:00:00")
                except Exception as e:
                    # Si el valor es corrupto, limpiar para no bloquear al usuario
                    print(f"[WARN] Invalid ultimo_paquete '{ultimo_str}': {e}. Resetting value.")
                    ultimo_dt = None
    
                # Actualizar packs para que quede en formato completo si pudimos parsear
                if ultimo_dt is not None:
                    usuario_packs["ultimo_paquete"] = ultimo_dt.isoformat()
                    try:
                        guardar_packs(packs)
                    except Exception as e:
                        # No impedir el flujo por fallo al guardar, pero reportar
                        print(f"[ERROR] guardar_packs after normalization failed: {e}")
    
            # Validación de cooldown por franja si tenemos fecha válida
            if ultimo_dt is not None and ultimo_dt.date() == ahora.date():
                # Calcular en qué franja cayó el último pack
                segundos_ultimo = (ultimo_dt - inicio_dia).total_seconds()
                # En casos raros podría ser negativo (si ultimo_dt es de otro día), controlar
                if segundos_ultimo < 0:
                    segundos_ultimo = 0
                franja_ultimo = int(segundos_ultimo // intervalo_segundos)
    
                # Si ya abrió en la misma franja, bloquear y calcular tiempo restante
                if franja_actual == franja_ultimo:
                    restante = intervalo_segundos - (segundos_actual - segundos_ultimo)
                    if restante < 0:
                        restante = 0
                    horas, resto = divmod(int(restante), 3600)
                    minutos = resto // 60
                    await interaction.followup.send(
                        f"🚫 {interaction.user.mention}, you must wait {horas}h {minutos}m before opening another pack."
                    )
                    return
    
        # Cargar cartas disponibles
        try:
            cartas = cargar_cartas()
        except Exception as e:
            await interaction.followup.send("❌ Could not load cards. Please try again later.", ephemeral=True)
            print(f"[ERROR] cargar_cartas failed: {e}")
            return
    
        if not cartas:
            await interaction.followup.send("❌ No cards available.", ephemeral=True)
            return
    
        # Validar que hay al menos 5 cartas para el sample
        if len(cartas) < 5:
            await interaction.followup.send("❌ Not enough cards to open a pack.", ephemeral=True)
            return
    
        # Seleccionar 5 cartas aleatorias
        try:
            nuevas_cartas = random.sample(cartas, 5)
        except Exception as e:
            await interaction.followup.send("❌ Could not select cards for the pack. Please try again.", ephemeral=True)
            print(f"[ERROR] random.sample failed: {e}")
            return
    
        # Guardar fecha y hora exacta del pack abierto
        usuario_packs["ultimo_paquete"] = ahora.isoformat()
        try:
            guardar_packs(packs)
        except Exception as e:
            # No bloquear la entrega del pack por fallo al guardar, pero informar internamente
            print(f"[ERROR] guardar_packs failed: {e}")
    
        # Guardar las cartas obtenidas en propiedades del usuario
        try:
            propiedades = cargar_propiedades()
            servidor_props = propiedades.setdefault(servidor_id, {})
            usuario_cartas = servidor_props.setdefault(usuario_id, [])
            usuario_cartas.extend([c["id"] for c in nuevas_cartas])
            guardar_propiedades(propiedades)
        except Exception as e:
            # Si falla persistencia de propiedades, enviar pack igualmente y reportar
            print(f"[ERROR] propiedades persistence failed: {e}")
    
        # Preparar la vista del paquete con las cartas
        try:
            cartas_info = cartas_por_id()
            cartas_ids = [c["id"] for c in nuevas_cartas]
            vista = NavegadorPaquete(interaction, cartas_ids, cartas_info, interaction.user)
            embed, archivo = vista.mostrar()
        except Exception as e:
            # Si falla la vista, enviar un mensaje simple igualmente
            print(f"[ERROR] NavegadorPaquete failed: {e}")
            embed, archivo = None, None
    
        # Enviar log al canal de logs central (no bloquear si falla)
        try:
            log_guild_id = 286617766516228096
            log_channel_id = 1441990735883800607
            log_guild = interaction.client.get_guild(log_guild_id)
            if log_guild:
                log_channel = log_guild.get_channel(log_channel_id)
                if log_channel:
                    nombres_cartas = ", ".join([f"{c['nombre']} [ID: {c['id']}]" for c in nuevas_cartas])
                    await log_channel.send(
                        f"[PACK] {interaction.user.display_name} opened a pack in {interaction.guild.name} "
                        f"with the cards: {nombres_cartas}"
                    )
        except Exception as e:
            print(f"[ERROR] Could not send log: {e}")
    
        # Enviar el resultado al usuario
        if archivo:
            await interaction.followup.send(file=archivo, embed=embed, view=vista)
        else:
            # Si no hay embed/archivo, enviar un mensaje de éxito mínimo
            await interaction.followup.send("✅ Pack opened: 5 cards added to your collection.", embed=embed, view=vista)




    # -----------------------------
    # y!pack (diario)
    # -----------------------------
    @commands.command(name="pack")
    async def pack_prefix(self, ctx: commands.Context):
        """Permite abrir un paquete diario de 5 cartas (prefijo)."""
        servidor_id = str(ctx.guild.id)
        usuario_id = str(ctx.author.id)

        # ✅ Usamos packs en lugar de settings
        packs = cargar_packs()
        servidor_packs = packs.setdefault(servidor_id, {})
        usuario_packs = servidor_packs.setdefault(usuario_id, {})

        hoy = datetime.date.today().isoformat()
        ahora = datetime.datetime.now()

        if usuario_packs.get("ultimo_paquete") == hoy:
            mañana = ahora + datetime.timedelta(days=1)
            medianoche = datetime.datetime.combine(mañana.date(), datetime.time.min)
            restante = medianoche - ahora
            horas, resto = divmod(restante.seconds, 3600)
            minutos = resto // 60
            await ctx.send(
                f"🚫 {ctx.author.mention}, you already opened today's pack, come back in {horas}h {minutos}m."
            )
            return

        cartas = cargar_cartas()
        if not cartas:
            await ctx.send("❌ No cards available.")
            return

        nuevas_cartas = random.sample(cartas, 5)
        usuario_packs["ultimo_paquete"] = hoy
        guardar_packs(packs)  # ✅ Guardamos en packs

        propiedades = cargar_propiedades()
        servidor_props = propiedades.setdefault(servidor_id, {})
        usuario_cartas = servidor_props.setdefault(usuario_id, [])
        usuario_cartas.extend([c["id"] for c in nuevas_cartas])
        guardar_propiedades(propiedades)

        cartas_info = cartas_por_id()
        cartas_ids = [c["id"] for c in nuevas_cartas]
        vista = NavegadorPaquete(ctx, cartas_ids, cartas_info, ctx.author)
        embed, archivo = vista.mostrar()

        # 🔥 Enviar log al servidor/canal de logs
        log_guild_id = 286617766516228096
        log_channel_id = 1441990735883800607
        log_guild = ctx.bot.get_guild(log_guild_id)  # ✅ corregido: ctx.bot
        if log_guild:
            log_channel = log_guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    nombres_cartas = ", ".join([f"{c['nombre']} [ID: {c['id']}]" for c in nuevas_cartas])
                    await log_channel.send(
                        f"[PACK] {ctx.author.display_name} abrió un paquete en {ctx.guild.name} "
                        f"con las cartas: {nombres_cartas}"
                    )
                except Exception as e:
                    print(f"[ERROR] Could not send log: {e}")

        if archivo:
            await ctx.send(file=archivo, embed=embed, view=vista)
        else:
            await ctx.send(embed=embed, view=vista)
            
    
    @app_commands.default_permissions(administrator=True)  # Solo visible para administradores
    @app_commands.command(
        name="pack_limit",
        description="(Admin) Set how many packs per day can be opened in this server (1-6)."
    )
    @app_commands.describe(packs="Number of packs per day allowed (1 to 6)")
    async def pack_limit(self, interaction: discord.Interaction, packs: int):
        # ID del servidor
        gid = str(interaction.guild_id)

        # Limitar el valor entre 1 y 6
        packs = max(1, min(packs, 6))

        # Tabla de cooldown en horas según packs diarios
        cooldown_map = {
            6: 4,       # 6 packs → cada 4h
            5: 4.8,     # 5 packs → cada 4h48m
            4: 6,       # 4 packs → cada 6h
            3: 8,       # 3 packs → cada 8h
            2: 12,      # 2 packs → cada 12h
            1: 24       # 1 pack → cada 24h
        }
        cooldown_horas = cooldown_map[packs]

        # Guardar configuración en settings del servidor
        self.settings["guilds"].setdefault(gid, {})
        self.settings["guilds"][gid]["pack_limit"] = packs
        self.settings["guilds"][gid]["pack_cooldown_hours"] = cooldown_horas
        self.marcar_cambios()

        # Respuesta al administrador
        await interaction.response.send_message(
            f"✅ Pack limit set to {packs} per day, cooldown {cooldown_horas}h between packs."
        )





    # -----------------------------
    # /show (detalles de una carta)
    # -----------------------------
    @app_commands.command(name="show", description="Shows a card's image and data")
    @app_commands.describe(name="Name of the card you want to see")
    async def show(self, interaction: discord.Interaction, name: str):
        """Muestra una carta concreta buscando por nombre (slash)."""
        await self._safe_defer(interaction)

        if not name:
            await interaction.followup.send("⚠️ You must provide a card's name.", ephemeral=True)
            return

        cartas = cargar_cartas()
        carta = next((c for c in cartas if name.lower() in c["nombre"].lower()), None)
        if not carta:
            await interaction.followup.send(f"❌ No card found containing '{name}'.")
            return

        # Diccionarios de formato visual
        colores = {"UR": 0x8841f2, "KSR": 0xabfbff, "SSR": 0x57ffae, "SR": 0xfcb63d, "R": 0xfc3d3d, "N": 0x8c8c8c}
        atributos = {"heart": "心", "technique": "技", "body": "体", "light": "陽", "shadow": "陰"}
        tipos = {"attack": "⚔️ Attack", "defense": "🛡️ Defense", "recovery": "❤️ Recovery", "support": "✨ Support"}

        rareza = carta.get("rareza", "N")
        color = colores.get(rareza, 0x8c8c8c)
        attr_raw = str(carta.get("atributo", "—")).lower()
        tipo_raw = str(carta.get("tipo", "—")).lower()
        attr_symbol = atributos.get(attr_raw, "")
        attr_name = attr_raw.capitalize() if attr_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
        tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

        embed = discord.Embed(
            title=f"{carta.get('nombre', 'Carta')}",
            color=color,
            description=(f"**Attribute:** {atributo_fmt}\n"
                         f"**Type:** {tipo_fmt}\n"
                         f"❤️ {carta.get('health', '—')} | ⚔️ {carta.get('attack', '—')} | "
                         f"🛡️ {carta.get('defense', '—')} | 💨 {carta.get('speed', '—')}")
        )

        ruta_img = carta.get("imagen")
        if ruta_img and ruta_img.startswith("http"):
            embed.set_image(url=ruta_img)
        else:
            embed.description += "\n⚠️ Image not found. Please, contact my creator."

        await interaction.followup.send(embed=embed)

    @commands.command(name="show")
    async def show_prefix(self, ctx: commands.Context, *, name: str):
        """Muestra una carta concreta buscando por nombre (prefijo)."""
        if not name:
            await ctx.send("⚠️ You must provide a card's name.")
            return

        cartas = cargar_cartas()
        carta = next((c for c in cartas if name.lower() in c["nombre"].lower()), None)
        if not carta:
            await ctx.send(f"❌ No card found containing '{name}'.")
            return

        # Diccionarios de formato visual
        colores = {"UR": 0x8841f2, "KSR": 0xabfbff, "SSR": 0x57ffae, "SR": 0xfcb63d, "R": 0xfc3d3d, "N": 0x8c8c8c}
        atributos = {"heart": "心", "technique": "技", "body": "体", "light": "陽", "shadow": "陰"}
        tipos = {"attack": "⚔️ Attack", "defense": "🛡️ Defense", "recovery": "❤️ Recovery", "support": "✨ Support"}

        rareza = carta.get("rareza", "N")
        color = colores.get(rareza, 0x8c8c8c)
        attr_raw = str(carta.get("atributo", "—")).lower()
        tipo_raw = str(carta.get("tipo", "—")).lower()
        attr_symbol = atributos.get(attr_raw, "")
        attr_name = attr_raw.capitalize() if attr_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
        tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

        embed = discord.Embed(
            title=f"{carta.get('nombre', 'Carta')}",
            color=color,
            description=(f"**Attribute:** {atributo_fmt}\n"
                         f"**Type:** {tipo_fmt}\n"
                         f"❤️ {carta.get('health', '—')} | ⚔️ {carta.get('attack', '—')} | "
                         f"🛡️ {carta.get('defense', '—')} | 💨 {carta.get('speed', '—')}")
        )

        ruta_img = carta.get("imagen")
        if ruta_img and ruta_img.startswith("http"):
            embed.set_image(url=ruta_img)
        else:
            embed.description += "\n⚠️ Image not found. Please, contact my creator."

        await ctx.send(embed=embed)

    # -----------------------------
    # /trade (intercambio de cartas entre jugadores)
    # -----------------------------
    @app_commands.command(name="trade", description="Starts a card trade with another user")
    @app_commands.describe(user="User to trade with", card="Card to trade")
    async def trade(self, interaction: discord.Interaction, user: discord.Member, card: str):
        servidor_id = str(interaction.guild.id)
        usuario1_id = str(interaction.user.id)
        usuario2_id = str(user.id)

        propiedades = cargar_propiedades()
        coleccion1 = propiedades.get(servidor_id, {}).get(usuario1_id, [])

        cartas = cargar_cartas()
        carta1_obj = next((c for c in cartas if card.lower() in c["nombre"].lower()), None)
        if not carta1_obj:
            await interaction.response.send_message(f"❌ The card '{card}' hasn't been found.", ephemeral=True)
            return

        if carta1_obj["id"] not in coleccion1:
            await interaction.response.send_message(f"❌ You don't own a card named {card}.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"{user.mention}, {interaction.user.display_name} wants to trade their card **{carta1_obj['nombre']}** with you.\n"
            f"Please choose whether to accept or reject.",
            view=TradeView(interaction.user, user, carta1_obj)
        )

    @commands.command(name="trade")
    async def trade_prefix(self, ctx: commands.Context, user: discord.Member, *, card: str):
        servidor_id = str(ctx.guild.id)
        usuario1_id = str(ctx.author.id)

        propiedades = cargar_propiedades()
        coleccion1 = propiedades.get(servidor_id, {}).get(usuario1_id, [])

        cartas = cargar_cartas()
        carta1_obj = next((c for c in cartas if card.lower() in c["nombre"].lower()), None)
        if not carta1_obj:
            await ctx.send(f"❌ The card '{card}' hasn't been found.")
            return

        if carta1_obj["id"] not in coleccion1:
            await ctx.send(f"❌ You don't own a card named {card}.")
            return

        await ctx.send(
            f"{user.mention}, {ctx.author.display_name} wants to trade their card **{carta1_obj['nombre']}** with you.\n"
            f"Please choose whether to accept or reject.",
            view=TradeView(ctx.author, user, carta1_obj)
        )


# -----------------------------
# Registro del cog en el bot
# -----------------------------
async def setup(bot: commands.Bot):
    """Función de setup para registrar el cog en el bot."""
    await bot.add_cog(Cartas(bot))
