import discord
from discord.ext import commands
import asyncio
from discord import app_commands
from core.firebase_client import db
import json
import os

GUILD_ID = 286617766516228096
GUILD = discord.Object(id=GUILD_ID)
OWNER_ID = 182920174276575232

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
            arg = "What do you want me to say? Write it after the command. Ex: `/say Good morning`"
        await interaction.response.send_message(arg)

    @commands.command(name="say")
    async def say_prefix(self, ctx: commands.Context, *, arg: str = None):
        if arg is None:
            arg = "What do you want me to say? Write it after the command. Ex: `y!say Good morning`"
        await ctx.send(arg)

    # ---------------------------
    # COUNT
    # ---------------------------
    @app_commands.command(name="count", description="Counts up to the chosen number (max 200).")
    @app_commands.describe(numero="Number you want to count up to (max 200)")
    async def count_slash(self, interaction: discord.Interaction, numero: int = 10):
        try:
            if numero <= 0:
                await interaction.response.send_message(
                    "❌ You count up to that number and then tell me about it. Use a positive number. Ex: `/count 5`.",
                    ephemeral=True
                )
                return
            if numero > 200:
                await interaction.response.send_message(
                    "⚠️ Greedy! You can only count up to 200.",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message(
                "❌ Choose a valid number. Ex: `/count 5`.",
                ephemeral=True
            )
            return

        mensaje = await interaction.response.send_message("Counting... 0", ephemeral=False)

        async def contar_mensaje():
            for i in range(1, numero + 1):
                await asyncio.sleep(1)
                await interaction.edit_original_response(content=f"Counting... {i}")
            await interaction.edit_original_response(content=f"✅ Finished counting to {numero}")

        asyncio.create_task(contar_mensaje())


    @commands.command(name="count")
    async def count_prefix(self, ctx: commands.Context, numero: int = 10):
        try:
            if numero <= 0:
                await ctx.send("❌ You count up to that number and then tell me about it. Use a positive number. Ex: `y!count 5`.")
                return
            if numero > 200:
                await ctx.send("⚠️ Greedy! You can only count up to 200.")
                return
        except ValueError:
            await ctx.send("❌ Choose a valid number. Ex: `y!count 5`.")
            return

        mensaje = await ctx.send("Counting... 0")

        async def contar_mensaje():
            for i in range(1, numero + 1):
                await asyncio.sleep(1)
                await mensaje.edit(content=f"Counting... {i}")
            await mensaje.edit(content=f"✅ Finished counting to {numero}")

        asyncio.create_task(contar_mensaje())

    # ---------------------------
    # UPDATES
    # ---------------------------
    @app_commands.command(name="updates", description="Shows the latest updates and what's coming up.")
    async def updates_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            "**Version 1.2.2 Patch notes**\n"
            "Version 1.2.2 is mostly an urgent bug fixing update, but it also adds some new cards, a feature and some QoL changes. Also, sorry for the downtime of the bot, I wasn't home to fix the issue quickly.\n\n" 
            
            "**Bug fixes:**\n"
            "- Fixed an error that made adding cards to someone's inventory not work because the database where they were stored got too big. This involved changing many things in both the code and how cards are stored.\n"
            "- Removed a duplicate card.\n\n"
            
            "**New features:**\n"
            "- Added a rarity order mode to the ''/album'' command. Now the alphabetical order ignores card rarity and therefore all of the cards of the same character will be together.\n\n"

            "**Quality of life changes:**\n"
            "- Due to the changes in how cards are saved and stored, the bot might be a bit quicker when using commands such as ''/pack''."
            "- Added the number of copies of one card that are owned (if it's more than one) next to the card's name in the ''/search'' command, just like in the ''/collection'' command.\n\n"
            
            "**New cards:**\n"
            "- UR Masumi Arakawa (YLAD Summon)\n"
            "- UR Taiga Saejima (Christmas Eve)\n"
            "- UR Lily (Christmas Eve)\n"
            "- UR Noah Rich (PY)\n"
            "- UR Goro Majima (PY Mad Dog)\n\n"

            "**Coming up:**\n"
            "- The choice to show wiki search results in the server's chat rather than in DMs.\n"
            "- Documentation for the bot (already started).\n"
            "- Deck creation (almost done!)."
            "- Community-made cards (just maybe).\n"
            "- Card combat (eventually)."
        )

    @commands.command(name="updates")
    async def updates_prefix(self, ctx: commands.Context):
        await ctx.send(
            "**Version 1.2.2 Patch notes**\n"
            "Version 1.2.2 is mostly an urgent bug fixing update, but it also adds some new cards, a feature and some QoL changes. Also, sorry for the downtime of the bot, I wasn't home to fix the issue quickly.\n\n" 
            
            "**Bug fixes:**\n"
            "- Fixed an error that made adding cards to someone's inventory not work because the database where they were stored got too big. This involved changing many things in both the code and how cards are stored.\n"
            "- Removed a duplicate card.\n\n"
            
            "**New features:**\n"
            "- Added a rarity order mode to the ''/album'' command. Now the alphabetical order ignores card rarity and therefore all of the cards of the same character will be together.\n\n"

            "**Quality of life changes:**\n"
            "- Due to the changes in how cards are saved and stored, the bot might be a bit quicker when using commands such as ''/pack''."
            "- Added the number of copies of one card that are owned (if it's more than one) next to the card's name in the ''/search'' command, just like in the ''/collection'' command.\n\n"
            
            "**New cards:**\n"
            "- UR Masumi Arakawa (YLAD Summon)\n"
            "- UR Taiga Saejima (Christmas Eve)\n"
            "- UR Lily (Christmas Eve)\n"
            "- UR Noah Rich (PY)\n"
            "- UR Goro Majima (PY Mad Dog)\n\n"

            "**Coming up:**\n"
            "- The choice to show wiki search results in the server's chat rather than in DMs.\n"
            "- Documentation for the bot (already started).\n"
            "- Deck creation (almost done!)."
            "- Community-made cards (just maybe).\n"
            "- Card combat (eventually)."
        )

    # ---------------------------
    # FEEDBACK
    # ---------------------------
    @app_commands.command(name="feedback", description="Send the feedback form link.")
    async def feedback_slash(self, interaction: discord.Interaction):
        await interaction.response.send_message("Here is the feedback form. I appreciate your input! https://forms.gle/Y4e2TpHRgpfZ18Hj6")

    @commands.command(name="feedback")
    async def feedback_prefix(self, ctx: commands.Context):
        await ctx.send("Here is the feedback form. I appreciate your input! https://forms.gle/Y4e2TpHRgpfZ18Hj6")

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
        # Ya no usamos ephemeral=True
        await interaction.response.defer(ephemeral=False)

        categorias = {
            "👤 General": ["count", "feedback", "help", "hola", "ping", "say", "updates"],
            "🃏 Cards": ["album", "collection", "discard", "gift", "search", "pack", "show", "status"],
            "🌐 Wiki": ["wiki", "character"],
            "🔨 Moderation": ["auto_cards", "pack_limit"]
        }

        comandos_dict = {c.name: c for c in self.bot.tree.get_commands()}

        embed = discord.Embed(
            title="📖 Available slash commands:",
            color=discord.Color.blurple()
        )

        for nombre_cat, lista_comandos in categorias.items():
            texto = ""
            for nombre in lista_comandos:
                comando = comandos_dict.get(nombre)
                if comando:
                    texto += f"**/{comando.name}** → {comando.description or 'Sin descripción'}\n"
            if texto:
                embed.add_field(name=nombre_cat, value=texto, inline=False)

        # Este mensaje ya no es ephemeral, será visible para todos en el canal
        await interaction.followup.send(embed=embed)


    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context):
        categorias = {
            "👤 General": ["count", "feedback", "help", "hola", "ping", "say", "updates"],
            "🃏 Cards": ["album", "collection", "discard", "gift", "search", "pack", "show"],
            "🌐 Wiki": ["wiki", "character"],
            "🔨 Moderation": ["auto_cards", "pack_limit", "status"]
        }

        comandos_dict = {c.name: c for c in self.bot.tree.get_commands()}

        embed = discord.Embed(
            title="📖 Available commands:",
            color=discord.Color.blurple()
        )

        for nombre_cat, lista_comandos in categorias.items():
            texto = ""
            for nombre in lista_comandos:
                comando = comandos_dict.get(nombre)
                if comando:
                    # Mostrar tanto el prefijo como el slash
                    texto += f"**y!{comando.name}** → {comando.description or 'Sin descripción'}\n"
            if texto:
                embed.add_field(name=nombre_cat, value=texto, inline=False)

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Generales(bot))
