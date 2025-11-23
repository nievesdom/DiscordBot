import discord
from discord.ui import View, button
from core.firebase_storage import cargar_propiedades, guardar_propiedades

from core.cartas import cargar_cartas

class TradeView(View):
    def __init__(self, user1: discord.Member, user2: discord.Member, carta1_obj: dict):
        super().__init__(timeout=120)
        self.user1 = user1
        self.user2 = user2
        self.carta1_obj = carta1_obj
        self.value = None

    @button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo el segundo jugador puede pulsar este botón
        if interaction.user.id != self.user2.id:
            await interaction.response.send_message("🚫 This button is not for you.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"{self.user2.mention}, please type the name of the card you want to offer in exchange.",
            ephemeral=True
        )

        def check(m):
            return m.author.id == self.user2.id and m.channel.id == interaction.channel_id

        try:
            respuesta = await interaction.client.wait_for("message", timeout=120, check=check)
        except Exception:
            await interaction.followup.send("⌛ Time's up. Trade cancelled.")
            self.stop()
            return

        carta2_nombre = respuesta.content.strip()
        cartas = cargar_cartas()
        carta2_obj = next((c for c in cartas if carta2_nombre.lower() in c["nombre"].lower()), None)

        if not carta2_obj:
            await interaction.followup.send(f"❌ The card '{carta2_nombre}' hasn't been found. Trade cancelled.")
            self.stop()
            return

        # Comprobar posesión
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

        # ➡️ Nueva confirmación: pedir al iniciador que acepte o rechace
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
        await interaction.response.send_message(f"❌ {self.user2.display_name} has rejected the trade.")
        self.value = "reject"
        self.stop()


class ConfirmTradeView(View):
    """Segunda confirmación: el iniciador decide si acepta la carta ofrecida."""
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

        # Intercambiar cartas
        coleccion1 = self.propiedades[self.servidor_id][str(self.user1.id)]
        coleccion2 = self.propiedades[self.servidor_id][str(self.user2.id)]
        coleccion1.remove(self.carta1_obj["id"])
        coleccion2.remove(self.carta2_obj["id"])
        coleccion1.append(self.carta2_obj["id"])
        coleccion2.append(self.carta1_obj["id"])
        guardar_propiedades(self.propiedades)
        
        print(f"[Comando] {self.user1.display_name} intercambió {self.carta1_obj['nombre']} a cambio de {self.carta2_obj['nombre']} con {self.user2.display_name} en {interaction.guild.name}.")
        
        await interaction.response.send_message(
            f"✅ Trade successful:\n- {self.user1.mention} traded **{self.carta1_obj['nombre']}** "
            f"and received **{self.carta2_obj['nombre']}**\n"
            f"- {self.user2.mention} traded **{self.carta2_obj['nombre']}** "
            f"and received **{self.carta1_obj['nombre']}**"
        )
        self.stop()

    @button(label="Reject Trade", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user1.id:
            await interaction.response.send_message("🚫 Only the initiator can reject.", ephemeral=True)
            return
        await interaction.response.send_message(f"❌ {self.user1.display_name} has rejected the trade.")
        self.stop()
