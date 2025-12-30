import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from core.firebase_storage import cargar_inventario_usuario, cargar_mazo, cargar_mazo, guardar_mazo, guardar_mazo, cargar_propiedades
from core.cartas import cargar_cartas, cartas_por_id
from views.navegador_mazo import NavegadorMazo

DECK_SIZE = 8 # Tamaño máximo del mazo

def normalizar_mazo(nombre: str) -> str:
        nombre = nombre.strip().lower()

        if nombre in ("a", "1"):
            return "A"
        if nombre in ("b", "2"):
            return "B"
        if nombre in ("c", "3"):
            return "C"

        return "A"

class Battle(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        
    # -----------------------------
    # Comando slash: /deck_add
    # -----------------------------
    @discord.app_commands.command(
        name="deck_add",
        description="Add a card to one of your decks (A, B or C)."
    )
    @app_commands.describe(
        deck="Deck name: A, B, C or 1, 2, 3",
        card_name="Exact name of the card"
    )
    async def deck_add_slash(self, interaction: discord.Interaction, deck: str, card_name: str):
        server_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        letra_mazo = normalizar_mazo(deck)

        cards = cargar_cartas()
        card = next((c for c in cards if c["nombre"].lower() == card_name.lower()), None)

        if not card:
            await interaction.response.send_message(
                f"No card found with the name '{card_name}'.",
                ephemeral=False
            )
            return

        card_id = str(card["id"])

        user_cards = cargar_inventario_usuario(server_id, user_id)

        if card_id not in map(str, user_cards):
            await interaction.response.send_message(
                f"You do not own the card '{card['nombre']}'.",
                ephemeral=False
            )
            return

        # Cargar los tres mazos
        mazo_a = cargar_mazo(server_id, user_id, "A")
        mazo_b = cargar_mazo(server_id, user_id, "B")
        mazo_c = cargar_mazo(server_id, user_id, "C")

        # Comprobar si la carta ya está en otro mazo
        total_en_mazos = (
            sum(1 for c in mazo_a if str(c) == card_id) +
            sum(1 for c in mazo_b if str(c) == card_id) +
            sum(1 for c in mazo_c if str(c) == card_id)
        )

        owned_count = sum(1 for c in user_cards if str(c) == card_id)

        if total_en_mazos >= owned_count:
            await interaction.response.send_message(
                f"You only own {owned_count} copies of '{card['nombre']}', "
                f"and all of them are already in other decks.",
                ephemeral=False
            )
            return

        # Cargar el mazo elegido
        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if len(user_deck) >= DECK_SIZE:
            await interaction.response.send_message(
                f"Your deck {letra_mazo} already has {DECK_SIZE} cards.",
                ephemeral=False
            )
            return

        user_deck.append(card_id)
        guardar_mazo(server_id, user_id, letra_mazo, user_deck)

        await interaction.response.send_message(
            f"The card '{card['nombre']}' has been added to deck {letra_mazo}.",
            ephemeral=False
        )
        
    # -----------------------------
    # Comando prefijo: y!deck_add
    # -----------------------------
    @commands.command(name="deck_add")
    async def deck_add_prefix(self, ctx: commands.Context, deck: str, *, card_name: str):
        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        letra_mazo = normalizar_mazo(deck)

        cards = cargar_cartas()
        card = next((c for c in cards if c["nombre"].lower() == card_name.lower()), None)

        if not card:
            await ctx.send(f"No card found with the name '{card_name}'.")
            return

        card_id = str(card["id"])

        user_cards = cargar_inventario_usuario(server_id, user_id)

        if card_id not in map(str, user_cards):
            await ctx.send(f"You do not own the card '{card['nombre']}'.")
            return

        mazo_a = cargar_mazo(server_id, user_id, "A")
        mazo_b = cargar_mazo(server_id, user_id, "B")
        mazo_c = cargar_mazo(server_id, user_id, "C")

        total_en_mazos = (
            sum(1 for c in mazo_a if str(c) == card_id) +
            sum(1 for c in mazo_b if str(c) == card_id) +
            sum(1 for c in mazo_c if str(c) == card_id)
        )

        owned_count = sum(1 for c in user_cards if str(c) == card_id)

        if total_en_mazos >= owned_count:
            await ctx.send(
                f"You only own {owned_count} copies of '{card['nombre']}', "
                f"and all of them are already in other decks."
            )
            return

        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if len(user_deck) >= DECK_SIZE:
            await ctx.send(f"Your deck {letra_mazo} already has {DECK_SIZE} cards.")
            return

        user_deck.append(card_id)
        guardar_mazo(server_id, user_id, letra_mazo, user_deck)

        await ctx.send(f"The card '{card['nombre']}' has been added to deck {letra_mazo}.")


    # -----------------------------
    # Comando slash: /deck
    # -----------------------------

    @discord.app_commands.command(
        name="deck",
        description="Shows one of your decks (A, B, C or 1, 2, 3)."
    )
    @app_commands.describe(
        deck="Deck name: either A, B or C or 1, 2 or 3"
    )
    async def deck_slash(self, interaction: discord.Interaction, deck: str = "A"):
        server_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        letra_mazo = normalizar_mazo(deck)

        # Cargar el mazo elegido
        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if not user_deck:
            await interaction.response.send_message(
                f"{interaction.user.display_name}, your deck {letra_mazo} is empty.",
                ephemeral=False
            )
            return

        cartas_info = cartas_por_id()
        vista = NavegadorMazo(interaction, user_deck, cartas_info, interaction.user)

        await vista.enviar()
        
    # -----------------------------
    # Comando prefijo: y!deck
    # -----------------------------

    @commands.command(name="deck")
    async def deck_prefix(self, ctx: commands.Context, deck: str = "A"):
        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        letra_mazo = normalizar_mazo(deck)

        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if not user_deck:
            await ctx.send(f"{ctx.author.display_name}, your deck {letra_mazo} is empty.")
            return

        cartas_info = cartas_por_id()
        vista = NavegadorMazo(ctx, user_deck, cartas_info, ctx.author)

        await vista.enviar()

        
        
    # -----------------------------
    # Comando slash: /deck_remove
    # -----------------------------
    @discord.app_commands.command(
        name="deck_remove",
        description="Remove a card from one of your decks (A, B or C)."
    )
    @app_commands.describe(
        deck="Deck name: A, B, C or 1, 2, 3",
        card_name="Exact name of the card"
    )
    async def deck_remove_slash(self, interaction: discord.Interaction, deck: str, card_name: str):
        server_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        letra_mazo = normalizar_mazo(deck)

        cards = cargar_cartas()
        card = next((c for c in cards if c["nombre"].lower() == card_name.lower()), None)

        if not card:
            await interaction.response.send_message(
                f"No card found with the name '{card_name}'.",
                ephemeral=False
            )
            return

        card_id = str(card["id"])

        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if card_id not in map(str, user_deck):
            await interaction.response.send_message(
                f"The card '{card['nombre']}' is not in deck {letra_mazo}.",
                ephemeral=False
            )
            return

        user_deck.remove(card_id)
        guardar_mazo(server_id, user_id, letra_mazo, user_deck)

        await interaction.response.send_message(
            f"The card '{card['nombre']}' has been removed from deck {letra_mazo}.",
            ephemeral=False
        )

    # -----------------------------
    # Comando prefijo: y!deck_remove
    # -----------------------------
    @commands.command(name="deck_remove")
    async def deck_remove_prefix(self, ctx: commands.Context, deck: str, *, card_name: str):
        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        letra_mazo = normalizar_mazo(deck)

        cards = cargar_cartas()
        card = next((c for c in cards if c["nombre"].lower() == card_name.lower()), None)

        if not card:
            await ctx.send(f"No card found with the name '{card_name}'.")
            return

        card_id = str(card["id"])

        user_deck = cargar_mazo(server_id, user_id, letra_mazo)

        if card_id not in map(str, user_deck):
            await ctx.send(f"The card '{card['nombre']}' is not in deck {letra_mazo}.")
            return

        user_deck.remove(card_id)
        guardar_mazo(server_id, user_id, letra_mazo, user_deck)

        await ctx.send(f"The card '{card['nombre']}' has been removed from deck {letra_mazo}.")



# Setup del cog
async def setup(bot):
    await bot.add_cog(Battle(bot))
