import discord, asyncio
from discord.ui import View, button
from core.firebase_storage import cargar_propiedades, guardar_propiedades
from core.cartas import cargar_cartas

class TradeView(View):
    """
    Primera fase del intercambio:
    - user1 propone intercambiar su carta.
    - user2 acepta y escribe el nombre exacto de la carta que ofrece.
    - Se crea ConfirmTradeView para que user1 confirme el intercambio.
    """
    def __init__(self, user1: discord.Member, user2: discord.Member, carta1_obj: dict):
        super().__init__(timeout=120)
        self.user1 = user1
        self.user2 = user2
        self.carta1_obj = carta1_obj

    @button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user2.id:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)
            return

        # Completar la interacción inmediatamente
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(
            f"{self.user2.mention}, please type the exact name of the card you want to offer in exchange in this channel.",
            ephemeral=True
        )

        def check(m: discord.Message):
            return m.author.id == self.user2.id and m.channel.id == interaction.channel.id

        try:
            respuesta = await interaction.client.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Time's up. Trade cancelled.")
            self.stop()
            return

        carta2_nombre = respuesta.content.strip()

        # Búsqueda exacta por nombre, case-insensitive
        def find_card_by_exact_name(name: str):
            cartas = cargar_cartas()
            name_lower = name.strip().lower()
            return next((c for c in cartas if str(c.get("nombre", "")).lower() == name_lower), None)

        carta2_obj = find_card_by_exact_name(carta2_nombre)
        if not carta2_obj:
            await interaction.followup.send(f"The card '{carta2_nombre}' hasn't been found with exact name. Trade cancelled.")
            self.stop()
            return

        propiedades = cargar_propiedades()
        servidor_id = str(interaction.guild.id)
        coleccion1 = propiedades.get(servidor_id, {}).get(str(self.user1.id), [])
        coleccion2 = propiedades.get(servidor_id, {}).get(str(self.user2.id), [])

        # Comprobación de posesión normalizando IDs a str
        def owns_card(user_cards: list, card_id) -> bool:
            target = str(card_id)
            return any(str(cid) == target for cid in user_cards)

        if not owns_card(coleccion1, self.carta1_obj["id"]):
            await interaction.followup.send(f"You don't own {self.carta1_obj['nombre']}.")
            self.stop()
            return
        if not owns_card(coleccion2, carta2_obj["id"]):
            await interaction.followup.send(f"{self.user2.display_name} doesn't own {carta2_obj['nombre']}.")
            self.stop()
            return

        confirm_view = ConfirmTradeView(self.user1, self.user2, self.carta1_obj, carta2_obj, propiedades, servidor_id)
        await interaction.followup.send(
            f"{self.user1.mention}, {self.user2.display_name} offers **{carta2_obj['nombre']}** "
            f"in exchange for your **{self.carta1_obj['nombre']}**.\nDo you accept?",
            view=confirm_view
        )
        self.stop()

    @button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user2.id:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)
            return
        # Usar message.edit para evitar errores de interacción ya respondida
        await interaction.message.edit(content=f"{self.user2.display_name} has rejected the trade.", view=None)
        self.stop()


class ConfirmTradeView(View):
    """Segunda fase: el iniciador confirma o rechaza el intercambio."""
    def __init__(self, user1, user2, carta1_obj, carta2_obj, propiedades, servidor_id):
        super().__init__(timeout=120)
        self.user1 = user1
        self.user2 = user2
        self.carta1_obj = carta1_obj
        self.carta2_obj = carta2_obj
        self.propiedades = propiedades
        self.servidor_id = servidor_id

    @button(label="Accept Trade", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user1.id:
            await interaction.response.send_message("Only the initiator can confirm.", ephemeral=True)
            return

        propiedades = cargar_propiedades()
        srv = propiedades.setdefault(self.servidor_id, {})
        col1 = srv.setdefault(str(self.user1.id), [])
        col2 = srv.setdefault(str(self.user2.id), [])

        # Comprobar posesión normalizando IDs a str
        def owns_card(user_cards: list, card_id) -> bool:
            target = str(card_id)
            return any(str(cid) == target for cid in user_cards)

        if not owns_card(col1, self.carta1_obj["id"]) or not owns_card(col2, self.carta2_obj["id"]):
            await interaction.response.send_message("One of the cards is no longer owned. Trade cancelled.")
            self.stop()
            return

        # Eliminar una copia de cada inventario normalizando IDs
        def remove_one_copy(user_cards: list, card_id) -> bool:
            target = str(card_id)
            for idx, uid in enumerate(user_cards):
                if str(uid) == target:
                    del user_cards[idx]
                    return True
            return False

        removed1 = remove_one_copy(col1, self.carta1_obj["id"])
        removed2 = remove_one_copy(col2, self.carta2_obj["id"])
        if not removed1 or not removed2:
            await interaction.response.send_message("Could not remove one of the cards. Trade cancelled.")
            self.stop()
            return

        # Añadir la carta recibida. Se guarda el ID como str para consistencia
        col1.append(str(self.carta2_obj["id"]))
        col2.append(str(self.carta1_obj["id"]))
        guardar_propiedades(propiedades)
        
        print(f"[TRADE] {self.user1.display_name} intercambio '{self.carta1_obj['nombre']}' con {self.user2.display_name} por {self.carta2_obj['nombre']} en {interaction.guild.name}.")

        # Enviar log al servidor/canal de logs
        log_guild_id = 286617766516228096
        log_channel_id = 1441990735883800607
        log_guild = interaction.client.get_guild(log_guild_id)
        if log_guild:
            log_channel = log_guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    await log_channel.send(
                        f"[TRADE] {self.user1.display_name} intercambio '{self.carta1_obj['nombre']}' con {self.user2.display_name} por {self.carta2_obj['nombre']}' en {interaction.guild.name}"
                    )
                except Exception as e:
                    print(f"[ERROR] Could not send log: {e}")
        
        # Editar el mensaje original del trade con el resultado final
        await interaction.message.edit(
            content=(
                f"Trade successful:\n- {self.user1.mention} traded **{self.carta1_obj['nombre']}** "
                f"and received **{self.carta2_obj['nombre']}**\n"
                f"- {self.user2.mention} traded **{self.carta2_obj['nombre']}** "
                f"and received **{self.carta1_obj['nombre']}**"
            ),
            view=None
        )
        self.stop()

    @button(label="Reject Trade", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user1.id:
            await interaction.response.send_message("Only the initiator can reject.", ephemeral=True)
            return
        await interaction.message.edit(content=f"{self.user1.display_name} has rejected the trade.", view=None)
        self.stop()
