"""
Holler in-wall endpoint - parametric generator for a double-gang electrical box.

Printed parts (PETG, no supports):
  carrier.stl       plate that screws to the box's four device holes and carries everything:
                    driver seat, button collars and board standoffs, mic pocket, LED groove,
                    and four posts for the electronics sled (print front face down)
  sled.stl          plate that screws to the carrier posts behind the driver; holds the ESP32
                    and amp (print flat, trays up)
  cover.stl         cosmetic wall plate held on by magnets; hides the screws, holds the grille
                    cloth (print front face down)
  button_caps.stl   TALK, VOL-, VOL+, MIC MUTE, BACKGROUND (print tops down)
  driver_ring.stl   clamp ring for the 2 in. driver (print flat)

Reference only, do not print:
  box_reference.stl a double-gang new-work box for fit checks and renders

Coordinates (mm), looking at the wall from the room:
  x = right, y = up, z = out of the wall toward the room.
  z = 0 is the front face of the carrier. The carrier is CAR_T thick, so the wall surface and the
  front edge of the box are at z = -CAR_T. Everything in the box is behind that. The cover and
  the button tops are at z > 0.

Run:  python3 inwall_endpoint.py   (needs manifold3d, trimesh, numpy)
Every dimension marked VERIFY should be checked against the part in hand.
"""
import math
import numpy as np
import manifold3d as m3
import trimesh

M = m3.Manifold
SEG = 64

# ------------------------------------------------------------------ the box (reference)
# Carlon B232A class 2-gang new-work box: 4 in. wide, 3-3/4 in. tall, 3 in. deep. VERIFY
BOX_W, BOX_H, BOX_DEPTH, BOX_WALL = 101.6, 95.25, 76.2, 2.3
BOX_IN_W, BOX_IN_H = BOX_W - 2 * BOX_WALL, BOX_H - 2 * BOX_WALL
# Device mounting holes (NEMA): 3.281 in. apart vertically, gangs 1.812 in. apart
DEV_DX, DEV_DY = 1.812 * 25.4 / 2, 3.281 * 25.4 / 2          # 23.01, 41.67
DEV_PTS = [(sx * DEV_DX, sy * DEV_DY) for sx in (-1, 1) for sy in (-1, 1)]
BOSS_D, BOSS_DEPTH = 9.0, 25.0     # screw bosses moulded into the box top and bottom VERIFY

# ------------------------------------------------------------------ carrier
CAR_W, CAR_H, CAR_T, CAR_R = 112.0, 108.0, 3.0, 6.0
DEV_HOLE_D = 4.2                   # clearance for 6-32 device screws
DEV_CSK_D, DEV_CSK_DEPTH = 7.4, 1.8   # countersink for 6-32 flat-head screws

# Driver: Dayton Audio CE52N-4, 2 in. (52 mm frame, 47.5 mm cutout, 30.8 mm deep) VERIFY
DRV_X, DRV_Y = -19.0, 0.0
DRV_OD, DRV_DEPTH, DRV_FLANGE_T = 52.0, 30.8, 3.0
SOUND_HOLE_D = 46.0
SEAT_ID, SEAT_OD, SEAT_H = DRV_OD + 0.8, 56.0, 3.0
CLAMP_R = 31.5                     # clamp screw circle radius, bosses at 45 degrees
CLAMP_PTS = [(DRV_X + CLAMP_R * math.cos(math.radians(a)), DRV_Y + CLAMP_R * math.sin(math.radians(a)))
             for a in (45, 135, 225, 315)]
M2_INSERT_D, M2_INSERT_DEPTH = 3.2, 3.5

