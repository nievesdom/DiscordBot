import discord
from discord.ui import View, button
from core.firebase_storage import cargar_propiedades, guardar_propiedades

class GiftView(View):
    def __init__(self, sender: discord.Member, recipient: discord.Member, carta_obj: dict,
                 propiedades, servidor_id, client: discord.Client):
        super().__init__(timeout=120)
        self.sender = sender
        self.recipient = recipient
        self.carta_obj = carta_obj
        self.propiedades = propiedades
        self.servidor_id = servidor_id
        self.client = client  # Puede ser bot o interaction.client

    @button(label="Accept Gift", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo el destinatario puede aceptar
        if interaction.user.id != self.recipient.id:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)
            return

        servidor_props = self.propiedades.setdefault(self.servidor_id, {})
        sender_cards = servidor_props.setdefault(str(self.sender.id), [])
        recipient_cards = servidor_props.setdefault(str(self.recipient.id), [])

        # Normalizar tipos a string para comparación y eliminación
        target_id = str(self.carta_obj["id"])
        sender_cards_str = [str(cid) for cid in sender_cards]

        if target_id not in sender_cards_str:
            await interaction.response.send_message("❌ The sender no longer owns this card.", ephemeral=True)
            self.stop()
            return

        # Transferencia (operar sobre listas normalizadas)
        # Si la lista original mezcla tipos, reconstruimos a strings para consistencia
        servidor_props[str(self.sender.id)] = sender_cards_str
        servidor_props[str(self.recipient.id)] = [str(cid) for cid in recipient_cards]

        servidor_props[str(self.sender.id)].remove(target_id)
        servidor_props[str(self.recipient.id)].append(target_id)

        guardar_propiedades(self.propiedades)

        # Log en canal de administración (no bloquea la respuesta del botón)
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

        # Editar el mensaje del botón usando la respuesta de la interacción (más fiable)
        await interaction.response.edit_message(
            content=(
                f"✅ {self.recipient.mention} accepted the gift and received **{self.carta_obj['nombre']}**"
            ),
            view=None
        )
        self.stop()

    @button(label="Reject Gift", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo el destinatario puede rechazar
        if interaction.user.id != self.recipient.id:
            await interaction.response.send_message("This button is not for you.", ephemeral=True)
            return

        # Para componentes, usa también edit_message como respuesta primaria
        await interaction.response.edit_message(
            content=f"❌ {self.recipient.display_name} rejected the gift.",
            view=None
        )
        self.stop()
