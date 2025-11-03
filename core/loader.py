import os

def cargar_comandos(bot):
    for archivo in os.listdir("commands"):
        if archivo.endswith(".py"):
            nombre = archivo[:-3]
            bot.load_extension(f"commands.{nombre}")