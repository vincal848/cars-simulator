"""Read-only replay playback on its own copy of the campaign; the live game stays paused."""

from typing import TYPE_CHECKING

import pygame

from cars.persist.replay import Playback
from cars.sim.campaign import Campaign
from cars.ui.renderer import GameRenderer, ViewState

if TYPE_CHECKING:
    from cars.ui.context import UiContext
    from cars.ui.screens.game import GameScreen

STEP_SECONDS = 0.8
BUTTONS = {
    name: pygame.Rect(22 + i * 143, 632, 134, 34)
    for i, name in enumerate(("play", "step", "restart", "exit"))
}
KEYS = {pygame.K_ESCAPE: "exit", pygame.K_SPACE: "play", pygame.K_RIGHT: "step", pygame.K_HOME: "restart"}


class ReplayScreen:
    def __init__(self, context: "UiContext", game: "GameScreen", data: dict) -> None:
        self.context = context
        self.game = game
        self.playback = Playback(data)
        self.view = ViewState(message="Paused / verified command replay")
        self.playing = False
        self.timer = 0.0
        self._bind()

    def _bind(self) -> None:
        playback = self.playback
        campaign = Campaign(playback.state)
        campaign.player = playback.player
        self.renderer = GameRenderer(self.context, playback.state, playback.shapes, playback.seas, campaign)
        self.renderer.fog = False  # Replays are watched as an observer.

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
        state = self.playback.state
        self.renderer.set_state(state)
        # Show the layer of the unit the command moved, if any.
        command = self.playback.commands[self.playback.index - 1]
        unit = state.units.get(command["args"][0]) if command["args"] else None
        self.view.layer = unit.layer if unit else "land"
        self.view.message = self.playback.message

    def restart(self) -> None:
        self.playback.reset()
        self._bind()
        self.view.layer = "land"
        self.playing = False
        self.view.message = "Replay restarted."

    def update(self, dt: float) -> None:
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
            action = next((name for name, rect in BUTTONS.items() if rect.collidepoint(event.pos)), None)
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
        t = self.context.theme
        self.renderer.draw(self.view, None)
        t.tips.draw(t)
        t.panel((16, 547, 584, 127), True)
        t.text("CAMPAIGN REPLAY / READ ONLY", 30, 559, t.heading)
        t.text(f"Command {self.playback.index} of {len(self.playback.commands)}", 30, 587, t.body)
        t.text("Space: play/pause / Right: step / Home: restart / Esc: return", 30, 610, t.small)
        for name, rect in BUTTONS.items():
            label = ("Pause" if self.playing else "Play") if name == "play" else name.title()
            t.button(rect, label)
