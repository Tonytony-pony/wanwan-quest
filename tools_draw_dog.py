# -*- coding: utf-8 -*-
"""
わんわんクエスト  いぬの ドットえ せいせいスクリプト
---------------------------------------------------
76 x 76 ドット（= 5776ドット。24x24 の やく 10ばい）。

だ円・かどまるしかく・さんかく を くみあわせて シルエットを つくり、
そのふちを じどうで なぞって せんを ひく。
できた もじれつを index.html の `var ART = {...}` に うめこむ。

つかいかた:  python tools_draw_dog.py
"""
import io, re, sys

S = 76                      # キャンバスの おおきさ（たて＝よこ）
OUTLINE = 2                 # せんの ふとさ（ドット）

# ---------------------------------------------------------------- かたち
def ell(cx, cy, rx, ry):
    """だ円の なかの てん"""
    pts = set()
    y0, y1 = int(cy - ry) - 1, int(cy + ry) + 1
    x0, x1 = int(cx - rx) - 1, int(cx + rx) + 1
    for y in range(max(0, y0), min(S, y1 + 1)):
        for x in range(max(0, x0), min(S, x1 + 1)):
            dx = (x - cx) / float(rx)
            dy = (y - cy) / float(ry)
            if dx * dx + dy * dy <= 1.0:
                pts.add((y, x))
    return pts

def rrect(x0, y0, x1, y1, r):
    """かどまるの しかく"""
    pts = set()
    for y in range(max(0, y0), min(S, y1 + 1)):
        for x in range(max(0, x0), min(S, x1 + 1)):
            qx = min(max(x, x0 + r), x1 - r)
            qy = min(max(y, y0 + r), y1 - r)
            if (x - qx) ** 2 + (y - qy) ** 2 <= r * r:
                pts.add((y, x))
    return pts

def tri(cx, ytop, ybase, halfw):
    """さんかく（かんむりの とがり）"""
    pts = set()
    h = float(ybase - ytop)
    for y in range(max(0, ytop), min(S, ybase + 1)):
        w = int(round(halfw * (y - ytop) / h))
        for x in range(cx - w, cx + w + 1):
            if 0 <= x < S:
                pts.add((y, x))
    return pts

