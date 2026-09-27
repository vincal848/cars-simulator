"""Choosing a nation: every nation in a list, with the selected one's history and traits."""

import pygame

from cars.sim.entities import BALLOON, FLEET
from cars.sim.nations import NATIONS
from cars.sim.objectives import controlled_cities
from cars.ui.frames import Window
from cars.ui.kit import style
from cars.ui.kit.grid import draw_grid, facts, section

LIST_WIDTH = 330


class PickerWindow(Window):
    name = "picker"
    title = "Choose your nation"
    icon = "nation"
    closable = False
    size = (1080, 700)

    def __init__(self, game) -> None:
        super().__init__(game)
        self.choice = next(iter(game.state.factions))

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        state = self.state
        listing = pygame.Rect(rect.x, rect.y, ui.px(LIST_WIDTH), rect.height)
        row_height = ui.px(64)
        for i, faction_id in enumerate(state.factions):
            faction = state.factions[faction_id]
            row = pygame.Rect(listing.x, listing.y + i * (row_height + ui.px(6)), listing.width, row_height)
            ui.inset(
                row,
                style.SELECTED_ROW
                if faction_id == self.choice
                else style.PANEL_DARK
                if ui.hovered(row)
                else style.PANEL_LIGHT,
            )
            ui.swatch((row.x + ui.px(20), row.centery), faction.color, 11)
            ui.text(
                faction.name,
                (row.x + ui.px(40), row.y + ui.px(10)),
                style.HEADING,
                style.INK,
                bold=True,
                width=row.width - ui.px(50),
            )
            provinces = sum(p.controller == faction_id for p in state.provinces.values())
            cities = len(controlled_cities(state, faction_id))
            ui.text(
                f"{provinces} provinces · {cities} cities",
                (row.x + ui.px(40), row.y + ui.px(36)),
                style.SMALL,
                style.INK_MUTED,
            )
            self.clickable(row, "choose:" + faction_id)
        detail = pygame.Rect(
            listing.right + ui.px(24), rect.y, rect.right - listing.right - ui.px(24), rect.height
        )
        self._detail(ui, detail)
        return rect.height

    def _detail(self, ui, rect: pygame.Rect) -> None:
        state = self.state
        faction = state.factions[self.choice]
        nation = NATIONS.get(self.choice)
        x, y, width = rect.x, rect.y, rect.width
        ui.text(faction.name, (x, y), style.TITLE + 4, style.SLATE, bold=True)
        y += ui.px(40)
        if nation:
            ui.text(f"“{nation.motto}”", (x, y), style.BODY, style.INK_MUTED, italic=True)
            y += ui.px(28)
            units = [u for u in state.units.values() if u.owner == self.choice]
            forces = f"{sum(u.is_land for u in units)} armies"
            if any(u.kind == FLEET for u in units):
                forces += ", a fleet"
            if any(u.kind == BALLOON for u in units):
                forces += ", a balloon corps"
            y += facts(
                ui,
                x,
                y,
                width,
                [
                    ("Ruler", nation.ruler),
                    ("Capital", nation.capital),
                    ("Government", nation.government),
                    ("Forces", forces),
                ],
            )
            y += ui.px(4)
            y += section(ui, "History", x, y, width)
            for paragraph in nation.history[:2]:
                y += ui.paragraph(paragraph, pygame.Rect(x, y, width, ui.px(160)), style.BODY) + ui.px(8)
            y += section(ui, "National traits", x, y, width)
            rows = [[(trait.name, style.SLATE), trait.effect] for trait in nation.traits]
            y += draw_grid(ui, x, y, width, [("Trait", 160, "left"), ("Effect", None, "left")], rows)
        button = pygame.Rect(rect.right - ui.px(260), rect.bottom - ui.px(44), ui.px(260), ui.px(44))
        self.button(button, f"Lead {faction.name}", "start", kind="primary")

    def handle_other(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN:
            factions = list(self.state.factions)
            if pygame.K_1 <= event.key <= pygame.K_8:
                self.choice = factions[event.key - pygame.K_1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.game.choose_faction(self.choice)
            elif event.key == pygame.K_F9:
                self.game.open_window("load")
            elif event.key in (pygame.K_UP, pygame.K_DOWN):
                index = factions.index(self.choice) + (1 if event.key == pygame.K_DOWN else -1)
                self.choice = factions[index % len(factions)]
            return True
        return False

    def act(self, action: str) -> None:
        verb, _, value = action.partition(":")
        if verb == "choose":
            self.choice = value
        elif verb == "start":
            self.game.choose_faction(self.choice)
