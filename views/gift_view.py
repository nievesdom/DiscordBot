import discord
from discord.ui import View, button

from core.firebase_storage import (
    cargar_inventario_usuario,
    quitar_cartas_inventario,
    agregar_cartas_inventario,
    cargar_mazo
)


def carta_en_mazo(servidor_id: str, usuario_id: str, carta_id: str) -> bool:
    carta_id = str(carta_id)

    # Comprobar mazo A
    mazo_a = cargar_mazo(servidor_id, usuario_id, "A")
    if carta_id in map(str, mazo_a):
        return True

    # Comprobar mazo B
    mazo_b = cargar_mazo(servidor_id, usuario_id, "B")
    if carta_id in map(str, mazo_b):
        return True

    # Comprobar mazo C
    mazo_c = cargar_mazo(servidor_id, usuario_id, "C")
    if carta_id in map(str, mazo_c):
        return True

    return False



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

        sender_cards = cargar_inventario_usuario(servidor_id, sender_id)
        recipient_cards = cargar_inventario_usuario(servidor_id, recipient_id)

        if carta_id not in map(str, sender_cards):
            await interaction.response.send_message(
                "The sender no longer owns this card.",
                ephemeral=True
            )
            self.stop()
            return

        if carta_en_mazo(servidor_id, sender_id, carta_id):
            await interaction.response.send_message(
                f"The sender cannot gift {self.carta_obj['nombre']} because it is currently in their deck.",
                ephemeral=True
            )
            self.stop()
            return

        ok1 = quitar_cartas_inventario(servidor_id, sender_id, [carta_id])
        if not ok1:
            await interaction.response.send_message(
                "Could not remove the card from the sender.",
                ephemeral=True
            )
            self.stop()
            return

        agregar_cartas_inventario(servidor_id, recipient_id, [carta_id])

        try:
            log_guild_id = 286617766516228096
            log_channel_id = 1441990735883800607
            log_guild = self.client.get_guild(log_guild_id)
            if log_guild:
                log_channel = log_guild.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(
                        f"[GIFT] {self.sender.display_name} regaló '{self.carta_obj['nombre']}' "
                        f"a {self.recipient.display_name} en {interaction.guild.name}"
                    )
        except Exception as e:
            print(f"[ERROR] Could not send log: {e}")

        await interaction.response.edit_message(
            content=(
                f"{self.recipient.mention} accepted the gift and received {self.carta_obj['nombre']}"
            ),
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
