"""Scripted, deterministic runs that exercise every rule and every screen.

Each run yields ``(label, payload)`` pairs. The golden tests hash the payloads and
compare them with the stored references; ``python -m tests.golden.update``
regenerates the references after an intentional change.
"""

import hashlib
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import pygame

from cars.persist.replay import Playback, Recorder, digest
from cars.persist.savegame import decode_game, encode_game
from cars.sim.ai import faction_actions
from cars.sim.air import coverage
from cars.sim.buildings import BUILDINGS
from cars.sim.buildings import quote as quote_build
from cars.sim.calendar import date_label, turn_phase
from cars.sim.campaign import Campaign
from cars.sim.economy import forecast
from cars.sim.entities import LAND_KINDS
from cars.sim.forecast import forecast_order
from cars.sim.market import quote as quote_trade
from cars.sim.market import treasury_income
from cars.sim.movement import reachable
from cars.sim.objectives import campaign_stage
from cars.sim.recruitment import quote_recruit
from cars.sim.scenario import COMPACT_SCENARIO, DETAILED_SCENARIO, load_scenario
from cars.sim.supply import supplied_provinces, supply_route, threatened_route
from cars.sim.topology import analyze
from cars.sim.turn import end_turn
from cars.ui.audio import Audio
from cars.ui.context import UiContext
from cars.ui.screens.game import GameScreen
from cars.ui.screens.replay import ReplayScreen
from cars.ui.screens.title import TitleScreen
from cars.ui.typography import FONT_CHOICES, system_font

EXAMPLE_REPLAY = Path(__file__).resolve().parents[2] / "examples" / "opening.json"
RECRUIT_KINDS = ("infantry", "scout", "cavalry", "artillery", "fleet", "air", "regional", "bogus")
OFF_SCREEN = (-100, -100)


def fingerprint(payload) -> str:
    """Stable hash of JSON-compatible data; floats are hashed via repr, so exactly."""
    text = json.dumps(payload, sort_keys=True, default=repr)
    return hashlib.sha256(text.encode()).hexdigest()


# Simulation --------------------------------------------------------------------------


def snapshot(state) -> dict:
    return dict(
        round=state.round,
        active=state.active_index,
        clock=state.clock,
        objectives=state.objectives,
        market=state.market,
        recruited=list(state.recruited),
        air_support=state.air_support,
        units=[
            (u.id, u.owner, u.kind, u.location, repr(u.hp), repr(u.remaining), u.supplied, u.regional)
            for u in state.units.values()
        ],
        provinces=[
            (p.id, p.controller, sorted(p.buildings.items()), list(p.units)) for p in state.provinces.values()
        ],
        factions=[
            (f.id, repr(f.gold), sorted((k, repr(v)) for k, v in f.resources.items()))
            for f in state.factions.values()
        ],
        reports=state.reports[-6:],
        digest=digest(state),
    )


def probes(state, player: str) -> dict:
    """Read-only queries the UI relies on, evaluated at the start of the player's turn."""
    out = dict(
        date=date_label(state.clock),
        date_ahead=date_label(state.clock, 3),
        stage=list(campaign_stage(state)),
        phase=list(turn_phase(state)),
        supplied={f: sorted(supplied_provinces(state, f)) for f in state.factions},
        production={f: {k: repr(v) for k, v in forecast(state, f).items()} for f in state.factions},
        income={f: treasury_income(state, f) for f in state.factions},
    )
    out["routes"] = {p: supply_route(state, player, p) for p in sorted(state.provinces)[::17]}
    route = next((r for r in out["routes"].values() if r), [])
    out["threat"] = sorted(threatened_route(state, player, route))
    whole = analyze(state.land)
    owned = analyze(state.land, [p for p in state.provinces if state.provinces[p].controller == player])
    out["topology"] = [len(whole.components), sorted(whole.cuts), sorted(whole.bridges), sorted(owned.cuts)]
    out["trade"] = {
        r + s: quote_trade(state, player, r, s) for r in ("wood", "food", "iron") for s in ("buy", "sell")
    }
    own = sorted(p for p in state.provinces if state.provinces[p].controller == player)[:6]
    out["build"] = {p + k: quote_build(state, p, k) for p in own for k in BUILDINGS}
    out["recruit"] = {p + k: quote_recruit(state, p, k) for p in own for k in RECRUIT_KINDS}
    out["coverage"] = {u.id: sorted(coverage(state, u)) for u in state.units.values() if u.kind == "air"}
    forecasts = {}
    for unit in sorted(state.units.values(), key=lambda u: u.id):
        if unit.owner != state.active or unit.remaining <= 0:
            continue
        if unit.kind in LAND_KINDS:
            costs = reachable(state, unit).costs
            out.setdefault("reach", {})[unit.id] = sorted((k, repr(v)) for k, v in costs.items())
            for target in sorted(costs)[:4]:
                forecasts[unit.id + target] = forecast_order(state, unit.id, target)
        elif unit.kind == "air":
            for target in sorted(coverage(state, unit))[:3]:
                for mode in ("strike", "support", "rebase"):
                    forecasts[unit.id + target + mode] = forecast_order(state, unit.id, target, mode)
    out["forecasts"] = {k: {kk: repr(vv) for kk, vv in v.items()} for k, v in forecasts.items()}
    return out


