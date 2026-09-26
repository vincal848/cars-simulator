## What and why

<!-- What does this change, and what problem does it solve? -->

## Checklist

- [ ] `python -m unittest discover -s tests -t .` passes
- [ ] `ruff check .` and `ruff format --check .` pass
- [ ] If rules changed: `RULESET` bumped (once per release), sample replay re-recorded,
      golden references regenerated
- [ ] If the save format changed: `SAVE_VERSION` bumped with an upgrade step
- [ ] `docs/CHANGELOG.md` updated for player-visible changes
