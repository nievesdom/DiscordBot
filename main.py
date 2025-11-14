import discord
from discord.ext import commands
from config import TOKEN, INTENTS
import logging
from keep_alive import iniciar_servidor

# Configuración de los logs
logging.basicConfig(
    level=logging.INFO,
    filename='bot.log',
    filemode='a', # "a" para añadir, "w" para sobrescribir cada vez
    format='%(asctime)s - %(levelname)s - %(message)s'
)

bot = commands.Bot(command_prefix='y!', intents=INTENTS, help_command=None)

iniciar_servidor()

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Bot conectado como {bot.user}')

    # Cargar extensiones
    await bot.load_extension("commands.generales")
    await bot.load_extension("commands.cartas")
    await bot.load_extension("commands.wiki")
    await bot.load_extension("commands.moderation")
    await bot.load_extension("commands.auto_cards")

# Ejecutar el bot
bot.run(TOKEN)
