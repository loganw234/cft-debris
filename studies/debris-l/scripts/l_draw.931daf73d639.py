# l_draw.py - cft-debris (DEBRIS-L): projection and drawing of the tracked population with numpy; no map, no font file.
# cft-debris, MIT licence (see LICENSE at the repository root). Written by DEBRIS-L, 2026-11-23.
#
# Views are inertial, as M1's states are. TOP: looking down on the north pole, column = x, row = -y (x right, y up),
# a point with z < 0 inside the Earth's disc is hidden. EDGE: looking along +y from the -y side, column = x, row = -z,
# a point with y > 0 inside the Earth's disc is hidden. A point is a 3 x 3 block centred on its pixel
# (column = floor(cx + x s + 1/2), row = floor(cy -/+ v s + 1/2), x, v in km, s in pixels a km).
import numpy as np

import l_font
import l_lib as L

W, H = 1280, 720
BG = (6, 8, 16)
EARTH = (22, 52, 104)
LIMB = (70, 120, 200)
WHITE = (230, 235, 245)
GREY = (140, 150, 170)

# layout name -> list of (view, centre column, centre row, pixels a km)
LAYOUTS = {
    "both": [("top", 320, 380, 0.04), ("edge", 960, 380, 0.04)],
    "top": [("top", 640, 380, 0.045)],
    "edge": [("edge", 640, 380, 0.045)],
}


def project(pos_km, view, cx, cy, s):
    """(column, row, depth_hidden_axis) of positions (N, 3) in km, integer pixel arrays"""
    x = pos_km[:, 0]
    v = pos_km[:, 1] if view == "top" else pos_km[:, 2]
    col = np.floor(cx + x * s + 0.5).astype(np.int64)
    row = np.floor(cy - v * s + 0.5).astype(np.int64)
    return col, row


def hidden_mask(pos_km, view):
    if view == "top":
        return (pos_km[:, 2] < 0) & (pos_km[:, 0] ** 2 + pos_km[:, 1] ** 2 < L.EARTH_R_KM ** 2)
    return (pos_km[:, 1] > 0) & (pos_km[:, 0] ** 2 + pos_km[:, 2] ** 2 < L.EARTH_R_KM ** 2)


def _disc(img, cx, cy, r):
    yy, xx = np.ogrid[:img.shape[0], :img.shape[1]]
    d2 = (xx - cx) ** 2 + (yy - cy) ** 2
    img[d2 <= r * r] = EARTH
    img[(d2 <= r * r) & (d2 > (r - 1.6) ** 2)] = LIMB


def draw_dots(img, col, row, colors, half=1):
    """3 x 3 blocks (half = 1) at the pixels; points outside the image are skipped; later points overwrite earlier ones"""
    h, w = img.shape[:2]
    for dy in range(-half, half + 1):
        for dx in range(-half, half + 1):
            c, r = col + dx, row + dy
            ok = (c >= 0) & (c < w) & (r >= 0) & (r < h)
            img[r[ok], c[ok]] = colors[ok]


def group_order(gidx):
    """stable draw order: fengyun first, stations last"""
    return np.argsort(gidx, kind="stable")


def render(pos_km, gidx, layout, lines=(), caption="", show=None, with_earth=True, bg=True, legend=True, counts=None, labels=True):
    """pos_km (N, 3) float km; gidx (N,) int index into L.GROUPS; show: optional boolean (N,) filter.
    Returns (img, info) with info[view] = dict(col, row, drawn) per object (drawn false for hidden or filtered or off-image)"""
    img = np.zeros((H, W, 3), dtype=np.uint8)
    if bg:
        img[:] = BG
    n = len(pos_km)
    pal = np.array([L.GROUP_COLOR[g] for g in L.GROUPS], dtype=np.uint8)
    info = {}
    order = group_order(gidx)
    for view, cx, cy, s in LAYOUTS[layout]:
        if with_earth:
            _disc(img, cx, cy, int(round(L.EARTH_R_KM * s)))
        col, row = project(pos_km, view, cx, cy, s)
        hid = hidden_mask(pos_km, view) if with_earth else np.zeros(n, dtype=bool)
        vis = ~hid
        if show is not None:
            vis &= show
        inimg = (col >= 1) & (col < W - 1) & (row >= 1) & (row < H - 1)
        drawn = vis & inimg
        idx = order[drawn[order]]
        draw_dots(img, col[idx], row[idx], pal[gidx[idx]])
        info[view] = {"col": col, "row": row, "drawn": drawn}
        if labels:
            name = "TOP: NORTH POLE, X RIGHT, Y UP" if view == "top" else "EDGE-ON: X RIGHT, Z UP"
            l_font.draw_text(img, cx - 150, 8 + 18 * len(lines) + 20, name, GREY, 2)
    y = 8
    for ln in lines:
        l_font.draw_text(img, 12, y, ln, WHITE, 2)
        y += 18
    if legend:
        xx = 12
        for gi, g in enumerate(L.GROUPS):
            img[y + 1:y + 11, xx:xx + 10] = L.GROUP_COLOR[g]
            lab = L.GROUP_LABEL[g] + ("" if counts is None else " %d" % counts[gi])
            xx += 18 + l_font.draw_text(img, xx + 14, y, lab, WHITE, 2) + 6
    if caption:
        l_font.draw_text(img, 12, H - 18, caption, GREY, 2)
    return img, info
