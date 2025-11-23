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
        
    @app_commands.check(lambda i: i.user.id == OWNER_ID)
    @app_commands.command(name="migrar_json", description="(Owner only) Migra los JSON locales a Firestore")
    async def migrar_json(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            # Leer settings.json
            with open("settings.json", "r", encoding="utf-8") as f:
                settings = json.load(f)
            db.collection("settings").document("global").set(settings)

            # Leer propiedades.json
            with open("propiedades.json", "r", encoding="utf-8") as f:
                propiedades = json.load(f)
            db.collection("propiedades").document("global").set(propiedades)

            await interaction.followup.send("✅ Migración completada en Firestore.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error en la migración: {e}", ephemeral=True)

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
            "**Version:** 1.1.2\n**Patch notes:**\n"
            "- The bot is now compatible with slash commands. You can use the commands with `/` as a prefix instead of `y!` and discord will tell you when and how to introduce arguments to a command, making it easier to use commands such as `/trade`.\n"
            "- Some regular commands also work, use the prefix `y!`. I'll keep working to update all of them.\n"
            "- Migrated the database to a new service to prevent a bug that would cause the bot to reach the request limit while trying to save data from multiple servers at the same time. I never expected this bot to be in more than a couple of servers, but it should be fixed now (for real now (I hope)).\n"
            "- Other minor quality of life changes, such as increasing the time to claim a spawned card.\n"
            "- [New!] Removed a bug that would cause people to be able to open more than one pack a day and wiped the cards from those that I detected were abusing this bugs. Please, if you find a bug, report it using the feedback form instead.\n"
            "**Newly added cards:**\n"
            "- UR Kaoru Sayama (Palace)\n"
            "- UR Homare Nishitani (Festival)\n"
            "- UR Yoshitaka Mine (Festival)\n"
            "**Coming up:**\n"
            "- Gift and discard card commands\n"
            "- New alphabetical order, different from rarity order\n"
            "- A choice for admins to choose how many packs everyone can open every day, for those of you who love opening many packs. I just ask that you don't do this in unintended ways because there's a chance you could break the bot for everyone (it happened, but shouldn't happen anymore now that the database has been migrated)."
            "- Card combat!"
        )

    @commands.command(name="updates")
    async def updates_prefix(self, ctx: commands.Context):
        await ctx.send(
            "**Version:** 1.1.2\n**Patch notes:**\n"
            "- The bot is now compatible with slash commands. You can use the commands with `/` as a prefix instead of `y!` and discord will tell you when and how to introduce arguments to a command, making it easier to use commands such as `/trade`.\n"
            "- Some regular commands also work, use the prefix `y!`. I'll keep working to update all of them.\n"
            "- Migrated the database to a new service to prevent a bug that would cause the bot to reach the request limit while trying to save data from multiple servers at the same time. I never expected this bot to be in more than a couple of servers, but it should be fixed now (for real now (I hope)).\n"
            "- Other minor quality of life changes, such as increasing the time to claim a spawned card.\n"
            "- [New!] Removed a bug that would cause people to be able to open more than one pack a day and wiped the cards from those that I detected were abusing this bugs. Please, if you find a bug, report it using the feedback form instead.\n"
            "**Newly added cards:**\n"
            "- UR Kaoru Sayama (Palace)\n"
            "- UR Homare Nishitani (Festival)\n"
            "- UR Yoshitaka Mine (Festival)\n"
            "**Coming up:**\n"
            "- Gift and discard card commands\n"
            "- New alphabetical order, different from rarity order\n"
            "- A choice for admins to choose how many packs everyone can open every day, for those of you who love opening many packs. I just ask that you don't do this in unintended ways because there's a chance you could break the bot for everyone (it happened, but shouldn't happen anymore now that the database has been migrated)."
            "- Card combat!"
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
            "🃏 Cards": ["album", "collection", "search", "pack", "show"],
            "🌐 Wiki": ["wiki", "character"],
            "🔨 Moderation": ["auto_cards", "spawning_status"]
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
            "🃏 Cards": ["album", "collection", "search", "pack", "show"],
            "🌐 Wiki": ["wiki", "character"],
            "🔨 Moderation": ["auto_cards", "spawning_status"]
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
