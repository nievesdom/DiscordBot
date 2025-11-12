import discord

# Navegar visualmente por las cartas de un paquete diario
class NavegadorPaquete(discord.ui.View):
    def __init__(self, ctx, cartas_ids, cartas_info, dueño):
        super().__init__(timeout=120)  # La vista expira tras 2 minutos
        self.ctx = ctx
        self.cartas_ids = cartas_ids  # Lista de IDs de cartas del paquete
        self.cartas_info = cartas_info  # Diccionario con info de cada carta
        self.dueño = dueño  # Usuario dueño del paquete
        self.i = 0  # Índice de la carta actual
        self.msg = None  # Mensaje que contiene el embed

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
                f"**Attribute:** {carta.get('atributo', '—')}\n"
                f"**Type:** {carta.get('tipo', '—')}\n"
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
