# -*- coding: utf-8 -*-
"""
フレンチブルドッグの しあげ。tools_make_dog_png.py frenchbulldog の あとに じっこう する。
いちまつの はいいろマスが からだに かこまれて のこった ちいさな ごみ（はいいろの しかく）を けす。
"""
import numpy as np
from collections import deque
from PIL import Image, ImageFilter

for name in ('lv1', 'lv3', 'lv5'):
    path = 'img/frenchbulldog_%s.png' % name
    a = np.asarray(Image.open(path).convert('RGBA')).copy()
    c = a[..., :3].astype(int)
    sat = c.max(-1) - c.min(-1); val = c.max(-1)
    H, W = val.shape
    ys = np.where(a[..., 3] > 8)[0]
    grey = (a[..., 3] > 8) & (sat < 14) & (val >= 180) & (val <= 224)
    dark = Image.fromarray(((val < 120) & (a[..., 3] > 8)).astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(9))
    dark = np.asarray(dark) > 127                                # くろ・ふちの そばは まもる
    seen = np.zeros_like(grey)
    kill = np.zeros_like(grey)
    for y0, x0 in zip(*np.where(grey)):
        if seen[y0, x0]:
            continue
        comp = []; q = deque([(y0, x0)]); seen[y0, x0] = True
        while q:
            y, x = q.popleft(); comp.append((y, x))
            for dy, dx in ((1,0),(-1,0),(0,1),(0,-1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < H and 0 <= xx < W and grey[yy, xx] and not seen[yy, xx]:
                    seen[yy, xx] = True; q.append((yy, xx))
        if len(comp) < 700 and not any(dark[y, x] for y, x in comp):
            for y, x in comp: kill[y, x] = True
    m = Image.fromarray((kill * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))
    kill = np.asarray(m) > 127
    a[..., 3][kill] = 0
    Image.fromarray(a, 'RGBA').save(path, optimize=True)
    print(name, int(kill.sum()), 'px removed')
