# Holler in-wall endpoint (optional)

An option for people who want speakers in the walls. It is not part of the reference build, and nothing here has been modeled or built yet.

The electronics, mic privacy circuit, buttons, and firmware are the same as the tabletop endpoint. See docs/design.md, section 3.1.

## What it is

- A double-gang new-work electrical box used as a sealed speaker enclosure
- One 2 in. full-range driver (Dayton Audio CE52N-4) and one MAX98357A amp
- ESP32-S3 with Ethernet and PoE preferred, so one low-voltage cable powers and connects it
- INMP441 mic behind a gasketed port in the plate
- Five moving button caps: TALK, VOL -, VOL +, MIC MUTE, BACKGROUND

## Parts still to design

| Part | Notes |
|---|---|
| Wall plate | Double-gang size. Speaker opening with a cloth grille, mic port, light window, and five button openings with guide collars, using the same cap design as the tabletop lid |
| Speaker bracket | Holds the driver behind the plate and carries the ESP32, amp, and button board |
| Button caps | Same stack as the tabletop caps, sized for the plate |

The tabletop generator in `../tabletop/tabletop_endpoint.py` has the cap, collar, and grille ring code to start from.

## Before installing in a wall

- Use PoE or a listed low-voltage supply. Do not put line voltage and the endpoint's wiring in the same box without a listed barrier.
- Use in-wall-rated cable, and follow local electrical code.
