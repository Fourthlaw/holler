# Holler tabletop endpoint

The reference build: a desktop speaker with USB-C power and a battery that carries it through outages. This is a first design. It has been modeled and checked for fit, but not yet printed.

See docs/design.md, section 3.4, for the full design.

![Front, with the grille ring removed](renders/render_front_exploded.png)

| | |
|---|---|
| ![Top](renders/render_top.png) | ![Transmission line layout](renders/render_plan.png) |

## What it is

- 250 x 173 x 84 mm, printed in PETG on a Bambu Lab A1 with no supports
- Dayton Audio CE70PR-4 2.5 in. woofer and ND16FA-6 tweeter, front-mounted in a recess, each on its own MAX98357A amp, with the crossover in software
- A folded transmission line about 730 mm long behind the woofer, tuned to about 115 Hz
- ESP32-S3-DevKitC-1 on Wi-Fi, INMP441 mic, USB-C power, and an 18650 cell for backup
- Five moving button caps on top: TALK, VOL -, VOL +, MIC MUTE, BACKGROUND
- A cloth grille on a printed ring held by magnets
- Lid screws come up through the bottom, so nothing shows on top but the buttons
- The status glow is indirect: an LED under the grille ring shines sideways behind the cloth

## Parts

| File | What it is | Print orientation |
|---|---|---|
| `base.stl` | Case, transmission line, electronics bay | Floor on the bed |
| `lid.stl` | Top, button guides, and the pillars the bottom screws thread into | Top face on the bed |
| `button_caps.stl` | All five caps on one plate | Cap tops on the bed |
| `grille_ring.stl` | Magnetic frame for the speaker cloth | Front face on the bed |

The base uses roughly 450 to 500 g of PETG and nearly fills the A1 bed. Print one cap and a small test piece of the lid first to check the cap fit.

## Hardware

| Item | Qty |
|---|---|
| Dayton Audio CE70PR-4 woofer and ND16FA-6 tweeter | 1 each |
| MAX98357A I2S amp breakout | 2 |
| 10 to 22 uF film capacitor (in series with the tweeter) | 1 |
| ESP32-S3-DevKitC-1, INMP441 mic module | 1 each |
| 18650 cell and holder, power-path charger, 5 V boost, USB-C breakout | 1 each |
| 3 mm bicolor LED (red/green) | 1 |
| 6x6 mm tact switch | 5 |
| M3 heat-set insert and M3 x 8 socket head screw (lid) | 6 |
| M4 heat-set insert and M4 x 10 screw (woofer) | 4 |
| M2 x 5 self-tapping screw (button board) | 4 |
| 6 x 3 mm disc magnet | 8 |
| 12 mm self-adhesive feet | 4 |
| Speaker cloth, foam gasket tape, polyfill, zip ties | |

Assembly steps are in docs/design.md, section 3.4.5.

## Change it

Every dimension is a named parameter at the top of `tabletop_endpoint.py`:

```
pip install manifold3d trimesh numpy pillow matplotlib
python3 tabletop_endpoint.py     # writes the STLs
python3 render_views.py          # writes preview images to renders/
python3 render_plan.py           # writes the line layout to renders/
```

Dimensions marked `VERIFY` are estimates. Check them against the parts in hand before printing: the woofer frame and basket, the tweeter faceplate, the mic board, the 18650 holder, the tact switch height, and the USB-C breakout.
