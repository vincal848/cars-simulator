"""Replay studio: watch or export this session's verified command recording."""

import pygame

from cars.persist.replay import latest_export_path, read_replay_file
from cars.ui.dialogs.base import Dialog
from cars.ui.palette import GOLD

ACTIONS = (("watch", "Watch current"), ("export", "Export recording"), ("latest", "Open latest export"))


class ReplayStudioDialog(Dialog):
    title = "Replay Studio"
    seal = "end"

    def layout(self) -> dict[str, pygame.Rect]:
        return {name: pygame.Rect(268 + i * 221, 480, 210, 38) for i, (name, _) in enumerate(ACTIONS)}

    def click(self, action: str) -> None:
        game = self.game
        recorder = game.campaign.recorder
        try:
            if action == "latest":
                game.watch_replay(read_replay_file(latest_export_path()))
            elif not game.campaign.human_turn or game.view.animation or not recorder:
                self.notice = "Wait until your turn and movement has finished."
            elif action == "export":
                self.notice = "Exported: " + str(recorder.export())
            else:
                game.watch_replay(recorder.data())
        except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
            self.notice = "Could not open replay: " + str(exc)

    def draw(self) -> None:
        t = self.theme
        recorder = self.game.campaign.recorder
        commands = len(recorder.commands) if recorder else 0
        t.text(f"{commands} commands recorded this session", 268, 192, t.heading, GOLD)
        t.paragraph(
            "Replay runs in a separate, read-only campaign. Each command is checked against the "
            "recorded result. End Turn includes all seven rival turns. Your live campaign is paused "
            "and remains untouched.",
            268,
            240,
            650,
            5,
        )
        t.paragraph(
            "Recording begins at faction selection or the latest load. Export before closing to keep this "
            "recording. Load latest opens your last exported replay; other JSON files can be dragged "
            "onto CARS.exe.",
            268,
            365,
            650,
            4,
        )
        for name, label in ACTIONS:
            t.button(self.buttons[name], label)
        t.paragraph(self.notice, 268, 548, 650, 4)
