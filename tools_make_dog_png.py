# -*- coding: utf-8 -*-
"""
イラスト犬/<いぬしゅ>/01〜04.jpg  ->  img/<いぬしゅ>_lv1,_lv3,_lv5,_sad.png
イラスト犬/paw.jpg                ->  img/paw.png

Geminiの しゅつりょくを JPGで ほぞんすると、とうめいぶぶんが
「いちまつもよう」として やきこまれて しまう。
このスクリプトは そのもようを けして とうめいに もどし、
アプリで つかいやすい おおきさに そろえて PNGに する。

やること:
  1. がめんの ふちから ぬりつぶして「はいけい（むちゃくしょくで あかるい）」を みつける
  2. ちいさすぎる ゴミを すてる（あしあとの ように はなれた かたちは のこす）
  3. ふちを 2ドット けずって JPGの にじみを とる
  4. 512x512 の キャンバスに はいち。いぬは したそろえ、あしあとは まんなか
     （あしもとの たかさを そろえるので、レベルアップで がぞうが とばない）

つかいかた:
  python tools_make_dog_png.py              ぜんぶ
  python tools_make_dog_png.py shiba        しばいぬ だけ
  python tools_make_dog_png.py paw          あしあと だけ
  python tools_make_dog_png.py items        アイテム だけ
"""
import os, sys
from collections import deque
from PIL import Image, ImageFilter, ImageChops

SRC_ROOT = 'イラスト犬'
OUT_DIR  = 'img'
CANVAS   = 512          # しゅつりょくの おおきさ
BOTTOM   = 496          # あしもとの いち（したから 16ドット あける）
MARGIN_X = 16

# もとファイル -> しゅつりょくの すえおき, たかさ
POSES = [
    ('01', 'lv1', 360),   # こいぬ    （レベル 1〜2）
    ('02', 'lv3', 400),   # わんこ    （レベル 3〜4）
    ('03', 'lv5', 440),   # でんせつ  （レベル 5〜）
    ('04', 'sad', 400),   # そっぽを むいた すがた
    # おやこ（レベル15〜）。たかさは 03 と おなじ 440。
    # おやいぬの せたけを そろえる ため。こいぬは よこに ふえるだけ。
    ('05', 'lv15', 440),  # おやこ    （レベル 15〜。ない いぬしゅは とばす）
]
EXTS = ('.jpg', '.jpeg', '.png', '.webp')   # どの かたちで ほぞんしても OK

# アイテム（いぬ小屋・ごはん・ボール・メダル）。おおきさは たかさで そろえる。
ITEM_DIR = 'items'
ITEMS = [
    ('house', 320),   # いぬ小屋
    ('bowl',  150),   # ごはんの おさら
    ('ball',  150),   # ボール
    ('medal', 220),   # きんの メダル
]

def find_src(folder, stem):
    for e in EXTS:
        f = os.path.join(folder, stem + e)
        if os.path.isfile(f):
            return f
    return None

# はいけい はんてい: いろみが なくて「はいいろ」の ドット
#   いちまつもようの はいマス = 214 / したじの ベタ = 211  -> はいけい
#   いぬの しろい からだ     = 253 / いちまつの しろマス = 255 -> はいけいに しない
# しろマスは よこと たてで となりあわない（ななめだけ）ので、
# ちいさい かたまりの まま のこり、あとの 2% フィルタで おちる。
SAT_MAX   = 26          # R,G,B の さ が これいか なら むちゃくしょく
LIGHT_MIN = 178         # いちばん くらい チャンネルが これいじょう なら あかるい
WHITE_MIN = 249         # これいじょう しろい ものは いぬの しろ かも しれないので のこす
ERODE     = 2           # ふちを けずる ドットすう
MIN_BLOB_RATIO = 0.02   # いちばん おおきい かたまりの 2% いじょう なら のこす
SEPARATE  = 6           # いちまつの しろマスと いぬの ほそい つながりを きる ドットすう
CHROMA_TOL = 120        # グリーンバックの ゆるさ（いろの ずれ）


def is_bg(px):
    r, g, b = px[0], px[1], px[2]
    if max(r, g, b) - min(r, g, b) > SAT_MAX:
        return False                      # いろが ついている -> いぬ
    m = min(r, g, b)
    return LIGHT_MIN <= m < WHITE_MIN     # はいいろ だけ はいけい。まっしろは のこす


