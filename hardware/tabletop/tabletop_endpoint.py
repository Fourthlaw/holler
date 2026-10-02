"""
Holler tabletop endpoint enclosure - parametric generator.

Parts (all print on a Bambu Lab A1, 256 x 256 x 256 mm):
  base.stl         tub with folded transmission line + electronics bay (print open side up)
  lid.stl          top plate with five button openings and guide collars, plus the pillars
                   the bottom screws thread into (print top face down)
  button_caps.stl  TALK, VOL-, VOL+, MIC MUTE, BACKGROUND caps (print tops down)
  grille_ring.stl  magnetic grille ring for speaker cloth over the woofer and tweeter,
                   sits flush in the front recess (print face down)

Coordinates (mm): x = width (left to right, viewed from front)
                  y = depth (0 = front face)
                  z = height (0 = bottom of base)

Run:  python3 tabletop_endpoint.py   (needs manifold3d, trimesh, numpy)
Every dimension marked VERIFY should be checked against the part in hand.
"""
import math
import numpy as np
import manifold3d as m3
import trimesh

M = m3.Manifold

# ------------------------------------------------------------------ parameters
W, D = 250.0, 173.0          # outer footprint
WALL = 2.4                   # outer walls
FLOOR = 2.4
IN_H = 78.6                  # internal height of base
HB = FLOOR + IN_H            # top of base walls (63.6)
LID_T = 3.0
IW = 2.0                     # inner (TL) wall thickness

BAY_W = 58.0                 # electronics bay internal width (right side)
SEP_X1 = W - WALL - BAY_W    # inner face of bay / right face of separator wall
SEP_X0 = SEP_X1 - 2.4        # separator wall left face = right end of TL
TL_X0, TL_X1 = WALL, SEP_X0  # TL region in x

# Transmission line legs, front to back (y widths). Last leg takes the remainder.
LEG_W = [53.0, 42.0, 36.0]
TURN_GAP = [44.0, 38.0, 32.0]   # opening at the end of each divider wall

# Driver: Dayton Audio CE70PR-4, 2.5 in. Front-mounted on a recessed baffle.
# Frame is a 70 x 70 mm square with R7 corners; four 4.2 mm holes on a 79 mm circle
# (55.9 mm square pattern). Depth 38.6 mm (41.2 mm with terminals).
DRV_FRAME, DRV_FRAME_R = 70.0, 7.0
DRV_CUT = 64.0               # baffle cutout (spec sheet lists 60 to 63.8; 64 clears the basket) VERIFY
DRV_DEPTH = 41.2
DRV_HOLE_PCD = 79.0
DRV_FLANGE_T = 3.0           # frame flange thickness, sets the counterbore depth VERIFY
DRV_X = 52.0
DRV_Z = HB / 2               # centred on the front face

# Tweeter: Dayton Audio ND16FA-6, 5/8 in. neodymium dome (32.5 mm faceplate, 25 mm cutout,
# 14.5 mm deep). Front-mounted beside the woofer, glued into a shallow counterbore.
TW_X = DRV_X + DRV_FRAME / 2 + 2.0 + 16.25      # faceplate 2 mm clear of the woofer frame
TW_Z = DRV_Z
TW_FACE_D, TW_CUT, TW_FACE_T = 32.5, 25.0, 3.0   # faceplate thickness sets the counterbore VERIFY

# Front recess + magnetic grille ring (one ring, one cloth, covers both drivers)
RECESS_X0 = DRV_X - 46.0
RECESS_X1 = TW_X + 30.0
RECESS_W, RECESS_H, RECESS_R = RECESS_X1 - RECESS_X0, 76.0, 14.0
RECESS_CX = (RECESS_X0 + RECESS_X1) / 2
RECESS_D = 4.5               # ring thickness; ring face ends flush with the front
BAFFLE_T = 5.0               # baffle behind the recess floor
RING_CLEAR = 0.3             # per side, ring to recess
RING_OPEN_D = 64.0           # woofer part of the ring opening
TW_OPEN_D = 30.0             # tweeter part of the ring opening (opening is the hull of the two)
CLOTH_LAND = 5.0             # glue land for the cloth, this far outside the opening
CLOTH_RELIEF_T = 0.6
MAG_D, MAG_T = 6.0, 3.0      # disc magnets, 4 in the ring and 4 in the base
# absolute x, z of the magnets (left pair beside the woofer, right pair beside the tweeter)
MAG_POS = [(DRV_X - 40.5, DRV_Z - 29.0), (DRV_X - 40.5, DRV_Z + 29.0),
           (TW_X + 22.0, DRV_Z - 22.0), (TW_X + 22.0, DRV_Z + 22.0)]
DRV_INSERT_D, DRV_INSERT_DEPTH = 5.6, 6.0    # M4 heat-set inserts for the driver screws

