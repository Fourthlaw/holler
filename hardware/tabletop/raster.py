"""Small z-buffer renderer for the enclosure previews (orthographic, flat shaded, with outlines)."""
import math, numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont


def rot(elev, azim):
    a, e = math.radians(azim), math.radians(elev)
    # camera looks from direction (azim around z, elevation above xy plane)
    Rz = np.array([[math.cos(a), -math.sin(a), 0], [math.sin(a), math.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, math.cos(e), -math.sin(e)], [0, math.sin(e), math.cos(e)]])
    # rotate world so view dir aligns with -y screen depth: screen x = X, screen y = Z, depth = Y
    return Rx @ Rz


def render(meshes, elev, azim, size=(1600, 1100), light=(0.35, -0.75, 0.55), margin=40):
    R = rot(elev, azim)
    allv = np.vstack([(m.vertices @ R.T) for m, _ in meshes])
    mn, mx = allv.min(0), allv.max(0)
    W, H = size
    s = min((W - 2 * margin) / (mx[0] - mn[0]), (H - 2 * margin) / (mx[2] - mn[2]))
    ox = (W - s * (mx[0] - mn[0])) / 2
    oy = (H - s * (mx[2] - mn[2])) / 2
    zbuf = np.full((H, W), np.inf)
    img = np.ones((H, W, 3))
    nid = np.full((H, W), -1, dtype=np.int64)
    L = np.array(light) / np.linalg.norm(light)
    fid0 = 0
    for mesh, color in meshes:
        v = mesh.vertices @ R.T
        px = (v[:, 0] - mn[0]) * s + ox
        py = H - ((v[:, 2] - mn[2]) * s + oy)
        dz = v[:, 1]  # larger y = farther
        n = mesh.face_normals @ R.T
        col = np.array(color)
        for fi, (a, b, c) in enumerate(mesh.faces):
            x = np.array([px[a], px[b], px[c]]); y = np.array([py[a], py[b], py[c]]); z = np.array([dz[a], dz[b], dz[c]])
            x0, x1 = int(max(0, math.floor(x.min()))), int(min(W - 1, math.ceil(x.max())))
            y0, y1 = int(max(0, math.floor(y.min()))), int(min(H - 1, math.ceil(y.max())))
            if x1 < x0 or y1 < y0:
                continue
            den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(den) < 1e-12:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
            w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not inside.any():
                continue
            zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            upd = inside & (zz < sub)
            if not upd.any():
                continue
            nn = n[fi]
            k = abs(nn @ L) * 0.6 + 0.4 if True else 1
            sub[upd] = zz[upd]
            img[y0:y1 + 1, x0:x1 + 1][upd] = np.clip(col * k, 0, 1)
            nid[y0:y1 + 1, x0:x1 + 1][upd] = fid0 + fi
        fid0 += len(mesh.faces)
    # outlines: depth discontinuities
    zb = np.where(np.isinf(zbuf), zbuf[~np.isinf(zbuf)].max() + 50, zbuf)
    edge = np.zeros((H, W), bool)
    thr = 2.0 / s * 3
    dzx = np.abs(np.diff(zb, axis=1)) > thr
    dzy = np.abs(np.diff(zb, axis=0)) > thr
    edge[:, 1:] |= dzx; edge[1:, :] |= dzy
    # crease edges: big normal change
    img[edge] = img[edge] * 0.35
    return Image.fromarray((img * 255).astype(np.uint8)), (R, mn, s, ox, oy, H)


def project(pt, ctx):
    R, mn, s, ox, oy, H = ctx
    v = np.array(pt) @ R.T
    return ((v[0] - mn[0]) * s + ox, H - ((v[2] - mn[2]) * s + oy))


def label(img, items, title=None):
    d = ImageDraw.Draw(img)
    try:
        f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        ft = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 26)
    except Exception:
        f = ft = ImageFont.load_default()
    for (x, y), (tx, ty), text in items:
        d.line([(x, y), (tx, ty)], fill=(224, 122, 31), width=3)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(224, 122, 31))
        bb = d.textbbox((tx, ty), text, font=f, anchor="mm")
        d.rectangle([bb[0] - 8, bb[1] - 6, bb[2] + 8, bb[3] + 6], fill="white", outline=(150, 150, 150))
        d.text((tx, ty), text, fill=(30, 30, 30), font=f, anchor="mm")
    if title:
        d.text((img.width / 2, 28), title, fill=(30, 30, 30), font=ft, anchor="mm")
    return img
