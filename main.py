import discord
from discord.ext import commands
from config import TOKEN, INTENTS
import logging
from keep_alive import iniciar_servidor
import asyncio

bot = commands.Bot(command_prefix='y!', intents=INTENTS, help_command=None)

iniciar_servidor()

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    synced = await bot.tree.sync()
    print(f"Slash commands sincronizados: {len(synced)} comandos.")

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