# Buttons: same moving-cap stack as the tabletop lid, sized for the right-hand gang.
# (name, centre x, centre y, cap width, cap height, corner radius)
BTN_CX = 28.0
BUTTONS = [
    ("TALK",       BTN_CX,        21.6, 32.0, 16.0, 3.5),
    ("VOL_DOWN",   BTN_CX - 9.0,   4.7, 14.0, 11.0, 2.5),
    ("VOL_UP",     BTN_CX + 9.0,   4.7, 14.0, 11.0, 2.5),
    ("MIC_MUTE",   BTN_CX - 9.0,  -9.7, 14.0, 11.0, 2.5),   # hardware latch
    ("BACKGROUND", BTN_CX + 9.0,  -9.7, 14.0, 11.0, 2.5),   # software toggle
]
CAP_CLEAR = 0.3                    # per side, cap to carrier collar
COVER_CAP_CLEAR = 0.6              # per side, cap to cover opening (the collar does the guiding)
CAP_PROUD = 0.6                    # cap top above the cover face
COLLAR_T, COLLAR_H = 1.2, 4.0
FLANGE_W, FLANGE_T = 1.5, 1.2
STEM_D, STEM_GAP = 4.0, 0.05
SWITCH_H = 5.0                     # tact switch height above its PCB VERIFY
MARK_DEPTH = 0.4
BOARD_X = (11.5, 44.5)             # button board extents (perfboard about 33 x 73 mm)
BOARD_Y = (-36.5, 36.5)
BOARD_PTS = [(14.0, 34.0), (42.0, 34.0), (14.0, -34.0), (42.0, -34.0)]   # M2 standoffs
SWITCH_TOP = -CAR_T - COLLAR_H - FLANGE_T - STEM_GAP          # z of the switch actuator tops
BOARD_Z = SWITCH_TOP - SWITCH_H                                # z of the board's front face
STANDOFF_LEN = -CAR_T - BOARD_Z

# Mic: INMP441 round breakout (about 14 mm), port facing the room VERIFY
MIC_X, MIC_Y = 28.0, -26.2
MIC_POCKET_ID, MIC_POCKET_H = 14.4, 4.0
MIC_PORT_CARRIER_D, MIC_PORT_COVER_D = 4.0, 2.6
# Status glow, indirect: a small LED lies in a groove in the carrier's front face, under the
# cover and behind the grille cloth, at the top of the speaker opening. It fires sideways across
# the driver cone. There is no window or light pipe; nothing points at the room.
LED_GROOVE_W, LED_GROOVE_DEPTH = 3.2, 1.8
LED_GROOVE_R = (SOUND_HOLE_D / 2 - 0.5, 32.0)     # radial extent from the driver centre, straight up
LED_WIRE_D = 2.5                                   # wire hole through the carrier at the outer end

# Sled posts and sled
POST_D = 7.0
POST_PTS = [(sx * 44.5, sy * 40.2) for sx in (-1, 1) for sy in (-1, 1)]
SLED_Z = -38.0                     # front face of the sled; clears the 30.8 mm deep driver
SLED_T = 2.4
SLED_W, SLED_H, SLED_R = 94.0, 87.0, 5.0
M3_INSERT_D, M3_INSERT_DEPTH = 4.0, 6.0
ESP_BOARD = (26.4, 70.5)           # ESP32-S3-DevKitC-1 footprint; change for a PoE board VERIFY
AMP_BOARD = (19.8, 18.2)           # MAX98357A breakout

# Cover (wall plate)
COVER_T = 3.0
COVER_GAP, COVER_SKIRT_T = 0.3, 2.0
COVER_W = CAR_W + 2 * (COVER_GAP + COVER_SKIRT_T)
COVER_H = CAR_H + 2 * (COVER_GAP + COVER_SKIRT_T)
GRILLE_D = 48.0                    # speaker opening in the cover; cloth is glued behind it
CLOTH_LAND, CLOTH_RELIEF = 5.0, 0.6
MAG_D, MAG_T = 6.0, 2.0            # 6 x 2 mm disc magnets, 4 in the carrier and 4 in the cover
MAG_PTS = [(sx * 50.5, sy * 48.5) for sx in (-1, 1) for sy in (-1, 1)]


# ------------------------------------------------------------------ helpers
def box(x0, x1, y0, y1, z0, z1):
    return M.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl(x, y, z0, z1, d, d2=None, seg=SEG):
    return M.cylinder(z1 - z0, d / 2, (d2 if d2 is not None else d) / 2, seg).translate([x, y, z0])


