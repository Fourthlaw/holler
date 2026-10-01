import math, numpy as np, trimesh, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import tabletop_endpoint as T

base = trimesh.load("_asm_base.stl")
lid = trimesh.load("_asm_lid.stl")
ring = None


def shade(ax, mesh, color, light=(0.3, -0.6, 0.75), alpha=1.0):
    tris = mesh.triangles
    n = mesh.face_normals
    l = np.array(light) / np.linalg.norm(light)
    k = np.clip(n @ l, 0, 1) * 0.65 + 0.35
    c = np.array(matplotlib.colors.to_rgb(color))
    cols = np.clip(k[:, None] * c[None, :], 0, 1)
    pc = Poly3DCollection(tris, facecolors=cols, edgecolors="none", alpha=alpha)
    ax.add_collection3d(pc)


def setup(ax, elev, azim, lim):
    (x0, x1), (y0, y1), (z0, z1) = lim
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_zlim(z0, z1)
    ax.set_box_aspect((x1 - x0, y1 - y0, z1 - z0))
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()


# 1. base iso, open top (TL visible)
fig = plt.figure(figsize=(12, 8), dpi=130)
ax = fig.add_subplot(111, projection="3d")
shade(ax, base, "#c9ccd1")
setup(ax, 48, -62, ((0, 200), (0, 135), (0, 64)))
ax.set_title("Base: folded transmission line (left) and electronics bay (right)", fontsize=13)
plt.tight_layout(); plt.savefig("renders/render_base_iso.png", bbox_inches="tight"); plt.close()

# 2. front view assembly (lid on) iso from front-left low
fig = plt.figure(figsize=(12, 7), dpi=130)
ax = fig.add_subplot(111, projection="3d")
shade(ax, base, "#3a3f46", light=(-0.2, -0.9, 0.4))
shade(ax, lid, "#4a5059", light=(-0.2, -0.9, 0.4))
setup(ax, 18, -70, ((0, 200), (0, 135), (0, 67)))
ax.set_title("Assembled, front view (driver grille left, mic port and LED window right)", fontsize=13)
plt.tight_layout(); plt.savefig("renders/render_front.png", bbox_inches="tight"); plt.close()

# 3. lid underside
lu = lid.copy()
fig = plt.figure(figsize=(12, 8), dpi=130)
ax = fig.add_subplot(111, projection="3d")
shade(ax, lu, "#c9ccd1", light=(0.3, -0.5, -0.8))
setup(ax, -45, -62, ((0, 200), (0, 135), (52, 67)))
ax.set_title("Lid underside: wall grooves, alignment lip, button standoffs and plunger nubs", fontsize=13)
plt.tight_layout(); plt.savefig("renders/render_lid_under.png", bbox_inches="tight"); plt.close()

# 4. annotated plan section at mid height
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
SEC_Z = 12.0
bm, _ = T.build_base()
polys = bm.slice(SEC_Z).to_polygons()
verts, codes = [], []
for p in polys:
    p = np.asarray(p)
    verts += list(p) + [p[0]]
    codes += [MPath.MOVETO] + [MPath.LINETO] * (len(p) - 1) + [MPath.CLOSEPOLY]
fig, ax = plt.subplots(figsize=(14, 11), dpi=130)
ax.add_patch(PathPatch(MPath(verts, codes), fc="#5b6370", ec="none"))
ax.set_aspect("equal")

legs = T.legs
# path arrows
mid = [(a + b) / 2 for a, b in legs]
tg = T.TURN_GAP
X0, X1 = T.TL_X0, T.TL_X1
path = [(X1 - 4, mid[0]), (X0 + tg[0] / 2, mid[0]), (X0 + tg[0] / 2, mid[1]),
        (X1 - tg[1] / 2, mid[1]), (X1 - tg[1] / 2, mid[2]), (X0 + tg[2] / 2, mid[2]),
        (X0 + tg[2] / 2, mid[3]), ((T.MOUTH_X0 + T.MOUTH_X1) / 2, mid[3]),
        ((T.MOUTH_X0 + T.MOUTH_X1) / 2, T.D + 6)]
px, py = zip(*path)
ax.plot(px, py, color="#e07a1f", lw=2.2, zorder=5)
for (xa, ya), (xb, yb) in zip(path[:-1], path[1:]):
    ax.annotate("", xy=((xa + xb) / 2 + (xb - xa) * 0.05, (ya + yb) / 2 + (yb - ya) * 0.05),
                xytext=((xa + xb) / 2, (ya + yb) / 2),
                arrowprops=dict(arrowstyle="-|>", color="#e07a1f", lw=2), zorder=6)
ax.add_patch(plt.Circle((T.DRV_X, 30), 3, color="#e07a1f", zorder=6))

st = T.tl_stats()
def lab(x, y, s, **k):
    ax.text(x, y, s, fontsize=9.5, ha="center", va="center",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#999", lw=0.6), zorder=7, **k)

lab(T.DRV_X, -10, "Driver (CE70PR-4), front-firing")
lab(X1 - 22, mid[0] + 8, "closed end\n(stuff here)")
for i, (a, b) in enumerate(legs):
    lab(100, mid[i] - 7 if i else mid[0] + 9, f"leg {i+1}: {b-a:.0f} mm  ({st['areas_mm2'][i]/100:.0f} cm²)")
lab((T.MOUTH_X0 + T.MOUTH_X1) / 2, T.D + 13, "mouth (rear slots)")
bx = (T.SEP_X1 + T.W - T.WALL) / 2
lab(bx + 12, 2.4 - 8, "mic port + LED window")
lab(T.SEP_X1 + 13.5, 16, "amp")
lab(T.SEP_X1 + 16.5, 85, "ESP32-S3\nDevKitC-1")
lab(T.W - T.WALL - 13, 85, "18650\nholder")
lab(T.SEP_X1 + 16.5, T.D - 15, "charger /\nUPS")
lab(T.SEP_X1 + 37, T.D + 6, "USB-C")
ax.text(T.W / 2, -22, f"Plan section at z = 12 mm   |   line length about {st['length_mm']:.0f} mm, "
        f"quarter-wave about {st['f_quarter_wave_hz']:.0f} Hz, driver offset {st['offset_ratio']*100:.0f}% of length",
        ha="center", fontsize=10.5)
ax.set_xlim(-8, T.W + 8); ax.set_ylim(T.D + 20, -28)
ax.set_axis_off()
plt.tight_layout(); plt.savefig("renders/render_plan.png", bbox_inches="tight"); plt.close()
print("ok")
