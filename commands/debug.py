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

PROPIEDADES_COLLECTION = "propiedades"
PROPIEDADES_DOC = "global"


class Debug(commands.Cog):
    """Cog con comandos exclusivos para el dueño del bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(
        name="backup_propiedades",
        description="(Owner only) Create a safe backup of propiedades in Firebase."
    )
    async def backup_propiedades(self, interaction: discord.Interaction):

        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "🚫 Only the bot owner can run this command.",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            timestamp = datetime.datetime.now().isoformat()
            backup_ref = db.collection("propiedades_backup").document(timestamp)

            # ⚠️ IMPORTANTE: leer SIN to_dict()
            doc = (
                db.collection(PROPIEDADES_COLLECTION)
                .document(PROPIEDADES_DOC)
                .get()
            )

            if not doc.exists:
                await interaction.followup.send(
                    "⚠️ No propiedades document found.",
                    ephemeral=True
                )
                return

            propiedades = doc.to_dict()
            total_servidores = len(propiedades)

            guardados = 0

            for servidor_id, datos_servidor in propiedades.items():
                backup_ref.collection("servidores").document(servidor_id).set(datos_servidor)
                guardados += 1

                # ceder control al event loop cada cierto número
                if guardados % 10 == 0:
                    await asyncio.sleep(0)

            await interaction.followup.send(
                f"✅ Propiedades backup completed.\n"
                f"Servers backed up: {guardados}/{total_servidores}\n"
                f"Backup ID: `{timestamp}`",
                ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(
                f"❌ Propiedades backup failed:\n`{type(e).__name__}: {e}`",
                ephemeral=True
            )


    
    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(
        name="backup_packs",
        description="(Owner only) Create a backup of packs in Firebase."
    )
    async def backup_packs(self, interaction: discord.Interaction):
        # Verificar que el usuario es el dueño
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "🚫 Only the bot owner can run this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # 1. Cargar packs actuales
            packs = cargar_packs()

            # 2. Crear ID de backup con timestamp
            timestamp = datetime.datetime.now().isoformat()
            backup_id = f"packs_backup_{timestamp}"

            # 3. Guardar en Firebase en colección 'packs_backup'
            db.collection("packs_backup").document(backup_id).set(packs)

            await interaction.followup.send(
                f"✅ Packs backup created as `{backup_id}` in Firebase.", ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Packs backup failed: {e}", ephemeral=True)
            
            
    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(
        name="backup_settings",
        description="(Owner only) Create a backup of settings in Firebase."
    )
    async def backup_settings(self, interaction: discord.Interaction):
        # Verificar que el usuario es el dueño
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "🚫 Only the bot owner can run this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # 1. Cargar settings actuales
            settings = cargar_settings()

            # 2. Crear ID de backup con timestamp
            timestamp = datetime.datetime.now().isoformat()
            backup_id = f"settings_backup_{timestamp}"

            # 3. Guardar en Firebase en colección 'settings_backup'
            db.collection("settings_backup").document(backup_id).set(settings)

            await interaction.followup.send(
                f"✅ Settings backup created as `{backup_id}` in Firebase.", ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Settings backup failed: {e}", ephemeral=True)
            
            
    '''@app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)        
    @app_commands.command(
        name="normalize_packs",
        description="(Owner only) Normalize dates in the latest packs backup to include hours and minutes."
    )
    async def normalize_backup_packs(self, interaction: discord.Interaction):
        # Verificar que el usuario es el dueño
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "🚫 Only the bot owner can run this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # 1. Obtener el último backup de la colección packs_backup
            backups = db.collection("packs_backup").get()
            if not backups:
                await interaction.followup.send("❌ No backups found.", ephemeral=True)
                return

            # Ordenar por nombre (backup_<timestamp>) y coger el último
            backups_sorted = sorted(backups, key=lambda b: b.id, reverse=True)
            latest_backup = backups_sorted[0]
            packs = latest_backup.to_dict()

            # 2. Normalizar fechas
            cambios = 0
            for servidor_id, usuarios in packs.items():
                for usuario_id, datos in usuarios.items():
                    ultimo_str = datos.get("ultimo_paquete")
                    if not ultimo_str:
                        continue

                    # Caso 1: solo fecha YYYY-MM-DD
                    if len(ultimo_str) == 10 and "T" not in ultimo_str:
                        ultimo_dt = datetime.datetime.fromisoformat(ultimo_str + "T00:00:00")
                        datos["ultimo_paquete"] = ultimo_dt.strftime("%Y-%m-%dT%H:%M")
                        cambios += 1

                    # Caso 2: fecha con hora pero sin minutos/segundos → normalizar a HH:MM
                    elif "T" in ultimo_str:
                        try:
                            ultimo_dt = datetime.datetime.fromisoformat(ultimo_str)
                            datos["ultimo_paquete"] = ultimo_dt.strftime("%Y-%m-%dT%H:%M")
                            cambios += 1
                        except Exception as e:
                            print(f"[WARN] Could not parse {ultimo_str}: {e}")

            # 3. Guardar backup normalizado en Firebase con nuevo ID
            new_backup_id = f"{latest_backup.id}_normalized"
            db.collection("packs_backup").document(new_backup_id).set(packs)

            await interaction.followup.send(
                f"✅ Normalized {cambios} entries. Saved as `{new_backup_id}`.", ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)'''
        
          
    '''@app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(
        name="add_pack_limit",
        description="(Owner only) Add pack_limit=1 to settings for all guilds."
    )
    async def add_pack_limit(self, interaction: discord.Interaction):
        # Verificar que el usuario es el dueño
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "🚫 Only the bot owner can run this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # 1. Cargar settings actuales
            settings = cargar_settings()

            # 2. Asegurar que cada guild tenga pack_limit
            cambios = 0
            guilds = settings.setdefault("guilds", {})
            for guild_id, config in guilds.items():
                if "pack_limit" not in config:
                    config["pack_limit"] = 1
                    cambios += 1

            # 3. Guardar settings actualizados
            guardar_settings(settings)

            await interaction.followup.send(
                f"✅ Added pack_limit=1 to {cambios} guilds in settings.", ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)'''
            

    '''@app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(
        name="fix_packs",
        description="(Owner only) Backup packs and normalize last pack dates."
    )
    async def owner_fix_packs(self, interaction: discord.Interaction):
        # Verificar que el usuario es el dueño
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "🚫 Only the bot owner can run this command.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            # 1. Cargar packs actuales
            packs = cargar_packs()

            # 2. Guardar copia de seguridad en Firebase
            timestamp = datetime.datetime.now().isoformat()
            backup_id = f"backup_{timestamp}"
            db.collection("packs_backup").document(backup_id).set(packs)

            # 3. Normalizar fechas antiguas
            cambios = 0
            for servidor_id, usuarios in packs.items():
                for usuario_id, datos in usuarios.items():
                    ultimo_str = datos.get("ultimo_paquete")
                    if ultimo_str and len(ultimo_str) == 10:  # formato YYYY-MM-DD
                        ultimo_dt = datetime.datetime.fromisoformat(ultimo_str + "T00:00:00")
                        datos["ultimo_paquete"] = ultimo_dt.isoformat()
                        cambios += 1

            # 4. Guardar packs normalizados
            guardar_packs(packs)

            await interaction.followup.send(
                f"✅ Backup created as `{backup_id}`. Normalized {cambios} entries to full datetime format."
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Unexpected error: {e}")'''
            
        
    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(
        name="servers_info",
        description="(Owner only) Shows the servers where the bot is and their member counts."
    )
    async def servers_info(self, interaction: discord.Interaction):
        """Muestra información de todos los servidores donde está el bot."""
        await interaction.response.defer(ephemeral=False)
    
        guilds = self.bot.guilds
        total_servers = len(guilds)
    
        # Construyo las líneas
        info_lines = [
            f"• **{g.name}** (ID: {g.id}) → 👥 {g.member_count} members"
            for g in guilds
        ]
    
        # Discord permite 4096 caracteres en la descripcion del embed. Usamos 3800 para mayor seguridad.
        LIMIT = 3800
    
        chunks = []
        current_chunk = ""
    
        # Ensamblo los fragmentos sin romper líneas
        for line in info_lines:
            if len(current_chunk) + len(line) + 1 > LIMIT:
                chunks.append(current_chunk)
                current_chunk = ""
            current_chunk += line + "\n"
    
        if current_chunk:
            chunks.append(current_chunk)
    
        # Primer embed (con el título)
        first_embed = discord.Embed(
            title="🌐 Servers where the bot is present",
            description=f"Currently in **{total_servers} servers**:\n\n{chunks[0]}",
            color=discord.Color.green()
        )
    
        await interaction.followup.send(embed=first_embed)
    
        # Embeds adicionales si hacen falta
        for part in chunks[1:]:
            embed = discord.Embed(
                description=part,
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed)

        
    '''@app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(name="migrar_json", description="(Owner only) Migra los JSON locales a Firestore")
    async def migrar_json(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            # Leer settings.json
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
            db.collection("settings").document("global").set(settings)

            # Leer propiedades.json
            with open("propiedades.json", "r", encoding="utf-8") as f:
                propiedades = json.load(f)
            db.collection("propiedades").document("global").set(propiedades)

            await interaction.followup.send("✅ Migración completada en Firestore.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error en la migración: {e}", ephemeral=True)'''
        
    # Decorador para restringir el comando solo a ti
    '''@app_commands.default_permissions()
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
        )'''
        
    '''@app_commands.default_permissions()
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
        )'''


    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(name="avisar_update", description="**[Bot owner only]** Send update notice to all servers with auto_cards enabled.")
    async def avisar_update(self, interaction: discord.Interaction):
        """Envía aviso de actualización a todos los servidores con auto_cards activado."""
        await interaction.response.defer(ephemeral=True)
        message = (
            "🚀 **The bot has been updated to version 1.2** and now fully supports both regular commands and slash commands. This version contains new commands (some suggested through the feedback form), quality of life changes and bug fixes. Commands such as gift, discard and status have been added, as well as a way for admins to control how many packs can be opened.\n"
            "Use `/help` to see the full list of available commands or `/updates` in order to see a more detailed description of all the changes.\n"
            "Updates may slow down in the near future, as this time of the year is busier for me, but the bot will continue to be worked on."
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
            
    
    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(name="resetpacks", description="Owner only: reset packs_opened for all users")
    async def resetpacks(self, interaction: discord.Interaction):
        # Verificar que el usuario es el owner del bot
        app_owner = (await self.bot.application_info()).owner
        if interaction.user.id != app_owner.id:
            await interaction.response.send_message("🚫 Only the bot owner can use this command.", ephemeral=True)
            return

        packs = cargar_packs()
        total_reseteados = 0

        for servidor_id, servidor_packs in packs.items():
            for usuario_id, usuario_packs in servidor_packs.items():
                usuario_packs["packs_opened"] = 0
                total_reseteados += 1

        guardar_packs(packs)

        await interaction.response.send_message(
            f"✅ Reset completed. packs_opened has been reset to 0 for {total_reseteados} users.",
            ephemeral=True
        )
        
    
    @app_commands.default_permissions()
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(
        name="migrate_inventory",
        description="Copies user inventories from 'propiedades/global' to the new 'inventario' structure (no deletion)."
    )
    async def migrate_inventory(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
    
        # Leer documento gigante
        doc = db.collection("propiedades").document("global").get()
        propiedades = doc.to_dict()
    
        if not propiedades:
            await interaction.followup.send("❌ No data found in propiedades/global.", ephemeral=True)
            return
    
        migrated_servers = 0
        migrated_users = 0
    
        for server_id, usuarios in propiedades.items():
            if not isinstance(usuarios, dict):
                continue
            
            server_ref = db.collection("inventario").document(server_id)
            server_doc = server_ref.get().to_dict() or {}
    
            for user_id, cartas in usuarios.items():
                # Si ya existe, no sobrescribimos
                if user_id in server_doc:
                    continue
                
                server_doc[user_id] = cartas
                migrated_users += 1
    
            # Guardar documento del servidor
            server_ref.set(server_doc, merge=True)
            migrated_servers += 1
    
        await interaction.followup.send(
            f"✅ Migration completed.\n"
            f"📁 Servers processed: **{migrated_servers}**\n"
            f"👤 Users copied: **{migrated_users}**\n"
            f"⚠️ No data was deleted from propiedades/global.",
            ephemeral=True
        )
            

# Setup del cog
async def setup(bot: commands.Bot):
    await bot.add_cog(Debug(bot))
