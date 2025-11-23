import discord, asyncio
from discord.ui import View, button
from core.firebase_storage import cargar_propiedades, guardar_propiedades
from core.cartas import cargar_cartas


class TradeView(View):
    """
    Primera fase del intercambio:
    - user1 propone intercambiar su carta.
    - user2 acepta y escribe el nombre de la carta que ofrece.
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
            await interaction.response.send_message("🚫 This button is not for you.", ephemeral=True)
            return

        # Completar la interacción inmediatamente
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(
            f"{self.user2.mention}, please type the name of the card you want to offer in exchange in this channel.",
            ephemeral=True
        )

        def check(m: discord.Message):
            return m.author.id == self.user2.id and m.channel.id == interaction.channel.id

        try:
            respuesta = await interaction.client.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("⌛ Time's up. Trade cancelled.")
            self.stop()
            return

        carta2_nombre = respuesta.content.strip()
        cartas = cargar_cartas()
        carta2_obj = next((c for c in cartas if carta2_nombre.lower() in str(c.get("nombre", "")).lower()), None)

        if not carta2_obj:
            await interaction.followup.send(f"❌ The card '{carta2_nombre}' hasn't been found. Trade cancelled.")
            self.stop()
            return

        propiedades = cargar_propiedades()
        servidor_id = str(interaction.guild.id)
        coleccion1 = propiedades.get(servidor_id, {}).get(str(self.user1.id), [])
        coleccion2 = propiedades.get(servidor_id, {}).get(str(self.user2.id), [])

        if self.carta1_obj["id"] not in coleccion1:
            await interaction.followup.send(f"❌ You don't own {self.carta1_obj['nombre']}.")
            self.stop()
            return
        if carta2_obj["id"] not in coleccion2:
            await interaction.followup.send(f"❌ {self.user2.display_name} doesn't own {carta2_obj['nombre']}.")
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
            await interaction.response.send_message("🚫 This button is not for you.", ephemeral=True)
            return
        await interaction.response.edit_message(content=f"❌ {self.user2.display_name} has rejected the trade.", view=None)
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
            await interaction.response.send_message("🚫 Only the initiator can confirm.", ephemeral=True)
            return

        propiedades = cargar_propiedades()
        srv = propiedades.setdefault(self.servidor_id, {})
        col1 = srv.setdefault(str(self.user1.id), [])
        col2 = srv.setdefault(str(self.user2.id), [])

        if self.carta1_obj["id"] not in col1 or self.carta2_obj["id"] not in col2:
            await interaction.response.send_message("❌ One of the cards is no longer owned. Trade cancelled.")
            self.stop()
            return

        col1.remove(self.carta1_obj["id"])
        col2.remove(self.carta2_obj["id"])
        col1.append(self.carta2_obj["id"])
        col2.append(self.carta1_obj["id"])
        guardar_propiedades(propiedades)
        
        print(f"[TRADE] {self.user1.display_name} intercambió '{self.carta1_obj['nombre']}' con {self.user2.display_name} por {self.carta2_obj['nombre']} en {interaction.guild.name}.")

        await interaction.response.edit_message(
            content=(
                f"✅ Trade successful:\n- {self.user1.mention} traded **{self.carta1_obj['nombre']}** "
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
            await interaction.response.send_message("🚫 Only the initiator can reject.", ephemeral=True)
            return
        await interaction.response.edit_message(content=f"❌ {self.user1.display_name} has rejected the trade.", view=None)
        self.stop()
