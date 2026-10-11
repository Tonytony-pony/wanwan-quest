# -*- coding: utf-8 -*-
"""
フレンチブルドッグ（01〜03）の きりぬき。いちまつ はいけいで、しろい からだと しろマスが
くっつく ため、tools_make_dog_png.py では あしや ふちが ガビガビに なる。
ここでは いちまつの ますめ（かくし）の いちを つかって、くっついた しろマスだけを おとす。

つかいかた:  python tools_make_frenchbulldog.py        （img/frenchbulldog_lv1,lv3,lv5 を うわがき）
  04（そっぽ）と 05（おやこ）は tools_make_dog_png.py の ままで よい。
"""
import os, sys
from collections import deque
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, '.')
import tools_make_dog_png as T

SRC = os.path.join('イラスト犬', 'frenchbulldog')
# 3つめは しろマスと いぬの しろが ほぼ おなじ いろ（255 と 254）なので、マスの いちだけで はんだんする。
# 1・2つめは しろマス（247〜248）が いぬの しろ（252〜254）より わずかに くらい ので いろでも はいけいに できる。
JOBS = [('01', 'lv1', 360, 250, 220), ('02', 'lv3', 400, 250, 216), ('03', 'lv5', 440, 0, 216)]

SAT_MAX = 26
GREY_LO, GREY_HI = 178, 224       # はいマス（かげの 230〜240 は いれない）
PURE_GREY = 0.90                  # マスの なんわりが はいいろなら「はいマス」
WHITE_FILL = 0.95                 # マスの なんわりが しろなら「しろマス こうほ」
ERODE_PX = 5                      # ふちを けずる（2048px のうえで）
SMOOTH_SIGMA = 9.0                # りんかくを なめらかに


GRID_P, GRID_O = 51.2, -1.2       # 2048px を 40マス。ますめの ふちは x = 51.2*k - 1.2


def cell_classes(neutral, mn, grey):
    """ますごとに「はいいろの わりあい」「しろの わりあい」を だす"""
    H, W = grey.shape
    cx = np.floor((np.arange(W) - GRID_O) / GRID_P).astype(int)
    cy = np.floor((np.arange(H) - GRID_O) / GRID_P).astype(int)
    nx, ny = cx.max() + 1, cy.max() + 1
    idx = (cy[:, None] * nx + cx[None, :]).ravel()
    # マスの ふちは JPEG の にじみが あるので、まんなか だけで しらべる
    fx = (((np.arange(W) - GRID_O) / GRID_P) % 1.0) * GRID_P
    fy = (((np.arange(H) - GRID_O) / GRID_P) % 1.0) * GRID_P
    inner = ((fy[:, None] > 7) & (fy[:, None] < GRID_P - 7) &
             (fx[None, :] > 7) & (fx[None, :] < GRID_P - 7)).ravel().astype(float)
    tot = np.bincount(idx, weights=inner, minlength=nx * ny)
    g = np.bincount(idx, weights=grey.ravel() * inner, minlength=nx * ny) / np.maximum(tot, 1)
    w = np.bincount(idx, weights=(neutral & (mn >= 238)).ravel() * inner,
                    minlength=nx * ny) / np.maximum(tot, 1)
    pure = (g >= PURE_GREY).reshape(ny, nx)
    white = (w >= WHITE_FILL).reshape(ny, nx)
    nogrey = (g < 0.05).reshape(ny, nx)
    return pure, white, nogrey, cx, cy