def rrect(x, y, w, h, r, z0, z1):
    r = min(r, w / 2 - 0.01, h / 2 - 0.01)
    cs = m3.CrossSection.square([w - 2 * r, h - 2 * r], center=True).offset(r, m3.JoinType.Round, circular_segments=32)
    return M.extrude(cs, z1 - z0).translate([x, y, z0])


def union(parts):
    return M.batch_boolean(parts, m3.OpType.Add)


# ------------------------------------------------------------------ box reference
def build_box():
    outer = rrect(0, 0, BOX_W, BOX_H, 4.0, -BOX_DEPTH, 0)
    inner = rrect(0, 0, BOX_IN_W, BOX_IN_H, 3.0, -BOX_DEPTH + BOX_WALL, 1)
    shell = outer - inner
    bosses = []
    for x, y in DEV_PTS:
        sy = 1 if y > 0 else -1
        b = union([cyl(x, y, -BOSS_DEPTH, 0, BOSS_D, seg=32),
                   box(x - BOSS_D / 2, x + BOSS_D / 2, min(y, sy * BOX_IN_H / 2), max(y, sy * BOX_IN_H / 2), -BOSS_DEPTH, 0)])
        bosses.append(b - cyl(x, y, -BOSS_DEPTH - 1, 1, 2.8, seg=20))
    return union([shell] + bosses).translate([0, 0, -CAR_T])     # box front edge = wall surface = back of the carrier


# ------------------------------------------------------------------ carrier
def build_carrier():
    zb = -CAR_T                                   # back face of the plate
    adds = [rrect(0, 0, CAR_W, CAR_H, CAR_R, zb, 0)]
    # driver seat ring and clamp bosses
    adds.append(cyl(DRV_X, DRV_Y, zb - SEAT_H, zb + 0.01, SEAT_OD))
    for x, y in CLAMP_PTS:
        adds.append(cyl(x, y, zb - SEAT_H, zb + 0.01, 6.5, seg=32))
    # button guide collars
    for name, bx, by, bw, bh, r in BUTTONS:
        ow, oh = bw + 2 * CAP_CLEAR, bh + 2 * CAP_CLEAR
        adds.append(rrect(bx, by, ow + 2 * COLLAR_T, oh + 2 * COLLAR_T, r + CAP_CLEAR + COLLAR_T, zb - COLLAR_H, zb + 0.01))
    # button board standoffs
    for x, y in BOARD_PTS:
        adds.append(cyl(x, y, BOARD_Z, zb + 0.01, 5.0, seg=32))
    # mic pocket ring
    adds.append(cyl(MIC_X, MIC_Y, zb - MIC_POCKET_H, zb + 0.01, MIC_POCKET_ID + 3.2))
    # sled posts
    for x, y in POST_PTS:
        adds.append(cyl(x, y, SLED_Z, zb + 0.01, POST_D, seg=40))
    car = union(adds)

    cuts = []
    # device screw holes, countersunk from the front
    for x, y in DEV_PTS:
        cuts.append(cyl(x, y, zb - 1, 1, DEV_HOLE_D, seg=32))
        cuts.append(cyl(x, y, -DEV_CSK_DEPTH, 0.01, DEV_HOLE_D, DEV_CSK_D, seg=32))
    # sound hole and driver seat bore
    cuts.append(cyl(DRV_X, DRV_Y, zb - 1, 1, SOUND_HOLE_D, seg=96))
    cuts.append(cyl(DRV_X, DRV_Y, zb - SEAT_H - 1, zb, SEAT_ID, seg=96))
    for x, y in CLAMP_PTS:
        cuts.append(cyl(x, y, zb - SEAT_H - 0.1, zb - SEAT_H + M2_INSERT_DEPTH, M2_INSERT_D, seg=24))
    # button openings through plate and collar
    for name, bx, by, bw, bh, r in BUTTONS:
        cuts.append(rrect(bx, by, bw + 2 * CAP_CLEAR, bh + 2 * CAP_CLEAR, r + CAP_CLEAR, zb - COLLAR_H - 1, 1))
    # standoff pilots (M2 self-tap)
    for x, y in BOARD_PTS:
        cuts.append(cyl(x, y, BOARD_Z - 1, BOARD_Z + 6, 1.6, seg=16))
    # mic pocket and port
    cuts.append(cyl(MIC_X, MIC_Y, zb - MIC_POCKET_H - 1, zb, MIC_POCKET_ID, seg=48))
    cuts.append(cyl(MIC_X, MIC_Y, zb - 1, 1, MIC_PORT_CARRIER_D, seg=24))
    # LED groove in the front face, from the sound hole straight up, and its wire hole
    cuts.append(box(DRV_X - LED_GROOVE_W / 2, DRV_X + LED_GROOVE_W / 2, DRV_Y + LED_GROOVE_R[0], DRV_Y + LED_GROOVE_R[1],
                    -LED_GROOVE_DEPTH, 0.01))
    cuts.append(cyl(DRV_X, DRV_Y + LED_GROOVE_R[1] - LED_WIRE_D / 2, zb - 1, 0.01, LED_WIRE_D, seg=20))
    # post inserts (M3 heat-set at the post ends)
    for x, y in POST_PTS:
        cuts.append(cyl(x, y, SLED_Z - 1, SLED_Z + M3_INSERT_DEPTH, M3_INSERT_D, seg=24))
    # magnet pockets in the front face
    for x, y in MAG_PTS:
        cuts.append(cyl(x, y, -MAG_T - 0.1, 0.01, MAG_D + 0.2, seg=32))
    # cable notch in the bottom edge of the driver seat for the speaker leads
    cuts.append(box(DRV_X - 3, DRV_X + 3, DRV_Y - SEAT_OD / 2 - 1, DRV_Y - SEAT_ID / 2 + 1, zb - SEAT_H - 1, zb - 1.0))
    return car - union(cuts)


