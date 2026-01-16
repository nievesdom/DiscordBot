import discord, asyncio
from discord.ui import View, button

# ✅ Usamos SOLO funciones reales de core.firebase_storage
from core.firebase_storage import (
    cargar_inventario_usuario,
    quitar_cartas_inventario,
    agregar_cartas_inventario,
    cargar_mazo
)

from core.cartas import cargar_cartas


def carta_en_mazo(servidor_id: str, usuario_id: str, carta_id: str) -> bool:
    """Comprueba si una carta está en cualquiera de los mazos A, B o C del usuario."""
    carta_id = str(carta_id)

    # Mazo A
    mazo_a = cargar_mazo(servidor_id, usuario_id, "A")
    if carta_id in map(str, mazo_a):
        return True

    # Mazo B
    mazo_b = cargar_mazo(servidor_id, usuario_id, "B")
    if carta_id in map(str, mazo_b):
        return True

    # Mazo C
    mazo_c = cargar_mazo(servidor_id, usuario_id, "C")
    if carta_id in map(str, mazo_c):
        return True

    return False



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

        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(
            f"{self.user2.mention}, please type the exact name of the card you want to offer in exchange.",
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

        # Buscar carta exacta
        cartas = cargar_cartas()
        name_lower = carta2_nombre.lower()
        carta2_obj = next((c for c in cartas if c["nombre"].lower() == name_lower), None)

        if not carta2_obj:
            await interaction.followup.send(f"The card '{carta2_nombre}' was not found. Trade cancelled.")
            self.stop()
            return

        servidor_id = str(interaction.guild.id)
        usuario1_id = str(self.user1.id)
        usuario2_id = str(self.user2.id)

        # Inventarios reales
        col1 = cargar_inventario_usuario(servidor_id, usuario1_id)
        col2 = cargar_inventario_usuario(servidor_id, usuario2_id)

        id1 = str(self.carta1_obj["id"])
        id2 = str(carta2_obj["id"])

        # Comprobar posesión
        if id1 not in col1:
            await interaction.followup.send(f"You no longer own {self.carta1_obj['nombre']}.")
            self.stop()
            return

        if id2 not in col2:
            await interaction.followup.send(f"{self.user2.display_name} does not own {carta2_obj['nombre']}.")
            self.stop()
            return

        # Comprobar mazos
        if carta_en_mazo(servidor_id, usuario1_id, id1):
            await interaction.followup.send(
                f"🚫 You can't trade **{self.carta1_obj['nombre']}** because it is in your deck."
            )
            self.stop()
            return

        if carta_en_mazo(servidor_id, usuario2_id, id2):
            await interaction.followup.send(
                f"🚫 {self.user2.display_name} can't trade **{carta2_obj['nombre']}** because it is in their deck."
            )
            self.stop()
            return

        # Pasar a la fase de confirmación
        confirm_view = ConfirmTradeView(
            self.user1, self.user2,
            self.carta1_obj, carta2_obj,
            servidor_id
        )

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

        await interaction.message.edit(
            content=f"{self.user2.display_name} has rejected the trade.",
            view=None
        )
        self.stop()


class ConfirmTradeView(View):
    """Segunda fase: el iniciador confirma o rechaza el intercambio."""
    def __init__(self, user1, user2, carta1_obj, carta2_obj, servidor_id):
        super().__init__(timeout=120)
        self.user1 = user1
        self.user2 = user2
        self.carta1_obj = carta1_obj
        self.carta2_obj = carta2_obj
        self.servidor_id = servidor_id

    @button(label="Accept Trade", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user1.id:
            await interaction.response.send_message("Only the initiator can confirm.", ephemeral=True)
            return

        servidor_id = self.servidor_id
        uid1 = str(self.user1.id)
        uid2 = str(self.user2.id)

        # Inventarios actuales
        col1 = cargar_inventario_usuario(servidor_id, uid1)
        col2 = cargar_inventario_usuario(servidor_id, uid2)

        id1 = str(self.carta1_obj["id"])
        id2 = str(self.carta2_obj["id"])

        # Comprobar posesión
        if id1 not in col1 or id2 not in col2:
            await interaction.response.send_message("One of the cards is no longer owned. Trade cancelled.")
            self.stop()
            return

        # Quitar una copia a cada uno
        ok1 = quitar_cartas_inventario(servidor_id, uid1, [id1])
        ok2 = quitar_cartas_inventario(servidor_id, uid2, [id2])

        if not ok1 or not ok2:
            await interaction.response.send_message("Could not remove one of the cards. Trade cancelled.")
            self.stop()
            return

        # Añadir la carta recibida
        agregar_cartas_inventario(servidor_id, uid1, [id2])
        agregar_cartas_inventario(servidor_id, uid2, [id1])

        # Editar mensaje final
        await interaction.message.edit(
            content=(
                f"✅ **Trade successful!**\n"
                f"- {self.user1.mention} traded **{self.carta1_obj['nombre']}** "
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

        await interaction.message.edit(
            content=f"{self.user1.display_name} has rejected the trade.",
            view=None
        )
        self.stop()