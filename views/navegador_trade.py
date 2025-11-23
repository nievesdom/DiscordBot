import discord
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
        self.msg = None  # opcional, si quieres guardar el mensaje donde se adjunta la vista

    async def on_timeout(self):
        # Al expirar, deshabilita los botones
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.msg:
            try:
                await self.msg.edit(view=self)
            except Exception:
                pass

    @button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo el segundo jugador puede pulsar este botón
        if interaction.user.id != self.user2.id:
            await interaction.response.send_message("🚫 This button is not for you.", ephemeral=True)
            return

        # Responder la interacción (ephemeral) e indicar que esperamos su mensaje
        await interaction.response.send_message(
            f"{self.user2.mention}, please type the name of the card you want to offer in exchange in this channel.",
            ephemeral=True
        )

        def check(m: discord.Message):
            # El mensaje debe ser del usuario 2 y en el mismo canal
            return m.author.id == self.user2.id and m.channel.id == interaction.channel.id

        try:
            respuesta = await interaction.client.wait_for("message", timeout=120, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("⌛ Time's up. Trade cancelled.")
            self.stop()
            return
        except Exception as e:
            await interaction.followup.send(f"❌ Unexpected error: {e}\nTrade cancelled.")
            self.stop()
            return

        carta2_nombre = respuesta.content.strip()
        cartas = cargar_cartas()
        carta2_obj = next((c for c in cartas if carta2_nombre.lower() in str(c.get("nombre", "")).lower()), None)

        if not carta2_obj:
            await interaction.followup.send(f"❌ The card '{carta2_nombre}' hasn't been found. Trade cancelled.")
            self.stop()
            return

        # Comprobar posesión
        propiedades = cargar_propiedades()
        servidor_id = str(interaction.guild.id)
        user1_id = str(self.user1.id)
        user2_id = str(self.user2.id)

        coleccion1 = propiedades.get(servidor_id, {}).get(user1_id, [])
        coleccion2 = propiedades.get(servidor_id, {}).get(user2_id, [])

        if self.carta1_obj["id"] not in coleccion1:
            await interaction.followup.send(f"❌ You don't own {self.carta1_obj['nombre']}.")
            self.stop()
            return
        if carta2_obj["id"] not in coleccion2:
            await interaction.followup.send(f"❌ {self.user2.display_name} doesn't own {carta2_obj['nombre']}.")
            self.stop()
            return

        # Crear la segunda vista de confirmación (solo user1 puede confirmar)
        confirm_view = ConfirmTradeView(self.user1, self.user2, self.carta1_obj, carta2_obj, propiedades, servidor_id)

        # Enviar el mensaje de confirmación (mensaje público, no ephemeral)
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
        self.stop()


class ConfirmTradeView(View):
    """
    Segunda fase:
    - user1 confirma o rechaza el intercambio propuesto.
    - Si confirma, se actualiza Firestore de forma segura.
    """
    def __init__(self, user1: discord.Member, user2: discord.Member,
                 carta1_obj: dict, carta2_obj: dict,
                 propiedades: dict, servidor_id: str):
        super().__init__(timeout=120)
        self.user1 = user1
        self.user2 = user2
        self.carta1_obj = carta1_obj
        self.carta2_obj = carta2_obj
        self.propiedades = propiedades
        self.servidor_id = servidor_id

    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True

    @button(label="Accept Trade", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user1.id:
            await interaction.response.send_message("🚫 Only the initiator can confirm.", ephemeral=True)
            return

        # Revalidación rápido: asegurar que las colecciones siguen conteniendo las cartas
        # (evita carreras si las colecciones cambiaron durante la espera)
        propiedades = cargar_propiedades()
        srv = propiedades.setdefault(self.servidor_id, {})
        col1 = srv.setdefault(str(self.user1.id), [])
        col2 = srv.setdefault(str(self.user2.id), [])

        if self.carta1_obj["id"] not in col1:
            await interaction.response.send_message(f"❌ You no longer own {self.carta1_obj['nombre']}.")
            self.stop()
            return
        if self.carta2_obj["id"] not in col2:
            await interaction.response.send_message(f"❌ {self.user2.display_name} no longer owns {self.carta2_obj['nombre']}.")
            self.stop()
            return

        # Intercambiar cartas
        try:
            col1.remove(self.carta1_obj["id"])
        except ValueError:
            pass
        try:
            col2.remove(self.carta2_obj["id"])
        except ValueError:
            pass
        col1.append(self.carta2_obj["id"])
        col2.append(self.carta1_obj["id"])

        # Persistir en Firestore
        guardar_propiedades(propiedades)

        # Confirmación visible y desactivar la vista
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
