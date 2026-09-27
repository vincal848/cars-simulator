"""Replay studio: watch or export this session's verified command recording."""

import pygame

from cars.persist.replay import latest_export_path, read_replay_file
from cars.ui.frames import Window
from cars.ui.kit import style

ACTIONS = (("watch", "Watch this session"), ("export", "Export recording"), ("latest", "Open latest export"))


class ReplayWindow(Window):
    name = "replay"
    title = "Replay studio"
    icon = "end"
    fit_content = True
    size = (640, 440)

    def draw_body(self, ui, rect: pygame.Rect) -> int:
        recorder = self.game.campaign.recorder
        commands = len(recorder.commands) if recorder else 0
        x, y, width = rect.x, rect.y, rect.width
        ui.text(f"{commands} commands recorded this session", (x, y), style.HEADING, style.SLATE, bold=True)
        y += ui.px(34)
        for paragraph in (
            "A replay runs in a separate, read-only copy of the campaign and checks every command "
            "against the recorded result. End Turn includes all seven rival turns. Your campaign "
            "is paused meanwhile and left untouched.",
            "Recording starts when you choose a nation or load a save. Export it to keep it; a "
            "replay file can also be dropped onto CARS.exe.",
        ):
            y += ui.paragraph(paragraph, pygame.Rect(x, y, width, ui.px(120)), style.BODY) + ui.px(10)
        button_width = width // len(ACTIONS) - ui.px(6)
        for i, (action, label) in enumerate(ACTIONS):
            self.button(
                pygame.Rect(x + i * (button_width + ui.px(6)), y, button_width, ui.px(34)),
                label,
                action,
                kind="primary" if action == "watch" else "secondary",
            )
        y += ui.px(48)
        if self.notice:
            y += ui.paragraph(self.notice, pygame.Rect(x, y, width, ui.px(80)), style.BODY, style.SLATE)
        return y - rect.y

    def act(self, action: str) -> None:
        game = self.game
        recorder = game.campaign.recorder
        try:
            if action == "latest":
                game.watch_replay(read_replay_file(latest_export_path()))
            elif not game.campaign.human_turn or game.view.animation or not recorder:
                self.notice = "Wait until it is your turn and movement has finished."
            elif action == "export":
                self.notice = "Exported to " + str(recorder.export())
            else:
                game.watch_replay(recorder.data())
        except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
            self.notice = "Could not open the replay: " + str(exc)
