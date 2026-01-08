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
    Vista para que un jugador elija una carta de su mazo.
    deck_cards: lista de IDs de cartas (str).
    used_indices: índices ya usados en esta partida.
    Llama a on_choose(interaction, index, card_id).
    """
    def __init__(
        self,
        player: discord.Member,
        deck_cards: List[str],
        cartas_info: Dict[str, Dict],
        used_indices: set[int],
        on_choose: Callable[[discord.Interaction, int, str], None]
    ):
        super().__init__(timeout=120)
        self.player = player
        self.deck_cards = deck_cards
        self.cartas_info = cartas_info
        self.used_indices = used_indices
        self.on_choose = on_choose

        for idx, cid in enumerate(deck_cards):
            if idx in used_indices:
                continue
            info = cartas_info.get(str(cid), {})
            nombre = info.get("nombre", f"ID {cid}")
            self.add_item(CardButton(idx, str(cid), nombre))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.player.id


class CardButton(discord.ui.Button):
    def __init__(self, index: int, card_id: str, nombre: str):
        label = nombre if len(nombre) <= 80 else nombre[:77] + "..."
        super().__init__(label=label, style=discord.ButtonStyle.secondary)
        self.index = index
        self.card_id = card_id

    async def callback(self, interaction: discord.Interaction):
        view: ChooseCardView = self.view  # type: ignore
        await view.on_choose(interaction, self.index, self.card_id)
        view.stop()
