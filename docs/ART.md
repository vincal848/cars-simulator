# Painted artwork

C.A.R.S. draws everything procedurally, but three places are designed to show a
painting when one exists: event pop-ups, the diplomacy screen and the title
screen. This document specifies each painting so that an artist or an image
generator can produce a consistent set. The game runs perfectly well without
any of them. A painting that is present replaces the procedural art, and one
that is missing falls back to it.

## Where paintings go

```
src/cars/content/gfx/paintings/events/<event id>.png
src/cars/content/gfx/paintings/leaders/<nation id>.png
src/cars/content/gfx/paintings/title/backdrop.png
```

A mod can add or replace any of them under `mods/<mod>/gfx/paintings/...`, which
is the easiest way to try a painting before committing it. PNG and JPEG both
work. Images are scaled to cover their frame and cropped evenly, so keep the
subject inside the central 80 percent.

| Kind | Frame in game | Deliver at | Aspect |
| --- | --- | --- | --- |
| Event illustration | 664 × 170 | 1328 × 340 | about 4:1 (a wide band) |
| Leader portrait | 34 × 42 now; larger later | 480 × 600 | 4:5 |
| Title backdrop | 1200 × 780 | 2400 × 1560 | 20:13 |

Deliver at twice the frame size, because the game will render at higher
resolutions in future.

## Direction

- **Period and medium:** European and American history painting from about
  1790 to 1830: oil on canvas, visible brushwork, restrained detail. The look
  should sit between a museum painting and the event art in Victoria and
  Europa Universalis.
- **Palette:** muted and warm, to match the interface: lacquer maroon
  (`#4E1A25`), brass gold (`#DBB35B`), parchment (`#FAE6BF`), dark sea teal
  (`#233E53`). Avoid saturated primaries and pure black.
- **Light:** one warm key light from the upper left, which the map and interface
  lighting also use. Soft shadows, and a gentle vignette into dark edges so the
  image sits in its gilt frame.
- **Content:** the nations are those of 1836, so period dress, uniforms and
  flags are welcome, and should be accurate to the 1830s. There
  must be no lettering, signatures, logos, borders or frames in the image; the
  game draws the frame.
- **Composition:** event bands are wide, low panoramas with the focal point
  near the centre and room on the left and right for cropping. Portraits are
  head and shoulders, three-quarter view, against a plain dark background.

### Shared prompt text

Start every image-generator prompt with:

> Oil painting in the manner of early nineteenth-century history painting, muted
> warm palette of maroon, brass gold, parchment and dark teal, warm light from the
> upper left, visible brushwork, soft vignette,

and add as negative prompt, or state explicitly:

> no text, no lettering, no signature, no watermark, no frame, no border, no real
> flags, no modern objects, no photography, no 3D render look

Do not name living artists in prompts.

## Event illustrations

One for each event in `content/events/americas.json`, named by its id.

| File | Scene |
| --- | --- |
| `bountiful_harvest.png` | Wide autumn fields at dusk, sheaves stacked, stewards beside overflowing granaries with carts waiting; abundance, calm. |
| `veteran_volunteers.png` | Weathered old soldiers in mismatched coats gathered in a town square before a council house, captains in front; dignified, a little ragged. |
| `camp_fever.png` | A field hospital tent at night lit by lanterns, surgeons among cots of wounded soldiers, a steaming kettle; sombre, compassionate. |
| `iron_seam.png` | Prospectors on a wooded hillside at a fresh ore face, timber shoring and an ox wagon, smoke from a small forge below; industrious. |
| `merchant_convoy.png` | Several tall merchant ships anchored in a calm bay, boats ferrying barrels and timber to a quay, a factor in a dark coat on the jetty; prosperous. |
| `envoys_of_peace.png` | Envoys in fine coats exchanging papers across a long table in a candlelit hall, councillors watching warily; ceremonial. |
| `lean_winter.png` | A snowbound army camp with thin horses and near-empty supply wagons, quartermasters counting sacks; cold, hungry. |
| `last_stand.png` | A last fortress on a hill under a stormy sky, a loyal court handing silver plate to an officer, a small regiment forming up; defiant, desperate. |

## Leader portraits

One for each nation in `content/common/factions.json`, named by its id, showing
the ruler named in `content/common/nations.json`. Every one of them was painted
or engraved in their lifetime, and many of those portraits are in the public
domain: a cropped, credited period portrait is the best choice. Background:
plain and dark, with a faint wash of the nation's map colour.

| File | Nation | Ruler in 1836 | Colour wash |
| --- | --- | --- | --- |
| `f0.png` | United States | President Andrew Jackson | `#3E68AA` |
| `f1.png` | Mexico | Acting President José Justo Corro | `#308C70` |
| `f2.png` | Texas | Interim President David G. Burnet | `#B66278` |
| `f3.png` | British North America | The Earl of Gosford, Governor-in-Chief | `#BE4640` |
| `f4.png` | New Granada | President Francisco de Paula Santander | `#E2AE3C` |
| `f5.png` | Peru-Bolivian Confederation | Supreme Protector Andrés de Santa Cruz | `#7C62AC` |
| `f6.png` | Empire of Brazil | Emperor Pedro II as a boy (or the Regent Feijó) | `#64A048` |
| `f7.png` | Argentine Confederation | Governor Juan Manuel de Rosas | `#6CA8D6` |

## Title backdrop

`title/backdrop.png`: a map room of the 1830s. A large hand-drawn map of the
Americas is spread on a table under warm lamplight, with brass instruments,
wax-sealed letters and model regiments in several colours. Keep the right third
darker and quieter, because the menu is drawn there, and the top left clear for
the title.

## Licensing and credits

Only commit a painting you have the right to redistribute under a licence
compatible with the project: your own work, public domain, CC0 or CC BY
(credited). If it comes from an image generator, check that the service's
terms allow redistribution in an open-source game. Add every painting to
`THIRD_PARTY.md` with its source, author or tool, and licence.

## Checking a painting

1. Drop it into a mod folder and start a campaign. The event pop-up, diplomacy
   (D) and title screens show it straight away.
2. Check that nothing important is cropped and that the text and buttons around
   it stay readable.
3. Run `python -m tests.golden.update` only if the painting is bundled with the
   game, because the reference screens will change.
