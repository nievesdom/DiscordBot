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
            "**Version:** 1.1\n**Latest update:** now compatible with slash commands. You can use the commands with `/` as a prefix instead of `y!` and discord will tell you when and how to introduce arguments to a command, making it easier to use commands such as `/trade`.\n"
            "**Newly added cards:**\n- UR Kaoru Sayama (Palace)\n- UR Homare Nishitani (Festival)\n- UR Yoshitaka Mine (Festival)\n"
            "**Coming up:** card combat!"
        )

    @app_commands.command(name="feedback", description="Send the feedback form link.")
    async def feedback(self, interaction: discord.Interaction):
        await interaction.response.send_message("Here is the feedback form. I appreciate your input! https://forms.gle/Y4e2TpHRgpfZ18Hj6")

    @app_commands.command(name="ping", description="Responde con Pong!")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")

    @app_commands.command(name="help", description="Shows all available slash commands.")
    async def help(self, interaction: discord.Interaction):
        # Hacemos defer para evitar que la interacción caduque mientras construimos la lista
        await interaction.response.defer(ephemeral=True)

        # Obtenemos todos los comandos registrados en el árbol de slash commands
        comandos = self.bot.tree.get_commands(guild=interaction.guild)

        # Creamos el embed que contendrá la lista
        embed = discord.Embed(
            title="📖 Available commands",
            color=discord.Color.blurple(),
            description="Use the / prefix and let Discord guide you with parameters."
        )

        # 🔎 Recorremos los comandos y añadimos cada uno con su descripción
        for comando in sorted(comandos, key=lambda c: c.name):
            # Si es un grupo de comandos (ej. /cards add, /cards remove)
            if isinstance(comando, app_commands.Group):
                texto = ""
                for sub in comando.commands:
                    texto += f"**/{comando.name} {sub.name}** — {sub.description or 'No description'}\n"
                embed.add_field(name=f"/{comando.name}", value=texto, inline=False)
            else:
                # Comando normal
                embed.add_field(
                    name=f"/{comando.name}",
                    value=comando.description or "No description",
                    inline=False
                )

        # Enviamos el embed como respuesta
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Generales(bot))
