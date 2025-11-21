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
    # Sincroniza los comandos SOLO en tu servidor de pruebas
    guild = discord.Object(id=286617766516228096)  # tu GUILD_ID
    synced = await bot.tree.sync(guild=guild)
    print(f"Slash commands sincronizados en el servidor {guild.id}: {len(synced)} comandos.")


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
