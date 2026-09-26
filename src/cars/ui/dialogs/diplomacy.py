"""Diplomacy: war and peace with each rival nation."""

import pygame

from cars.sim.diplomacy import RULES, military_strength, quote_peace, quote_war, truce_ends
from cars.ui.dialogs.base import Dialog
from cars.ui.palette import DIM, GOLD, GREEN, HOSTILE

ROW_HEIGHT = 56


class DiplomacyDialog(Dialog):
    title = "Diplomacy"
    seal = "home"

    def rivals(self) -> list[str]:
        return [f for f in self.game.state.factions if f != self.game.campaign.player]

    def layout(self) -> dict[str, pygame.Rect]:
        buttons = {}
        for i, faction in enumerate(self.rivals()):
            buttons[faction] = pygame.Rect(762, 194 + i * ROW_HEIGHT, 170, 32)
        return buttons

    def click(self, faction: str) -> None:
        campaign = self.game.campaign
        if campaign.player is None:
            return
        if self.game.state.at_war(campaign.player, faction):
            _, self.notice = campaign.propose_peace(faction)
        else:
            _, self.notice = campaign.declare_war(faction)

    def draw(self) -> None:
        t = self.theme
        state, player = self.game.state, self.game.campaign.player
        if player is None:
            t.text("Choose a nation first.", 268, 200, t.body)
            return
        own_strength = military_strength(state, player)
        for i, faction in enumerate(self.rivals()):
            top = 185 + i * ROW_HEIGHT
            rival = state.factions[faction]
            pygame.draw.circle(t.screen, rival.color, (286, top + 25), 12)
            pygame.draw.circle(t.screen, GOLD, (286, top + 25), 12, 1)
            t.text(rival.name, 308, top + 6, t.heading, width=260)
            strength = military_strength(state, faction)
            t.text(f"Strength {strength:.0f} against your {own_strength:.0f}", 308, top + 31, t.small, DIM)
            at_war = state.at_war(player, faction)
            if at_war:
                status, color = "At war", HOSTILE
                refusal = quote_peace(state, player, faction)
                label = "Offer peace"
            else:
                ends = truce_ends(state, player, faction)
                truce = f" / truce until round {ends}" if state.round < ends else ""
                status, color = "At peace" + truce, GREEN
                refusal = quote_war(state, player, faction)
                label = "Declare war"
            t.text(status, 580, top + 16, t.body, color, width=170)
            button = self.buttons[faction]
            t.button(button, label, enabled=not refusal)
            if refusal:
                t.hint(button, label, refusal)
        hint = (
            "Peace closes both borders and ends attacks on each other. "
            f"A truce lasts {RULES.truce_rounds} rounds."
        )
        t.text(self.notice or hint, 268, 600, t.small, DIM, width=664)