# ------------------------------------------------------------------ sled
def ledge_tray(x0, y0, bw, bl, z0, ledge_h=3.0, ledge=1.6, side_h=3.0, t=1.6):
    """Board rests on two ledges along its long sides. Built upward from z0."""
    parts = []
    for xa in (x0 - t, x0 + bw):
        parts.append(box(xa, xa + t, y0, y0 + bl, z0, z0 + ledge_h + side_h))
    for xa in (x0, x0 + bw - ledge):
        parts.append(box(xa, xa + ledge, y0, y0 + bl, z0, z0 + ledge_h))
    parts.append(box(x0 - t, x0 + bw + t, y0 - t, y0, z0, z0 + ledge_h + side_h))
    return union(parts)


def build_sled_local():
    """Sled in its print orientation: plate on z = 0..SLED_T, trays upward."""
    plate = rrect(0, 0, SLED_W, SLED_H, SLED_R, 0, SLED_T)
    adds = [plate]
    ew, el = ESP_BOARD
    ex0, ey0 = 8.0, -el / 2
    adds.append(ledge_tray(ex0, ey0, ew, el, SLED_T - 0.01))
    aw, al = AMP_BOARD
    ax0, ay0 = -34.0, 14.0
    adds.append(ledge_tray(ax0, ay0, aw, al, SLED_T - 0.01))
    # stiffening rib between the trays
    adds.append(box(-2.0, 0.0, -SLED_H / 2 + 6, SLED_H / 2 - 6, SLED_T - 0.01, SLED_T + 4.0))
    sled = union(adds)
    cuts = []
    for x, y in POST_PTS:
        cuts.append(cyl(x, y, -1, SLED_T + 1, 3.4, seg=24))
    # zip-tie slots: across the ESP32 and amp boards, and a free area for a PoE splitter
    for y in (-22.0, 22.0):
        for x in (ex0 - 4.2, ex0 + ew + 2.2):
            cuts.append(box(x, x + 2.0, y - 2.5, y + 2.5, -1, SLED_T + 1))
    for y in (-30.0, -8.0):
        for x in (-40.0, -12.0):
            cuts.append(box(x, x + 2.0, y - 2.5, y + 2.5, -1, SLED_T + 1))
    # wire pass-through windows (speaker, buttons, mic)
    cuts.append(rrect(-22.0, 39.0, 20.0, 5.0, 2.0, -1, SLED_T + 1))
    cuts.append(rrect(-22.0, -39.0, 20.0, 5.0, 2.0, -1, SLED_T + 1))
    cuts.append(rrect(3.5, 0.0, 5.0, 24.0, 2.0, -1, SLED_T + 1))
    return sled - union(cuts)