# INMP441 mic module (VERIFY board width / thickness)
MIC_X, MIC_Z = SEP_X1 + 38.4, 40.0
MIC_PORT_D = 2.6
MIC_BOARD_W, MIC_BOARD_T = 14.5, 1.2
# Status light bar: thin-skin slot in the front wall, LEDs behind it
LED_X, LED_Z = SEP_X1 + 15.4, 46.0
LED_W, LED_H = 22.0, 3.5

# Lid buttons: five separate printed caps that travel in guide collars in the lid.
# Each cap has a retaining flange under the collar and a stem that presses a 6x6 mm
# tact switch on the button board. The switch is the return spring.
# (name, centre x, centre y, cap width, cap depth, corner radius)
BTN_CX = (SEP_X1 + W - WALL) / 2
BUTTONS = [
    ("TALK",     BTN_CX,        26.0, 40.0, 24.0, 4.0),
    ("VOL_DOWN", BTN_CX - 12.5, 58.0, 18.0, 14.0, 3.0),
    ("VOL_UP",   BTN_CX + 12.5, 58.0, 18.0, 14.0, 3.0),
    ("MIC_MUTE", BTN_CX - 12.5, 86.0, 18.0, 14.0, 3.0),   # hardware latch
    ("BACKGROUND", BTN_CX + 12.5, 86.0, 18.0, 14.0, 3.0), # software toggle, server can reset it
]
CAP_CLEAR = 0.3              # per side, cap body to lid opening
CAP_PROUD = 0.6              # cap top stands this far above the lid top
COLLAR_T, COLLAR_H = 1.2, 4.0   # guide collar wall and depth below the lid underside
FLANGE_W, FLANGE_T = 1.5, 1.2   # retaining flange: overhang per side, thickness
STEM_D = 4.0
STEM_GAP = 0.05              # stem to switch actuator at rest
SWITCH_H = 5.0               # tact switch height above PCB, actuator top (VERIFY)
MARK_DEPTH = 0.4             # touch marks on the cap tops
BTN_HOLES_X = 49.0           # M2 hole spacing across the button board
BTN_HOLES_Y = (15.5, 99.0)   # M2 hole rows (board about 54 x 91 mm, y 12.5 to 103)
# Board height follows from the cap stack: switch top sits just under the stem.
SWITCH_TOP = (FLOOR + IN_H) - COLLAR_H - FLANGE_T - STEM_GAP
STANDOFF_LEN = (FLOOR + IN_H) - (SWITCH_TOP - SWITCH_H)

# Lid fastening: pillars hang from the lid, M3 screws come up through the floor.
PILLAR_D = 9.0
PILLAR_INSET = WALL + 0.3 + PILLAR_D / 2
SCREW_PTS = [(PILLAR_INSET, WALL + RECESS_D + BAFFLE_T + 0.4 + PILLAR_D / 2), (PILLAR_INSET, D - PILLAR_INSET),
             (W - PILLAR_INSET, PILLAR_INSET), (W - PILLAR_INSET, D - PILLAR_INSET),
             (SEP_X0 - 0.3 - PILLAR_D / 2, PILLAR_INSET), (SEP_X0 - 0.3 - PILLAR_D / 2, D - PILLAR_INSET)]
PAD_D, PAD_H = 11.0, 4.0     # floor pads under each pillar
SOCKET_DEPTH = 1.0           # pillar end locates in a shallow socket in the pad
INSERT_D, INSERT_DEPTH = 4.0, 6.0    # M3 heat-set insert in the bottom of each pillar
CBORE_D, CBORE_DEPTH = 6.2, 3.2      # M3 socket head counterbore from the bottom
PILLAR_SHORT = 0.2           # pillar ends this much short of the socket floor, so screws pull the lid down

# Feet: shallow rings for 12 mm self-adhesive bumpers
FOOT_D, FOOT_DEPTH, FOOT_INSET = 12.6, 0.8, 18.0

# 18650 holder pocket (Keystone 1042 class holder, about 77.5 x 20.5 mm) VERIFY
BAT_W, BAT_L = 21.1, 78.1
BAT_X = W - WALL - 1.6 - 0.4 - BAT_W
BAT_Y = 36.0

SEG = 64


# ------------------------------------------------------------------ helpers
def box(x0, x1, y0, y1, z0, z1):
    return M.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def cyl_z(x, y, z0, z1, d, d2=None, seg=SEG):
    return M.cylinder(z1 - z0, d / 2, (d2 if d2 else d) / 2, seg).translate([x, y, z0])


def cyl_y(x, z, y0, y1, d, seg=SEG):
    # cylinder axis along +y
    return M.cylinder(y1 - y0, d / 2, d / 2, seg).rotate([-90, 0, 0]).translate([x, y0, z])


