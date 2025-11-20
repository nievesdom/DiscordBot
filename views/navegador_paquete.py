import discord

# Navegar visualmente por las cartas de un paquete diario
class NavegadorPaquete(discord.ui.View):
    def __init__(self, ctx, cartas_ids, cartas_info, dueño):
        super().__init__(timeout=180)  # La vista expira tras 2 minutos
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

        # Diccionario de atributos con símbolo japonés
        self.atributos = {
            "heart": "心",
            "technique": "技",
            "body": "体",
            "light": "陽",
            "shadow": "陰"
        }

        # Diccionario de tipos con emoji
        self.tipos = {
            "attack": "⚔️ Attack",
            "defense": "🛡️ Defense",
            "recovery": "❤️ Recovery",
            "support": "✨ Support"
        }

    def mostrar(self):
        carta_id = str(self.cartas_ids[self.i])
        carta = self.cartas_info.get(carta_id, {})
        nombre = carta.get("nombre", f"ID {carta_id}")
        rareza = carta.get("rareza", "N")
        color = self.colores.get(rareza, 0x8c8c8c)
        imagen = carta.get("imagen")

        # Formato de atributo y tipo
        atributo_raw = str(carta.get("atributo", "—")).lower()
        tipo_raw = str(carta.get("tipo", "—")).lower()

        attr_symbol = self.atributos.get(atributo_raw, "")
        attr_name = atributo_raw.capitalize() if atributo_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name

        tipo_fmt = self.tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

        # Crear embed
        embed = discord.Embed(
            title=f"{nombre}",
            color=color,
            description=(
                f"**Attribute:** {atributo_fmt}\n"
                f"**Type:** {tipo_fmt}\n"
                f"❤️ {carta.get('health', '—')} | ⚔️ {carta.get('attack', '—')} | "
                f"🛡️ {carta.get('defense', '—')} | 💨 {carta.get('speed', '—')}"
            )
        )
        # Footer del embed
        embed.set_footer(
            text=f"Card {self.i + 1} out of {len(self.cartas_ids)} • {self.dueño.display_name}'s daily pack"
        )

        # Comprobar que la imagen existe
        if imagen and imagen.startswith("http"):
            embed.set_image(url=imagen)
            return embed, None
        else:
            embed.description += "\n⚠️ Card image not found. Please, contact my creator."
            return embed, None

    # Actualizar vista
    async def actualizar(self):
        embed, archivo = self.mostrar()
        if archivo:
            await self.msg.edit(embed=embed, attachments=[archivo], view=self)
        else:
            await self.msg.edit(embed=embed, view=self)

    # Botón anterior
    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def atras(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i - 1) % len(self.cartas_ids)
        await self.actualizar()
        await interaction.response.defer()

    # Botón siguiente
    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i + 1) % len(self.cartas_ids)
        await self.actualizar()
        await interaction.response.defer()