def key_color(im):
    """よすみを みて、たんしょくの はいけい（グリーンバックなど）か しらべる。
    そうなら その いろを、ちがえば None を かえす。"""
    w, h = im.size
    px = im.load()
    pts = [px[4, 4], px[w - 5, 4], px[4, h - 5], px[w - 5, h - 5]]
    r = sum(p[0] for p in pts) // 4
    g = sum(p[1] for p in pts) // 4
    b = sum(p[2] for p in pts) // 4
    for q in pts:                        # よすみが そろって いない = べつの はいけい
        if abs(q[0] - r) > 30 or abs(q[1] - g) > 30 or abs(q[2] - b) > 30:
            return None
    if max(r, g, b) - min(r, g, b) < 60:  # いろみが よわい = はいいろ／いちまつ
        return None
    return (r, g, b)


def detect_grid(im):
    """いちまつもようの ますの おおきさと ずれを しらべる。
    がめんの はしを はしって、しろマスと はいマスの きりかわる いちを ひろう。"""
    w, h = im.size
    px = im.load()

    def scan(get):
        edges, prev = [], None
        for t in range(len(get.rng)):
            r, g, b = get(t)
            if max(r, g, b) - min(r, g, b) > SAT_MAX:
                prev = None; continue
            v = 1 if min(r, g, b) >= 240 else 0
            if prev is not None and v != prev:
                edges.append(t)
            prev = v
        return edges

    class H:
        rng = range(w)
        def __call__(self, t): return px[t, 2]
    class V:
        rng = range(h)
        def __call__(self, t): return px[2, t]

    ex, ey = scan(H()), scan(V())
    if len(ex) < 4 or len(ey) < 4:
        return None
    d = sorted([ex[i+1] - ex[i] for i in range(len(ex) - 1)] +
               [ey[i+1] - ey[i] for i in range(len(ey) - 1)])
    P = d[len(d) // 2]
    if P < 8 or P > 250:
        return None
    return P, ex[0] % P, ey[0] % P


def checker_mask(im):
    """いちまつの しろマスの ばしょに 1 を たてた マスク。

    しろマスは「まわりを はいマスに かこまれた まっしろな ましかく」。
    いぬの しろい からだは まわりも しろい ので、この じょうけんで はずれる。
    """
    w, h = im.size
    px = im.load()
    m = bytearray(w * h)
    grid = detect_grid(im)
    if not grid:
        return m, 0
    P, offx, offy = grid

    xs = list(range(offx - P, w + P, P))
    ys = list(range(offy - P, h + P, P))
    W, H = len(xs), len(ys)

    def cell_kind(x0, y0):
        """0=それいがい  1=まっしろな ましかく  2=はいいろの ましかく"""
        vals = []
        for dy in (P // 4, P // 2, P * 3 // 4):
            for dx in (P // 4, P // 2, P * 3 // 4):
                x, y = x0 + dx, y0 + dy
                if not (0 <= x < w and 0 <= y < h):
                    return 2                      # がめんの そとは はいけい あつかい
                r, g, b = px[x, y]
                if max(r, g, b) - min(r, g, b) > SAT_MAX:
                    return 0                      # いろが ついている
                vals.append(min(r, g, b))
        if max(vals) - min(vals) > 12:
            return 0                              # むらが ある = ましかくでは ない
        lo = min(vals)
        if lo >= 245:
            return 1
        if LIGHT_MIN <= lo < 245:
            return 2
        return 0

    kind = [[cell_kind(xs[i], ys[j]) for i in range(W)] for j in range(H)]

    def paint(x0, y0, white_only=False):
        for y in range(max(0, y0), min(h, y0 + P)):
            base = y * w
            for x in range(max(0, x0), min(w, x0 + P)):
                if white_only:
                    r, g, b = px[x, y]
                    if max(r, g, b) - min(r, g, b) > SAT_MAX or min(r, g, b) < 245:
                        continue
                m[base + x] = 1

    cells = 0
    for j in range(H):
        for i in range(W):
            if kind[j][i] != 1:
                continue
            # いちまつの しろマスは、となりが かならず はいマス。
            # いぬの しろい からだは となりも しろい ので ここで はずれる。
            grey = white = 0
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                k = kind[nj][ni] if (0 <= ni < W and 0 <= nj < H) else 2
                if k == 2:   grey += 1
                elif k == 1: white += 1
            if white > 0 or grey < 2:
                continue
            cells += 1
            paint(xs[i], ys[j])

    # いぬの りんかくが かかった マスは「ましかく」に ならないので うえで もれる。
    # まわりの ようすから いちまつの ばしょだと わかる マスは、
    # マスぜんぶ ではなく「まっしろな てん だけ」を けす。
    for j in range(H):
        for i in range(W):
            if kind[j][i] != 0:
                continue
            grey = white = 0
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ni, nj = i + di, j + dj
                k = kind[nj][ni] if (0 <= ni < W and 0 <= nj < H) else 2
                if k == 2:   grey += 1
                elif k == 1: white += 1
            if white > 0 or grey < 2:
                continue
            paint(xs[i], ys[j], white_only=True)
    return m, cells


def background_mask(im):
    """がめんの ふちから つながっている はいけいを ぬりつぶす"""
    w, h = im.size
    px = im.load()
    key = key_color(im)

    if key:                              # グリーンバックなど たんしょくの はいけい
        kr, kg, kb = key
        chk, ncell = bytearray(w * h), -1
        def hit(c):
            return ((c[0] - kr) ** 2 + (c[1] - kg) ** 2 +
                    (c[2] - kb) ** 2) < CHROMA_TOL * CHROMA_TOL
    else:                                # いちまつもよう
        chk, ncell = checker_mask(im)
        def hit(c):
            return is_bg(c)

    bg = bytearray(w * h)
    q = deque()

    def push(x, y):
        i = y * w + x
        if not bg[i] and (chk[i] or hit(px[x, y])):
            bg[i] = 1
            q.append((x, y))

    for x in range(w):
        push(x, 0); push(x, h - 1)
    for y in range(h):
        push(0, y); push(w - 1, y)

    while q:
        x, y = q.popleft()
        if x > 0:     push(x - 1, y)
        if x < w - 1: push(x + 1, y)
        if y > 0:     push(x, y - 1)
        if y < h - 1: push(x, y + 1)
    return bg, w, h, ncell, key


def keep_blobs(fg, w, h):
    """まえけい（fg が 0いがい）の かたまりを あつめる。
    ちいさすぎる ゴミは すてるが、あしあとの ように はなれた ものは のこす。"""
    seen = bytearray(w * h)
    comps = []
    for sy in range(h):
        for sx in range(w):
            i0 = sy * w + sx
            if not fg[i0] or seen[i0]:
                continue
            comp, q = [], deque([(sx, sy)])
            seen[i0] = 1
            while q:
                x, y = q.popleft()
                comp.append(y * w + x)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if fg[j] and not seen[j]:
                            seen[j] = 1
                            q.append((nx, ny))
            comps.append(comp)

    if not comps:
        return bytearray(w * h), 0, 0
    biggest = max(len(c) for c in comps)
    keep, total = bytearray(w * h), 0
    for c in comps:
        if len(c) >= biggest * MIN_BLOB_RATIO:
            total += len(c)
            for i in c:
                keep[i] = 255
    return keep, total, len(comps)


def drop_holes(keep, w, h, rgb, key, tol):
    """犬に かこまれて のこった はいけいの「あな」を けす。

    はいけいの けしこみは ふちから ひろげる ので、
    耳と くびの あいだの ような とじた すきまには とどかない。
    ここでは まえけいの なかを しらべて、
    「はいけいの いろに ちかい かたまり」を まとめて すてる。
    """
    seen = bytearray(w * h)
    removed = 0
    holes = 0
    kr, kg, kb = key
    for sy in range(h):
        for sx in range(w):
            i0 = sy * w + sx
            if not keep[i0] or seen[i0]:
                continue
            r, g, b = rgb[i0 * 3], rgb[i0 * 3 + 1], rgb[i0 * 3 + 2]
            if abs(r - kr) + abs(g - kg) + abs(b - kb) > tol:
                seen[i0] = 1
                continue
            comp, q = [], deque([(sx, sy)])
            seen[i0] = 1
            edge = False
            while q:
                x, y = q.popleft()
                comp.append(y * w + x)
                if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                    edge = True
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < w and 0 <= ny < h):
                        continue
                    j = ny * w + nx
                    if seen[j] or not keep[j]:
                        continue
                    r2, g2, b2 = rgb[j * 3], rgb[j * 3 + 1], rgb[j * 3 + 2]
                    if abs(r2 - kr) + abs(g2 - kg) + abs(b2 - kb) <= tol:
                        seen[j] = 1
                        q.append((nx, ny))
            # がぞうの ふちに ついて いる なら はいけい本体。すでに けして ある はず
            if edge or len(comp) < 8:
                continue
            for i in comp:
                keep[i] = 0
            removed += len(comp)
            holes += 1
    return removed, holes


CHK_FLAT_SAT  = 12       # これいか なら「いろみの ない」ドット
CHK_FLAT_MIN  = 235      # これいじょう あかるければ いちまつの しろ かも
CHK_AIR_MIN   = 0.15     # まわりが とうめいな わりあい
CHK_SIZE      = 1.7      # ますめ なんこぶんまでを ゴミと みなすか


def drop_checker_blobs(keep, w, h, rgb, P):
    """いぬに くっついて のこった いちまつの ますめを すてる。

    ちいさくて、たいらな しろで、まわりが とうめいな かたまり だけを ねらう。
    目の ひかりの ような ほんとうの しろは いぬに かこまれて いる（まわりが
    とうめいでは ない）ので のこる。
    """
    lim = int((P * CHK_SIZE) ** 2)
    seen = bytearray(w * h)
    removed = blobs = 0

    def flat(i):
        if not keep[i]:
            return False
        r, g, b = rgb[i * 3], rgb[i * 3 + 1], rgb[i * 3 + 2]
        return (max(r, g, b) - min(r, g, b) <= CHK_FLAT_SAT and
                min(r, g, b) >= CHK_FLAT_MIN)

    for sy in range(h):
        for sx in range(w):
            i0 = sy * w + sx
            if seen[i0] or not flat(i0):
                continue
            comp, q = [], deque([(sx, sy)])
            seen[i0] = 1
            while q:
                x, y = q.popleft()
                comp.append((x, y))
                if len(comp) > lim:
                    break
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < w and 0 <= ny < h):
                        continue
                    j = ny * w + nx
                    if not seen[j] and flat(j):
                        seen[j] = 1
                        q.append((nx, ny))
            while q:                              # おおきすぎ。しるしだけ つけて とばす
                x, y = q.popleft()
                seen[y * w + x] = 1
            if len(comp) > lim:
                continue

            cs = set(comp)
            air = edge = 0
            for (x, y) in comp:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if (nx, ny) in cs:
                        continue
                    edge += 1
                    if not (0 <= nx < w and 0 <= ny < h) or not keep[ny * w + nx]:
                        air += 1
            if edge and air / float(edge) >= CHK_AIR_MIN:
                for (x, y) in comp:
                    keep[y * w + x] = 0
                removed += len(comp)
                blobs += 1
    return removed, blobs


def process(src_path, out_name, target_h, align='bottom', pad=True):
    im0 = Image.open(src_path)

    # とうめいの ある PNG なら、はいけいを けす しょりは いらない。
    # そのまま つかえるので いちばん きれいに しあがる。
    if im0.mode in ('RGBA', 'LA') or 'transparency' in im0.info:
        rgba  = im0.convert('RGBA')
        alpha = rgba.getchannel('A')
        return finish(rgba, alpha, out_name, target_h, align, src_path, 'とうめいPNG', pad)

    im = im0.convert('RGB')
    bg, w, h, ncell, key = background_mask(im)

    fg_img = Image.frombytes('L', (w, h),
                             bytes(bytearray(0 if v else 255 for v in bg)))

    # いちまつの しろマスは いぬと ほそく つながる ことが ある。
    # いちど やせさせて きりはなし、かたまりを えらんでから ふとらせて もどす。
    thin = fg_img
    for _ in range(SEPARATE):
        thin = thin.filter(ImageFilter.MinFilter(3))
    keep, n, ncomp = keep_blobs(thin.tobytes(), w, h)

    # 犬に かこまれて のこった はいけいの あなを けす。
    # ふちからの けしこみが とどかない ところ（耳と くびの あいだ など）。
    #
    # ※ みどりバックの ときだけ やる。
    #   いちまつ（しろ）の ときに おなじ ことを すると、
    #   クリームいろの むねや あしまで「あな」と まちがえて けずって しまう。
    #   （ビーグルで じっさいに こわれた）
    #   ふるい いちまつの えは 手で なおす。
    if key:
        nhole, nh = drop_holes(keep, w, h, im.tobytes(), key, CHROMA_TOL)
        if nh:
            print('    あなを %d こ けしました（%d px）' % (nh, nhole))

    else:
        # いちまつの え だけ。いぬに くっついて のこった ますめを すてる。
        grid = detect_grid(im)
        if grid:
            ndrop, nb = drop_checker_blobs(keep, w, h, im.tobytes(), grid[0])
            if nb:
                print('    いちまつの のこりを %d こ けしました（%d px）' % (nb, ndrop))

    alpha = Image.frombytes('L', (w, h), bytes(keep))
    for _ in range(SEPARATE):
        alpha = alpha.filter(ImageFilter.MaxFilter(3))
    alpha = ImageChops.multiply(alpha, fg_img)   # もとの りんかくに もどす

    for _ in range(ERODE):                       # JPGの にじみを けずる
        alpha = alpha.filter(ImageFilter.MinFilter(3))
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.8))

    rgba = im.convert('RGBA')
    if key:
        despill(rgba)                    # ふちに のこる みどりを おとす
        note = 'たんしょくはいけい かたまり=%d' % ncomp
    else:
        note = 'しろマス=%d かたまり=%d' % (ncell, ncomp)
    return finish(rgba, alpha, out_name, target_h, align, src_path, note, pad)


