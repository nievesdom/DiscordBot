# views/battle_views.py

import discord
from typing import Callable, Dict, List, Optional


class AcceptDuelView(discord.ui.View):
    """
    Vista para que el jugador retado acepte o rechace el combate.
    Llama a on_decision(interaction, accepted: bool).
    """
    def __init__(self, on_decision: Callable[[discord.Interaction, bool], None]):
        super().__init__(timeout=120)
        self.on_decision = on_decision

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.on_decision(interaction, True)
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.on_decision(interaction, False)
        self.stop()


class ChooseDeckView(discord.ui.View):
    """
    Vista para que un jugador elija el mazo con el que jugar.
    available_decks: lista de letras ["A", "B", "C"].
    Llama a on_choose(interaction, letra_mazo).
    """
    def __init__(
        self,
        player: discord.Member,
        available_decks: List[str],
        on_choose: Callable[[discord.Interaction, str], None]
    ):
        super().__init__(timeout=120)
        self.player = player
        self.on_choose = on_choose

        for letra in available_decks:
            self.add_item(DeckButton(letra))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.player.id


class DeckButton(discord.ui.Button):
    def __init__(self, letra: str):
        super().__init__(label=f"Deck {letra}", style=discord.ButtonStyle.primary)
        self.letra = letra

    async def callback(self, interaction: discord.Interaction):
        view: ChooseDeckView = self.view  # type: ignore
        await view.on_choose(interaction, self.letra)
        view.stop()


class ChooseCardView(discord.ui.View):
    """
    Vista avanzada para elegir una carta:
    - Embed estilo NavegadorMazo
    - Botones de navegación
    - Botón para jugar la carta
    - Select Menu para elegir directamente
    """
    def __init__(
        self,
        player: discord.Member,
        deck_cards: List[str],
        cartas_info: Dict[str, Dict],
        used_indices: set[int],
        on_choose: Callable[[discord.Interaction, int, str], None]
    ):
        super().__init__(timeout=180)
        self.player = player
        self.deck_cards = deck_cards
        self.cartas_info = cartas_info
        self.used_indices = used_indices
        self.on_choose = on_choose

        # Lista de índices disponibles
        self.indices = [i for i in range(len(deck_cards)) if i not in used_indices]
        self.i = 0  # índice actual

        # Añadir select menu
        self.add_item(ElegirCartaSelect(self))

    def _embed_actual(self):
        """Genera el embed estilo NavegadorMazo."""
        idx = self.indices[self.i]
        cid = str(self.deck_cards[idx])
        carta = self.cartas_info.get(cid, {})

        nombre = carta.get("nombre", f"ID {cid}")
        rareza = carta.get("rareza", "N")
        imagen = carta.get("imagen")

        colores = {
            "UR": 0x8841f2, "KSR": 0xabfbff, "SSR": 0x57ffae,
            "SR": 0xfcb63d, "R": 0xfc3d3d, "N": 0x8c8c8c
        }
        atributos = {
            "heart": "心", "technique": "技", "body": "体",
            "light": "陽", "shadow": "陰"
        }
        tipos = {
            "attack": "⚔️ Attack", "defense": "🛡️ Defense",
            "recovery": "❤️ Recovery", "support": "✨ Support"
        }

        color = colores.get(rareza, 0x8c8c8c)

        atributo_raw = str(carta.get("atributo", "—")).lower()
        tipo_raw = str(carta.get("tipo", "—")).lower()
        attr_symbol = atributos.get(atributo_raw, "")
        attr_name = atributo_raw.capitalize() if atributo_raw != "—" else "—"
        atributo_fmt = f"{attr_symbol} {attr_name}" if attr_symbol else attr_name
        tipo_fmt = tipos.get(tipo_raw, tipo_raw.capitalize() if tipo_raw != "—" else "—")

        embed = discord.Embed(
            title=nombre,
            color=color,
            description=(
                f"**Attribute:** {atributo_fmt}\n"
                f"**Type:** {tipo_fmt}\n"
                f"❤️ {carta.get('health', '—')} | "
                f"⚔️ {carta.get('attack', '—')} | "
                f"🛡️ {carta.get('defense', '—')} | "
                f"💨 {carta.get('speed', '—')}"
            )
        )

        embed.set_footer(
            text=f"Card {self.i + 1} of {len(self.indices)} • {self.player.display_name}"
        )

        if imagen and str(imagen).startswith("http"):
            embed.set_image(url=imagen)

        return embed

    async def enviar(self, interaction: discord.Interaction):
        embed = self._embed_actual()
        await interaction.followup.send(embed=embed, view=self, ephemeral=True)

    async def actualizar(self, interaction: discord.Interaction):
        embed = self._embed_actual()
        await interaction.response.edit_message(embed=embed, view=self)

    # -------------------------
    # Botones de navegación
    # -------------------------

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def atras(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i - 1) % len(self.indices)
        await self.actualizar(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.i = (self.i + 1) % len(self.indices)
        await self.actualizar(interaction)

    # -------------------------
    # Botón para jugar carta
    # -------------------------

    @discord.ui.button(label="Jugar esta carta", style=discord.ButtonStyle.success)
    async def jugar(self, interaction: discord.Interaction, button: discord.ui.Button):
        idx = self.indices[self.i]
        cid = str(self.deck_cards[idx])
        await self.on_choose(interaction, idx, cid)
        self.stop()


class ElegirCartaSelect(discord.ui.Select):
    """Select menu para elegir carta directamente."""
    def __init__(self, view: ElegirCartaView):
        self.view_ref = view

        opciones = []
        for idx in view.indices:
            cid = str(view.deck_cards[idx])
            carta = view.cartas_info.get(cid, {})
            nombre = carta.get("nombre", f"ID {cid}")
            opciones.append(
                discord.SelectOption(
                    label=nombre[:80],
                    value=str(idx)
                )
            )

        super().__init__(
            placeholder="Selecciona una carta...",
            min_values=1,
            max_values=1,
            options=opciones
        )

    async def callback(self, interaction: discord.Interaction):
        idx = int(self.values[0])
        self.view_ref.i = self.view_ref.indices.index(idx)
        await self.view_ref.actualizar(interaction)

