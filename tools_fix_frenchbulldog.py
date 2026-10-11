# -*- coding: utf-8 -*-
"""
フレンチブルドッグ lv1 / lv3 の しあげ。tools_make_frenchbulldog.py の あとに じっこう する。
あたまの てっぺんの しろい すじ（おでこ）が、まわりの しろマスと くっついて
くろい あたまの まるみ より うえに はみだし、ガビガビに なる。
くろい あたまの へりを つないだ まるみで、はみだした しろい ぶぶんを きる。
"""
import numpy as np
from PIL import Image

for name in ('lv1', 'lv3'):
    path = 'img/frenchbulldog_%s.png' % name
    a = np.asarray(Image.open(path).convert('RGBA')).copy()
    H, W = a.shape[:2]
    c = a[..., :3].astype(int)
    lum = c.mean(-1)
    solid = a[..., 3] > 128
    dark = solid & (lum < 110)
    ys, xs = np.where(solid)
    top = ys.min()
    limit = top + int((ys.max() - top) * 0.45)       # あたまの ぶぶんだけ しらべる

    dark_top = np.full(W, -1)
    for x in range(W):
        col = np.where(dark[:limit, x])[0]
        if len(col):
            dark_top[x] = col[0]
    # おでこの すじ：くろい ぶぶんが ない れつ（あたまの うえの ほうに）の いちばん ながい れんぞく
    hasdark = dark_top >= 0
    hassolid = solid[:limit].any(0)
    cx0, cx1 = xs.min() + (xs.max() - xs.min()) // 5, xs.max() - (xs.max() - xs.min()) // 5
    central = dark_top[cx0:cx1][dark_top[cx0:cx1] >= 0]
    ref0 = int(np.percentile(central, 60))          # あたまの まるみの たかさ（めやす）
    stripe = hassolid & ((~hasdark) | (dark_top > ref0 + 25))
    stripe[:cx0] = False; stripe[cx1:] = False
    best, cur0 = (0, 0), None
    for x in range(W + 1):
        if x < W and stripe[x]:
            if cur0 is None: cur0 = x
        else:
            if cur0 is not None and x - cur0 > best[1] - best[0]:
                best = (cur0, x)
            cur0 = None
    xa, xb = best
    if xb - xa < 8:
        print(name, 'おでこが みつからない'); continue
    # りょうがわの くろい あたまの まるみ：すじに ちかい れつは へりが ななめで ふかい ので、
    # すじから すこし はなれた ところで いちばん うえの れつを えらぶ
    def arc_col(rng):
        cand = [x for x in rng if 0 <= x < W and dark_top[x] >= 0]
        ref = min(dark_top[x] for x in cand)
        for x in rng:                                  # すじに ちかい ほうから
            if 0 <= x < W and 0 <= dark_top[x] <= ref + 5:
                return x
        return cand[0]
    xl = arc_col(range(xa - 1, xa - 45, -1))
    xr = arc_col(range(xb, xb + 45))
    yl, yr = dark_top[xl], dark_top[xr]
    n = 0
    for x in range(xl, xr + 1):
        t = (x - xl) / float(max(1, xr - xl))
        y_arc = yl + (yr - yl) * t - 0.07 * (xr - xl) * np.sin(np.pi * t)   # すこし まるく
        y0 = int(round(y_arc))
        # このれつで y0 より うえに ある ふとうめい を けす
        col = a[:y0, x, 3]
        n += int((col > 0).sum())
        a[:y0, x, 3] = 0
    # りょうがわの ちいさな しろい かけら（ふちの そと）
    for x in range(W):
        if xl <= x <= xr or dark_top[x] < 0:
            continue
        seg = a[:dark_top[x], x]
        white = (seg[..., 3] > 0) & (seg[..., :3].astype(int).mean(-1) > 130)
        n += int(white.sum())
        seg[white, 3] = 0
    # ひとりぼっちの ちいさな かけら（80px みまん）を けす
    op = a[..., 3] > 20
    seen = np.zeros_like(op)
    for y0, x0 in zip(*np.where(op)):
        if seen[y0, x0]:
            continue
        comp = [(y0, x0)]; seen[y0, x0] = True; i = 0
        while i < len(comp):
            y, x = comp[i]; i += 1
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and op[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True; comp.append((yy, xx))
        if len(comp) < 80:
            for y, x in comp:
                a[y, x, 3] = 0
    Image.fromarray(a, 'RGBA').save(path, optimize=True)
    print(name, 'おでこ', xa, xb, '/ けした', n, 'px')


# ふちの いろを うちがわの いろで ぬりなおす（はいけいの はいいろが にじんだ ほそい ふちどりを けす）
from PIL import ImageFilter


def decontaminate(path):
    a = np.asarray(Image.open(path).convert('RGBA')).copy()
    alpha = a[..., 3]
    inner = np.asarray(Image.fromarray(((alpha > 250) * 255).astype(np.uint8))
                       .filter(ImageFilter.MinFilter(5))) > 127
    known = inner.copy()
    rgb = a[..., :3].astype(np.float64)
    for _ in range(4):                                # ふちの 4px ぶんを うちがわから ひろげる
        acc = np.zeros_like(rgb); cnt = np.zeros(known.shape)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                k = np.roll(np.roll(known, dy, 0), dx, 1)
                acc += np.roll(np.roll(rgb, dy, 0), dx, 1) * k[..., None]
                cnt += k
        new = (~known) & (cnt > 0) & (alpha > 0)
        rgb[new] = acc[new] / cnt[new][:, None]
        known = known | new
    a[..., :3] = np.clip(rgb + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(a, 'RGBA').save(path, optimize=True)


for name in ('lv1', 'lv3', 'lv5'):
    decontaminate('img/frenchbulldog_%s.png' % name)
    print(name, 'ふちを ぬりなおした')
