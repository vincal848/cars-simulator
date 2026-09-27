"""Panels docked beside the side bar: the province and the nation's affairs."""

from cars.ui.frames import DockedPanel
from cars.ui.panels.chronicle import ChroniclePanel
from cars.ui.panels.diplomacy import DiplomacyPanel
from cars.ui.panels.market import MarketPanel
from cars.ui.panels.military import MilitaryPanel
from cars.ui.panels.nation import NationPanel
from cars.ui.panels.province import ProvincePanel

PANELS: dict[str, type[DockedPanel]] = {
    "province": ProvincePanel,
    "nation": NationPanel,
    "military": MilitaryPanel,
    "diplomacy": DiplomacyPanel,
    "market": MarketPanel,
    "chronicle": ChroniclePanel,
}
