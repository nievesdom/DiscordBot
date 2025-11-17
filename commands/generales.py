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

    @commands.command(help="Says hola to the user.", extras={"categoria": "General 👤"})
    async def hola(self, ctx):
        await ctx.send(f"¡Hola, {ctx.author.mention}!")


    @commands.command(help="Repeats what the user says. Usage: `y!say <argument>`", extras={"categoria": "General 👤"})
    async def say(self, ctx, *, arg = None):
        # Si no se escribe nada tras el comando, avisa
        if arg == None:
            arg = "What do you want me to say? Write it after the command. Ex: `y!say Good morning`"
        await ctx.send(arg)


    @commands.command(help="Counts up to the chosen number. Usage: `y!count <number>`", extras={"categoria": "General 👤"})
    async def contar(self, ctx, numero: int = 10):
        try:
            # Comprueba si se ha introducido un número entero positivo
            if numero <= 0:
                await ctx.send("❌ You count up to that number and then tell me about it. Use a positive number. Ex: `y!count 5`.")
                return
        except ValueError:
            await ctx.send("❌ Choose a valid number. Ex: `y!count 5`.")
            return

        # Mensaje inicial
        mensaje = await ctx.send("Counting... 0")

        async def contar_mensaje():
            # Bucle para contar desde 1 hasta el número introducido
            for i in range(1, numero + 1):
                # Espera 1 segundo entre números
                await asyncio.sleep(1)
                await mensaje.edit(content=f"Contando... {i}")
            await mensaje.edit(content=f"✅ Finished counting to {numero}")

        # Ejecuta la función de conteo como tarea asincrónica
        asyncio.create_task(contar_mensaje())


    @commands.command(help="Show the latest updates and what's coming up.", extras={"categoria": "General 👤"})
    async def updates(self, ctx):
        await ctx.send("**Version:** 1.0\n**Latest update:** bot published, yaay!\n**Newly added cards:**\n- UR Kasuga Ichiban (Festival II)\n- UR Mayumi Seto (Festival)\n**Coming up:** card combat.")
    

    @commands.command(help="Send the feedback form link.", extras={"categoria": "General 👤"})
    async def feedback(self, ctx):
        await ctx.send("Here is the feedback form. I appreciate your input! https://forms.gle/Y4e2TpHRgpfZ18Hj6")


    @commands.command(help="Shows all available commands.", extras={"categoria": "General 👤"})
    async def help(self, ctx):
        embed = discord.Embed(
            title="📖 Available commands:",
            color=discord.Color.blurple()
        )
    
        # Lista manual de categorías y comandos
        categorias = {
            "👤 General": ["count", "feedback", "help", "hola", "say", "updates"],
            "🃏 Cards": ["auto_cards", "album", "collection", "search", "pack", "show"],
            "🌐 Wiki": ["wiki", "character"],
            "🔨 Moderation": ["migrate", "tags1", "tags2"]
        }
    
        # Agrupar comandos por nombre
        comandos_dict = {c.name: c for c in self.bot.commands if c.help}
    
        # Listar el nombre de los comandos y la ayuda
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
