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
            backup_id = f"backup_{timestamp}"

            # 3. Guardar en Firebase en colección 'packs_backup'
            db.collection("packs_backup").document(backup_id).set(packs)

            await interaction.followup.send(
                f"✅ Backup created as `{backup_id}` in Firebase.", ephemeral=True
            )

        except Exception as e:
            await interaction.followup.send(f"❌ Backup failed: {e}", ephemeral=True)
            

    # Comando exclusivo del dueño
    @app_commands.command(
        name="owner_fix_packs",
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
