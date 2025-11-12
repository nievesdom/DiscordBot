import discord

class NavegadorPaquete(discord.ui.View):
    def __init__(self, ctx, cartas_ids, cartas_info, dueño):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.cartas_ids = cartas_ids
        self.cartas_info = cartas_info
        self.dueño = dueño
        self.i = 0
        self.msg = None

        # Colores por rareza
        self.colores = {
            "UR": 0x8841f2,
            "KSR": 0xabfbff,
            "SSR": 0x57ffae,
            "SR": 0xfcb63d,
            "R": 0xfc3d3d,
            "N": 0x8c8c8c
        }

    def mostrar(self):
        carta_id = str(self.cartas_ids[self.i])
        carta = self.cartas_info.get(carta_id, {})
        nombre = carta.get("nombre", f"ID {carta_id}")
        rareza = carta.get("rareza", "N")
        color = self.colores.get(rareza, 0x8c8c8c)
        imagen = carta.get("imagen")

        embed = discord.Embed(
            title=f"{nombre} [{rareza}]",
            color=color,
            description=(
                f"**Atributo:** {carta.get('atributo', '—')} | "
                f"**Tipo:** {carta.get('tipo', '—')}\n"
                f"❤️ {carta.get('health', '—')} | ⚔️ {carta.get('attack', '—')} | "
                f"🛡️ {carta.get('defense', '—')} | 💨 {carta.get('speed', '—')}"
            )
        )
        embed.set_footer(
            text=f"Carta {self.i + 1} de {len(self.cartas_ids)} • Paquete diario de {self.dueño.display_name}"
        )

        if imagen and imagen.startswith("http"):
            embed.set_image(url=imagen)
            return embed, None
        else:
            embed.description += "\n⚠️ Imagen no encontrada."
            return embed, None

    async def actualizar(self):
        embed, archivo = self.mostrar()
        if archivo:
            await self.msg.edit(embed=embed, attachments=[archivo], view=self)
        else:
            await self.msg.edit(embed=embed, view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def atras(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i - 1) % len(self.cartas_ids)
        await self.actualizar()
        await interaction.response.defer()

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i + 1) % len(self.cartas_ids)
        await self.actualizar()
        await interaction.response.defer()
