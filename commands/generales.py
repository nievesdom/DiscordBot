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
            "**Version 1.3 Patch notes**\n"
            "Version 1.3 adds decks, the first version of card battles and documentation for the bot.\n\n" 
            
            "**New features:**\n"
            "- Added decks. You can now add your cards to decks to either battle or for showcasing reasons. Each person has 3 decks (A, B and C) that consist of 8 cards each. The deck-related commands are `/deck_add`, `/deck_remove` and `/deck`.\n"
            "- Added the first version of card combat: stat battles. This is a simplified version of battles while a more complex battle system is developed. To try it, challenge someone with `/battle` (note that you two must have a full deck). For more info about it, check the documentation.\n"
            "- The documentation for the bot is finally ready. It has more detailed explanations about every command, card structure and more.\n\n"
            "**Other changes:**\n"
            "- Having added decks, if you want to gift, trade or discard a card it can’t be in any of your decks (unless you have more copies of it). This is to prevent losing valuable cards.\n\n"
            "**Bug fixes:**\n"
            "- Fixed a bug that made the “/trade” command not work due to the changes in inventory management and early deck work.\n\n"
            "**New cards:**\n"
            "- UR Jason Rich (PY)\n"
            "- UR Goro Majima (PY)\n"
            "- UR Taiga Saejima (PY)\n"
            "- UR Mortimer (PY)\n"
            "- UR .Notes (Christmas Eve)\n"
            "- UR Kamulop (Christmas Eve)\n"
            "- UR Asuka (New Year's II)\n"
            "- UR Yui (New Year's II)\n"
            "- UR Hikaru (New Year's II)\n"
            "- UR Maya (New Year's II)\n"
            "- UR Sofia (New Year's II)\n"
            "- UR Futoshi Shimano ('05 Fighting Spirit)\n"
            "- UR Masaru Sera ('05 Fighting Spirit)\n"
            "- UR Keiji Shibusawa (Black)\n"
            "- UR Ryo Takashima (Summon)\n"
            "- UR Seonhee (True)\n"
            "- UR Koichi Takasugi ('12 Assist)\n"
            "- UR Tatsuo Shinada (Assist)\n"
            "- UR Jun Oda (Palace)\n\n"

            "**Coming up:**\n"
            "- The choice to show wiki search results in the server's chat rather than in DMs.\n"
            "- Community-made cards (just maybe).\n"
            "- Complex card combat."
        )

    @commands.command(name="updates")
    async def updates_prefix(self, ctx: commands.Context):
        await ctx.send(
            "**Version 1.3 Patch notes**\n"
            "Version 1.3 adds decks, the first version of card battles and documentation for the bot.\n\n" 
            
            "**New features:**\n"
            "- Added decks. You can now add your cards to decks to either battle or for showcasing reasons. Each person has 3 decks (A, B and C) that consist of 8 cards each. The deck-related commands are `/deck_add`, `/deck_remove` and `/deck`.\n"
            "- Added the first version of card combat: stat battles. This is a simplified version of battles while a more complex battle system is developed. To try it, challenge someone with `/battle` (note that you two must have a full deck). For more info about it, check the documentation.\n"
            "- The documentation for the bot is finally ready. It has more detailed explanations about every command, card structure and more.\n\n"
            "**Other changes:**\n"
            "- Having added decks, if you want to gift, trade or discard a card it can’t be in any of your decks (unless you have more copies of it). This is to prevent losing valuable cards.\n\n"
            "**Bug fixes:**\n"
            "- Fixed a bug that made the “/trade” command not work due to the changes in inventory management and early deck work.\n\n"
            "**New cards:**\n"
            "- UR Jason Rich (PY)\n"
            "- UR Goro Majima (PY)\n"
            "- UR Taiga Saejima (PY)\n"
            "- UR Mortimer (PY)\n"
            "- UR .Notes (Christmas Eve)\n"
            "- UR Kamulop (Christmas Eve)\n"
            "- UR Asuka (New Year's II)\n"
            "- UR Yui (New Year's II)\n"
            "- UR Hikaru (New Year's II)\n"
            "- UR Maya (New Year's II)\n"
            "- UR Sofia (New Year's II)\n"
            "- UR Futoshi Shimano ('05 Fighting Spirit)\n"
            "- UR Masaru Sera ('05 Fighting Spirit)\n"
            "- UR Keiji Shibusawa (Black)\n"
            "- UR Ryo Takashima (Summon)\n"
            "- UR Seonhee (True)\n"
            "- UR Koichi Takasugi ('12 Assist)\n"
            "- UR Tatsuo Shinada (Assist)\n"
            "- UR Jun Oda (Palace)\n\n"

            "**Coming up:**\n"
            "- The choice to show wiki search results in the server's chat rather than in DMs.\n"
            "- Community-made cards (just maybe).\n"
            "- Complex card combat."
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
        await interaction.response.defer(ephemeral=False)

        categorias = {
            "👤 General": ["count", "feedback", "help", "hola", "ping", "say", "updates"],
            "🃏 Cards": ["album", "battle", "collection","deck","deck_add","deck_remove", "discard", "gift", "search", "pack", "show", "status", "trade"],
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

        # Añadir link a la documentación
        embed.add_field(
            name="📘 Documentation",
            value="[Click here to open the full documentation](https://docs.google.com/document/d/1rTfRPUR-YUN_pYVgCU8PLx1q9XYR64WqukWsmL6Oi3Y/edit?usp=sharing)",
            inline=False
        )

        await interaction.followup.send(embed=embed)



    @commands.command(name="help")
    async def help_prefix(self, ctx: commands.Context):
        categorias = {
            "👤 General": ["count", "feedback", "help", "hola", "ping", "say", "updates"],
            "🃏 Cards": ["album", "collection","deck","deck_add","deck_remove", "discard", "gift", "search", "pack", "show", "status", "trade"],
            "🌐 Wiki": ["wiki", "character"],
            "🔨 Moderation": ["auto_cards", "pack_limit"]
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
                
        # Añadir link a la documentación
        embed.add_field(
            name="📘 Documentation",
            value="[Click here to open the full documentation](https://docs.google.com/document/d/1rTfRPUR-YUN_pYVgCU8PLx1q9XYR64WqukWsmL6Oi3Y/edit?usp=sharing)",
            inline=False
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Generales(bot))
