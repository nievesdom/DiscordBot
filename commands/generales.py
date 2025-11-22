import discord
from discord.ext import commands
import asyncio
from discord import app_commands

GUILD_ID = 286617766516228096
GUILD = discord.Object(id=GUILD_ID)

class Generales(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ---------------------------
    # HOLA
    # ---------------------------
    @app_commands.command(name="hola", description="Says hola to the user.")
    async def hola_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"¡Hola, {interaction.user.mention}!")

    @commands.command(name="hola")
    async def hola_prefix(self, ctx: commands.Context):
        await ctx.send(f"¡Hola, {ctx.author.mention}!")

    # ---------------------------
    # SAY
    # ---------------------------
    @app_commands.command(name="say", description="Repeats what the user says.")
    @app_commands.describe(arg="Text you want the bot to repeat")
    async def say_slash(self, interaction: discord.Interaction, arg: str = None):
        if arg is None:
            arg = "What do you want me to say? Example: `/say Good morning`"
        await interaction.response.send_message(arg)

    @commands.command(name="say")
    async def say_prefix(self, ctx: commands.Context, *, arg: str = None):
        if arg is None:
            arg = "What do you want me to say? Example: `y!say Good morning`"
        await ctx.send(arg)

    # ---------------------------
    # COUNT
    # ---------------------------
    @app_commands.command(name="count", description="Counts up to the chosen number (max 200).")
    @app_commands.describe(numero="Number you want to count up to (max 200)")
    async def count_slash(self, interaction: discord.Interaction, numero: int = 10):
        if numero <= 0:
            await interaction.response.send_message("❌ Use a positive number. Example: `/count 5`.", ephemeral=True)
            return
        if numero > 200:
            await interaction.response.send_message("⚠️ You can only count up to 200.", ephemeral=True)
            return

        await interaction.response.send_message("Counting... 0")

        async def contar():
            for i in range(1, numero + 1):
                await asyncio.sleep(1)
                await interaction.edit_original_response(content=f"Counting... {i}")
            await interaction.edit_original_response(content=f"✅ Finished counting to {numero}")

        asyncio.create_task(contar())

    @commands.command(name="count")
    async def count_prefix(self, ctx: commands.Context, numero: int = 10):
        if numero <= 0:
            await ctx.send("❌ Use a positive number. Example: `y!count 5`.")
            return
        if numero > 200:
            await ctx.send("⚠️ You can only count up to 200.")
            return

        mensaje = await ctx.send("Counting... 0")

        async def contar():
            for i in range(1, numero + 1):
                await asyncio.sleep(1)
                await mensaje.edit(content=f"Counting... {i}")
            await mensaje.edit(content=f"✅ Finished counting to {numero}")

        asyncio.create_task(contar())

    # ---------------------------
    # UPDATES
    # ---------------------------
    @app_commands.command(name="updates", description="Shows the latest updates and what's coming up.")
    async def updates_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("**Version:** 1.1\n**Patch notes:** ...")

    @commands.command(name="updates")
    async def updates_prefix(self, ctx: commands.Context):
        await ctx.send("**Version:** 1.1\n**Patch notes:** ...")

    # ---------------------------
    # FEEDBACK
    # ---------------------------
    @app_commands.command(name="feedback", description="Send the feedback form link.")
    async def feedback_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("Feedback form: https://forms.gle/Y4e2TpHRgpfZ18Hj6")

    @commands.command(name="feedback")
    async def feedback_prefix(self, ctx: commands.Context):
        await ctx.send("Feedback form: https://forms.gle/Y4e2TpHRgpfZ18Hj6")

    # ---------------------------
    # PING
    # ---------------------------
    @app_commands.command(name="ping", description="Responds with Pong!, checking response time.")
    async def ping_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pong!")

    @commands.command(name="ping")
    async def ping_prefix(self, ctx: commands.Context):
        await ctx.send("Pong!")

    # ---------------------------
    # HELP
    # ---------------------------
    @app_commands.command(name="help", description="Shows all available commands.")
    async def help_slash(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        embed = discord.Embed(title="📖 Available slash commands:", color=discord.Color.blurple())
        embed.add_field(name="👤 General", value="/hola, /say, /count, /updates, /feedback, /ping", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context):
        embed = discord.Embed(title="📖 Available prefix commands:", color=discord.Color.blurple())
        embed.add_field(name="👤 General", value="y!hola, y!say, y!count, y!updates, y!feedback, y!ping", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Generales(bot))
