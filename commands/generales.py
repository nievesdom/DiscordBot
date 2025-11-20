import discord
from discord.ext import commands
import asyncio
from discord import app_commands

GUILD_ID = 286617766516228096
GUILD = discord.Object(id=GUILD_ID)

class Generales(commands.Cog):
    
    def categoría(nombre):
        def decorador(comando):
            comando.category = nombre
            return comando
        return decorador
    
    def __init__(self, bot):
        self.bot = bot

    # NECESARIO para registrar los slash commands en el guild de pruebas
    async def cog_load(self):
        self.bot.tree.add_command(self.hola, guild=GUILD)
        self.bot.tree.add_command(self.say, guild=GUILD)
        self.bot.tree.add_command(self.count, guild=GUILD)
        self.bot.tree.add_command(self.updates, guild=GUILD)
        self.bot.tree.add_command(self.feedback, guild=GUILD)
        self.bot.tree.add_command(self.ping, guild=GUILD)
        self.bot.tree.add_command(self.help, guild=GUILD)

    @app_commands.command(name="hola", description="Says hola to the user.")
    async def hola(self, interaction: discord.Interaction):
        # Envía un saludo al usuario que ejecuta el comando
        await interaction.response.send_message(f"¡Hola, {interaction.user.mention}!")

    @app_commands.command(name="say", description="Repeats what the user says.")
    @app_commands.describe(arg="Texto que quieres que el bot repita")
    async def say(self, interaction: discord.Interaction, arg: str = None):
        if arg is None:
            arg = "What do you want me to say? Write it after the command. Ex: `/say Good morning`"
        await interaction.response.send_message(arg)

    @app_commands.command(name="count", description="Counts up to the chosen number.")
    @app_commands.describe(numero="Número hasta el que quieres contar")
    async def count(self, interaction: discord.Interaction, numero: int = 10):
        try:
            if numero <= 0:
                await interaction.response.send_message("❌ You count up to that number and then tell me about it. Use a positive number. Ex: `/count 5`.")
                return
        except ValueError:
            await interaction.response.send_message("❌ Choose a valid number. Ex: `/count 5`.")
            return

        mensaje = await interaction.response.send_message("Counting... 0", ephemeral=False)

        async def contar_mensaje():
            # Bucle para contar desde 1 hasta el número introducido
            for i in range(1, numero + 1):
                await asyncio.sleep(1)
                await interaction.edit_original_response(content=f"Counting... {i}")
            await interaction.edit_original_response(content=f"✅ Finished counting to {numero}")

        # Ejecuta la función de conteo como tarea asincrónica
        asyncio.create_task(contar_mensaje())

    @app_commands.command(name="updates", description="Show the latest updates and what's coming up.")
    async def updates(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "**Version:** 1.0\n**Latest update:** bot published, yaay!\n"
            "**Newly added cards:**\n- UR Kasuga Ichiban (Festival II)\n- UR Mayumi Seto (Festival)\n"
            "**Coming up:** card combat."
        )

    @app_commands.command(name="feedback", description="Send the feedback form link.")
    async def feedback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Here is the feedback form. I appreciate your input! https://forms.gle/Y4e2TpHRgpfZ18Hj6")

    @app_commands.command(name="ping", description="Responde con Pong!")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")

    @app_commands.command(name="help", description="Shows all available commands.")
    async def help(self, interaction: discord.Interaction):
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
                    texto += f"**/{comando.name}** → {comando.help}\n"
            if texto:
                embed.add_field(name=nombre_cat, value=texto, inline=False)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Generales(bot))
