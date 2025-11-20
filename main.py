import discord
from discord.ext import commands
from config import TOKEN, INTENTS
import logging
from keep_alive import iniciar_servidor
import asyncio

GUILD_ID = 286617766516228096  # ID del servidor de pruebas

bot = commands.Bot(command_prefix='y!', intents=INTENTS, help_command=None)

iniciar_servidor()

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    # Sincroniza solo los guild commands para pruebas rápidas
    synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Slash commands sincronizados en el guild de pruebas: {len(synced)} comandos.")

async def main():
    async with bot:
        await bot.load_extension("commands.generales")
        await bot.load_extension("commands.cartas")
        await bot.load_extension("commands.wiki")
        await bot.load_extension("commands.moderation")
        await bot.load_extension("commands.auto_cards")
        await bot.load_extension("commands.battle")
        await bot.start(TOKEN)

asyncio.run(main())
