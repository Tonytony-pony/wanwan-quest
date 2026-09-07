# -*- coding: utf-8 -*-
"""
イラスト犬1/*.jpg  ->  img/*.png

Geminiの しゅつりょくを JPGで ほぞんすると、とうめいぶぶんが
「いちまつもよう」として やきこまれて しまう。
このスクリプトは そのもようを けして とうめいに もどし、
アプリで つかいやすい おおきさに そろえて PNGに する。

やること:
  1. がめんの ふちから ぬりつぶして「はいけい（むちゃくしょくで あかるい）」を みつける
  2. いちばん おおきい かたまり（＝いぬ）だけ のこす
  3. ふちを 2ドット けずって JPGの にじみを とる
  4. 512x512 の キャンバスに したそろえ・まんなかぞろえで はいち
     （たかさを そろえるので、レベルアップで がぞうが とんで みえない）

つかいかた:  python tools_make_dog_png.py
"""
import io, os, sys
from collections import deque
from PIL import Image, ImageFilter

SRC_DIR = 'イラスト犬1'
OUT_DIR = 'img'
CANVAS = 512          # しゅつりょくの おおきさ
BOTTOM = 496          # あしもとの いち（したから 16ドット あける）
MARGIN_X = 16

# (もとファイル, しゅつりょくファイル, たかさ, たてのそろえかた)
JOBS = [
    ('01.jpg', 'dog_lv1.png', 360, 'bottom'),   # こいぬ
    ('02.jpg', 'dog_lv3.png', 400, 'bottom'),   # わんこ
    ('03.jpg', 'dog_lv5.png', 440, 'bottom'),   # でんせつの犬
    ('04.jpg', 'dog_sad.png', 400, 'bottom'),   # そっぽを むいた いぬ
    ('05.jpg', 'paw.png',     300, 'center'),   # あしあと
]

# はいけい はんてい: いろみが なくて あかるい ドット
SAT_MAX = 26          # R,G,B の さ が これいか なら むちゃくしょく
LIGHT_MIN = 178       # いちばん くらい チャンネルが これいじょう なら あかるい
ERODE = 2             # ふちを けずる ドットすう


def is_bg(px):
    r, g, b = px[0], px[1], px[2]
    return (max(r, g, b) - min(r, g, b) <= SAT_MAX) and (min(r, g, b) >= LIGHT_MIN)


def background_mask(im):
    """がめんの ふちから つながっている はいけいを ぬりつぶす"""
    w, h = im.size
    px = im.load()
    bg = bytearray(w * h)
    q = deque()

    def push(x, y):
        i = y * w + x
        if not bg[i] and is_bg(px[x, y]):
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
    return bg, w, h


MIN_BLOB_RATIO = 0.02   # いちばん おおきい かたまりの 2% いじょう なら のこす

def keep_blobs(bg, w, h):
    """はいけい いがいの かたまりを あつめる。
    ちいさすぎる ゴミは すてるが、あしあとの ように はなれた ものは のこす。"""
    seen = bytearray(w * h)
    comps = []
    for sy in range(h):
        for sx in range(w):
            i0 = sy * w + sx
            if bg[i0] or seen[i0]:
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
                        if not bg[j] and not seen[j]:
                            seen[j] = 1
                            q.append((nx, ny))
            comps.append(comp)

    biggest = max(len(c) for c in comps)
    keep = bytearray(w * h)
    total = 0
    for c in comps:
        if len(c) >= biggest * MIN_BLOB_RATIO:
            total += len(c)
            for i in c:
                keep[i] = 255
    return keep, total, len(comps)


def process(src, dst, target_h, align='bottom'):
    im = Image.open(os.path.join(SRC_DIR, src)).convert('RGB')
    bg, w, h = background_mask(im)
    keep, n, ncomp = keep_blobs(bg, w, h)

    alpha = Image.frombytes('L', (w, h), bytes(keep))
    # JPGの にじみを けずる
    for _ in range(ERODE):
        alpha = alpha.filter(ImageFilter.MinFilter(3))
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.8))

    rgba = im.convert('RGBA')
    rgba.putalpha(alpha)
    box = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    rgba = rgba.crop(box)

    cw, ch = rgba.size
    scale = target_h / float(ch)
    if cw * scale > CANVAS - MARGIN_X * 2:
        scale = (CANVAS - MARGIN_X * 2) / float(cw)
    nw, nh = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))
    rgba = rgba.resize((nw, nh), Image.LANCZOS)

    out = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0))
    top = (BOTTOM - nh) if align == 'bottom' else ((CANVAS - nh) // 2)
    out.paste(rgba, ((CANVAS - nw) // 2, top), rgba)

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    path = os.path.join(OUT_DIR, dst)
    out.save(path, 'PNG', optimize=True)
    return path, (w, h), box, (nw, nh), n, ncomp, os.path.getsize(path)


if __name__ == '__main__':
    only = sys.argv[1:]      # 'python tools_make_dog_png.py 05.jpg' で 1まいだけ
    for src, dst, th, al in JOBS:
        if only and src not in only:
            continue
        path, size, box, fin, n, ncomp, bytes_ = process(src, dst, th, al)
        print('%s -> %s  crop=%s  final=%dx%d  かたまり=%d  px=%d  %.0fKB'
              % (src, path, box, fin[0], fin[1], ncomp, n, bytes_ / 1024.0))