def build_sled():
    """Sled placed in the assembly: plate front at SLED_Z, trays toward the back of the box."""
    return build_sled_local().mirror([0, 0, 1]).translate([0, 0, SLED_Z])


# ------------------------------------------------------------------ cover
def build_cover():
    face = rrect(0, 0, COVER_W, COVER_H, CAR_R + COVER_GAP + COVER_SKIRT_T, 0, COVER_T)
    skirt = (rrect(0, 0, COVER_W, COVER_H, CAR_R + COVER_GAP + COVER_SKIRT_T, -CAR_T, 0.01)
             - rrect(0, 0, CAR_W + 2 * COVER_GAP, CAR_H + 2 * COVER_GAP, CAR_R + COVER_GAP, -CAR_T - 1, 1))
    cov = union([face, skirt])
    # soften the front edge
    ch = 1.0
    r = CAR_R + COVER_GAP + COVER_SKIRT_T
    edge = (rrect(0, 0, COVER_W + 2, COVER_H + 2, r + 1, COVER_T - ch, COVER_T + 1)
            - M.hull(union([rrect(0, 0, COVER_W - 2 * ch, COVER_H - 2 * ch, r - ch, COVER_T - 0.01, COVER_T),
                            rrect(0, 0, COVER_W, COVER_H, r, COVER_T - ch - 0.01, COVER_T - ch)])))
    cov = cov - edge
    cuts = []
    cuts.append(cyl(DRV_X, DRV_Y, -1, COVER_T + 1, GRILLE_D, seg=96))
    cuts.append(cyl(DRV_X, DRV_Y, -0.01, CLOTH_RELIEF, GRILLE_D + 2 * CLOTH_LAND, seg=96))   # cloth land on the back
    for name, bx, by, bw, bh, rr in BUTTONS:
        cuts.append(rrect(bx, by, bw + 2 * COVER_CAP_CLEAR, bh + 2 * COVER_CAP_CLEAR, rr + COVER_CAP_CLEAR, -1, COVER_T + 1))
    cuts.append(cyl(MIC_X, MIC_Y, -1, COVER_T + 1, MIC_PORT_COVER_D, seg=24))
    cuts.append(cyl(MIC_X, MIC_Y, -0.01, 0.8, 8.0, seg=32))                 # foam gasket seat around the mic port
    for x, y in MAG_PTS:
        cuts.append(cyl(x, y, -0.01, MAG_T + 0.1, MAG_D + 0.2, seg=32))
    # fingernail notch in the bottom of the skirt
    cuts.append(box(-8, 8, -COVER_H / 2 - 1, -COVER_H / 2 + COVER_SKIRT_T + 0.5, -CAR_T - 1, -CAR_T + 1.6))
    return cov - union(cuts)