def tri_prism(p0, p1, p2, z0, z1):
    cs = m3.CrossSection([[p0, p1, p2]])
    return M.extrude(cs, z1 - z0).translate([0, 0, z0])


def union(parts):
    return M.batch_boolean(parts, m3.OpType.Add)


# ------------------------------------------------------------------ TL layout
legs = []
y = WALL
for w in LEG_W:
    legs.append((y, y + w))
    y += w + IW
legs.append((y, D - WALL))
dividers = [(legs[i][1], legs[i][1] + IW) for i in range(3)]

# Path: leg1 closed at the RIGHT end (separator wall), driver near the left,
# turn left -> leg2 runs right -> turn right -> leg3 runs left -> turn left ->
# leg4 runs right -> mouth through the rear wall at the right end.
# Divider 1 gap at left, divider 2 gap at right, divider 3 gap at left.
div_spans = [(TL_X0 + TURN_GAP[0], TL_X1),
             (TL_X0, TL_X1 - TURN_GAP[1]),
             (TL_X0 + TURN_GAP[2], TL_X1)]

MOUTH_X1 = TL_X1 - 11.0           # stop short of the rear pillar
MOUTH_X0 = MOUTH_X1 - 50.0
MOUTH_Z0, MOUTH_Z1 = FLOOR + 3.0, HB - 3.0


def tl_stats():
    h = IN_H
    areas = [(b - a) * h for a, b in legs]
    # centerline length estimate
    cx = [(a + b) / 2 for a, b in legs]
    L = 0.0
    # leg1 from closed end to turn centre, etc.
    turn_x = [TL_X0 + TURN_GAP[0] / 2, TL_X1 - TURN_GAP[1] / 2, TL_X0 + TURN_GAP[2] / 2]
    L += TL_X1 - turn_x[0]
    L += abs(cx[1] - cx[0])
    L += abs(turn_x[1] - turn_x[0])
    L += abs(cx[2] - cx[1])
    L += abs(turn_x[2] - turn_x[1])
    L += abs(cx[3] - cx[2])
    L += (MOUTH_X0 + MOUTH_X1) / 2 - turn_x[2]
    L += (D - WALL - cx[3])  # last bend into the rear mouth
    vol = sum(areas[i] * (TL_X1 - TL_X0) for i in range(4)) / 1e6  # litres (approx)
    drv_offset = TL_X1 - DRV_X
    mouth_area = areas[3]
    r_eq = math.sqrt(mouth_area / math.pi)
    L_eff = L + 0.6 * r_eq
    f = 343000.0 / (4 * L_eff)
    return dict(areas_mm2=areas, length_mm=L, eff_length_mm=L_eff, f_quarter_wave_hz=f,
                volume_l=vol, driver_offset_mm=drv_offset, offset_ratio=drv_offset / L)


