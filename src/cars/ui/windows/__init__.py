"""Modal windows over the campaign. At most one is open; it takes all input."""

from cars.ui.frames import Window
from cars.ui.pedia.window import PediaWindow
from cars.ui.windows.event import EventWindow
from cars.ui.windows.keyboard import KeyboardWindow
from cars.ui.windows.library import LoadWindow, SaveWindow
from cars.ui.windows.menu import MenuWindow
from cars.ui.windows.picker import PickerWindow
from cars.ui.windows.replay_studio import ReplayWindow
from cars.ui.windows.settings import MusicWindow, SettingsWindow
from cars.ui.windows.strategy import StrategyWindow
from cars.ui.windows.timeline import TimelineWindow

WINDOWS: dict[str, type[Window]] = {
    "menu": MenuWindow,
    "save": SaveWindow,
    "load": LoadWindow,
    "settings": SettingsWindow,
    "music": MusicWindow,
    "keyboard": KeyboardWindow,
    "timeline": TimelineWindow,
    "strategy": StrategyWindow,
    "replay": ReplayWindow,
    "event": EventWindow,
    "pedia": PediaWindow,
    "picker": PickerWindow,
}
