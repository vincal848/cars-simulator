"""Replay studio: watch or export this session's verified command recording."""

import pygame

from cars.persist.replay import latest_export_path, read_replay_file
from cars.ui.frames import Window
from cars.ui.kit import style

ACTIONS = (("watch", "Watch this session"), ("export", "Export recording"), ("latest", "Open latest export"))
HELP = {
    "watch": "Plays the session back on a read-only copy, checking every command against its "
    "recorded result. Your campaign is paused and left untouched.",
    "export": "Recording starts when you choose a nation or load a save. A replay file can also be "
    "dropped onto CARS.exe.",
}


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
        y += ui.px(40)
        button_width = width // len(ACTIONS) - ui.px(6)
        for i, (action, label) in enumerate(ACTIONS):
            self.button(
                pygame.Rect(x + i * (button_width + ui.px(6)), y, button_width, ui.px(34)),
                label,
                action,
                kind="primary" if action == "watch" else "secondary",
            )
            if action in HELP:
                ui.hint(self.area_of(action), label, HELP[action])
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