# ------------------------------------------------------------------ base
def build_base():
    shell = box(0, W, 0, D, 0, HB) - box(WALL, W - WALL, WALL, D - WALL, FLOOR, HB + 1)
    adds = []

    # separator wall between TL and electronics bay
    adds.append(box(SEP_X0, SEP_X1, WALL, D - WALL, FLOOR, HB))
    # TL divider walls
    for (y0, y1), (x0, x1) in zip(dividers, div_spans):
        adds.append(box(x0, x1, y0, y1, FLOOR, HB))
    # 45 degree deflectors at the outer corners of each turn
    f = 14.0
    corners = [
        # turn 1 (left): only the leg2 corner; the leg1 front-left corner is left
        # square because the driver flange sits there
        ((TL_X0, legs[1][1]), (TL_X0 + f, legs[1][1]), (TL_X0, legs[1][1] - f)),
        # turn 2 (right)
        ((TL_X1, legs[1][0]), (TL_X1 - f, legs[1][0]), (TL_X1, legs[1][0] + f)),
        ((TL_X1, legs[2][1]), (TL_X1 - f, legs[2][1]), (TL_X1, legs[2][1] - f)),
        # turn 3 (left)
        ((TL_X0, legs[2][0]), (TL_X0 + f, legs[2][0]), (TL_X0, legs[2][0] + f)),
        ((TL_X0, legs[3][1]), (TL_X0 + f, legs[3][1]), (TL_X0, legs[3][1] - f)),
    ]
    for p0, p1, p2 in corners:
        # make CCW
        a = np.array(p0); b = np.array(p1); c = np.array(p2)
        u, v = b - a, c - a
        if u[0] * v[1] - u[1] * v[0] < 0:
            p1, p2 = p2, p1
        adds.append(tri_prism(p0, p1, p2, FLOOR, HB))

    # driver seat ring on inside of front wall + clamp bosses
    # recessed baffle: a cup behind the front wall that carries the recess floor
    cup_w, cup_h = RECESS_W + 2 * WALL, RECESS_H + 2 * WALL
    cup = rrect_y(RECESS_CX, DRV_Z, cup_w, cup_h, RECESS_R + WALL, WALL - 0.01, RECESS_D + BAFFLE_T)
    adds.append(cup ^ box(0, W, 0, D, 0, HB))
    drv_holes = [(DRV_X + sx * DRV_HOLE_PCD / 2 / math.sqrt(2), DRV_Z + sz * DRV_HOLE_PCD / 2 / math.sqrt(2))
                 for sx in (-1, 1) for sz in (-1, 1)]
    for hx, hz in drv_holes:
        adds.append(cyl_y(hx, hz, RECESS_D + BAFFLE_T - 0.01, RECESS_D + DRV_FLANGE_T + DRV_INSERT_DEPTH + 1.0, 10.0, seg=32))

    # floor pads under the lid pillars
    for x, yy in SCREW_PTS:
        adds.append(cyl_z(x, yy, FLOOR - 0.01, FLOOR + PAD_H, PAD_D))

    # ---- electronics bay fixtures
    bx0, bx1 = SEP_X1, W - WALL
    # mic gasket ring + slide rails
    adds.append(cyl_y(MIC_X, MIC_Z, WALL, WALL + 1.5, 11.0))
    rail_y0, rail_y1 = WALL, WALL + 6.0
    for side in (-1, 1):
        xr = MIC_X + side * (MIC_BOARD_W / 2 + 0.2)
        xa, xb = (xr, xr + 2.4) if side > 0 else (xr - 2.4, xr)
        adds.append(box(xa, xb, rail_y0, rail_y1, MIC_Z - 11, MIC_Z + 9))
    adds.append(box(MIC_X - MIC_BOARD_W / 2 - 2.6, MIC_X + MIC_BOARD_W / 2 + 2.6,
                    rail_y0, rail_y1, MIC_Z - 13, MIC_Z - 11))       # bottom stop

    # light box behind the light bar (open at the back for the LED board)
    lb = box(LED_X - LED_W / 2 - 2.0, LED_X + LED_W / 2 + 2.0, WALL, WALL + 6.0, LED_Z - LED_H / 2 - 2.0, LED_Z + LED_H / 2 + 2.0)
    lb = lb - box(LED_X - LED_W / 2, LED_X + LED_W / 2, WALL - 0.1, WALL + 6.1, LED_Z - LED_H / 2, LED_Z + LED_H / 2)
    adds.append(lb)

    # amp tray (MAX98357A breakout ~19.4 x 17.8)
    adds.append(ledge_tray(bx0 + 3.5, 14.0, 19.8, 18.2, ledge_h=6.0))           # woofer channel
    adds.append(ledge_tray(bx0 + 3.5 + 19.8 + 4.0, 14.0, 19.8, 18.2, ledge_h=6.0))  # tweeter channel
    # ESP32-S3-DevKitC-1 tray (no mounting holes on that board: ledges + tie slots)
    adds.append(ledge_tray(bx0 + 3.5, 36.0, 26.4, 70.5, ledge_h=10.0))
    # 18650 holder pocket (Keystone 1042 class, ~77.5 x 20.5) VERIFY
    adds.append(pocket(BAT_X, BAT_Y, BAT_W, BAT_L, wall_h=10.0))
    # charger / UPS board tray at rear
    adds.append(ledge_tray(bx0 + 3.5, D - WALL - 26.0, 26.0, 22.0, ledge_h=4.0))
    # USB-C breakout slide frame on rear wall
    usb_x, usb_z = bx0 + 37.0, FLOOR + 9.0
    for side in (-1, 1):
        xr = usb_x + side * (15.0 / 2 + 0.2)
        xa, xb = (xr, xr + 2.0) if side > 0 else (xr - 2.0, xr)
        g = box(xa, xb, D - WALL - 5.0, D - WALL, FLOOR, usb_z + 9)
        adds.append(g)

    base = union([shell] + adds)

    # ---- cuts
    cuts = []
    # front recess for the grille ring
    cuts.append(rrect_y(RECESS_CX, DRV_Z, RECESS_W, RECESS_H, RECESS_R, -1, RECESS_D))
    # pry notch at the bottom edge of the recess (fingernail behind the ring)
    cuts.append(box(RECESS_CX - 8, RECESS_CX + 8, -1, RECESS_D + 1.5, DRV_Z - RECESS_H / 2, DRV_Z - RECESS_H / 2 + 3.0))
    # driver frame counterbore (frame face ends flush with the recess floor)
    cuts.append(rrect_y(DRV_X, DRV_Z, DRV_FRAME + 0.6, DRV_FRAME + 0.6, DRV_FRAME_R + 0.3,
                        RECESS_D - 0.01, RECESS_D + DRV_FLANGE_T))
    # baffle cutout
    cuts.append(cyl_y(DRV_X, DRV_Z, RECESS_D - 1, RECESS_D + BAFFLE_T + 1, DRV_CUT, seg=96))
    # M4 heat-set inserts for the driver screws
    for hx, hz in drv_holes:
        cuts.append(cyl_y(hx, hz, RECESS_D + DRV_FLANGE_T - 0.01, RECESS_D + DRV_FLANGE_T + DRV_INSERT_DEPTH, DRV_INSERT_D, seg=24))
    # tweeter faceplate counterbore + cutout
    cuts.append(cyl_y(TW_X, TW_Z, RECESS_D - 0.01, RECESS_D + TW_FACE_T, TW_FACE_D + 0.6, seg=64))
    cuts.append(cyl_y(TW_X, TW_Z, RECESS_D - 1, RECESS_D + BAFFLE_T + 1, TW_CUT, seg=64))
    # magnet pockets in the recess floor (outside both driver frames)
    for mx, mz in MAG_POS:
        cuts.append(cyl_y(mx, mz, RECESS_D - 0.01, RECESS_D + MAG_T + 0.2, MAG_D + 0.2, seg=32))

    # mouth: vertical slots in rear wall at the end of leg 4
    slot_w, bar_w = 4.0, 1.6
    x = MOUTH_X0
    while x + slot_w <= MOUTH_X1:
        cuts.append(box(x, x + slot_w, D - WALL - 1, D + 1, MOUTH_Z0, MOUTH_Z1))
        x += slot_w + bar_w

    # pillar clearance above the pads, pillar sockets, screw holes, counterbores
    for xx, yy in SCREW_PTS:
        cuts.append(cyl_z(xx, yy, FLOOR + PAD_H - SOCKET_DEPTH, HB + 1, PILLAR_D + 0.4, seg=48))
        cuts.append(cyl_z(xx, yy, -1, FLOOR + PAD_H, 3.4, seg=24))
        cuts.append(cyl_z(xx, yy, -1, CBORE_DEPTH, CBORE_D, seg=32))

    # mic port + gasket bore
    cuts.append(cyl_y(MIC_X, MIC_Z, -1, WALL + 2, MIC_PORT_D, seg=24))
    cuts.append(cyl_y(MIC_X, MIC_Z, WALL, WALL + 2, 8.4, seg=32))
    # mic board slot in rails (board slides down from above)
    cuts.append(box(MIC_X - MIC_BOARD_W / 2 - 1.2, MIC_X + MIC_BOARD_W / 2 + 1.2,
                    WALL + 2.5, WALL + 2.5 + MIC_BOARD_T + 0.3, MIC_Z - 11, MIC_Z + 10))
    # light bar: thin-skin slot (0.6 mm skin left) with a small light box behind it
    cuts.append(box(LED_X - LED_W / 2, LED_X + LED_W / 2, 0.6, WALL + 1, LED_Z - LED_H / 2, LED_Z + LED_H / 2))

    # speaker wire pass-through in separator wall (seal after wiring)
    cuts.append(box(SEP_X0 - 1, SEP_X1 + 1, 20, 24, FLOOR + 4, FLOOR + 8))
    # USB-C receptacle opening in rear wall
    cuts.append(slot_y(usb_x, usb_z, D - WALL - 1, D + 1, 9.6, 4.0))
    # foot rings: shallow seats for self-adhesive bumpers
    for fx in (FOOT_INSET, W - FOOT_INSET):
        for fy in (FOOT_INSET, D - FOOT_INSET):
            cuts.append(cyl_z(fx, fy, -1, FOOT_DEPTH, FOOT_D, seg=48))
    # zip-tie slots through the floor inside the battery pocket (strap the holder down)
    for yy in (BAT_Y + 18.0, BAT_Y + 56.0):
        cuts.append(box(BAT_X + 0.3, BAT_X + 2.3, yy, yy + 4, -1, FLOOR + 1))
        cuts.append(box(BAT_X + BAT_W - 2.3, BAT_X + BAT_W - 0.3, yy, yy + 4, -1, FLOOR + 1))

    base = base - union(cuts)
    return base, drv_holes


