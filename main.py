import discord
from discord.ext import commands
from config import TOKEN, INTENTS
import logging

logging.basicConfig(
    level=logging.INFO,  # Puedes cambiar a DEBUG, WARNING, ERROR, etc.
    filename='bot.log',  # Nombre del archivo donde se guardarán los logs
    filemode='a',        # 'a' para añadir, 'w' para sobrescribir cada vez
    format='%(asctime)s - %(levelname)s - %(message)s'
)

bot = commands.Bot(command_prefix='y!', intents=INTENTS, help_command=None)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Bot conectado como {bot.user}')

    # Cargar extensiones

    await bot.load_extension("commands.generales")
    await bot.load_extension("commands.cartas")
    await bot.load_extension("commands.wiki")

# Ejecutar el bot
bot.run(TOKEN)
