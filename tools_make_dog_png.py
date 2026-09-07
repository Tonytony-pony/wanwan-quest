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
"""
import os, sys
from collections import deque
from PIL import Image, ImageFilter

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
]
EXTS = ('.jpg', '.jpeg', '.png', '.webp')   # どの かたちで ほぞんしても OK

def find_src(folder, stem):
    for e in EXTS:
        f = os.path.join(folder, stem + e)
        if os.path.isfile(f):
            return f
    return None

# はいけい はんてい: いろみが なくて あかるい ドット
SAT_MAX   = 26          # R,G,B の さ が これいか なら むちゃくしょく
LIGHT_MIN = 178         # いちばん くらい チャンネルが これいじょう なら あかるい
ERODE     = 2           # ふちを けずる ドットすう
MIN_BLOB_RATIO = 0.02   # いちばん おおきい かたまりの 2% いじょう なら のこす


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


def process(src_path, out_name, target_h, align='bottom'):
    im = Image.open(src_path).convert('RGB')
    bg, w, h = background_mask(im)
    keep, n, ncomp = keep_blobs(bg, w, h)

    alpha = Image.frombytes('L', (w, h), bytes(keep))
    for _ in range(ERODE):                       # JPGの にじみを けずる
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
    path = os.path.join(OUT_DIR, out_name)
    out.save(path, 'PNG', optimize=True)
    print('  %-16s <- %-32s %dx%d  かたまり=%d  %.0fKB'
          % (out_name, src_path, nw, nh, ncomp, os.path.getsize(path) / 1024.0))


def breeds():
    if not os.path.isdir(SRC_ROOT):
        return []
    return sorted(d for d in os.listdir(SRC_ROOT)
                  if os.path.isdir(os.path.join(SRC_ROOT, d)))


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

    paw = find_src(SRC_ROOT, 'paw')
    if paw and (not only or 'paw' in only):
        print('あしあと（ぜんぶの いぬで きょうよう）')
        process(paw, 'paw.png', 300, 'center')
        done += 1

    if done == 0:
        print('つくるものが ありません。イラスト犬/<いぬしゅ>/01〜04.jpg を おいてね。')
        print('いま ある いぬしゅ:', ', '.join(breeds()) or 'なし')
