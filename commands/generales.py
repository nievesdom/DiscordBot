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

    @app_commands.command(name="hola", description="Says hola to the user.")
    async def hola(self, interaction: discord.Interaction):
        # Envía un saludo al usuario que ejecuta el comando
        await interaction.response.send_message(f"¡Hola, {interaction.user.mention}!")

    @app_commands.command(name="say", description="Repeats what the user says.")
    @app_commands.describe(arg="Text you want the bot to repeat")
    async def say(self, interaction: discord.Interaction, arg: str = None):
        if arg is None:
            arg = "What do you want me to say? Write it after the command. Ex: `/say Good morning`"
        await interaction.response.send_message(arg)

    @app_commands.command(name="count", description="Counts up to the chosen number.")
    @app_commands.describe(numero="Number you want to count up to")
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
            "**Version:** 1.1\n**Patch notes:**\n- The bot is now compatible with slash commands. You can use the commands with `/` as a prefix instead of `y!` and discord will tell you when and how to introduce arguments to a command, making it easier to use commands such as `/trade`.\n- Fixed a bug that would cause the bot to quickly reach the request limit while trying to save the automatic cards information from multiple servers at the same time. I never expected this bot to be in more than a couple of servers.\n"
            "**Newly added cards:**\n- UR Kaoru Sayama (Palace)\n- UR Homare Nishitani (Festival)\n- UR Yoshitaka Mine (Festival)\n"
            "**Coming up:** card combat!"
        )

    @app_commands.command(name="feedback", description="Send the feedback form link.")
    async def feedback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Here is the feedback form. I appreciate your input! https://forms.gle/Y4e2TpHRgpfZ18Hj6")
    
    @app_commands.command(name="ping", description="Responds with Pong!, checking response time.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")

    @app_commands.command(name="help", description="Muestra todos los comandos agrupados por categoría.")
    async def help_slash(self, interaction: discord.Interaction):
        """
        Comando de ayuda global para slash commands.
        - Usa un diccionario manual de categorías y comandos.
        - Recorre el árbol de comandos y los agrupa por categoría.
        - Muestra nombre y descripción en un embed.
        """
        await interaction.response.defer(ephemeral=True)

        # Diccionario manual de categorías y comandos (igual que tu ejemplo)
        categorias = {
            "👤 General": ["count", "feedback", "help", "hola", "ping", "say", "updates"],
            "🃏 Cards": ["album", "collection", "search", "pack", "show"],
            "🌐 Wiki": ["wiki", "character"],
            "🔨 Moderation": ["auto_cards", "spawning_status"]
        }

        # Obtenemos todos los slash commands registrados
        comandos_dict = {c.name: c for c in self.bot.tree.get_commands()}

        # Creamos el embed
        embed = discord.Embed(
            title="📖 Available slash commands:",
            color=discord.Color.blurple()
        )

        # Recorremos categorías y añadimos comandos
        for nombre_cat, lista_comandos in categorias.items():
            texto = ""
            for nombre in lista_comandos:
                comando = comandos_dict.get(nombre)
                if comando:
                    texto += f"**/{comando.name}** → {comando.description or 'Sin descripción'}\n"
            if texto:
                embed.add_field(name=nombre_cat, value=texto, inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Generales(bot))
