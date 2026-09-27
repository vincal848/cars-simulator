"""Read-only replay playback on its own copy of the campaign; the live game stays paused."""

from typing import TYPE_CHECKING

import pygame

from cars.persist.replay import Playback
from cars.sim.campaign import Campaign
from cars.ui.kit import style
from cars.ui.renderer import GameRenderer, ViewState

if TYPE_CHECKING:
    from cars.ui.context import UiContext
    from cars.ui.screens.game import GameScreen

STEP_SECONDS = 0.8
ACTIONS = ("play", "step", "restart", "exit")
KEYS = {pygame.K_ESCAPE: "exit", pygame.K_SPACE: "play", pygame.K_RIGHT: "step", pygame.K_HOME: "restart"}
SIZE = (560, 150)


class ReplayScreen:
    def __init__(self, context: "UiContext", game: "GameScreen", data: dict) -> None:
        self.context = context
        self.game = game
        self.playback = Playback(data)
        self.view = ViewState(message="Paused. This replay is read-only.")
        self.playing = False
        self.timer = 0.0
        self.buttons: dict[str, pygame.Rect] = {}
        self._bind()

    def _bind(self) -> None:
        playback = self.playback
        campaign = Campaign(playback.state)
        campaign.player = playback.player
        self.renderer = GameRenderer(self.context, playback.state, playback.shapes, playback.seas, campaign)
        self.renderer.fog = False  # Replays are watched as an observer.
        self.renderer.interactive = False

    def step(self) -> None:
        if self.playback.failed:
            self.playing = False
            return
        try:
            advanced = self.playback.step()
        except ValueError as exc:
            self.playing = False
            self.view.message = str(exc)
            return
        if not advanced:
            self.playing = False
            self.view.message = "Replay complete. Every command matched."
            return
        self.renderer.set_state(self.playback.state)
        self.view.message = self.playback.message

    def restart(self) -> None:
        self.playback.reset()
        self._bind()
        self.playing = False
        self.view.message = "Replay restarted."

    def update(self, dt: float) -> None:
        self.renderer.toasts.update(dt)
        if not self.playing:
            return
        self.timer += dt
        if self.timer >= STEP_SECONDS:
            self.timer = 0
            self.step()

    def event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        action = None
        if event.type == pygame.KEYDOWN:
            action = KEYS.get(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            action = next((name for name, rect in self.buttons.items() if rect.collidepoint(event.pos)), None)
        elif event.type == pygame.MOUSEWHEEL:
            self.renderer.map.zoom(1.2**event.y, self.context.mouse_pos())
        elif event.type == pygame.MOUSEMOTION and event.buttons[0]:
            self.renderer.map.pan(*event.rel, dragging=True)
        if action == "exit":
            self.game.viewer = None
        elif action == "play":
            self.playing = not self.playing
        elif action == "step":
            self.playing = False
            self.step()
        elif action == "restart":
            self.restart()
        return True

    def draw(self) -> None:
        ui = self.context.ui
        self.renderer.draw(self.view, None)
        rect = pygame.Rect(ui.px(16), 0, ui.px(SIZE[0]), ui.px(SIZE[1]))
        rect.bottom = ui.screen.bottom - ui.px(16)
        inner = ui.panel(rect, "Campaign replay · read-only", "end")
        playback = self.playback
        ui.text(
            f"Command {playback.index} of {len(playback.commands)}",
            (inner.x, inner.y),
            style.HEADING,
            style.SLATE,
            bold=True,
        )
        ui.text(
            self.view.message, (inner.x, inner.y + ui.px(24)), style.BODY, style.INK_MUTED, width=inner.width
        )
        width = (inner.width - ui.px(18)) // len(ACTIONS)
        self.buttons = {}
        for i, action in enumerate(ACTIONS):
            button = pygame.Rect(inner.x + i * (width + ui.px(6)), inner.bottom - ui.px(34), width, ui.px(34))
            label = ("Pause" if self.playing else "Play") if action == "play" else action.title()
            ui.button(button, label, kind="primary" if action == "play" else "secondary")
            self.buttons[action] = button
        ui.tips.draw(ui)
