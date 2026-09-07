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

# (もとファイル, しゅつりょくファイル, いぬの たかさ)
JOBS = [
    ('01.jpg', 'dog_lv1.png', 360),   # こいぬ
    ('02.jpg', 'dog_lv3.png', 400),   # わんこ
    ('03.jpg', 'dog_lv5.png', 440),   # でんせつの犬
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


def largest_blob(bg, w, h):
    """はいけい いがいで いちばん おおきい かたまり だけ のこす"""
    seen = bytearray(w * h)
    best, best_n = None, 0
    for sy in range(h):
        for sx in range(w):
            i0 = sy * w + sx
            if bg[i0] or seen[i0]:
                continue
            comp, q, n = [], deque([(sx, sy)]), 0
            seen[i0] = 1
            while q:
                x, y = q.popleft()
                comp.append(y * w + x); n += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        if not bg[j] and not seen[j]:
                            seen[j] = 1
                            q.append((nx, ny))
            if n > best_n:
                best, best_n = comp, n
    keep = bytearray(w * h)
    for i in best:
        keep[i] = 255
    return keep, best_n


def process(src, dst, target_h):
    im = Image.open(os.path.join(SRC_DIR, src)).convert('RGB')
    bg, w, h = background_mask(im)
    keep, n = largest_blob(bg, w, h)

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
    out.paste(rgba, ((CANVAS - nw) // 2, BOTTOM - nh), rgba)

    if not os.path.isdir(OUT_DIR):
        os.makedirs(OUT_DIR)
    path = os.path.join(OUT_DIR, dst)
    out.save(path, 'PNG', optimize=True)
    return path, (w, h), box, (nw, nh), n, os.path.getsize(path)


if __name__ == '__main__':
    for src, dst, th in JOBS:
        path, size, box, fin, n, bytes_ = process(src, dst, th)
        print('%s -> %s  src=%dx%d  crop=%s  final=%dx%d  px=%d  %.0fKB'
              % (src, path, size[0], size[1], box, fin[0], fin[1], n, bytes_ / 1024.0))