def ledge_tray(x0, y0, bw, bl, ledge_h, ledge=1.6, side_h=3.0, t=1.6, pcb_t=1.6):
    """Board sits on two ledges along its long sides; side walls locate it."""
    parts = []
    z0 = FLOOR - 0.01
    for xa in (x0 - t, x0 + bw):
        parts.append(box(xa, xa + t, y0, y0 + bl, z0, FLOOR + ledge_h + side_h))
    for xa in (x0, x0 + bw - ledge):
        parts.append(box(xa, xa + ledge, y0, y0 + bl, z0, FLOOR + ledge_h))
    # end stops
    parts.append(box(x0 - t, x0 + bw + t, y0 - t, y0, z0, FLOOR + ledge_h + side_h))
    # snap lips: 0.6 mm catches just above the PCB top on both side walls
    zl = FLOOR + ledge_h + pcb_t + 0.15
    for frac in (0.25, 0.75):
        yc = y0 + bl * frac
        parts.append(lip_prism(x0, yc - 5, yc + 5, zl, +1))
        parts.append(lip_prism(x0 + bw, yc - 5, yc + 5, zl, -1))
    return union(parts)


def lip_prism(xw, ya, yb, zl, direction, d=0.6, h=1.2):
    """Triangular catch on a wall face: flat underside at zl, sloped top (self-supporting)."""
    # profile in x-z plane, extruded along y
    if direction > 0:
        pts = [(xw, zl), (xw + d, zl), (xw, zl + h)]
    else:
        pts = [(xw, zl), (xw, zl + h), (xw - d, zl)]
    a, b, c = [np.array(p) for p in pts]
    u, v = b - a, c - a
    if u[0] * v[1] - u[1] * v[0] < 0:
        pts = [pts[0], pts[2], pts[1]]
    cs = m3.CrossSection([pts])
    # extrude along z then rotate so profile y->z and extrusion -> y
    p = M.extrude(cs, yb - ya)              # profile in (x, y=z_world), extruded along z
    p = p.rotate([90, 0, 0])                # (x, y, z) -> (x, -z, y)
    return p.translate([0, yb, 0])


