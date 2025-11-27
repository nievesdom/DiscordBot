import asyncio
import discord
from discord.ext import commands
from core.firebase_storage import cargar_mazos, guardar_mazos, cargar_propiedades
from core.cartas import cargar_cartas

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # -----------------------------
    # Comando slash: /deck_add
    # -----------------------------
    @discord.app_commands.command(
        name="deck_add",
        description="Add a card to your deck by exact name (slash)."
    )
    async def deck_add_slash(self, interaction: discord.Interaction, card_name: str):
        # IDs del servidor y usuario
        server_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        # Buscar carta por nombre exacto en el JSON
        cards = cargar_cartas()
        card = next((c for c in cards if c["nombre"].lower() == card_name.lower()), None)

        # Si no existe la carta
        if not card:
            await interaction.response.send_message(
                f"❌ No card found with the exact name '{card_name}'.", ephemeral=False
            )
            return

        card_id = str(card["id"])

        # Comprobar si el usuario tiene la carta en propiedad
        properties = cargar_propiedades()
        user_cards = properties.get(server_id, {}).get(user_id, [])

        if card_id not in map(str, user_cards):
            await interaction.response.send_message(
                f"❌ You do not own the card '{card['nombre']}'.", ephemeral=False
            )
            return

        # Añadir la carta al mazo en Firebase
        decks = cargar_mazos()
        server_decks = decks.setdefault(server_id, {})
        user_deck = server_decks.setdefault(user_id, [])

        # Evitar duplicados en el mazo
        if card_id in user_deck:
            await interaction.response.send_message(
                f"⚠️ The card '{card['nombre']}' is already in your deck.", ephemeral=False
            )
            return

        user_deck.append(card_id)
        guardar_mazos(decks)

        # Confirmación al usuario
        await interaction.response.send_message(
            f"✅ The card '{card['nombre']}' has been added to your deck.", ephemeral=False
        )

    # -----------------------------
    # Comando prefijo: y!deck_add
    # -----------------------------
    @commands.command(name="deck_add")
    async def deck_add_prefix(self, ctx: commands.Context, *, card_name: str):
        """Añade una carta al mazo del usuario buscando por nombre exacto (prefijo)."""
        # IDs del servidor y usuario
        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        # Buscar carta por nombre exacto en el JSON
        cards = cargar_cartas()
        card = next((c for c in cards if c["nombre"].lower() == card_name.lower()), None)

        # Si no existe la carta
        if not card:
            await ctx.send(f"❌ No card found with the exact name '{card_name}'.")
            return

        card_id = str(card["id"])

        # Comprobar si el usuario tiene la carta en propiedad
        properties = cargar_propiedades()
        user_cards = properties.get(server_id, {}).get(user_id, [])

        if card_id not in map(str, user_cards):
            await ctx.send(f"❌ You do not own the card '{card['nombre']}'.")
            return

        # Añadir la carta al mazo en Firebase
        decks = cargar_mazos()
        server_decks = decks.setdefault(server_id, {})
        user_deck = server_decks.setdefault(user_id, [])

        # Evitar duplicados en el mazo
        if card_id in user_deck:
            await ctx.send(f"⚠️ The card '{card['nombre']}' is already in your deck.")
            return

        user_deck.append(card_id)
        guardar_mazos(decks)

        # Confirmación al usuario
        await ctx.send(f"✅ The card '{card['nombre']}' has been added to your deck.")

# Setup del cog
async def setup(bot):
    await bot.add_cog(Battle(bot))
