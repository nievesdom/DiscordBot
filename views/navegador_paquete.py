import discord

class NavegadorPaquete(discord.ui.View):
    def __init__(self, context, cartas_ids, cartas_info, dueño):
        super().__init__(timeout=180)
        self.context = context
        self.cartas_ids = cartas_ids or []      # Protección por si viene None
        self.cartas_info = cartas_info or {}
        self.dueño = dueño
        self.i = 0
        self.msg = None

        self.colores = {
            "UR": 0x8841f2, "KSR": 0xabfbff, "SSR": 0x57ffae,
            "SR": 0xfcb63d, "R": 0xfc3d3d, "N": 0x8c8c8c
        }
        self.atributos = {
            "heart": "心", "technique": "技", "body": "体",
            "light": "陽", "shadow": "陰"
        }
        self.tipos = {
            "attack": "⚔️ Attack", "defense": "🛡️ Defense",
            "recovery": "❤️ Recovery", "support": "✨ Support"
        }

    def mostrar(self):
        # Si no hay cartas, muestra un embed informativo
        if not self.cartas_ids:
            embed = discord.Embed(
                title="No cards in this pack",
                description="This pack is empty or failed to load.",
                color=0x8c8c8c
            )
            embed.set_footer(text=f"{self.dueño.display_name}'s daily pack")
            return embed, None

        carta_id = str(self.cartas_ids[self.i])
        carta = self.cartas_info.get(carta_id, {})
        nombre = carta.get("nombre", f"ID {carta_id}")
        rareza = carta.get("rareza", "N")
        color = self.colores.get(rareza, 0x8c8c8c)
        imagen = carta.get("imagen")

        atributo_raw = str(carta.get("atributo", "—")).lower()
        tipo_raw = str(carta.get("tipo", "—")).lower()
        attr_symbol = self.atributos.get(atributo_raw, "")
        attr_name = atributo_raw.capitalize() if atributo_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
        tipo_fmt = self.tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

        embed = discord.Embed(
            title=f"{nombre}",
            color=color,
            description=(f"**Attribute:** {atributo_fmt}\n"
                         f"**Type:** {tipo_fmt}\n"
                         f"❤️ {carta.get('health', '—')} | ⚔️ {carta.get('attack', '—')} | "
                         f"🛡️ {carta.get('defense', '—')} | 💨 {carta.get('speed', '—')}")
        )
        embed.set_footer(
            text=f"Card {self.i + 1} out of {len(self.cartas_ids)} • {self.dueño.display_name}'s daily pack"
        )

        if imagen and str(imagen).startswith("http"):
            embed.set_image(url=imagen)
        else:
            embed.description += "\n⚠️ Card image not found. Please, contact my creator."

        return embed, None  # archivo=None: no usamos attachments aquí

    async def enviar(self):
        embed, archivo = self.mostrar()
        if isinstance(self.context, discord.Interaction):
            # Asegúrate de que la interacción original ya fue respondida/deferida antes
            if archivo:
                self.msg = await self.context.followup.send(file=archivo, embed=embed, view=self)
            else:
                self.msg = await self.context.followup.send(embed=embed, view=self)
        else:
            if archivo:
                self.msg = await self.context.send(file=archivo, embed=embed, view=self)
            else:
                self.msg = await self.context.send(embed=embed, view=self)

    async def actualizar(self, interaction: discord.Interaction | None = None):
        """Actualiza el embed mostrado al cambiar de carta."""
        embed, archivo = self.mostrar()

        if interaction:
            await interaction.response.edit_message(embed=embed, view=self)
            return

        if self.msg:
            await self.msg.edit(embed=embed, view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def atras(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Cualquiera puede usar los botones
        if not self.cartas_ids:
            await interaction.response.send_message("No cards to navigate.")
            return
        self.i = (self.i - 1) % len(self.cartas_ids)
        await self.actualizar(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Cualquiera puede usar los botones
        if not self.cartas_ids:
            await interaction.response.send_message("No cards to navigate.")
            return
        self.i = (self.i + 1) % len(self.cartas_ids)
        await self.actualizar(interaction)

    async def on_timeout(self):
        """Opcional: al expirar, deshabilita los botones y deja el último estado."""
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        if self.msg:
            try:
                embed, _ = self.mostrar()
                await self.msg.edit(embed=embed, view=self)
            except Exception:
                pass