def pocket(x0, y0, pw, pl, wall_h, t=1.6):
    outer = box(x0 - t, x0 + pw + t, y0 - t, y0 + pl + t, FLOOR - 0.01, FLOOR + wall_h)
    inner = box(x0, x0 + pw, y0, y0 + pl, FLOOR, FLOOR + wall_h + 1)
    # finger notch on one end
    notch = box(x0 + pw / 2 - 6, x0 + pw / 2 + 6, y0 + pl - 1, y0 + pl + t + 1, FLOOR + 4, FLOOR + wall_h + 1)
    return outer - inner - notch


def slot_y(x, z, y0, y1, w, h, seg=24):
    r = h / 2
    c1 = cyl_y(x - (w / 2 - r), z, y0, y1, h, seg)
    c2 = cyl_y(x + (w / 2 - r), z, y0, y1, h, seg)
    return union([c1, c2, box(x - (w / 2 - r), x + (w / 2 - r), y0, y1, z - r, z + r)])


# ------------------------------------------------------------------ lid + buttons
def rrect(x, y, w, h, r, z0, z1):
    r = min(r, w / 2 - 0.01, h / 2 - 0.01)
    cs = m3.CrossSection.square([w - 2 * r, h - 2 * r], center=True).offset(r, m3.JoinType.Round, circular_segments=32)
    return M.extrude(cs, z1 - z0).translate([x, y, z0])


