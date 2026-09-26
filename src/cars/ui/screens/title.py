"""The title screen: new campaign, tutorial, saved games, help and credits."""

from typing import TYPE_CHECKING, ClassVar

import pygame

from cars import __version__
from cars.persist.savegame import SaveLibrary
from cars.ui.art.ornament import branch, crown, fleur
from cars.ui.palette import CANVAS_SIZE, DIM, GOLD, PAPER

if TYPE_CHECKING:
    from cars.ui.context import UiContext
    from cars.ui.screens.game import GameScreen

ACTIONS = ("new", "tutorial", "load", "pedia", "display", "settings", "help", "quit")
HELP_LINES = [
    "Choose a nation, then click one of its regiments.",
    "Hover a highlighted province to preview a route; click to move or attack.",
    "Right-click a province to develop roads, resources and military facilities.",
    "Recruit land forces, fleets and air groups from controlled cities.",
    "End Turn collects resources and lets the other seven nations act.",
    "Hold three cities for five full seasonal rounds. T opens the calendar.",
    "",
    "N: next ready / F: focus / U: military overview / M: market",
    "F5: save slots / F9: load / J: reports / F10: sound / F11: fullscreen",
    "",
    "Original procedural artwork and interface. Natural Earth map data.",
    "Built with Python and pygame-ce. See MAP_SOURCES.md for credits.",
    "Air: choose Strike, Support or Rebase. Fleets fight enemy fleets on entry.",
    "",
    "Click anywhere or press Esc to return.",
]
CREDIT_LINES_FROM = 10  # Help lines from here on are dimmed credits.
RELEASE = ".".join(__version__.split(".")[:2])
# The backdrop map is a fixed equirectangular sketch of the Americas.
BACKDROP_ORIGIN = (780, 405)
BACKDROP_SCALE = 4.5
MENU_CENTER_X = 930


class TitleScreen:
    buttons: ClassVar[dict] = {
        name: pygame.Rect(765, 338 + i * 37, 330, 31) for i, name in enumerate(ACTIONS)
    }

    def __init__(self, context: "UiContext", game: "GameScreen") -> None:
        self.context = context
        self.game = game
        self.library = SaveLibrary()
        self.active = True
        self.help = False
        self.message = ""
        self.backdrop = self._draw_backdrop(game.renderer.map.geometry)

    @staticmethod
    def _draw_backdrop(geometry: dict) -> pygame.Surface:
        backdrop = pygame.Surface(CANVAS_SIZE)
        backdrop.fill((23, 39, 45))
        for x in range(0, CANVAS_SIZE[0], 80):
            pygame.draw.line(backdrop, (35, 51, 54), (x, 0), (x, CANVAS_SIZE[1]))
        for y in range(0, CANVAS_SIZE[1], 65):
            pygame.draw.line(backdrop, (35, 51, 54), (0, y), (CANVAS_SIZE[0], y))
        origin_x, origin_y = BACKDROP_ORIGIN
        for polygons in geometry.values():
            for rings in polygons:
                points = [
                    (int(origin_x + lon * BACKDROP_SCALE), int(origin_y - lat * BACKDROP_SCALE))
                    for lon, lat in rings[0]
                ]
                pygame.draw.polygon(backdrop, (107, 99, 74), points)
                pygame.draw.lines(backdrop, (62, 66, 57), True, points, 1)
        branch(backdrop, (130, 741), 1, 180)
        fleur(backdrop, (1060, 115), 70)
        return backdrop

    def event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        dialogs = self.game.dialogs
        if dialogs.mode:
            return dialogs.event(event)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.help = False
        action = None
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
            action = "pedia"
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            action = "help" if self.help else "new"
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.help:
                self.help = False
                return True
            action = next((name for name, rect in self.buttons.items() if rect.collidepoint(event.pos)), None)
        return self._perform(action)

    def _perform(self, action: str | None) -> bool:
        dialogs = self.game.dialogs
        if action == "new":
            self.active = False
        elif action == "tutorial":
            self.game.start_tutorial()
            self.active = False
        elif action == "pedia":
            dialogs.open("pedia")
        elif action == "load" and self.library.has_save():
            dialogs.open("load")
        elif action == "settings":
            dialogs.open("settings")
        elif action == "display":
            self.context.request_display_toggle()
        elif action == "help":
            self.help = not self.help
        elif action == "quit":
            return False
        return True

    def draw(self) -> None:
        t = self.context.theme
        screen = t.screen
        screen.blit(self.backdrop, (0, 0))
        t.dim_screen((12, 18, 25, 115))
        t.text("THE AMERICAS", 130, 648, t.font(42), GOLD)
        t.text("An atlas of provinces, pathways and ambition.", 130, 701, t.heading, DIM)
        t.panel((690, 75, 480, 640))
        crown(screen, (MENU_CENTER_X, 130), 64)
        branch(screen, (875, 145), -1, 105)
        branch(screen, (985, 145), 1, 105)
        for x in (721, 1139):
            fleur(screen, (x, 385), 28)
        t.centered("C.A.R.S.", MENU_CENTER_X, 183, t.font(66), GOLD)
        t.centered("COMBAT ARMS REGION SIMULATOR", MENU_CENTER_X, 269, t.heading)
        t.centered("An atlas of ambition. A world to command.", MENU_CENTER_X, 309, t.body, DIM)
        has_save = self.library.has_save()
        display = "Windowed" if self.context.borderless else "Fullscreen Windowed"
        labels = {
            "new": "Start Campaign / Enter",
            "tutorial": "Guided Tutorial",
            "load": "Continue Saved Campaign",
            "pedia": "CARSapedia",
            "display": display + " / F11",
            "settings": "Sound & Preferences",
            "help": "How to Play & Credits",
            "quit": "Quit",
        }
        for name, rect in self.buttons.items():
            t.button(rect, labels[name], enabled=name != "load" or has_save)
        t.centered("Eight nations / One Americas", MENU_CENTER_X, 657, t.body, GOLD)
        t.centered(f"Prototype {RELEASE} / Choose your realm", MENU_CENTER_X, 682, t.small, DIM)
        if self.message:
            t.text(self.message, 702, 716, t.body, width=516)
        if self.help:
            self._draw_help()

    def _draw_help(self) -> None:
        t = self.context.theme
        t.panel((250, 142, 700, 508))
        t.text("Your first campaign", 282, 166, t.serif)
        for i, line in enumerate(HELP_LINES):
            color = DIM if i >= CREDIT_LINES_FROM else PAPER
            t.text(line, 282, 212 + i * 27, t.body, color, width=638)
