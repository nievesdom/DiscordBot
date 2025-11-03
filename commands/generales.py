import discord
from discord.ext import commands
import asyncio

class Generales(commands.Cog):
    
    def categoría(nombre):
        def decorador(comando):
            comando.category = nombre
            return comando
        return decorador
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(help="Saluda al usuario", extras={"categoria": "General 👤"})
    async def hola(self, ctx):
        await ctx.send(f"¡Hola, {ctx.author.mention}!")


    @commands.command(help="Repite lo que escriba el usuario")
    async def decir(self, ctx, *, arg):
        await ctx.send(arg)


    @commands.command(help="Cuenta hasta un número introducido por el usuario", extras={"categoria": "General 👤"})
    async def contar(self, ctx, numero: int = 10):
        mensaje = await ctx.send("Contando... 0")
        async def contar_mensaje():
            for i in range(1, numero + 1):
                await asyncio.sleep(1)
                await mensaje.edit(content=f"Contando... {i}")
            await mensaje.edit(content=f"✅ Ya he terminado de contar hasta {numero}", extras={"categoria": "General 👤"})
        asyncio.create_task(contar_mensaje())


    @commands.command(help="Muestra todos los comandos disponibles")
    async def ayuda(self, ctx):
        embed = discord.Embed(
            title="📖 Comandos disponibles",
            description="Aquí tienes los comandos agrupados por categoría:",
            color=discord.Color.blurple()
        )
    
        # 🔒 Lista manual de categorías y comandos
        categorias = {
            "General 👤": ["hola", "decir", "contar", "ayuda"],
            "Cartas 🃏": ["carta", "album", "coleccion", "buscar"],
            "Wiki 🌐": ["wiki", "personaje"]
        }
    
        # Agrupar comandos por nombre
        comandos_dict = {c.name: c for c in self.bot.commands if c.help}
    
        for nombre_cat, lista_comandos in categorias.items():
            texto = ""
            for nombre in lista_comandos:
                comando = comandos_dict.get(nombre)
                if comando:
                    texto += f"**y!{comando.name}** → {comando.help}\n"
            if texto:
                embed.add_field(name=nombre_cat, value=texto, inline=False)
    
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Generales(bot))