def build_lid(base=None):
    z0, z1 = HB, HB + LID_T
    plate = box(0, W, 0, D, z0, z1)

    # alignment lip inside the outer walls
    c = 0.3
    lip_t, lip_h = 1.6, 3.0
    lo = box(WALL + c, W - WALL - c, WALL + c, D - WALL - c, z0 - lip_h, z0)
    li = box(WALL + c + lip_t, W - WALL - c - lip_t, WALL + c + lip_t, D - WALL - c - lip_t, z0 - lip_h - 1, z0 + 1)
    lip = lo - li
    notches = [box(SEP_X0 - 0.4, SEP_X1 + 0.4, 0, D, z0 - lip_h - 1, z0)]
    for (y0, y1), (x0, x1) in zip(dividers, div_spans):
        notches.append(box(x0 - 0.4, x1 + 0.4, y0 - 0.4, y1 + 0.4, z0 - lip_h - 1, z0))
    lip = lip - union(notches)
    if base is not None:
        zone = box(0, W, 0, D, z0 - lip_h - 0.5, z0)
        hits = base ^ zone
        lip = lip - union([hits.translate([dx, dy, 0]) for dx, dy in
                           ((0, 0), (0.4, 0), (-0.4, 0), (0, 0.4), (0, -0.4))])

    adds = [plate, lip]
    pillar_bot = FLOOR + PAD_H - SOCKET_DEPTH + PILLAR_SHORT
    for xx, yy in SCREW_PTS:
        adds.append(cyl_z(xx, yy, pillar_bot, z0 + 0.01, PILLAR_D, seg=48))
    stand_pts = [(BTN_CX + sx * BTN_HOLES_X / 2, hy) for sx in (-1, 1) for hy in BTN_HOLES_Y]
    for px, py in stand_pts:
        adds.append(cyl_z(px, py, z0 - STANDOFF_LEN, z0 + 0.01, 5.0, seg=32))
    # guide collars under each button opening
    for name, bx, by, bw, bd, r in BUTTONS:
        ow, od = bw + 2 * CAP_CLEAR, bd + 2 * CAP_CLEAR
        adds.append(rrect(bx, by, ow + 2 * COLLAR_T, od + 2 * COLLAR_T, r + CAP_CLEAR + COLLAR_T,
                          z0 - COLLAR_H, z0 + 0.01))
    lid = union(adds)

    cuts = []
    gd = 1.2
    cuts.append(box(SEP_X0 - 0.4, SEP_X1 + 0.4, WALL, D - WALL, z0 - 0.01, z0 + gd))
    for (y0, y1), (x0, x1) in zip(dividers, div_spans):
        cuts.append(box(x0 - 0.4, x1 + 0.4, y0 - 0.4, y1 + 0.4, z0 - 0.01, z0 + gd))
    for xx, yy in SCREW_PTS:
        cuts.append(cyl_z(xx, yy, pillar_bot - 1, pillar_bot + INSERT_DEPTH, INSERT_D, seg=32))
    for px, py in stand_pts:
        cuts.append(cyl_z(px, py, z0 - STANDOFF_LEN - 1, z0 + 1.0, 1.6, seg=16))
    # button openings through lid and collar, with a small chamfer at the top edge
    for name, bx, by, bw, bd, r in BUTTONS:
        ow, od = bw + 2 * CAP_CLEAR, bd + 2 * CAP_CLEAR
        cuts.append(rrect(bx, by, ow, od, r + CAP_CLEAR, z0 - COLLAR_H - 1, z1 + 1))
        cuts.append(rrect(bx, by, ow + 1.0, od + 1.0, r + CAP_CLEAR + 0.5, z1 - 0.5, z1 + 1))
    lid = lid - union(cuts)
    info = dict(switch_top=round(SWITCH_TOP, 2), standoff_len=round(STANDOFF_LEN, 2),
                standoffs=stand_pts, pillar_len=round(z0 - pillar_bot, 2))
    return lid, info


def build_cap(name, bx, by, bw, bd, r, assembled=True):
    """One button cap in its assembled (rest) position."""
    z0, z1 = HB, HB + LID_T
    top = z1 + CAP_PROUD
    collar_bot = z0 - COLLAR_H
    body = rrect(bx, by, bw, bd, r, collar_bot, top)
    # soften the top edge: 0.6 mm chamfer
    ch = 0.6
    body = body - (rrect(bx, by, bw + 2, bd + 2, r + 1, top - ch, top + 1)
                   - M.hull(union([rrect(bx, by, bw - 2 * ch, bd - 2 * ch, max(r - ch, 0.5), top - 0.01, top),
                                   rrect(bx, by, bw, bd, r, top - ch - 0.01, top - ch)])))
    # retaining flange with a 45 degree underside (prints without support upside down)
    fl_top = collar_bot
    fl_bot = collar_bot - FLANGE_T
    flange = M.hull(union([rrect(bx, by, bw + 2 * FLANGE_W, bd + 2 * FLANGE_W, r + FLANGE_W, fl_top - 0.4, fl_top),
                           rrect(bx, by, bw, bd, r, fl_bot, fl_bot + 0.01)]))
    core = rrect(bx, by, bw, bd, r, fl_bot, fl_top)
    stem = cyl_z(bx, by, SWITCH_TOP + STEM_GAP, fl_bot + 0.01, STEM_D, seg=32)
    cap = union([body, flange, core, stem])
    # touch marks on the cap top
    d = MARK_DEPTH
    if name == "TALK":
        mark = M.sphere(30.0, 96).translate([bx, by, top + 30.0 - 0.6])
    elif name == "VOL_DOWN":
        mark = box(bx - 4, bx + 4, by - 0.6, by + 0.6, top - d, top + 1)
    elif name == "VOL_UP":
        mark = union([box(bx - 4, bx + 4, by - 0.6, by + 0.6, top - d, top + 1),
                      box(bx - 0.6, bx + 0.6, by - 4, by + 4, top - d, top + 1)])
    elif name == "BACKGROUND":
        # three bars fading in length: "turned down, far away"
        mark = union([box(bx - w, bx + w, by + oy - 0.6, by + oy + 0.6, top - d, top + 1)
                      for w, oy in ((4.0, 3.0), (2.75, 0.0), (1.5, -3.0))])
    else:
        ring = cyl_z(bx, by, top - d, top + 1, 8.0) - cyl_z(bx, by, top - d - 1, top + 2, 5.6)
        slash = box(-0.6, 0.6, -4.0, 4.0, top - d, top + 1).rotate([0, 0, 45]).translate([bx, by, 0])
        mark = union([ring, slash])
    return cap - mark