# ------------------------------------------------------------------ button caps
def build_cap(name, bx, by, bw, bh, r):
    top = COVER_T + CAP_PROUD
    collar_bot = -CAR_T - COLLAR_H
    body = rrect(bx, by, bw, bh, r, collar_bot, top)
    ch = 0.6
    body = body - (rrect(bx, by, bw + 2, bh + 2, r + 1, top - ch, top + 1)
                   - M.hull(union([rrect(bx, by, bw - 2 * ch, bh - 2 * ch, max(r - ch, 0.5), top - 0.01, top),
                                   rrect(bx, by, bw, bh, r, top - ch - 0.01, top - ch)])))
    fl_top, fl_bot = collar_bot, collar_bot - FLANGE_T
    flange = M.hull(union([rrect(bx, by, bw + 2 * FLANGE_W, bh + 2 * FLANGE_W, r + FLANGE_W, fl_top - 0.4, fl_top),
                           rrect(bx, by, bw, bh, r, fl_bot, fl_bot + 0.01)]))
    core = rrect(bx, by, bw, bh, r, fl_bot, fl_top)
    stem = cyl(bx, by, SWITCH_TOP + STEM_GAP, fl_bot + 0.01, STEM_D, seg=32)
    cap = union([body, flange, core, stem])
    d = MARK_DEPTH
    if name == "TALK":
        mark = M.sphere(24.0, 96).translate([bx, by, top + 24.0 - 0.6])
    elif name == "VOL_DOWN":
        mark = box(bx - 3.2, bx + 3.2, by - 0.6, by + 0.6, top - d, top + 1)
    elif name == "VOL_UP":
        mark = union([box(bx - 3.2, bx + 3.2, by - 0.6, by + 0.6, top - d, top + 1),
                      box(bx - 0.6, bx + 0.6, by - 3.2, by + 3.2, top - d, top + 1)])
    elif name == "BACKGROUND":
        mark = union([box(bx - w, bx + w, by + oy - 0.5, by + oy + 0.5, top - d, top + 1)
                      for w, oy in ((3.2, 2.6), (2.2, 0.0), (1.2, -2.6))])
    else:
        ring = cyl(bx, by, top - d, top + 1, 7.0) - cyl(bx, by, top - d - 1, top + 2, 4.8)
        slash = box(-0.55, 0.55, -3.5, 3.5, top - d, top + 1).rotate([0, 0, 45]).translate([bx, by, 0])
        mark = union([ring, slash])
    return cap - mark


def build_caps():
    return {b[0]: build_cap(*b) for b in BUTTONS}


# ------------------------------------------------------------------ driver clamp ring
def build_ring(assembled=False):
    t = 3.0
    r_in = 23.0            # bears on the back of the driver's front flange VERIFY
    body = cyl(0, 0, 0, t, 2 * 28.0)
    ears = [cyl(CLAMP_R * math.cos(math.radians(a)), CLAMP_R * math.sin(math.radians(a)), 0, t, 8.0, seg=32)
            for a in (45, 135, 225, 315)]
    ring = union([body] + ears) - cyl(0, 0, -1, t + 1, 2 * r_in)
    holes = [cyl(CLAMP_R * math.cos(math.radians(a)), CLAMP_R * math.sin(math.radians(a)), -1, t + 1, 2.4, seg=20)
             for a in (45, 135, 225, 315)]
    ring = ring - union(holes)
    if assembled:
        z_top = -CAR_T - SEAT_H            # ring sits on the seat ring and the driver flange
        ring = ring.translate([DRV_X, DRV_Y, z_top - t])
    return ring


# ------------------------------------------------------------------ dummy components (fit checks, renders)
def dummy_driver():
    zb = -CAR_T
    flange = cyl(DRV_X, DRV_Y, zb - DRV_FLANGE_T, zb, DRV_OD)
    basket = cyl(DRV_X, DRV_Y, zb - 20.0, zb - DRV_FLANGE_T + 0.01, 30.0, 45.0)
    magnet = cyl(DRV_X, DRV_Y, zb - DRV_DEPTH, zb - 20.0 + 0.01, 30.0)
    return union([flange, basket, magnet])


def dummy_button_board():
    board = box(BOARD_X[0], BOARD_X[1], BOARD_Y[0], BOARD_Y[1], BOARD_Z - 1.6, BOARD_Z)
    sw = [union([box(x - 3, x + 3, y - 3, y + 3, BOARD_Z, BOARD_Z + 3.5), cyl(x, y, BOARD_Z + 3.5, SWITCH_TOP, 3.5, seg=24)])
          for n, x, y, *_ in BUTTONS]
    return board, union(sw)


