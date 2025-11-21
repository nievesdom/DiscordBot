import discord

# Navegar visualmente por las cartas de un usuario
class Navegador(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, cartas_ids, cartas_info, dueño):
        super().__init__(timeout=180)  # La vista expira tras 3 minutos
        self.interaction = interaction
        self.cartas_ids = cartas_ids
        self.cartas_info = cartas_info
        self.dueño = dueño
        self.orden = "original"
        self.i = 0
        self.message: discord.Message | None = None  # mensaje que se enviará y luego se editará

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

    def lista(self):
        if self.orden == "alfabetico":
            return sorted(self.cartas_ids, key=lambda cid: self.cartas_info.get(str(cid), {}).get("nombre", "").lower())
        return self.cartas_ids

    def mostrar(self):
        lista_actual = self.lista()
        carta_id = str(lista_actual[self.i])
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
        embed.set_footer(text=f"Card {self.i + 1} out of {len(lista_actual)} • {self.dueño.display_name}'s album")

        if imagen and imagen.startswith("http"):
            embed.set_image(url=imagen)
        else:
            embed.description += "\n⚠️ Image not found. Please, contact my creator."

        return embed, None

    async def enviar(self):
        """Envía el primer embed y guarda el mensaje para futuras ediciones."""
        embed, archivo = self.mostrar()
        if archivo:
            self.message = await self.interaction.followup.send(file=archivo, embed=embed, view=self)
        else:
            self.message = await self.interaction.followup.send(embed=embed, view=self)

    async def actualizar(self):
        lista_actual = self.lista()
        if self.i >= len(lista_actual):
            self.i = 0
        embed, archivo = self.mostrar()
        if self.message:
            if archivo:
                await self.message.edit(embed=embed, attachments=[archivo], view=self)
            else:
                await self.message.edit(embed=embed, view=self)

    # Botón para ir a la carta anterior
    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def atras(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i - 1) % len(self.lista())
        await self.actualizar()
        await interaction.response.defer()

    # Botón para ir a la carta siguiente
    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i + 1) % len(self.lista())
        await self.actualizar()
        await interaction.response.defer()

    # Botón para cambiar el orden de visualización
    @discord.ui.button(label="📆 Order: by date", style=discord.ButtonStyle.primary, custom_id="orden")
    async def cambiar(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.orden = "alfabetico" if self.orden == "original" else "original"
        self.i = 0  # Reiniciar índice
        nuevo_label = "🔤 Order: alphabetic" if self.orden == "alfabetico" else "📆 Order: by date"
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "orden":
                item.label = nuevo_label
        await self.actualizar()
        await interaction.response.defer()
