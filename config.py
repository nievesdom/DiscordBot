import os
from dotenv import load_dotenv
import discord

# Cargar las variables desde .env (el token del bot).
# Esto se hace para mantenerlo seguro y que no esté en el código, donde cualquiera pueda acceder
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Activar los intents necesarios
INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True
INTENTS.presences = True
