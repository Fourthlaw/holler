"""Preview renders for the in-wall endpoint. Run inwall_endpoint.py first."""
import os, sys
import numpy as np, trimesh
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tabletop"))
from raster import render, project, label
import inwall_endpoint as W

os.makedirs("renders", exist_ok=True)
# model (x, y, z = out of wall) -> render (x, depth, up): front of the wall faces the viewer
A = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=float)


def load(name, dz=0.0, dx=0.0):
    m = trimesh.load(f"_asm_{name}.stl") if name != "box" else trimesh.load("box_reference.stl")
    m.apply_translation([dx, 0, dz])
    m.apply_transform(A)
    return m


def P(ctx, x, y, z):
    return project((x, -z, y), ctx)


def place(img, anchors):
    """Put labels in a top and a bottom row, ordered by anchor x, so leader lines do not cross."""
    Wd, Ht = img.size
    top = sorted([a for a in anchors if a[0][1] < Ht / 2], key=lambda a: a[0][0])
    bot = sorted([a for a in anchors if a[0][1] >= Ht / 2], key=lambda a: a[0][0])
    out = []
    for row, y in ((top, 95), (bot, Ht - 60)):
        n = len(row)
        for i, (pt, text) in enumerate(row):
            x = Wd * (i + 0.5) / max(n, 1)
            out.append((pt, (x, y), text))
    return out


PLATE = (0.86, 0.87, 0.89)
CAP = (0.86, 0.58, 0.30)
CAR = (0.62, 0.66, 0.72)
SLED = (0.50, 0.62, 0.55)
BOX = (0.25, 0.42, 0.75)
DRV = (0.18, 0.18, 0.20)
PCB = (0.20, 0.55, 0.30)
RING = (0.80, 0.50, 0.25)
B = {n: (x, y) for n, x, y, *_ in W.BUTTONS}

# 1. front, assembled
img, ctx = render([(load("cover"), PLATE), (load("caps"), CAP), (load("driver"), DRV)], elev=12, azim=22, size=(1500, 1250), light=(-0.3, -0.85, 0.45))
items = place(img, [
    (P(ctx, W.DRV_X, W.DRV_Y + 16, W.COVER_T), "speaker opening (cloth glued behind)"),
    (P(ctx, *B["TALK"], W.COVER_T + 0.6), "TALK"),
    (P(ctx, *B["VOL_UP"], W.COVER_T + 0.6), "VOL - / VOL +"),
    (P(ctx, B["BACKGROUND"][0] + 3, B["BACKGROUND"][1] - 3, W.COVER_T + 0.6), "MIC MUTE / BACKGROUND"),
    (P(ctx, W.MIC_X, W.MIC_Y, W.COVER_T), "mic port"),
    (P(ctx, W.LED_X, W.LED_Y, W.COVER_T), "status light (thin skin)"),
])
label(img, items, f"In-wall endpoint: cover {W.COVER_W:.0f} x {W.COVER_H:.0f} mm, no visible screws").save("renders/render_front.png")

# 2. exploded
parts = [(load("box", dz=-150), BOX), (load("sled", dz=-78), SLED), (load("esp", dz=-78), PCB),
         (load("ring", dz=-44), RING), (load("driver", dz=-18), DRV), (load("board", dz=-30), PCB), (load("switches", dz=-30), DRV),
         (load("carrier"), CAR), (load("caps", dz=42), CAP), (load("cover", dz=95), PLATE)]
img, ctx = render(parts, elev=16, azim=62, size=(2100, 1100), light=(-0.5, -0.7, 0.5))
items = place(img, [
    (P(ctx, -40, 50, 95 + 1.5), "cover (magnets, cloth grille)"),
    (P(ctx, B["TALK"][0], B["TALK"][1] + 6, 42 + 2), "button caps"),
    (P(ctx, -50, 50, -1.5), "carrier (screws to the box)"),
    (P(ctx, W.BOARD_X[1] - 4, 33, -30 + W.BOARD_Z), "button board"),
    (P(ctx, W.DRV_X, -12, -18 - 26), "driver"),
    (P(ctx, W.DRV_X - 22, -22, -44 - 8), "clamp ring"),
    (P(ctx, -40, 42, -78 + W.SLED_Z), "electronics sled"),
    (P(ctx, -48, 46, -150 - 30), "double-gang box (reference)"),
])
label(img, items, "Exploded view (room side at right)").save("renders/render_exploded.png")

# 3. carrier from behind
img, ctx = render([(load("carrier"), CAR)], elev=28, azim=205, size=(1700, 1300), light=(0.3, 0.6, 0.7))
zb = -W.CAR_T
items = place(img, [
    (P(ctx, W.DRV_X + 20, W.DRV_Y + 20, zb - 3), "driver seat + M2 clamp bosses"),
    (P(ctx, B["VOL_DOWN"][0] - 8, B["VOL_DOWN"][1], zb - 4), "button guide collars"),
    (P(ctx, *W.BOARD_PTS[1], W.BOARD_Z), "button board standoffs"),
    (P(ctx, W.MIC_X, W.MIC_Y - 7.5, zb - 4), "mic pocket"),
    (P(ctx, W.LED_X, W.LED_Y, W.BOARD_Z), "light pipe"),
    (P(ctx, *W.POST_PTS[0], W.SLED_Z), "sled posts (M3 inserts)"),
    (P(ctx, *W.DEV_PTS[0], zb), "box screw holes (6-32)"),
])
label(img, items, "Carrier from behind").save("renders/render_carrier_back.png")

# 4. assembled in the box, top of the box cut away
import manifold3d as m3
bx = W.build_box() ^ W.box(-200, 200, -200, 4, -200, 200)
tb = W.to_trimesh(bx); tb.apply_transform(A)
parts = [(tb, BOX), (load("carrier"), CAR), (load("ring"), RING), (load("driver"), DRV), (load("board"), PCB),
         (load("switches"), DRV), (load("sled"), SLED), (load("esp"), PCB), (load("cover"), PLATE), (load("caps"), CAP)]
img, ctx = render(parts, elev=38, azim=200, size=(1700, 1250), light=(0.3, 0.6, 0.7))
items = place(img, [
    (P(ctx, 22, 20, W.SLED_Z - 8), "ESP32 on the sled"),
    (P(ctx, -30, 30, W.SLED_Z - 2.4), "sled"),
    (P(ctx, -24, 23, W.SLED_Z - 6), "amp tray"),
    (P(ctx, 30, 36.5, W.BOARD_Z - 0.8), "button board"),
    (P(ctx, 44.5, 40.2, -22), "sled post"),
    (P(ctx, 46, -10, -72), "box (top half cut away)"),
])
label(img, items, "Assembled in the box, seen from inside the wall").save("renders/render_in_box.png")
print("ok")
