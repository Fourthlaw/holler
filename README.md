# Home Intercom

Whole-home synchronized music and push-to-talk intercom. A Raspberry Pi 5 runs the music server, intercom server, and controls. ESP32-S3 endpoints in each room play music and carry pages. A paired iPhone app can page the house remotely.

Microphones are gated in hardware: a room mic has power only while someone in that room holds TALK and the room's mic mute is off. No software, including compromised firmware, can turn a mic on.

The full design is in [docs/design.md](docs/design.md).

## Layout

| Folder | What it holds | Status |
|---|---|---|
| `docs/` | System design | Current |
| `hardware/tabletop/` | Printable enclosure for the tabletop endpoint: parametric generator, STLs, preview renders | First design, not yet printed |
| `firmware/endpoint/` | ESP32-S3 endpoint firmware (in-wall and tabletop) | Not started |
| `controller/` | Pi 5 services: Snapserver config, intercom server, MQTT, web app, scheduler | Not started |
| `remote/` | Remote intercom: Pi gateway, cloud rendezvous server, iPhone app | Not started |

## Tabletop enclosure

Prints on a Bambu Lab A1 in PETG, no supports. Outer size 250 x 173 x 84 mm.

| File | Print orientation |
|---|---|
| `base.stl` | Floor on the bed |
| `lid.stl` | Top face on the bed |
| `button_caps.stl` | Cap tops on the bed |
| `grille_ring.stl` | Front face on the bed |

To change a dimension, edit the parameters at the top of `tabletop_endpoint.py` and regenerate:

```
cd hardware/tabletop
pip install manifold3d trimesh numpy pillow matplotlib
python3 tabletop_endpoint.py     # writes the STLs
python3 render_views.py          # writes preview images to renders/
python3 render_plan.py           # writes the line layout to renders/
```

Dimensions marked VERIFY in the script are estimates to check against parts in hand before printing.
