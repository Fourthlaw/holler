import numpy as np, trimesh
import tabletop_endpoint as T
from raster import render, project, label

base = trimesh.load("_asm_base.stl")
lid = trimesh.load("_asm_lid.stl")
caps = trimesh.load("_asm_caps.stl")
ring = trimesh.load("_asm_ring.stl")
RINGC = (0.18, 0.19, 0.21)
CAPC = (0.86, 0.58, 0.30)
GREY = (0.78, 0.80, 0.83)
DARK = (0.32, 0.35, 0.40)
LIDC = (0.40, 0.43, 0.48)
L = T.legs
B = {n: (x, y) for n, x, y, *_ in T.BUTTONS}
ZT = T.HB + T.LID_T

# 1. base open top
img, ctx = render([(base, GREY)], elev=66, azim=22, size=(1700, 1300))
P = lambda p: project(p, ctx)
items = [
    (P((60, (L[0][0] + L[0][1]) / 2, T.HB - 4)), (420, 1250), "leg 1 (driver end)"),
    (P((70, (L[3][0] + L[3][1]) / 2, T.HB - 4)), (330, 330), "leg 4"),
    (P(((T.MOUTH_X0 + T.MOUTH_X1) / 2, T.D, T.HB - 10)), (1050, 110), "mouth slots (rear)"),
    (P((T.TL_X1 - 5, T.legs[1][0] + 4, T.HB - 4)), (900, 1250), "45 degree turn deflectors"),
    (P((T.SEP_X1 + 16, 60, T.FLOOR + 10)), (1500, 640), "ESP32-S3 tray (snap lips)"),
    (P((T.BAT_X + 10, 60, T.FLOOR + 8)), (1530, 520), "18650 pocket + strap slots"),
    (P((T.SEP_X1 + 16, 120, T.FLOOR + 4)), (1560, 330), "charger / UPS tray"),
    (P((T.SCREW_PTS[0][0], T.SCREW_PTS[0][1], T.FLOOR + T.PAD_H)), (150, 1150), "pillar socket pads"),
]
label(img, items, "Base: folded transmission line (left), electronics bay (right)").save("renders/render_base_iso.png")

# 1b. inside of the front wall
img, ctx = render([(base, GREY)], elev=62, azim=200, size=(1700, 1300))
P = lambda p: project(p, ctx)
items = [
    (P((T.DRV_X + 28, T.RECESS_D + T.BAFFLE_T + 4, T.DRV_Z + 28)), (1480, 200), "recessed baffle + M4 insert bosses"),
    (P((T.TL_X1 - 15, (L[0][0] + L[0][1]) / 2, T.HB - 4)), (980, 1250), "closed end (polyfill here)"),
    (P((T.SEP_X1 + 13, 20, T.FLOOR + 9)), (200, 1150), "amp tray"),
    (P((T.MIC_X, T.WALL + 4, T.MIC_Z + 9)), (260, 280), "mic gasket ring + slide rails"),
    (P((T.LED_X, T.WALL + 5, T.LED_Z + 3)), (330, 420), "light box behind light bar"),
    (P((T.SEP_X1, 22, T.FLOOR + 6)), (560, 1250), "speaker wire pass-through"),
]
label(img, items, "Base from the rear: inside of the front wall").save("renders/render_base_front_inside.png")

# 2. assembled front
img, ctx = render([(base, DARK), (lid, LIDC), (caps, CAPC), (ring, RINGC)], elev=14, azim=18, size=(1700, 900))
P = lambda p: project(p, ctx)
items = [
    (P((T.RECESS_CX, 0, T.DRV_Z + 30)), (330, 830), "magnetic grille ring (cloth over woofer + tweeter)"),
    (P((T.MIC_X, 0, T.MIC_Z)), (1500, 840), "mic port"),
    (P((T.LED_X, 0, T.LED_Z)), (1100, 850), "light bar (mic-mute glow)"),
]
label(img, items, f"Assembled: {T.W:.0f} x {T.D:.0f} x {ZT:.1f} mm").save("renders/render_front.png")

# 3. top
img, ctx = render([(base, DARK), (lid, LIDC), (caps, CAPC), (ring, RINGC)], elev=55, azim=12, size=(1700, 1150), light=(0.2, -0.4, 0.9))
P = lambda p: project(p, ctx)
items = [
    (P((*B["TALK"], ZT + 0.6)), (1500, 1100), "TALK"),
    (P((*B["VOL_DOWN"], ZT + 0.6)), (1000, 1110), "VOL -"),
    (P((*B["VOL_UP"], ZT + 0.6)), (1580, 760), "VOL +"),
    (P((*B["MIC_MUTE"], ZT + 0.6)), (1050, 120), "MIC MUTE (hardware latch)"),
    (P((*B["BACKGROUND"], ZT + 0.6)), (1540, 200), "BACKGROUND"),
]
label(img, items, "Top: five moving button caps, no screws or other hardware").save("renders/render_top.png")

