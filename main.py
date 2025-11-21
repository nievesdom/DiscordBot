import discord
from discord.ext import commands
from config import TOKEN, INTENTS
from keep_alive import iniciar_servidor
import asyncio

bot = commands.Bot(command_prefix='y!', intents=INTENTS, help_command=None)

iniciar_servidor()

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    synced = await bot.tree.sync()
    print(f"Slash commands globales sincronizados: {len(synced)} comandos.")

async def main():
    # Carga cogs normalmente
    await bot.load_extension("commands.generales")
    await bot.load_extension("commands.cartas")
    await bot.load_extension("commands.wiki")
    await bot.load_extension("commands.moderation")
    await bot.load_extension("commands.auto_cards")
    await bot.load_extension("commands.battle")

    # Inicia el bot SIN usar 'async with bot'
    await bot.start(TOKEN)

asyncio.run(main())
