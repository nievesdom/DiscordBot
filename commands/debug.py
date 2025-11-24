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

class Debug(commands.Cog):
    """Cog con comandos exclusivos para el dueño del bot."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    
            
            
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
            
            
    @app_commands.default_permissions()
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
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)
        
          
    @app_commands.default_permissions()
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
            await interaction.followup.send(f"❌ Unexpected error: {e}", ephemeral=True)
            

    @app_commands.default_permissions()
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
            await interaction.followup.send(f"❌ Unexpected error: {e}")
            
        
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
            

# Setup del cog
async def setup(bot: commands.Bot):
    await bot.add_cog(Debug(bot))
