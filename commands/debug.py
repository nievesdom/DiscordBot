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

# Setup del cog
async def setup(bot: commands.Bot):
    await bot.add_cog(Debug(bot))