def dummy_esp():
    ew, el = ESP_BOARD
    b = box(8.0, 8.0 + ew, -el / 2, el / 2, SLED_T + 3.0, SLED_T + 4.6)
    b = union([b, box(8.0 + ew / 2 - 9, 8.0 + ew / 2 + 9, -el / 2 + 2, -el / 2 + 27, SLED_T + 4.6, SLED_T + 7.8)])
    return b.mirror([0, 0, 1]).translate([0, 0, SLED_Z])


# ------------------------------------------------------------------ export
def to_trimesh(man):
    mesh = man.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts), process=False)


def flipped(tm):
    """Turn a part over (front face down on the bed) and drop it to z = 0."""
    t = tm.copy()
    t.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    t.apply_translation(-t.bounds[0])
    return t


if __name__ == "__main__":
    import json
    car, cov, sled, caps, ring, bx = build_carrier(), build_cover(), build_sled(), build_caps(), build_ring(True), build_box()
    capu = union(list(caps.values()))
    drv = dummy_driver()
    board, sws = dummy_button_board()
    esp = dummy_esp()

    def vol(a, b):
        return round((a ^ b).volume(), 3)

    checks = {
        "carrier^box": vol(car, bx), "sled^box": vol(sled, bx), "carrier^sled": vol(car, sled),
        "caps^carrier": vol(capu, car), "caps^cover": vol(capu, cov), "cover^carrier": vol(cov, car),
        "caps pressed^carrier": vol(capu.translate([0, 0, -0.5]), car),
        "driver^carrier": vol(drv, car), "driver^sled": vol(drv, sled), "driver^ring": vol(drv, ring),
        "ring^carrier": vol(ring, car), "board^carrier": vol(board, car), "board^caps": vol(board, capu),
        "board^driver": vol(board, drv), "board^ring": vol(board, ring), "esp^box": vol(esp, bx),
        "switches^carrier": vol(sws, car),
    }

    tc, tv, ts, tr, tb = to_trimesh(car), to_trimesh(cov), to_trimesh(sled), to_trimesh(ring), to_trimesh(bx)
    tcap = to_trimesh(capu)
    for name, t in (("_asm_carrier", tc), ("_asm_cover", tv), ("_asm_sled", ts), ("_asm_ring", tr),
                    ("_asm_caps", tcap), ("_asm_driver", to_trimesh(drv)), ("_asm_board", to_trimesh(board)),
                    ("_asm_switches", to_trimesh(sws)), ("_asm_esp", to_trimesh(esp))):
        t.export(name + ".stl")
    tb.export("box_reference.stl")
    flipped(tc).export("carrier.stl")
    flipped(tv).export("cover.stl")
    to_trimesh(build_sled_local()).export("sled.stl")
    to_trimesh(build_ring(False)).export("driver_ring.stl")
    plate, xoff = [], 0.0
    for b in BUTTONS:
        m = flipped(to_trimesh(caps[b[0]]))
        m.apply_translation([xoff, 0, 0])
        xoff += m.extents[0] + 6
        plate.append(m)
    tcp = trimesh.util.concatenate(plate)
    tcp.export("button_caps.stl")

    info = dict(
        cover_mm=[round(COVER_W, 1), round(COVER_H, 1), COVER_T + CAR_T],
        carrier_mm=[CAR_W, CAR_H, CAR_T],
        depth_behind_wall_mm=round(-SLED_Z - CAR_T + SLED_T + 3.0 + 1.6 + 9.0, 1),
        box_depth_mm=BOX_DEPTH,
        board_standoff_len=round(STANDOFF_LEN, 2), switch_top_z=round(SWITCH_TOP, 2),
        watertight={k: v.is_watertight for k, v in dict(carrier=tc, cover=tv, sled=ts, ring=tr, caps=tcap, box=tb).items()},
        print_sizes={k: [round(e, 1) for e in v.extents] for k, v in dict(carrier=tc, cover=tv, sled=ts, caps=tcp).items()},
        interference_mm3=checks,
    )
    print(json.dumps(info, indent=1, default=float))
