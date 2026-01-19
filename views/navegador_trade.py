import discord, asyncio
from discord.ui import View, button

from core.firebase_storage import (
    cargar_propiedades,
    guardar_propiedades,
    cargar_inventario_usuario,
    quitar_cartas_inventario,
    agregar_cartas_inventario
)

from core.cartas import cargar_cartas
from core.firebase_storage import cargar_mazo


def puede_trade(sid: str, uid: str, cid: str):
    """
    Devuelve (True, None) si puede intercambiar.
    Devuelve (False, razon) si no puede.
    """
    cid = str(cid)

    inv = [str(c) for c in cargar_inventario_usuario(sid, uid)]
    total_inv = inv.count(cid)

    if total_inv == 0:
        return False, "You don't own that card."

    ma = [str(c) for c in cargar_mazo(sid, uid, "A")]
    mb = [str(c) for c in cargar_mazo(sid, uid, "B")]
    mc = [str(c) for c in cargar_mazo(sid, uid, "C")]

    total_mazos = ma.count(cid) + mb.count(cid) + mc.count(cid)

    if total_inv <= total_mazos:
        return False, "All your copies of that card are currently in your decks."

    return True, None



class TradeView(View):
    """
    Primera fase del intercambio.
    user1 ofrece una carta y user2 decide si acepta.
    Si acepta, escribe el nombre exacto de la carta que ofrece a cambio.
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

        # Se difiere la interacción para permitir mensajes posteriores
        await interaction.response.defer(ephemeral=True)

        # Se solicita a user2 que escriba el nombre de la carta que ofrece
        await interaction.followup.send(
            f"{self.user2.mention}, type the exact name of the card you want to offer.",
            ephemeral=False
        )

        canal_id = interaction.channel.id

        # Se espera un mensaje del usuario 2 en el mismo canal
        def check(m: discord.Message):
            return m.author.id == self.user2.id and m.channel.id == canal_id

        try:
            respuesta = await interaction.client.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Trade cancelled.")
            self.stop()
            return

        carta2_nombre = respuesta.content.strip().lower()

        # Búsqueda exacta de la carta ofrecida
        cartas = cargar_cartas()
        carta2_obj = next(
            (c for c in cartas if c["nombre"].lower() == carta2_nombre),
            None
        )

        if not carta2_obj:
            await interaction.followup.send(f"The card '{carta2_nombre}' was not found. Trade cancelled.")
            self.stop()
            return

        sid = str(interaction.guild.id)
        uid2 = str(self.user2.id)

        # Validación completa usando puede_trade
        ok, reason = puede_trade(sid, uid2, carta2_obj["id"])
        if not ok:
            await interaction.followup.send(reason)
            self.stop()
            return

        # Se pasa a la fase de confirmación
        confirm_view = ConfirmTradeView(
            self.user1, self.user2, self.carta1_obj, carta2_obj
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
    """
    Segunda fase del intercambio.
    user1 confirma o rechaza el intercambio final.
    """
    def __init__(self, user1, user2, carta1_obj, carta2_obj):
        super().__init__(timeout=120)
        self.user1 = user1
        self.user2 = user2
        self.carta1_obj = carta1_obj
        self.carta2_obj = carta2_obj

    @button(label="Accept Trade", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user1.id:
            await interaction.response.send_message("Only the initiator can confirm.", ephemeral=True)
            return

        sid = str(interaction.guild.id)
        uid1 = str(self.user1.id)
        uid2 = str(self.user2.id)

        id1 = str(self.carta1_obj["id"])
        id2 = str(self.carta2_obj["id"])

        # Validación final usando puede_trade
        ok1, r1 = puede_trade(sid, uid1, id1)
        if not ok1:
            await interaction.response.send_message(r1, ephemeral=True)
            self.stop()
            return

        ok2, r2 = puede_trade(sid, uid2, id2)
        if not ok2:
            await interaction.response.send_message(r2, ephemeral=True)
            self.stop()
            return

        # Intercambio real
        quitar_cartas_inventario(sid, uid1, [id1])
        quitar_cartas_inventario(sid, uid2, [id2])

        agregar_cartas_inventario(sid, uid1, [id2])
        agregar_cartas_inventario(sid, uid2, [id1])

        await interaction.message.edit(
            content=(
                f"Trade completed:\n"
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
