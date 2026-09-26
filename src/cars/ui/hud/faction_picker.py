"""Choosing a nation at the start of a campaign."""

from typing import TYPE_CHECKING

import pygame

from cars.sim.entities import AIR
from cars.ui.art.ornament import branch, fleur
from cars.ui.art.regiments import DEFAULT_UNIFORM, UNIFORMS
from cars.ui.palette import DIM, GOLD

if TYPE_CHECKING:
    from cars.sim.state import GameState
    from cars.ui.theme import Theme


class FactionPicker:
    def __init__(self, theme: "Theme", factions: list[str]) -> None:
        self.theme = theme
        self.buttons = {
            faction: pygame.Rect(170 + (i % 2) * 440, 204 + (i // 2) * 112, 420, 94)
            for i, faction in enumerate(factions)
        }

    def faction_at(self, point) -> str | None:
        return next((faction for faction, rect in self.buttons.items() if rect.collidepoint(point)), None)

    def draw(self, state: "GameState") -> None:
        t = self.theme
        t.dim_screen((5, 12, 18, 215))
        t.panel((144, 134, 912, 546))
        t.text("Choose your nation", 180, 151, t.serif)
        t.text("F9 / Resume saved campaign", 180, 651, t.small, GOLD)
        branch(t.screen, (865, 162), -1, 120)
        fleur(t.screen, (897, 160), 26)
        branch(t.screen, (929, 162), 1, 96)
        t.text("Command one faction. Seven rivals take their turns automatically.", 180, 183, t.body, DIM)
        for i, (faction_id, rect) in enumerate(self.buttons.items()):
            faction = state.factions[faction_id]
            t.panel(rect, rect.collidepoint(t.mouse_pos()))
            t.shield(rect.x + 15, rect.y + 17, faction.color)
            t.text(f"{i + 1}. {faction.name}", rect.x + 72, rect.y + 16, t.heading, width=332)
            provinces = sum(p.controller == faction_id for p in state.provinces.values())
            t.text(f"{provinces} provinces / Infantry command", rect.x + 73, rect.y + 45, t.small, DIM)
            has_air = any(u.owner == faction_id and u.kind == AIR for u in state.units.values())
            forces = "Includes fleet & air group" if has_air else "Land forces"
            culture = UNIFORMS.get(faction.style, UNIFORMS[DEFAULT_UNIFORM])["name"]
            t.text(culture + " / " + forces, rect.x + 73, rect.y + 65, t.small, GOLD, width=332)
