import discord
from discord.ext import commands
from config import TOKEN, INTENTS
import logging
from keep_alive import iniciar_servidor
from discord import app_commands
import asyncio

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    filename='bot.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s'
)

bot = commands.Bot(command_prefix='y!', intents=INTENTS, help_command=None)

iniciar_servidor()

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    synced = await bot.tree.sync()
    print(f"Slash commands sincronizados: {len(synced)} comandos.")

async def main():
    async with bot:
        # Cargar extensiones ANTES de iniciar y ANTES de sync
        await bot.load_extension("commands.generales")
        await bot.load_extension("commands.cartas")
        await bot.load_extension("commands.wiki")
        await bot.load_extension("commands.moderation")
        await bot.load_extension("commands.auto_cards")
        await bot.load_extension("commands.battle")

        await bot.start(TOKEN)

asyncio.run(main())

