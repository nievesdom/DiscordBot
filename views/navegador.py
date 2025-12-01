import discord

# Vista para navegar visualmente por las cartas de un usuario
class Navegador(discord.ui.View):
    def __init__(self, context, cartas_ids, cartas_info, dueño):
        super().__init__(timeout=300)  # La vista expira tras 5 minutos
        self.context = context  # Puede ser Interaction (slash) o Context (prefijo)
        self.cartas_ids = cartas_ids  # Lista de IDs de cartas del usuario
        self.cartas_info = cartas_info  # Diccionario con info de todas las cartas
        self.dueño = dueño  # Usuario dueño de la colección
        self.orden = "original"  # Orden inicial (por fecha)
        self.i = 0  # Índice actual de la carta mostrada
        self.message: discord.Message | None = None  # Mensaje que se enviará y luego se editará

        # Colores por rareza
        self.colores = {
            "UR": 0x8841f2, "KSR": 0xabfbff, "SSR": 0x57ffae,
            "SR": 0xfcb63d, "R": 0xfc3d3d, "N": 0x8c8c8c
        }
        
        # Diccionario de atributos con símbolo japonés
        self.atributos = {
            "heart": "心", "technique": "技", "body": "体",
            "light": "陽", "shadow": "陰"
        }

        # Diccionario de tipos con emoji
        self.tipos = {
            "attack": "⚔️ Attack", "defense": "🛡️ Defense",
            "recovery": "❤️ Recovery", "support": "✨ Support"
        }

    def lista(self):
        """Devuelve la lista de cartas según el orden actual."""
        if self.orden == "alfabetico":
            return sorted(self.cartas_ids, key=lambda cid: self.cartas_info.get(str(cid), {}).get("nombre", "").lower())
        return self.cartas_ids

    def mostrar(self):
        """Construye el embed de la carta actual."""
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

        # Embed con stats
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
        if isinstance(self.context, discord.Interaction):
            # Slash command
            if archivo:
                self.message = await self.context.followup.send(file=archivo, embed=embed, view=self)
            else:
                self.message = await self.context.followup.send(embed=embed, view=self)
        else:
            # Prefijo
            if archivo:
                self.message = await self.context.send(file=archivo, embed=embed, view=self)
            else:
                self.message = await self.context.send(embed=embed, view=self)

    async def actualizar(self):
        """Actualiza el embed mostrado al cambiar de carta u orden."""
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
        self.i = 0
        nuevo_label = "🔤 Order: alphabetic" if self.orden == "alfabetico" else "📆 Order: by date"
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "orden":
                item.label = nuevo_label
        await self.actualizar()
        await interaction.response.defer()
