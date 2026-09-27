"""The interface palette and type scale.

Light neutral panels with dark ink, deep slate headers and bars, and a muted gold
for emphasis. Sizes are logical: the Ui multiplies them by the player's UI scale.
"""

# Surfaces.
PANEL = (236, 236, 232)
PANEL_DARK = (222, 223, 219)  # alternate table rows, pressed buttons
PANEL_LIGHT = (248, 248, 246)  # wells, inputs, cards
RULE = (200, 202, 200)
SLATE = (29, 42, 58)  # headers, bars
SLATE_DARK = (19, 29, 42)
SLATE_LIGHT = (48, 66, 88)
ACCENT = (201, 162, 79)
ACCENT_LIGHT = (226, 192, 120)
FRAME = (44, 54, 66)

# Ink.
INK = (28, 32, 38)
INK_MUTED = (88, 96, 108)
INK_FAINT = (140, 146, 156)
ON_SLATE = (236, 239, 243)
ON_SLATE_MUTED = (160, 174, 190)

# Meaning.
GOOD = (38, 128, 82)
BAD = (192, 60, 50)
WARN = (200, 130, 24)
HIGHLIGHT = (214, 172, 84)
SELECTED_ROW = (214, 226, 242)
HOVER_ROW = (230, 234, 239)

# Shadows and veils.
SHADOW = (8, 12, 18)
VEIL = (12, 18, 26, 150)

# Type scale in logical pixels.
TITLE = 24
HEADING = 18
BODY = 15
SMALL = 13
NUMBER = 17

# Spacing in logical pixels.
PAD = 12
GAP = 8
ROW = 30
BAR_HEIGHT = 46
