"""The window, the active screen and the frame loop."""

import argparse

import pygame

from cars.persist.replay import read_replay_file
from cars.sim.scenario import DETAILED_SCENARIO, load_scenario
from cars.ui.audio import Audio
from cars.ui.context import UiContext
from cars.ui.display import Display
from cars.ui.screens.game import GameScreen
from cars.ui.screens.replay import ReplayScreen
from cars.ui.screens.title import TitleScreen

CAPTION = "C.A.R.S. - Combat Arms Region Simulator"
FRAME_RATE = 60
SMOKE_FRAMES = 3


class App:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.display = Display(args.fullscreen_windowed)
        pygame.display.set_caption(CAPTION)
        audio = Audio()
        self.context = UiContext(self.display.surface, audio)
        self.context.ui.set_font(audio.settings["font"])
        state, shapes, seas = load_scenario(args.scenario or DETAILED_SCENARIO)
        self.game = GameScreen(self.context, state, shapes, seas)
        if args.tutorial:
            self.game.start_tutorial()
        elif args.faction:
            self.game.choose_faction(args.faction)
        self.title = TitleScreen(self.context, self.game)
        self.title.active = not (args.faction or args.tutorial)
        replay = args.replay or args.replay_file
        if replay:
            try:
                self.game.viewer = ReplayScreen(self.context, self.game, read_replay_file(replay))
            except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
                self.title.message = "Could not open replay: " + str(exc)

    def _sync_display(self) -> None:
        self.context.borderless = self.display.borderless
        if self.context.ui.surface is not self.display.surface:
            self.context.set_surface(self.display.surface)

    def _handle(self, event: pygame.event.Event) -> bool:
        """Route one event; returns False to quit."""
        if event.type in (pygame.VIDEORESIZE, pygame.WINDOWSIZECHANGED):
            self.context.set_surface(self.display.surface)
            return True
        alt_enter = (
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_RETURN
            and getattr(event, "mod", 0) & pygame.KMOD_ALT
        )
        if (event.type == pygame.KEYDOWN and event.key == pygame.K_F11) or alt_enter:
            self.context.request_display_toggle()
            return True
        if self.game.viewer:
            return self.game.viewer.event(event)
        if self.title.active:
            return self.title.event(event)
        return self.game.event(event)

    def run(self) -> None:
        clock = pygame.time.Clock()
        running = True
        frames = 0
        while running:
            dt = clock.tick(FRAME_RATE) / 1000
            if self.context.audio:
                self.context.audio.update()
            self._sync_display()
            for event in pygame.event.get():
                running = self._handle(event) and running
            if self.context.display_toggle_requested:
                self.display.toggle()
                self.context.display_toggle_requested = False
                self._sync_display()
            self._draw(dt)
            self.display.present()
            frames += 1
            if self.args.smoke and frames == SMOKE_FRAMES:
                running = False
        if self.args.screenshot:
            pygame.image.save(self.display.surface, str(self.args.screenshot))

    def _draw(self, dt: float) -> None:
        game = self.game
        if self.title.active and game.campaign.player:
            self.title.active = False
        if game.viewer:
            game.viewer.update(dt)
            game.viewer.draw()
        elif self.title.active:
            self.title.draw()
        else:
            game.update(dt)
            game.draw(game.hit(self.context.mouse_pos()))