def build_caps():
    return {n: build_cap(n, x, y, w, d, r) for n, x, y, w, d, r in BUTTONS}


# ------------------------------------------------------------------ grille ring
def rrect_y(x, z, w, h, r, y0, y1):
    """Rounded rectangle in the x-z plane, extruded along +y from y0 to y1."""
    r = min(r, w / 2 - 0.01, h / 2 - 0.01)
    cs = m3.CrossSection.square([w - 2 * r, h - 2 * r], center=True).offset(r, m3.JoinType.Round, circular_segments=48)
    return M.extrude(cs, y1 - y0).rotate([-90, 0, 0]).translate([x, y0, z])


def build_grille_ring(assembled=True):
    """Ring sits in the front recess and covers the woofer and tweeter. Cloth is hot-glued
    to its back in a shallow land. Four magnets in the back meet four in the recess floor."""
    w, h = RECESS_W - 2 * RING_CLEAR, RECESS_H - 2 * RING_CLEAR
    cx = RECESS_CX
    ring = rrect_y(cx, DRV_Z, w, h, RECESS_R - RING_CLEAR, 0.0, RECESS_D)
    # soften the front edge
    ring = ring - (rrect_y(cx, DRV_Z, w + 2, h + 2, RECESS_R + 1, -1, 0.5)
                   - M.hull(union([rrect_y(cx, DRV_Z, w - 1.0, h - 1.0, RECESS_R - RING_CLEAR - 0.5, 0.0, 0.01),
                                   rrect_y(cx, DRV_Z, w, h, RECESS_R - RING_CLEAR, 0.5, 0.51)])))
    def opening(grow, y0, y1):
        return M.hull(union([cyl_y(DRV_X, DRV_Z, y0, y1, RING_OPEN_D + 2 * grow, seg=96),
                             cyl_y(TW_X, TW_Z, y0, y1, TW_OPEN_D + 2 * grow, seg=64)]))
    ring = ring - opening(0.0, -1, RECESS_D + 1)
    ring = ring - opening(CLOTH_LAND, RECESS_D - CLOTH_RELIEF_T, RECESS_D + 1)
    for mx, mz in MAG_POS:
        ring = ring - cyl_y(mx, mz, RECESS_D - MAG_T - 0.2, RECESS_D + 1, MAG_D + 0.2, seg=32)
    return ring


# ------------------------------------------------------------------ export
def to_trimesh(man):
    mesh = man.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    f = np.asarray(mesh.tri_verts)
    return trimesh.Trimesh(vertices=v, faces=f, process=False)


if __name__ == "__main__":
    import json, sys
    base, clamp_pts = build_base()
    lid, lid_info = build_lid(base)
    ring = build_grille_ring()

    caps = build_caps()
    tb, tl, tr = to_trimesh(base), to_trimesh(lid), to_trimesh(ring)
    # caps: assembled copy for previews, and a print plate (tops on the bed, spaced out)
    tc = to_trimesh(union(list(caps.values())))
    tc.export("_asm_caps.stl")
    plate, xoff = [], 0.0
    for n, x, y, w, d, r in BUTTONS:
        m = to_trimesh(caps[n])
        m.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
        m.apply_translation(-m.bounds[0] + [xoff, 0, 0])
        xoff += m.extents[0] + 6
        plate.append(m)
    tcp = trimesh.util.concatenate(plate)
    tcp.export("button_caps.stl")
    # export lid flipped (top face on bed) and dropped to z=0
    tl_print = tl.copy()
    tl_print.apply_transform(trimesh.transformations.rotation_matrix(math.pi, [1, 0, 0]))
    tl_print.apply_translation(-tl_print.bounds[0])
    tb.export("base.stl"); tl_print.export("lid.stl")
    tr.export("_asm_ring.stl")
    trp = tr.copy()
    trp.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
    trp.apply_translation(-trp.bounds[0])
    trp.export("grille_ring.stl")
    tb.export("_asm_base.stl"); tl.export("_asm_lid.stl")

    info = dict(
        outer_mm=[W, D, round(HB + LID_T, 1)],
        tl=tl_stats(),
        lid=lid_info,
        watertight=dict(base=tb.is_watertight, lid=tl.is_watertight, ring=tr.is_watertight, caps=tc.is_watertight),
        cap_print_plate_mm=tcp.extents.tolist(),
        bounds=dict(base=tb.extents.tolist(), lid=tl_print.extents.tolist(), ring=tr.extents.tolist()),
        volume_cm3=dict(base=tb.volume / 1000, lid=tl.volume / 1000, ring=tr.volume / 1000),
    )
    print(json.dumps(info, indent=2, default=float))