def ai_campaign(scenario: Path, player: str, rounds: int, save_every: int) -> Iterator[tuple[str, dict]]:
    """Every faction played by the AI, with trades and a save round trip every few rounds."""
    state, shapes, seas = load_scenario(scenario)
    campaign = Campaign(state)
    campaign.choose(player)
    for round_number in range(rounds):
        for _ in range(len(state.factions)):
            active = state.active
            step = dict(active=active, before=snapshot(state))
            if active == player:
                step["probes"] = probes(state, player)
                if round_number % save_every == 0:
                    blob = json.loads(json.dumps(encode_game(state, shapes, seas, player)))
                    restored, shapes, seas, _ = decode_game(blob)
                    step["save"] = [digest(state), digest(restored)]
                    state = campaign.state = restored
                trades = (("wood", "buy"), ("iron", "sell"), ("food", "sell"))
                step["trades"] = [campaign.trade(resource, side) for resource, side in trades]
            step["actions"] = [(uid, list(route), message) for uid, route, message in faction_actions(state)]
            step["gains"] = {k: repr(v) for k, v in end_turn(state).items()}
            step["after"] = snapshot(state)
            yield f"{scenario.stem} round {round_number + 1} {active}", step


def recorded_campaign() -> Iterator[tuple[str, dict]]:
    """Player commands of every kind through the campaign boundary, then verified playback."""
    state, shapes, seas = load_scenario(DETAILED_SCENARIO)
    campaign = Campaign(state)
    campaign.choose("f0")
    campaign.recorder = Recorder(state, shapes, seas, "f0")
    log = []
    for round_number in range(6):
        for resource, side in (("wood", "buy"), ("food", "buy"), ("iron", "sell")):
            log.append(repr(campaign.trade(resource, side)))
        for unit_id in sorted(u.id for u in state.units.values() if u.owner == "f0"):
            unit = state.units.get(unit_id)
            if unit is None:
                continue
            if unit.kind in LAND_KINDS:
                costs = reachable(state, unit).costs
                farthest = sorted(costs, key=lambda p: (-costs[p], p))
                log.append(repr(campaign.move(unit_id, farthest[0])))
            elif unit.kind == "air":
                in_range = sorted(coverage(state, unit))
                if in_range:
                    mode = "support" if round_number % 2 else "strike"
                    log.append(repr(campaign.air_mission(unit_id, in_range[-1], mode)))
        provinces = sorted(p for p in state.provinces if state.provinces[p].controller == "f0")
        for province in provinces:
            for kind in ("air", "fleet", "regional", "infantry", "cavalry"):
                result = campaign.recruit(province, kind)
                if result[0]:
                    log.append(repr(result))
        for province in provinces:
            for kind in ("farm", "roads", "mine", "airfield", "shipyard"):
                result = campaign.construct(province, kind)
                if result[0]:
                    log.append(repr(result))
                    break
        end_turn(state)
        for _ in range(7):
            list(faction_actions(state))
            end_turn(state)
        campaign.recorder.append(state, "end_turn", ())
    playback = Playback(json.loads(json.dumps(campaign.recorder.data())))
    while playback.step():
        pass
    commands = [(c["action"], c["args"], c["after"]) for c in campaign.recorder.commands]
    result = dict(log=log, commands=commands, final=digest(playback.state), live=digest(state))
    yield "recorded campaign", result


def simulation_runs() -> Iterator[tuple[str, dict]]:
    yield from ai_campaign(DETAILED_SCENARIO, "f3", rounds=30, save_every=5)
    yield from ai_campaign(COMPACT_SCENARIO, "f0", rounds=20, save_every=4)
    yield from recorded_campaign()


# Screens -----------------------------------------------------------------------------