def despill(rgba):
    """グリーンバックの みどりが ふちに にじむのを おさえる"""
    px = rgba.load()
    w, h = rgba.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            lim = max(r, b) + 10
            if g > lim:
                px[x, y] = (r, lim, b, a)


def finish(rgba, alpha, out_name, target_h, align, src_path, note, pad=True):
    """きりぬき -> おおきさそろえ -> 512x512 に はいち -> ほぞん"""
    rgba = rgba.copy()
    rgba.putalpha(alpha)
    box = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    rgba = rgba.crop(box)

    cw, ch = rgba.size
    scale = target_h / float(ch)
    if pad and cw * scale > CANVAS - MARGIN_X * 2:
        scale = (CANVAS - MARGIN_X * 2) / float(cw)
    nw, nh = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    rgba = rgba.resize((nw, nh), Image.LANCZOS)

    if pad:
        out = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
        top = (BOTTOM - nh) if align == 'bottom' else ((CANVAS - nh) // 2)
        out.paste(rgba, ((CANVAS - nw) // 2, top), rgba)
    else:
        out = rgba                       # アイテムは よはくを つけずに そのまま

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    path = os.path.join(OUT_DIR, out_name)
    out.save(path, 'PNG', optimize=True)
    print('  %-16s <- %-30s %dx%d  %s  %.0fKB'
          % (out_name, src_path, nw, nh, note, os.path.getsize(path) / 1024.0))


def breeds():
    if not os.path.isdir(SRC_ROOT):
        return []
    return sorted(d for d in os.listdir(SRC_ROOT)
                  if os.path.isdir(os.path.join(SRC_ROOT, d)) and d != ITEM_DIR)


if __name__ == '__main__':
    only = sys.argv[1:]
    done = 0

    for b in breeds():
        if only and b not in only:
            continue
        print(b)
        for stem, pose, th in POSES:
            src = find_src(os.path.join(SRC_ROOT, b), stem)
            if not src:
                print('  %-16s (%s.jpg が ないので とばす)' % (b + '_' + pose, stem))
                continue
            process(src, '%s_%s.png' % (b, pose), th, 'bottom')
            done += 1

    # アイテムは まんなかぞろえ。キャンバスに たいして ちいさめに おく。
    if not only or ITEM_DIR in only:
        idir = os.path.join(SRC_ROOT, ITEM_DIR)
        if os.path.isdir(idir):
            print('アイテム')
            for stem, th in ITEMS:
                src = find_src(idir, stem)
                if not src:
                    print('  %-16s (%s.jpg が ないので とばす)' % (stem, stem))
                    continue
                process(src, '%s.png' % stem, th, 'center', pad=False)
                done += 1

    paw = find_src(SRC_ROOT, 'paw')
    if paw and (not only or 'paw' in only):
        print('あしあと（ぜんぶの いぬで きょうよう）')
        process(paw, 'paw.png', 300, 'center')
        done += 1

    if done == 0:
        print('つくるものが ありません。イラスト犬/<いぬしゅ>/01〜04.jpg を おいてね。')
        print('いま ある いぬしゅ:', ', '.join(breeds()) or 'なし')
