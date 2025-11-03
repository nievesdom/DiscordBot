import discord
from discord.ext import commands
from config import TOKEN, INTENTS

bot = commands.Bot(command_prefix='y!', intents=INTENTS, help_command=None)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')

    # Cargar extensiones
    await bot.load_extension("commands.generales")
    await bot.load_extension("commands.cartas")
    await bot.load_extension("commands.wiki")

# Ejecutar el bot
bot.run(TOKEN)
