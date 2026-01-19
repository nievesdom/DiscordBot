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
    
async def send_view_msg(interaction, content=None, view=None, ephemeral=False):
    """
    Envía un mensaje desde una View tanto si el comando original fue slash como prefijo.
    """
    # Slash command (si aún no respondió)
    if hasattr(interaction, "response") and not interaction.response.is_done():
        await interaction.response.send_message(content, view=view, ephemeral=ephemeral)
        return

    # Slash followup
    if hasattr(interaction, "followup"):
        try:
            await interaction.followup.send(content, view=view, ephemeral=ephemeral)
            return
        except:
            pass

    # Prefijo (botón → interaction.message existe)
    await interaction.message.channel.send(content, view=view)


async def edit_view_msg(interaction, content=None, view=None):
    """
    Edita el mensaje que contiene la View.
    Funciona tanto para slash como para prefijo.
    """
    try:
        await interaction.message.edit(content=content, view=view)
    except:
        pass


    
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
        return False, "You don't own that card."

    # Los mazos del usuario
    ma = [str(c) for c in cargar_mazo(sid, uid, "A")]
    mb = [str(c) for c in cargar_mazo(sid, uid, "B")]
    mc = [str(c) for c in cargar_mazo(sid, uid, "C")]
    
    # Se cuentan las cartas con ese ID que tiene en sus mazos
    total_mazos = ma.count(cid) + mb.count(cid) + mc.count(cid)

    if total_inv <= total_mazos:
        return False, "All your copies of that card are currently in your decks."

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
            await send_view_msg(interaction, "Not for you.", ephemeral=True)
            return

        await send_view_msg(interaction, f"{self.u2.mention}, type the card you offer.")

        # Se comprueba que el mensaje sea del mismo autor, mismo canal.
        canal_id = interaction.channel.id

        def check(m: discord.Message):
            return m.author.id == self.u2.id and m.channel.id == canal_id

        try:
            msg = await interaction.client.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await send_view_msg(interaction, "Trade cancelled.")
            self.stop()
            return

        name = msg.content.strip().lower()
        cartas = cargar_cartas()
        c2 = next((c for c in cartas if c["nombre"].lower() == name), None)

        if not c2:
            await send_view_msg(interaction, "Card not found. Trade cancelled.")
            self.stop()
            return

        sid = str(interaction.guild.id)
        u2 = str(self.u2.id)

        ok, reason = puede_trade(sid, u2, c2["id"])
        if not ok:
            await send_view_msg(interaction, reason)
            self.stop()
            return

        await send_view_msg(
            interaction,
            f"{self.u1.mention}, {self.u2.display_name} offers **{c2['nombre']}**.\nDo you accept?",
            view=ConfirmView(self.u1, self.u2, self.c1, c2)
        )
        self.stop()

    @button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.u2.id:
            await send_view_msg(interaction, "Not for you.", ephemeral=True)
            return

        await edit_view_msg(interaction, f"{self.u2.display_name} rejected the trade.", view=None)
        self.stop()




class ConfirmView(View):
    def __init__(self, u1, u2, c1, c2):
        super().__init__(timeout=120)
        self.u1 = u1
        self.u2 = u2
        self.c1 = c1
        self.c2 = c2

    @button(label="Accept", style=discord.ButtonStyle.green)
    async def ok(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.u1.id:
            await send_view_msg(interaction, "Not for you.", ephemeral=True)
            return

        sid = str(interaction.guild.id)
        uid1 = str(self.u1.id)
        uid2 = str(self.u2.id)

        id1 = str(self.c1["id"])
        id2 = str(self.c2["id"])

        ok1, r1 = puede_trade(sid, uid1, id1)
        if not ok1:
            await send_view_msg(interaction, r1)
            self.stop()
            return

        ok2, r2 = puede_trade(sid, uid2, id2)
        if not ok2:
            await send_view_msg(interaction, r2)
            self.stop()
            return

        quitar_cartas_inventario(sid, uid1, [id1])
        quitar_cartas_inventario(sid, uid2, [id2])

        agregar_cartas_inventario(sid, uid1, [id2])
        agregar_cartas_inventario(sid, uid2, [id1])

        await edit_view_msg(
            interaction,
            content=(
                f"Trade completed.\n"
                f"- {self.u1.display_name} gave **{self.c1['nombre']}** and got **{self.c2['nombre']}**\n"
                f"- {self.u2.display_name} gave **{self.c2['nombre']}** and got **{self.c1['nombre']}**"
            ),
            view=None
        )
        self.stop()

    @button(label="Reject", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button):
        if interaction.user.id != self.u1.id:
            await send_view_msg(interaction, "Not for you.", ephemeral=True)
            return

        await edit_view_msg(interaction, f"{self.u1.display_name} cancelled the trade.", view=None)
        self.stop()