def trapezoid(ytop, ybot, hw_top, hw_bot, cx=S // 2):
    """マント（うえが せまく したが ひろい）"""
    pts = set()
    h = float(ybot - ytop)
    for y in range(max(0, ytop), min(S, ybot + 1)):
        w = int(round(hw_top + (hw_bot - hw_top) * (y - ytop) / h))
        for x in range(cx - w, cx + w + 1):
            if 0 <= x < S:
                pts.add((y, x))
    return pts

_OFFS = [(dy, dx)
         for dy in range(-OUTLINE, OUTLINE + 1)
         for dx in range(-OUTLINE, OUTLINE + 1)
         if dy * dy + dx * dx <= OUTLINE * OUTLINE]

def rim(mask):
    """シルエットの ふち（うちがわ OUTLINE ドットぶん）"""
    edge = set()
    for (y, x) in mask:
        for (dy, dx) in _OFFS:
            if (y + dy, x + dx) not in mask:
                edge.add((y, x)); break
    return edge

# ---------------------------------------------------------------- キャンバス
class Canvas(object):
    def __init__(self):
        self.g = [['.'] * S for _ in range(S)]

    def paint(self, pts, ch, only=None):
        for (y, x) in pts:
            if 0 <= y < S and 0 <= x < S:
                if only is None or self.g[y][x] in only:
                    self.g[y][x] = ch

    def rows(self):
        return [''.join(r) for r in self.g]


def face(c, cx, eye_y, nose_y, tongue_y, sc=1.0):
    """め・はな・した を えがく"""
    ex = int(round(9 * sc))
    c.paint(ell(cx - ex, eye_y, 5.0 * sc, 6.0 * sc), 'n')
    c.paint(ell(cx + ex, eye_y, 5.0 * sc, 6.0 * sc), 'n')
    c.paint(ell(cx - ex - 2 * sc, eye_y - 3 * sc, 2.0 * sc, 2.0 * sc), 'w')
    c.paint(ell(cx + ex - 2 * sc, eye_y - 3 * sc, 2.0 * sc, 2.0 * sc), 'w')
    c.paint(ell(cx, nose_y, 5.0 * sc, 4.0 * sc), 'n')
    c.paint(ell(cx, tongue_y, 5.0 * sc, 4.0 * sc), 'p')


# ---------------------------------------------------------------- こいぬ
def build_puppy():
    head = ell(38, 26, 20, 20)
    earL, earR = ell(13, 29, 10, 16), ell(63, 29, 10, 16)
    body = ell(38, 55, 22, 15)
    pawL, pawR = ell(28, 69, 8, 6), ell(48, 69, 8, 6)
    mask = head | earL | earR | body | pawL | pawR

    c = Canvas()
    c.paint(earL, 'e'); c.paint(earR, 'e')
    c.paint(ell(11, 31, 5, 11), 'f'); c.paint(ell(65, 31, 5, 11), 'f')
    c.paint(head, 'b')
    c.paint(pawL, 'b'); c.paint(pawR, 'b')
    c.paint(body, 'b')
    c.paint(ell(38, 63, 19, 9) & body, 'd')
    c.paint(ell(38, 55, 14, 12) & body, 'w')
    c.paint(ell(38, 37, 13, 9), 'w')
    c.paint(rim(mask), 'o')
    # まえあしは からだの うえから ふちどって わける
    c.paint(rim(pawL), 'o'); c.paint(rim(pawR), 'o')
    face(c, 38, 23, 34, 43)
    return c.rows()


# ---------------------------------------------------------------- わんこ
def build_adult(back=False):
    head = ell(38, 21, 19, 18)
    earL, earR = ell(14, 24, 9, 15), ell(62, 24, 9, 15)
    body = ell(38, 51, 21, 15)
    legL, legR = rrect(22, 56, 33, 74, 5), rrect(43, 56, 54, 74, 5)
    tail = ell(62, 52, 9, 12) | ell(70, 42, 7, 10)
    mask = head | earL | earR | body | legL | legR | tail

    c = Canvas()
    c.paint(tail, 'e')
    c.paint(earL, 'e'); c.paint(earR, 'e')
    if not back:
        c.paint(ell(12, 26, 5, 10), 'f'); c.paint(ell(64, 26, 5, 10), 'f')
    c.paint(head, 'b')
    c.paint(legL, 'b'); c.paint(legR, 'b')
    c.paint(body, 'b')
    c.paint(ell(38, 59, 18, 9) & body, 'd')
    c.paint(ell(38, 51, 14, 12) & body, 'w')
    if not back:
        c.paint(ell(38, 32, 12, 8), 'w')
    c.paint(rim(mask), 'o')
    c.paint(rim(tail), 'o')
    c.paint(rim(legL), 'o'); c.paint(rim(legR), 'o')
    if not back:
        face(c, 38, 18, 28, 38)
    return c.rows()


# ---------------------------------------------------------------- でんせつの犬
def build_hero():
    head = ell(38, 33, 19, 17)
    earL, earR = ell(15, 35, 9, 14), ell(61, 35, 9, 14)
    body = ell(38, 59, 20, 14)
    legL, legR = rrect(24, 62, 34, 74, 5), rrect(42, 62, 52, 74, 5)
    dog = head | earL | earR | body | legL | legR

    cape = trapezoid(46, 74, 12, 33) & rrect(3, 46, 73, 74, 11)
    crown = rrect(23, 10, 53, 19, 3) | tri(28, 1, 12, 5) | tri(38, 0, 12, 6) | tri(48, 1, 12, 5)

    c = Canvas()
    # マント（いちばん うしろ）
    c.paint(cape, 'v')
    c.paint(rim(cape), 'u')
    # いぬ
    c.paint(earL, 'e'); c.paint(earR, 'e')
    c.paint(ell(13, 37, 5, 9), 'f'); c.paint(ell(63, 37, 5, 9), 'f')
    c.paint(head, 'b')
    c.paint(legL, 'b'); c.paint(legR, 'b')
    c.paint(body, 'b')
    c.paint(ell(38, 66, 17, 8) & body, 'd')
    c.paint(ell(38, 59, 13, 11) & body, 'w')
    c.paint(ell(38, 43, 12, 8), 'w')
    c.paint(rim(dog), 'o')
    c.paint(rim(legL), 'o'); c.paint(rim(legR), 'o')
    face(c, 38, 30, 40, 49)
    # かんむり（いちばん まえ）
    c.paint(crown, 'y')
    c.paint(rim(crown), 'z')
    return c.rows()


# ---------------------------------------------------------------- そっぽを むいた いぬ
def build_sad():
    head = ell(38, 26, 20, 20)
    earL, earR = ell(13, 29, 10, 16), ell(63, 29, 10, 16)
    body = ell(38, 55, 22, 15)
    pawL, pawR = ell(28, 69, 8, 6), ell(48, 69, 8, 6)
    tail = ell(60, 52, 8, 13)
    mask = head | earL | earR | body | pawL | pawR | tail

    c = Canvas()
    c.paint(tail, 'e')
    c.paint(earL, 'e'); c.paint(earR, 'e')
    c.paint(head, 'b')
    c.paint(pawL, 'b'); c.paint(pawR, 'b')
    c.paint(body, 'b')
    c.paint(ell(38, 63, 19, 9) & body, 'd')
    c.paint(ell(38, 55, 14, 12) & body, 'w')
    c.paint(rim(mask), 'o')
    c.paint(rim(tail), 'o')
    c.paint(rim(pawL), 'o'); c.paint(rim(pawR), 'o')
    return c.rows()


# ---------------------------------------------------------------- あしあと
def build_paw():
    def one(cx, cy):
        toes = (ell(cx - 12, cy - 13, 4.5, 5.0) | ell(cx - 4, cy - 18, 5.0, 5.5) |
                ell(cx + 4, cy - 18, 5.0, 5.5) | ell(cx + 12, cy - 13, 4.5, 5.0))
        pad = ell(cx, cy + 3, 13, 10)
        return toes | pad

    a, b = one(23, 25), one(53, 55)
    c = Canvas()
    for shape in (a, b):
        c.paint(shape, 'b')
        c.paint(rim(shape), 'o')
    return c.rows()


# ---------------------------------------------------------------- しゅつりょく
art = {
    'puppy': build_puppy(),
    'adult': build_adult(),
    'hero':  build_hero(),
    'sad':   build_sad(),
    'paw':   build_paw(),
}
for k, v in art.items():
    assert len(v) == S and all(len(r) == S for r in v), k
    filled = sum(1 for r in v for ch in r if ch != '.')
    print('%-6s %d x %d   ぬったドット %d' % (k, S, S, filled))

def js(name, rows, comment):
    body = ',\n'.join("    '%s'" % r for r in rows)
    return "  /* %s */\n  %s:[\n%s\n  ]" % (comment, name, body)

block = "var ART = {\n" + ',\n'.join([
    js('puppy', art['puppy'], 'こいぬ（レベル 1〜2）'),
    js('adult', art['adult'], 'わんこ（レベル 3〜4）'),
    js('hero',  art['hero'],  'たくましい 犬 / でんせつの 犬（レベル 5〜）'),
    js('sad',   art['sad'],   'そっぽを むいた いぬ（うしろすがた）'),
    js('paw',   art['paw'],   'あしあと（いなく なった とき）'),
]) + "\n};"

p = r'D:\98 Antigravity\400 ゲーム\桜 算数アプリ\index.html'
s = io.open(p, encoding='utf-8').read()
s, cnt = re.subn(r'var ART = \{.*?\n\};', lambda m: block, s, count=1, flags=re.S)
if cnt != 1:
    print('ART block not found'); sys.exit(1)
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('index.html に うめこみました')
