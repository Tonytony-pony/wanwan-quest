import sys, numpy as np
from PIL import Image, ImageFilter

ROOT = 'img/'
OUT = sys.argv[1] if len(sys.argv) > 1 else ROOT
CFG = {'lv1': 16, 'lv3': 10, 'lv5': 16, 'sad': 10}

def close(mask, r):
    im = Image.fromarray((mask * 255).astype(np.uint8))
    k = 2 * r + 1
    im = im.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))
    return np.asarray(im) > 127

def fill_color(rgb, known, iters=60):
    rgb = rgb.astype(np.float64).copy()
    known = known.copy()
    for _ in range(iters):
        if known.all():
            break
        acc = np.zeros_like(rgb); cnt = np.zeros(known.shape)
        for dy, dx in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1)):
            k = np.roll(np.roll(known, dy, 0), dx, 1)
            c = np.roll(np.roll(rgb, dy, 0), dx, 1)
            acc += c * k[..., None]; cnt += k
        new = (~known) & (cnt > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        known = known | new
    return rgb

SPAN = {'lv1': 0.74, 'lv5': 0.80}   # この たかさ いかは よこに ぜんぶ うめる（まえむきの あし）

def smooth(v, k):
    out = v.copy()
    for i in range(len(v)):
        w = v[max(0, i - k): i + k + 1]
        out[i] = int(np.median(w))
    return out

for name, rb in CFG.items():
    im = Image.open(ROOT + f'frenchbulldog_{name}.png').convert('RGBA')
    a = np.asarray(im).astype(np.uint8)
    alpha = a[..., 3]
    solid = alpha > 128
    H, W = solid.shape
    ys, xs = np.where(solid)
    top, bot = ys.min(), ys.max()
    y_low = int(top + (bot - top) * 0.60)
    low = np.zeros_like(solid); low[y_low:, :] = True
    closed = close(solid, 4) | (close(solid, rb) & low)
    if name in SPAN:
        y0 = int(top + (bot - top) * SPAN[name])
        L = np.full(H, -1); R = np.full(H, -1)
        for y in range(y0, bot + 1):
            xx = np.where(closed[y])[0]
            if len(xx): L[y], R[y] = xx.min(), xx.max()
        rows = np.arange(y0, bot - 14)
        Ls = smooth(L[y0:bot + 1], 7); Rs = smooth(R[y0:bot + 1], 7)
        base = bot - 16
        for j, y in enumerate(range(y0, bot + 1)):
            l, r = Ls[j], Rs[j]
            if y > base:                      # したの かどを まるく
                t = (y - base) / 16.0
                inset = int(round(12 * (1 - np.sqrt(max(0.0, 1 - t * t)))))
                l += inset; r -= inset
            if l >= 0 and r > l:
                closed[y, l:r + 1] = True
    closed[bot + 1:, :] = False
    add = closed & ~solid
    rgb = fill_color(a[..., :3], solid)
    out = a.copy()
    out[..., :3][add] = np.clip(rgb[add], 0, 255).astype(np.uint8)
    # したの あたりの しろい ぶぶんは まっしろに そろえる（いちまつの ごみを けす）
    c = out[..., :3].astype(int)
    sat = c.max(-1) - c.min(-1); val = c.max(-1)
    white = closed & low & (sat < 28) & (val > 130)
    out[..., :3][white] = 255
    m = Image.fromarray((closed * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0))
    m = np.asarray(m).astype(np.float64) / 255
    al = np.where(closed, np.maximum(m, alpha / 255.0), alpha / 255.0)
    al = np.where(closed & (solid | add), np.maximum(al, np.where(add, m, 1.0) * (1 if True else 0)), al)
    out[..., 3] = np.clip(al * 255 + 0.5, 0, 255).astype(np.uint8)
    out[..., 3][~closed] = np.minimum(out[..., 3][~closed], alpha[~closed])
    Image.fromarray(out, 'RGBA').save(OUT + f'frenchbulldog_{name}.png')
    print(name, int(add.sum()), 'px added')
