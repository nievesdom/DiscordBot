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
    # Sincroniza globalmente todos los slash commands
    synced = await bot.tree.sync()
    print(f"Slash commands globales sincronizados: {len(synced)} comandos.")

async def main():
    async with bot:
        # Carga tus cogs normalmente, no hace falta registrar comando por comando
        await bot.load_extension("commands.generales")
        await bot.load_extension("commands.cartas")
        await bot.load_extension("commands.wiki")
        await bot.load_extension("commands.moderation")
        await bot.load_extension("commands.auto_cards")
        await bot.load_extension("commands.battle")
        await bot.start(TOKEN)

asyncio.run(main())
