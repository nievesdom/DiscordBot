import discord
from discord.ui import View, button
from core.gist_propiedades import cargar_propiedades, guardar_propiedades
from core.cartas import cargar_cartas

class TradeView(View):
    def __init__(self, user1: discord.Member, user2: discord.Member, carta1_obj: dict):
        super().__init__(timeout=120)
        self.user1 = user1        # quien inicia el trade
        self.user2 = user2        # con quien se negocia
        self.carta1_obj = carta1_obj
        self.value = None

    @button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user2.id:
            await interaction.response.send_message("🚫 This button is not for you.", ephemeral=True)
            return

        # Pedir al usuario2 que escriba el nombre de la carta que ofrece
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
            await interaction.followup.send(f"❌ You don't own {self.carta1_obj['nombre']}.", ephemeral=True)
            self.stop()
            return
        if carta2_obj["id"] not in coleccion2:
            await interaction.followup.send(f"❌ {self.user2.display_name} doesn't own {carta2_obj['nombre']}.", ephemeral=True)
            self.stop()
            return

        # Intercambiar
        coleccion1.remove(self.carta1_obj["id"])
        coleccion2.remove(carta2_obj["id"])
        coleccion1.append(carta2_obj["id"])
        coleccion2.append(self.carta1_obj["id"])
        propiedades[servidor_id][str(self.user1.id)] = coleccion1
        propiedades[servidor_id][str(self.user2.id)] = coleccion2
        guardar_propiedades(propiedades)

        await interaction.followup.send(
            f"✅ Trade successful:\n- {self.user1.mention} traded **{self.carta1_obj['nombre']}** and received **{carta2_obj['nombre']}**\n"
            f"- {self.user2.mention} traded **{carta2_obj['nombre']}** and received **{self.carta1_obj['nombre']}**"
        )
        self.value = "accept"
        self.stop()

    @button(label="Reject", style=discord.ButtonStyle.red)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user2.id:
            await interaction.response.send_message("🚫 This button is not for you.", ephemeral=True)
            return
        await interaction.response.send_message(f"❌ {self.user2.display_name} has rejected the trade.")
        self.value = "reject"
        self.stop()