def segment(path, white_hi=0, grey_hi=GREY_HI):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.int16)
    H, W = a.shape[:2]
    mn, mx = a.min(-1), a.max(-1)
    neutral = (mx - mn) <= SAT_MAX
    grey = neutral & (mn >= GREY_LO) & (mn < grey_hi)
    pure, white, nogrey, cx, cy = cell_classes(neutral, mn, grey)
    ny, nx = pure.shape

    def pure_at(j, i):
        if j < 0 or i < 0 or j >= ny or i >= nx:
            return True               # がめんの そとは はいけい あつかい
        return pure[j, i]

    # しろマスの うち、まわりの 2ほう いじょうが はいマスに ふれて いるものは はいけい
    bgwhite_cells = np.zeros((ny, nx), bool)
    fullwhite = np.zeros((ny, nx), bool)
    # はいマスの ならび（ぐうすう/きすう）を しらべる。しろマスは その はんたい。
    par = [0, 0]
    for j in range(ny):
        for i in range(nx):
            if pure[j, i]:
                par[(i + j) % 2] += 1
    white_par = 1 - (0 if par[0] >= par[1] else 1)
    for j in range(ny):
        for i in range(nx):
            if (i + j) % 2 != white_par:
                continue          # はいマスの ならびは いろ（はいいろ）で けすので ここでは さわらない
            # はいいろが ない マス（しろマス、または いぬの ふちが すこし かかった しろマス）で、
            # まわりの 2ほう いじょうが はいマスに ふれて いるものは はいけいの しろマス
            if white[j, i] or nogrey[j, i]:
                n = sum(pure_at(j + dj, i + di) for dj, di in ((1,0),(-1,0),(0,1),(0,-1)))
                if n >= 2:
                    bgwhite_cells[j, i] = True
                    fullwhite[j, i] = bool(white[j, i])
    cellbg = bgwhite_cells[cy[:, None], cx[None, :]]
    cellfull = fullwhite[cy[:, None], cx[None, :]]
    # まるごと しろい マスは いろみの ない ものを ぜんぶ、
    # いぬの ふちが かかった マスは ほとんど まっしろな ところだけ（くろい ふちは まもる）
    inwhite = (cellfull & neutral & (mn >= 200)) | (cellbg & ~cellfull & neutral & (mn >= 232))

    bgpix = grey | inwhite
    if white_hi:
        bgpix = bgpix | (neutral & (mn >= 238) & (mn <= white_hi))
    # ふちから つながる はいけい
    flat = bgpix.ravel()
    seen = np.zeros(H * W, bool)
    q = deque()
    for x in range(W):
        for y in (0, H - 1):
            k = y * W + x
            if flat[k] and not seen[k]:
                seen[k] = True; q.append(k)
    for y in range(H):
        for x in (0, W - 1):
            k = y * W + x
            if flat[k] and not seen[k]:
                seen[k] = True; q.append(k)
    while q:
        k = q.popleft()
        y, x = divmod(k, W)
        if x > 0 and flat[k - 1] and not seen[k - 1]: seen[k - 1] = True; q.append(k - 1)
        if x < W - 1 and flat[k + 1] and not seen[k + 1]: seen[k + 1] = True; q.append(k + 1)
        if y > 0 and flat[k - W] and not seen[k - W]: seen[k - W] = True; q.append(k - W)
        if y < H - 1 and flat[k + W] and not seen[k + W]: seen[k + W] = True; q.append(k + W)
    bg = seen.reshape(H, W)

    # からだに かこまれて のこった はいマス（あなの しろマス・はいマス）。
    # いろみが ほとんど ない（かげの ベージュは ちがう）ものだけ けす。
    flatneu = ((mx - mn) <= 5) & bgpix & ~bg
    # ほそい わっか（めの しろい ふち・みみの ふちの ぼかし）は のこす。
    # 13px の しかくが はいる ふとい かたまり（ますめの ごみ）だけ けす。
    thick = np.asarray(Image.fromarray((flatneu * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(13))) > 127
    thick = thick.ravel()
    hole = np.zeros(H * W, bool)
    f2 = flatneu.ravel()
    seen2 = np.zeros(H * W, bool)
    for s in np.flatnonzero(f2):
        if seen2[s]:
            continue
        comp = [s]; seen2[s] = True; qq = deque([s])
        while qq:
            k = qq.popleft(); y, x = divmod(k, W)
            for nk, ok in ((k - 1, x > 0), (k + 1, x < W - 1), (k - W, y > 0), (k + W, y < H - 1)):
                if ok and f2[nk] and not seen2[nk]:
                    seen2[nk] = True; qq.append(nk); comp.append(nk)
        if len(comp) < 60000 and thick[comp].any():
            hole[comp] = True
    bg = bg | hole.reshape(H, W)

    fg = ~bg
    # くろい ふちの そとがわに のこった しろい かけら（ふちの かかった しろマスの はんぱ）を けす。
    # はいけいに ふれて いて、ちいさい（6000px みまん）しろの かたまりだけ。
    # めの しろい ふち・ひかりは はいけいに ふれない ので のこる。
    whitepix = fg & neutral & (mn >= 238)
    bgdil = np.asarray(Image.fromarray(((~fg) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(7))) > 127
    wf = whitepix.ravel(); bd = bgdil.ravel(); wl = np.zeros(H * W, bool)
    seenw = np.zeros(H * W, bool)
    for s0 in np.flatnonzero(wf):
        if seenw[s0]:
            continue
        comp = [s0]; seenw[s0] = True; qq = deque([s0]); touch = bool(bd[s0])
        while qq:
            k = qq.popleft(); y, x = divmod(k, W)
            for nk, ok in ((k - 1, x > 0), (k + 1, x < W - 1), (k - W, y > 0), (k + W, y < H - 1)):
                if ok and wf[nk] and not seenw[nk]:
                    seenw[nk] = True; qq.append(nk); comp.append(nk)
                    if bd[nk]: touch = True
        if touch and len(comp) < 6000:
            wl[comp] = True
    fg = fg & ~wl.reshape(H, W)
    # さきに ふちを けずる。ますの さかいめの ほそい せんで くっついた しろマスを きりはなす。
    fgi = Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(2 * ERODE_PX + 1))
    # いちばん おおきい かたまりだけ のこす（ちいさい ごみを すてる）
    arr = np.asarray(fgi) > 127
    flatf = arr.ravel(); lab = np.zeros(H * W, np.int32); sizes = []
    for s in np.flatnonzero(flatf):
        if lab[s]:
            continue
        sizes.append(0); n = len(sizes); lab[s] = n; qq = deque([s])
        while qq:
            k = qq.popleft(); sizes[-1] += 1; y, x = divmod(k, W)
            for nk, ok in ((k - 1, x > 0), (k + 1, x < W - 1), (k - W, y > 0), (k + W, y < H - 1)):
                if ok and flatf[nk] and not lab[nk]:
                    lab[nk] = n; qq.append(nk)
    big = max(sizes)
    keep = np.zeros(len(sizes) + 1, bool)
    for n, sz in enumerate(sizes, 1):
        keep[n] = sz >= big * 0.02
    arr = keep[lab].reshape(H, W)
    m = Image.fromarray((arr * 255).astype(np.uint8))
    # りんかくを なめらかに
    m = m.filter(ImageFilter.GaussianBlur(SMOOTH_SIGMA)).point(lambda v: 255 if v > 127 else 0)
    return im, m


def main():
    for stem, pose, th, whi, ghi in JOBS:
        src = os.path.join(SRC, stem + '.jpg')
        print(stem, pose, '...', flush=True)
        im, mask = segment(src, whi, ghi)
        T.finish(im.convert('RGBA'), mask, 'frenchbulldog_%s.png' % pose,
                 th, 'bottom', src, 'ますめ ベース', True)


if __name__ == '__main__':
    main()
