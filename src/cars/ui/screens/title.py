"""The title screen: the continent as the campaign begins, and the ways into it."""

from typing import TYPE_CHECKING

import pygame

from cars import __version__
from cars.paths import active_mods
from cars.persist.savegame import SaveLibrary
from cars.ui.art.paintings import TITLE, painting
from cars.ui.kit import style
from cars.ui.map.map_view import Scene

if TYPE_CHECKING:
    from cars.ui.context import UiContext
    from cars.ui.screens.game import GameScreen

# (action, label)
ACTIONS = (
    ("new", "Start a campaign"),
    ("tutorial", "Guided tutorial"),
    ("load", "Continue a saved campaign"),
    ("pedia", "CARSapedia"),
    ("settings", "Settings"),
    ("quit", "Quit"),
)
KEYS = {pygame.K_RETURN: "new", pygame.K_F1: "pedia", pygame.K_F9: "load", pygame.K_F10: "settings"}
RELEASE = ".".join(__version__.split(".")[:2])
MENU_WIDTH = 380
BACKDROP_VEIL = (14, 20, 26, 120)


class TitleScreen:
    def __init__(self, context: "UiContext", game: "GameScreen") -> None:
        self.context = context
        self.game = game
        self.library = SaveLibrary()
        self.active = True
        self.message = ""
        self.buttons: dict[str, pygame.Rect] = {}

    @property
    def window(self):
        """A window opened from the title screen (the nation picker waits for the campaign)."""
        window = self.game.window
        return window if window is not None and getattr(window, "name", "") != "picker" else None

    def event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if self.window is not None:
            self.window.handle(event)
            return True
        action = None
        if event.type == pygame.KEYDOWN:
            action = KEYS.get(event.key)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = next((name for name, rect in self.buttons.items() if rect.collidepoint(event.pos)), None)
        return self._perform(action)

    def _perform(self, action: str | None) -> bool:
        game = self.game
        if action == "new":
            self.active = False
        elif action == "tutorial":
            game.start_tutorial()
            self.active = False
        elif action == "load" and self.library.has_save():
            game.open_window("load")
        elif action in ("pedia", "settings"):
            game.open_window(action)
        elif action == "quit":
            return False
        return True

    def draw(self) -> None:
        ui = self.context.ui
        backdrop = painting(TITLE, "backdrop", ui.screen.size)
        if backdrop:
            ui.surface.blit(backdrop, (0, 0))
        else:
            self.game.renderer.map.draw(ui.surface, Scene(), [], [])
        ui.veil(BACKDROP_VEIL)
        self._title(ui)
        self._menu(ui)
        if self.window is not None:
            ui.tips.begin()
            self.window.draw()
        ui.tips.draw(ui)

    def _title(self, ui) -> None:
        x, y = ui.px(48), ui.px(40)
        font = ui.font(64, bold=True)
        ui.surface.blit(font.render("C.A.R.S.", True, style.SHADOW), (x + ui.px(3), y + ui.px(3)))
        title = ui.surface.blit(font.render("C.A.R.S.", True, style.ON_SLATE), (x, y))
        y = title.bottom
        ui.text(
            "COMBAT ARMS REGION SIMULATOR", (x + ui.px(4), y), style.HEADING, style.BRASS_LIGHT, bold=True
        )
        ui.text(
            "Eight nations. One continent. The Americas, 1836.",
            (x + ui.px(4), y + ui.px(30)),
            style.BODY,
            style.ON_SLATE,
        )

    def _menu(self, ui) -> None:
        screen = ui.screen
        height = ui.px(40) + len(ACTIONS) * ui.px(48) + ui.px(60 if active_mods() else 44)
        rect = pygame.Rect(0, 0, ui.px(MENU_WIDTH), height)
        rect.midright = (screen.right - ui.px(48), screen.centery)
        inner = ui.panel(rect, "Command", "nation")
        has_save = self.library.has_save()
        self.buttons = {}
        for i, (action, label) in enumerate(ACTIONS):
            button = pygame.Rect(inner.x, inner.y + i * ui.px(48), inner.width, ui.px(40))
            enabled = action != "load" or has_save
            ui.button(button, label, kind="primary" if action == "new" else "secondary", enabled=enabled)
            if enabled:
                self.buttons[action] = button
        footer = inner.y + len(ACTIONS) * ui.px(48) + ui.px(8)
        ui.text(
            f"Version {RELEASE}  ·  Enter starts a campaign", (inner.x, footer), style.SMALL, style.INK_MUTED
        )
        mods = active_mods()
        if mods:
            names = ", ".join(mod.name for mod in mods)
            ui.text(
                "Mods: " + names, (inner.x, footer + ui.px(22)), style.SMALL, style.SLATE, width=inner.width
            )
        if self.message:
            ui.text(self.message, (inner.x, footer + ui.px(44)), style.SMALL, style.BAD, width=inner.width)