# 4. bottom
bf = base.copy()
bf.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
img, ctx = render([(bf, DARK)], elev=60, azim=15, size=(1700, 1150), light=(0.3, -0.5, 0.8))
P = lambda p: project(p, ctx)
sx, sy = T.SCREW_PTS[0]
items = [
    (P((sx, -sy, 0)), (250, 1100), "M3 screws, counterbored"),
    (P((T.FOOT_INSET, -T.FOOT_INSET, 0)), (700, 1110), "foot rings (12 mm adhesive bumpers)"),
]
label(img, items, "Bottom: all six lid screws come in from here").save("renders/render_bottom.png")

# 5. lid underside
lf = lid.copy()
lf.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
img, ctx = render([(lf, GREY)], elev=55, azim=-20, size=(1700, 1250))
P = lambda p: project(p, ctx)
items = [
    (P((B["TALK"][0], -B["TALK"][1], -(T.HB - 4))), (1450, 1200), "guide collars (caps drop in from below)"),
    (P((T.BTN_CX + T.BTN_HOLES_X / 2, -T.BTN_HOLES_Y[1], -(T.HB - 8))), (1550, 1050), "button board standoffs"),
    (P((T.SCREW_PTS[1][0], -T.SCREW_PTS[1][1], -10)), (230, 300), "pillars with M3 inserts at the ends"),
    (P((60, -T.legs[0][1], -T.HB)), (600, 1210), "grooves seal the line walls"),
]
label(img, items, "Lid underside").save("renders/render_lid_under.png")

# 6. section through the TALK button: cap, collar, switch, board
import manifold3d as m3
bx, by = B["TALK"]
def part(path):
    return trimesh.load(path)
def cut(mesh):
    m = m3.Manifold(m3.Mesh(vert_properties=np.asarray(mesh.vertices, dtype=np.float32), tri_verts=np.asarray(mesh.faces, dtype=np.uint32)))
    keep = T.box(bx, T.W + 1, -1, T.D + 1, 40, 70)
    return T.to_trimesh(m ^ keep)
sw_top = T.SWITCH_TOP; pcb_top = sw_top - T.SWITCH_H
board = T.box(bx - 27, bx + 27, 12.5, 98, pcb_top - 1.6, pcb_top)
sws = T.union([T.union([T.box(x - 3, x + 3, y - 3, y + 3, pcb_top, pcb_top + 3.5), T.cyl_z(x, y, pcb_top + 3.5, sw_top, 3.5)])
               for n, x, y, *_ in T.BUTTONS])
elec = T.to_trimesh(board ^ T.box(bx, T.W + 1, -1, T.D + 1, 0, 80))
swm = T.to_trimesh(sws ^ T.box(bx, T.W + 1, -1, T.D + 1, 0, 80))
img, ctx = render([(cut(base), DARK), (cut(lid), LIDC), (cut(caps), CAPC), (elec, (0.2, 0.55, 0.3)), (swm, (0.15, 0.15, 0.15))],
                  elev=12, azim=75, size=(1700, 1000), light=(-0.8, -0.3, 0.5))
P = lambda p: project(p, ctx)
items = [
    (P((bx, by - 8, ZT + 0.6)), (1250, 120), "cap stands 0.6 mm proud"),
    (P((bx, by - 12, T.HB - 2)), (1440, 230), "guide collar, 0.3 mm clearance"),
    (P((bx, by - 13.2, T.HB - T.COLLAR_H - 0.6)), (1450, 800), "retaining flange"),
    (P((bx, by, sw_top + 0.4)), (1100, 940), "stem on 6x6 tact switch (the return spring)"),
    (P((bx, 60, pcb_top - 0.8)), (420, 850), "button board on lid standoffs"),
]
label(img, items, "Section through the TALK button").save("renders/render_button_section.png")
print("ok")

# 7. front, grille ring pulled off
rx = ring.copy(); rx.apply_translation([-142, -20, 0])
img, ctx = render([(base, DARK), (lid, LIDC), (caps, CAPC), (rx, (0.75, 0.55, 0.30))], elev=22, azim=20, size=(1700, 1100), light=(-0.3, -0.9, 0.4))
P = lambda p: project(p, ctx)
dx = T.DRV_X; dz = T.DRV_Z
items = [
    (P((T.RECESS_CX - 142, -20, dz + 36)), (300, 120), "grille ring (one cloth over both drivers)"),
    (P((T.MAG_POS[3][0], T.RECESS_D, T.MAG_POS[3][1])), (1150, 110), "magnet pockets (4 in recess, 4 in ring)"),
    (P((T.TW_X, T.RECESS_D, T.TW_Z)), (1500, 300), "ND16FA-6 tweeter counterbore"),
    (P((dx - 20, T.RECESS_D, dz + 10)), (420, 950), "CE70PR-4 cutout + frame counterbore"),
    (P((dx + 27.9, T.RECESS_D + 3, dz - 27.9)), (950, 950), "M4 inserts for driver screws"),
    (P((dx, T.RECESS_D, dz - T.RECESS_H / 2 + 1)), (1450, 960), "pry notch"),
]
label(img, items, "Front recess with the grille ring removed").save("renders/render_front_exploded.png")
