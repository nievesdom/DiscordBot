import discord
from discord.ui import View, button
from core.firebase_storage import cargar_propiedades, guardar_propiedades

class GiftView(View):
    """
    Vista para que el destinatario acepte o rechace el regalo.
    Funciona tanto en comandos slash como en prefijo.
    """
    def __init__(self, sender: discord.Member, recipient: discord.Member, carta_obj: dict,
                 propiedades, servidor_id, client: discord.Client):
        super().__init__(timeout=60)
        self.sender = sender
        self.recipient = recipient
        self.carta_obj = carta_obj
        self.propiedades = propiedades
        self.servidor_id = servidor_id
        self.client = client  # Puede ser bot o interaction.client

    @button(label="Accept Gift", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.recipient.id:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)
            return

        servidor_props = self.propiedades.setdefault(self.servidor_id, {})
        sender_cards = servidor_props.setdefault(str(self.sender.id), [])
        recipient_cards = servidor_props.setdefault(str(self.recipient.id), [])

        target_id = str(self.carta_obj["id"])
        if target_id not in [str(cid) for cid in sender_cards]:
            await interaction.response.send_message("❌ The sender no longer owns this card.", ephemeral=True)
            self.stop()
            return

        # Transferencia
        sender_cards.remove(target_id)
        recipient_cards.append(target_id)
        guardar_propiedades(self.propiedades)

        # Log en canal de administración
        log_guild_id = 286617766516228096
        log_channel_id = 1441990735883800607
        log_guild = self.client.get_guild(log_guild_id)
        if log_guild:
            log_channel = log_guild.get_channel(log_channel_id)
            if log_channel:
                try:
                    await log_channel.send(
                        f"[GIFT] {self.sender.display_name} regaló '{self.carta_obj['nombre']}' "
                        f"a {self.recipient.display_name} en {interaction.guild.name}"
                    )
                except Exception as e:
                    print(f"[ERROR] Could not send log: {e}")

        await interaction.message.edit(
            content=(
                f"✅ {self.recipient.mention} accepted the gift!\n"
                f"- {self.sender.mention} gave **{self.carta_obj['nombre']}**\n"
                f"- {self.recipient.mention} received **{self.carta_obj['nombre']}**"
            ),
            view=None
        )
        self.stop()

    @button(label="Reject Gift", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.recipient.id:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)
            return

        await interaction.message.edit(
            content=f"❌ {self.recipient.display_name} rejected the gift.",
            view=None
        )
        self.stop()