class _Camera:
    """Drives the real screens and captures each frame."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen

    def new_game(self, faction: str | None = "f0"):
        state, shapes, seas = load_scenario(DETAILED_SCENARIO)
        context = UiContext(self.screen)
        context.pointer = OFF_SCREEN
        game = GameScreen(context, state, shapes, seas)
        if faction:
            game.choose_faction(faction)
        return game

    def frame(self, game: GameScreen, hover: str | None = None) -> pygame.Surface:
        game.context.theme.tips.key = None  # Never let a tooltip's delay depend on wall time.
        game.draw(hover)
        return self.screen


@contextmanager
def empty_user_data() -> Iterator[None]:
    """Screens show save slots and settings, so render them against an empty profile."""
    folder = tempfile.TemporaryDirectory()
    with folder, mock.patch.dict(os.environ, CARS_SAVE_DIR=f"{folder.name}/saves"):
        yield


def screen_runs(screen: pygame.Surface) -> Iterator[tuple[str, pygame.Surface]]:
    with empty_user_data():
        yield from _screens(screen)


def _screens(screen: pygame.Surface) -> Iterator[tuple[str, pygame.Surface]]:
    camera = _Camera(screen)

    game = camera.new_game(None)
    title = TitleScreen(game.context, game)
    title.draw()
    yield "title", screen
    title.help = True
    title.draw()
    yield "title help", screen
    yield "faction picker", camera.frame(game)

    game = camera.new_game()
    state, renderer, context = game.state, game.renderer, game.context
    yield "campaign map", camera.frame(game)
    renderer.objectives.collapsed = True
    yield "objectives collapsed", camera.frame(game)
    renderer.objectives.collapsed = False

    unit = next(u for u in sorted(state.units.values(), key=lambda u: u.id) if u.owner == "f0" and u.is_land)
    game.view.selected = unit.id
    costs = reachable(state, unit).costs
    hostile = sorted(p for p in costs if state.provinces[p].controller != "f0")
    friendly = sorted(p for p in costs if state.provinces[p].controller == "f0" and p != unit.location)
    target = hostile[0] if hostile else friendly[-1]
    context.pointer = renderer.map.anchors[target]
    yield "route and forecast", camera.frame(game, target)
    context.pointer = OFF_SCREEN
    game.view.debug = True
    yield "debug graph", camera.frame(game, friendly[0] if friendly else None)
    game.view.debug = False

    game.inspect(unit.location, renderer.map.anchors[unit.location])
    for tab in ("build", "infrastructure", "recruit"):
        renderer.province_window.select_tab(tab)
        yield f"province {tab}", camera.frame(game)
    for page in ("sea_air", "regional"):
        renderer.province_window.select_recruit_page(page)
        yield f"recruit {page}", camera.frame(game)
    renderer.province_window.close()

    for layer in ("naval", "air", "supply"):
        game.switch_layer(layer)
        yield f"layer {layer}", camera.frame(game)
    game.switch_layer("land")

    renderer.menu.open = True
    yield "menu", camera.frame(game)
    renderer.menu.open = False
    renderer.market.open = True
    yield "market", camera.frame(game)
    renderer.market.open = False

    context.audio = Audio()
    dialogs = (
        "pedia",
        "strategy",
        "replay",
        "reports",
        "roster",
        "diplomacy",
        "settings",
        "music",
        "timeline",
        "save",
        "load",
    )
    for mode in dialogs:
        game.dialogs.open(mode)
        yield f"dialog {mode}", camera.frame(game)
    state.events["fired"].append("bountiful_harvest")
    state.events["pending"].append("bountiful_harvest")
    game.dialogs.open("event")
    yield "dialog event", camera.frame(game)
    state.events["pending"].clear()
    pedia = game.dialogs.dialogs["pedia"]
    game.dialogs.open("pedia")
    pedia.section, pedia.index = "Units", 2
    yield "pedia units", camera.frame(game)
    pedia.section, pedia.index = "History", 0
    yield "pedia history", camera.frame(game)
    game.dialogs.open("strategy")
    strategy = game.dialogs.active
    strategy.layer = "supply"
    camera.frame(game)
    strategy.selected = sorted(strategy.points)[0]
    yield "strategy supply", camera.frame(game)
    game.dialogs.close()
    context.audio = None

    renderer.map.zoom(2.6, renderer.map.anchors[unit.location])
    yield "zoomed", camera.frame(game)
    renderer.map.zoom(3.0, renderer.map.anchors[unit.location])
    yield "zoomed max", camera.frame(game)

    for _ in range(16):
        list(faction_actions(state))
        end_turn(state)
    state.reindex_units()
    renderer.map.invalidate_labels()
    renderer.map.reset_camera()
    game.view.selected = None
    yield "after rival turns", camera.frame(game)
    game.dialogs.open("reports")
    yield "chronicle battles", camera.frame(game)
    game.dialogs.active.battles_only = False
    yield "chronicle all", camera.frame(game)
    game.dialogs.open("roster")
    yield "roster after rival turns", camera.frame(game)

    game = camera.new_game(None)
    game.start_tutorial()
    yield "tutorial", camera.frame(game)

    game = camera.new_game(None)
    viewer = ReplayScreen(game.context, game, json.loads(EXAMPLE_REPLAY.read_text(encoding="utf-8")))
    viewer.draw()
    yield "replay start", screen
    for _ in range(5):
        viewer.step()
    viewer.draw()
    yield "replay stepped", screen


def environment(screen_font) -> dict:
    """What screenshot pixels depend on besides our code: pygame, SDL and system fonts."""
    samples = {}
    for index, (name, _) in enumerate(FONT_CHOICES):
        rendered = system_font(index, 15).render("Qg The Americas 1800", True, (255, 255, 255))
        samples[name] = fingerprint(pygame.image.tobytes(rendered, "RGBA").hex())
    rendered = screen_font.render("North Pacific", True, (255, 255, 255))
    samples["georgia"] = fingerprint(pygame.image.tobytes(rendered, "RGBA").hex())
    return dict(pygame=pygame.version.ver, sdl=".".join(map(str, pygame.get_sdl_version())), fonts=samples)
