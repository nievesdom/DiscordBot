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
    
def puede_trade(sid: str, uid: str, cid: str) -> bool:
    """Devuelve True si el usuario puede intercambiar esa carta."""
    cid = str(cid)

    inv = [str(c) for c in cargar_inventario_usuario(sid, uid)]
    total_inv = inv.count(cid)

    ma = [str(c) for c in cargar_mazo(sid, uid, "A")]
    mb = [str(c) for c in cargar_mazo(sid, uid, "B")]
    mc = [str(c) for c in cargar_mazo(sid, uid, "C")]

    total_mazos = ma.count(cid) + mb.count(cid) + mc.count(cid)

    return total_inv > total_mazos



class TradeView(View):
    def __init__(self, u1: discord.Member, u2: discord.Member, c1: dict):
        super().__init__(timeout=120)
        self.u1 = u1
        self.u2 = u2
        self.c1 = c1

    @button(label="Accept", style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
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

        if not puede_trade(sid, u2, c2["id"]):
            await interaction.followup.send(f"You cannot trade {c2['nombre']}.")
            self.stop()
            return

        await interaction.followup.send(
            f"{self.u1.mention}, {self.u2.display_name} offers **{c2['nombre']}**.",
            view=ConfirmView(self.u1, self.u2, self.c1, c2)
        )
        self.stop()

    @button(label="Reject", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
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

    @button(label="OK", style=discord.ButtonStyle.green)
    async def ok(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.u1.id:
            await interaction.response.send_message("Not for you.", ephemeral=True)
            return

        sid = str(interaction.guild.id)
        uid1 = str(self.u1.id)
        uid2 = str(self.u2.id)

        id1 = str(self.c1["id"])
        id2 = str(self.c2["id"])

        if not puede_trade(sid, uid1, id1):
            await interaction.response.send_message("You no longer can trade your card.")
            self.stop()
            return

        if not puede_trade(sid, uid2, id2):
            await interaction.response.send_message("The other user cannot trade their card anymore.")
            self.stop()
            return

        quitar_cartas_inventario(sid, uid1, [id1])
        quitar_cartas_inventario(sid, uid2, [id2])

        agregar_cartas_inventario(sid, uid1, [id2])
        agregar_cartas_inventario(sid, uid2, [id1])

        await interaction.message.edit(
            content=(
                f"Trade done.\n"
                f"- {self.u1.display_name} gave **{self.c1['nombre']}** and got **{self.c2['nombre']}**\n"
                f"- {self.u2.display_name} gave **{self.c2['nombre']}** and got **{self.c1['nombre']}**"
            ),
            view=None
        )
        self.stop()

    @button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.u1.id:
            await interaction.response.send_message("Not for you.", ephemeral=True)
            return

        await interaction.message.edit(content=f"{self.u1.display_name} cancelled the trade.", view=None)
        self.stop()
