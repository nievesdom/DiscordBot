import discord
from discord.ui import View, button

from core.firebase_storage import (
    cargar_inventario_usuario,
    quitar_cartas_inventario,
    agregar_cartas_inventario
)

from core.cartas import cargar_cartas
from core.firebase_storage import cargar_mazo


def puede_trade(sid: str, uid: str, cid: str):
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



class GiftView(View):
    def __init__(self, sender: discord.Member, recipient: discord.Member, carta_obj: dict,
                 servidor_id: str, client: discord.Client):
        super().__init__(timeout=120)
        self.sender = sender
        self.recipient = recipient
        self.carta_obj = carta_obj
        self.servidor_id = servidor_id
        self.client = client

    @button(label="Accept Gift", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.recipient.id:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)
            return

        servidor_id = self.servidor_id
        sender_id = str(self.sender.id)
        recipient_id = str(self.recipient.id)
        carta_id = str(self.carta_obj["id"])

        # Validación completa usando puede_trade
        ok, reason = puede_trade(servidor_id, sender_id, carta_id)
        if not ok:
            await interaction.response.send_message(reason, ephemeral=True)
            self.stop()
            return

        # Transferencia de la carta
        ok1 = quitar_cartas_inventario(servidor_id, sender_id, [carta_id])
        if not ok1:
            await interaction.response.send_message(
                "Could not remove the card from the sender.",
                ephemeral=True
            )
            self.stop()
            return

        agregar_cartas_inventario(servidor_id, recipient_id, [carta_id])

        # Log opcional
        try:
            log_guild_id = 286617766516228096
            log_channel_id = 1441990735883800607
            log_guild = self.client.get_guild(log_guild_id)
            if log_guild:
                log_channel = log_guild.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(
                        f"[GIFT] {self.sender.display_name} gifted '{self.carta_obj['nombre']}' "
                        f"to {self.recipient.display_name} in {interaction.guild.name}"
                    )
        except Exception as e:
            print(f"[ERROR] Could not send log: {e}")

        await interaction.response.edit_message(
            content=f"{self.recipient.mention} accepted the gift and received {self.carta_obj['nombre']}",
            view=None
        )
        self.stop()

    @button(label="Reject Gift", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.recipient.id:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)
            return

        await interaction.response.edit_message(
            content=f"{self.recipient.display_name} rejected the gift.",
            view=None
        )
        self.stop()
