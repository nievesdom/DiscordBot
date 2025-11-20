import asyncio
import discord
from discord.ext import commands
from core.gist_propiedades import cargar_propiedades, guardar_propiedades
from core.cartas import cargar_cartas, cartas_por_id

class Battle(commands.Cog):
    def categoría(nombre):
        def decorador(comando):
            comando.category = nombre
            return comando
        return decorador
    
    def __init__(self, bot):
        self.bot = bot
        
        
        
async def setup(bot):
    await bot.add_cog(Battle(bot))
