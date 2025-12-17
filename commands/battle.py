import asyncio
import discord
from discord.ext import commands
from core.firebase_storage import cargar_inventario_usuario, cargar_mazo, cargar_mazos, guardar_mazo, guardar_mazos, cargar_propiedades
from core.cartas import cargar_cartas, cartas_por_id
from views.navegador_mazo import NavegadorMazo

DECK_SIZE = 8 # Tamaño máximo del mazo

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
    
        # Buscar carta por nombre exacto
        cards = cargar_cartas()
        card = next((c for c in cards if c["nombre"].lower() == card_name.lower()), None)
    
        if not card:
            await interaction.response.send_message(
                f"No card found with the name '{card_name}'.",
                ephemeral=False
            )
            return
    
        card_id = str(card["id"])
    
        # Cargar inventario real del usuario
        user_cards = cargar_inventario_usuario(server_id, user_id)
    
        if card_id not in map(str, user_cards):
            await interaction.response.send_message(
                f"You do not own the card '{card['nombre']}'.",
                ephemeral=False
            )
            return
    
        # Cargar mazo del usuario (por ejemplo mazo A)
        # Si usas varios mazos, aquí puedes elegir cuál. Por ahora asumimos "A".
        letra_mazo = "A"
        user_deck = cargar_mazo(server_id, user_id, letra_mazo)
    
        # Limitar tamaño del mazo
        if len(user_deck) >= DECK_SIZE:
            await interaction.response.send_message(
                f"Your deck already has {DECK_SIZE} cards, remove one to add another.",
                ephemeral=False
            )
            return
    
        # Contar copias en inventario y en el mazo
        owned_count = sum(1 for c in user_cards if str(c) == card_id)
        deck_count = sum(1 for c in user_deck if str(c) == card_id)
    
        if deck_count >= owned_count:
            await interaction.response.send_message(
                f"You only own {owned_count} copies of '{card['nombre']}', so you cannot add more to your deck.",
                ephemeral=False
            )
            return
    
        # Añadir la carta al mazo
        user_deck.append(card_id)
    
        # Guardar solo ese mazo sin tocar nada más
        guardar_mazo(server_id, user_id, letra_mazo, user_deck)
    
        await interaction.response.send_message(
            f"The card '{card['nombre']}' has been added to your deck.",
            ephemeral=False
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
            await ctx.send(f"❌ No card found with the name '{card_name}'.")
            return

        card_id = str(card["id"])

        # Comprobar si el usuario tiene la carta en propiedad
        properties = cargar_propiedades()
        user_cards = properties.get(server_id, {}).get(user_id, [])

        if card_id not in map(str, user_cards):
            await ctx.send(f"❌ You don't own the card '{card['nombre']}'.")
            return

        # Añadir la carta al mazo en Firebase
        decks = cargar_mazos()
        server_decks = decks.setdefault(server_id, {})
        user_deck = server_decks.setdefault(user_id, [])

        # Limitar el tamaño del mazo
        if len(user_deck) >= DECK_SIZE:
            await ctx.send(f"🚫 Your deck already has {DECK_SIZE} cards, remove one to add another.")
            return

        # Contar cuántas copias tiene en propiedad y cuántas ya están en el mazo
        owned_count = sum(1 for c in user_cards if str(c) == card_id)
        deck_count = sum(1 for c in user_deck if str(c) == card_id)

        if deck_count >= owned_count:
            await ctx.send(
                f"🚫 You only own {owned_count} copies of '{card['nombre']}', "
                f"so you can't add more to your deck."
            )
            return

        # Añadir la carta al mazo
        user_deck.append(card_id)
        guardar_mazos(decks)

        # Confirmación al usuario
        await ctx.send(f"✅ The card **{card['nombre']}** has been added to your deck.")


    # -----------------------------
    # Comando slash: /deck
    # -----------------------------
    @discord.app_commands.command(
        name="deck",
        description="Shows your current deck of cards."
    )
    async def deck_slash(self, interaction: discord.Interaction):
        # IDs del servidor y usuario
        server_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        # Cargar mazos desde Firebase
        decks = cargar_mazos()
        server_decks = decks.get(server_id, {})
        user_deck = server_decks.get(user_id, [])

        # Cargar info de cartas
        cartas_info = cartas_por_id()

        # Crear vista navegable del mazo
        vista = NavegadorMazo(interaction, user_deck, cartas_info, interaction.user)

        # Si el mazo está vacío, mostrar mensaje
        if not user_deck:
            await interaction.response.send_message(
                f"❌ {interaction.user.display_name}, your deck is empty.",
                ephemeral=False
            )
            return

        # Enviar la vista
        await vista.enviar()


    # -----------------------------
    # Comando prefijo: y!deck
    # -----------------------------
    @commands.command(name="deck")
    async def deck_prefix(self, ctx: commands.Context):
        """Muestra el mazo actual del usuario (prefijo)."""
        # IDs del servidor y usuario
        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        # Cargar mazos desde Firebase
        decks = cargar_mazos()
        server_decks = decks.get(server_id, {})
        user_deck = server_decks.get(user_id, [])

        # Cargar info de cartas
        cartas_info = cartas_por_id()

        # Crear vista navegable del mazo
        vista = NavegadorMazo(ctx, user_deck, cartas_info, ctx.author)

        # Si el mazo está vacío, mostrar mensaje
        if not user_deck:
            await ctx.send(f"❌ {ctx.author.display_name}, your deck is empty.")
            return

        # Enviar la vista
        await vista.enviar()
        
        
    # -----------------------------
    # Comando slash: /deck_remove
    # -----------------------------
    @discord.app_commands.command(
        name="deck_remove",
        description="Remove a card from your deck by exact name (slash)."
    )
    async def deck_remove_slash(self, interaction: discord.Interaction, card_name: str):
        # IDs del servidor y usuario
        server_id = str(interaction.guild.id)
        user_id = str(interaction.user.id)

        # Buscar carta por nombre exacto en el JSON
        cards = cargar_cartas()
        card = next((c for c in cards if c["nombre"].lower() == card_name.lower()), None)

        # Si no existe la carta
        if not card:
            await interaction.response.send_message(
                f"❌ No card found with the name '{card_name}'.", ephemeral=False
            )
            return

        card_id = str(card["id"])

        # Cargar mazos desde Firebase
        decks = cargar_mazos()
        server_decks = decks.setdefault(server_id, {})
        user_deck = server_decks.setdefault(user_id, [])

        # Comprobar si la carta está en el mazo
        if card_id not in user_deck:
            await interaction.response.send_message(
                f"❌ The card '{card['nombre']}' is not in your deck.", ephemeral=False
            )
            return

        # Quitar una copia de la carta del mazo
        user_deck.remove(card_id)
        guardar_mazos(decks)

        # Confirmación al usuario
        await interaction.response.send_message(
            f"✅ The card **{card['nombre']}** has been removed from your deck.", ephemeral=False
        )


    # -----------------------------
    # Comando prefijo: y!deck_remove
    # -----------------------------
    @commands.command(name="deck_remove")
    async def deck_remove_prefix(self, ctx: commands.Context, *, card_name: str):
        """Quita una carta del mazo del usuario buscando por nombre exacto (prefijo)."""
        # IDs del servidor y usuario
        server_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        # Buscar carta por nombre exacto en el JSON
        cards = cargar_cartas()
        card = next((c for c in cards if c["nombre"].lower() == card_name.lower()), None)

        # Si no existe la carta
        if not card:
            await ctx.send(f"❌ No card found with the name '{card_name}'.")
            return

        card_id = str(card["id"])

        # Cargar mazos desde Firebase
        decks = cargar_mazos()
        server_decks = decks.setdefault(server_id, {})
        user_deck = server_decks.setdefault(user_id, [])

        # Comprobar si la carta está en el mazo
        if card_id not in user_deck:
            await ctx.send(f"❌ The card '{card['nombre']}' is not in your deck.")
            return

        # Quitar una copia de la carta del mazo
        user_deck.remove(card_id)
        guardar_mazos(decks)

        # Confirmación al usuario
        await ctx.send(f"✅ The card **{card['nombre']}** has been removed from your deck.")


# Setup del cog
async def setup(bot):
    await bot.add_cog(Battle(bot))
