import discord, asyncio
from discord.ui import View, button

from core.firebase_storage import (
    cargar_inventario_usuario,
    quitar_cartas_inventario,
    agregar_cartas_inventario,
    cargar_mazo
)

from core.cartas import cargar_cartas


def carta_en_mazo(servidor_id: str, usuario_id: str, carta_id: str) -> bool:
    carta_id = str(carta_id)

    mazo_a = cargar_mazo(servidor_id, usuario_id, "A")
    mazo_b = cargar_mazo(servidor_id, usuario_id, "B")
    mazo_c = cargar_mazo(servidor_id, usuario_id, "C")

    return (
        carta_id in map(str, mazo_a)
        or carta_id in map(str, mazo_b)
        or carta_id in map(str, mazo_c)
    )
    
# Comprueba si un usuario puede intercambiar una carta o no
def puede_trade(sid: str, uid: str, cid: str):
    """
    Devuelve (True, None) si puede intercambiar.
    Devuelve (False, razon) si no puede.
    """
    cid = str(cid) # ID de la carta

    # Se cuentan las cartas con ese ID que tiene en el inventario
    inv = [str(c) for c in cargar_inventario_usuario(sid, uid)]
    total_inv = inv.count(cid)

    if total_inv == 0:
        return False, "You do not own this card."

    # Los mazos del usuario
    ma = [str(c) for c in cargar_mazo(sid, uid, "A")]
    mb = [str(c) for c in cargar_mazo(sid, uid, "B")]
    mc = [str(c) for c in cargar_mazo(sid, uid, "C")]
    
    # Se cuentan las cartas con ese ID que tiene en sus mazos
    total_mazos = ma.count(cid) + mb.count(cid) + mc.count(cid)

    if total_inv <= total_mazos:
        return False, "All your copies of this card are currently in your decks."

    return True, None




class TradeView(View):
    def __init__(self, u1: discord.Member, u2: discord.Member, c1: dict):
        super().__init__(timeout=120)
        self.u1 = u1
        self.u2 = u2
        self.c1 = c1

    @button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.u2.id:
            await interaction.response.send_message("Not for you.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"{self.u2.mention}, type the card you offer.",
            ephemeral=False
        )

        def check(m):
            return m.author.id == self.u2.id and m.channel == interaction.channel

        try:
            msg = await interaction.client.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Trade cancelled.")
            self.stop()
            return

        name = msg.content.strip().lower()
        cartas = cargar_cartas()
        c2 = next((c for c in cartas if c["nombre"].lower() == name), None)

        if not c2:
            await interaction.followup.send("Card not found. Trade cancelled.")
            self.stop()
            return

        sid = str(interaction.guild.id)
        u2 = str(self.u2.id)

        ok, reason = puede_trade(sid, u2, c2["id"])
        if not ok:
            await interaction.followup.send(reason)
            self.stop()
            return

        await interaction.followup.send(
            f"{self.u1.mention}, {self.u2.display_name} offers **{c2['nombre']}**.",
            view=ConfirmView(self.u1, self.u2, self.c1, c2)
        )
        self.stop()

    @button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.u2.id:
            await interaction.response.send_message("Not for you.", ephemeral=True)
            return

        await interaction.message.edit(content=f"{self.u2.display_name} rejected the trade.", view=None)
        self.stop()



class ConfirmView(View):
    def __init__(self, u1, u2, c1, c2):
        super().__init__(timeout=120)
        self.u1 = u1
        self.u2 = u2
        self.c1 = c1
        self.c2 = c2

    @button(label="Accept", style=discord.ButtonStyle.green)
    async def ok(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.u1.id:
            await interaction.response.send_message("Not for you.", ephemeral=True)
            return

        sid = str(interaction.guild.id)
        uid1 = str(self.u1.id)
        uid2 = str(self.u2.id)

        id1 = str(self.c1["id"])
        id2 = str(self.c2["id"])

        ok1, r1 = puede_trade(sid, uid1, id1)
        if not ok1:
            await interaction.response.send_message(r1)
            self.stop()
            return

        ok2, r2 = puede_trade(sid, uid2, id2)
        if not ok2:
            await interaction.response.send_message(r2)
            self.stop()
            return

        quitar_cartas_inventario(sid, uid1, [id1])
        quitar_cartas_inventario(sid, uid2, [id2])

        agregar_cartas_inventario(sid, uid1, [id2])
        agregar_cartas_inventario(sid, uid2, [id1])

        await interaction.message.edit(
            content=(
                f"Trade completed.\n"
                f"- {self.u1.display_name} gave **{self.c1['nombre']}** and got **{self.c2['nombre']}**\n"
                f"- {self.u2.display_name} gave **{self.c2['nombre']}** and got **{self.c1['nombre']}**"
            ),
            view=None
        )
        self.stop()

    @button(label="Reject", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.u1.id:
            await interaction.response.send_message("Not for you.", ephemeral=True)
            return

        await interaction.message.edit(content=f"{self.u1.display_name} cancelled the trade.", view=None)
        self.stop()
