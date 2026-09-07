# -*- coding: utf-8 -*-
"""シルエットを ぬってから 輪郭を 自動生成する 方式で 24x24 の いぬを かく"""
import io, re, sys

W = 24

def band(d):
    """{y:(x0,x1)} -> [(y,x0,x1)]"""
    return [(y, a, b) for y, (a, b) in sorted(d.items())]

def mirror(d):
    return dict((y, (W - 1 - b, W - 1 - a)) for y, (a, b) in d.items())

class Canvas(object):
    def __init__(self, h):
        self.h = h
        self.g = [['.'] * W for _ in range(h)]

    def fill(self, spans, ch):
        for (y, x0, x1) in spans:
            for x in range(x0, x1 + 1):
                self.g[y][x] = ch

    def outline(self, shapes, ch='o'):
        """shapes: 塗った領域(座標集合)。ふちを ch にする"""
        mask = set()
        for spans in shapes:
            for (y, x0, x1) in spans:
                for x in range(x0, x1 + 1):
                    mask.add((y, x))
        edge = []
        for (y, x) in mask:
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (y + dy, x + dx) not in mask:
                    edge.append((y, x)); break
        for (y, x) in edge:
            self.g[y][x] = ch
        return mask

    def dot(self, y, x, ch):
        if 0 <= y < self.h and 0 <= x < W:
            self.g[y][x] = ch

    def box(self, y0, y1, x0, x1, ch, only=None):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if only is None or self.g[y][x] in only:
                    self.dot(y, x, ch)

    def rows(self):
        return [''.join(r) for r in self.g]


# ================= こいぬ =================
def build_dog(kind):
    """kind: 'puppy' | 'adult' | 'sad'"""
    if kind == 'puppy':
        top = 3
        head = {3:(8,15),4:(7,16),5:(6,17),6:(6,17),7:(6,17),8:(6,17),
                9:(6,17),10:(6,17),11:(6,17),12:(7,16),13:(8,15)}
        earL = {4:(3,5),5:(2,5),6:(2,5),7:(2,5),8:(2,5),9:(2,5),10:(3,5),11:(3,5)}
        body = {14:(8,15),15:(6,17),16:(5,18),17:(4,19),18:(4,19),19:(4,19),
                20:(5,18),21:(6,17)}
        legL = {21:(5,9),22:(5,9),23:(5,9)}
        tail = {}
        h = 24
    else:   # adult / sad は おなじ たいけい（あたまが うえ、あしが ながい）
        top = 0
        head = {0:(8,15),1:(7,16),2:(6,17),3:(6,17),4:(6,17),5:(6,17),
                6:(6,17),7:(6,17),8:(6,17),9:(7,16),10:(8,15)}
        earL = {1:(3,5),2:(2,5),3:(2,5),4:(2,5),5:(2,5),6:(2,5),7:(3,5),8:(3,5)}
        body = {11:(8,15),12:(6,17),13:(4,19),14:(3,20),15:(3,20),16:(3,20),
                17:(3,20),18:(4,19),19:(5,18)}
        legL = {20:(5,9),21:(5,9),22:(5,9),23:(5,9)}
        tail = {9:(19,22),10:(18,22),11:(18,22),12:(17,21)}
        h = 24

    earR, legR = mirror(earL), mirror(legL)
    c = Canvas(h)
    shapes = [band(head), band(earL), band(earR), band(body), band(legL), band(legR)]
    if tail:
        shapes.append(band(tail))
        c.fill(band(tail), 'e')
    c.fill(band(body), 'b')
    c.fill(band(legL), 'b'); c.fill(band(legR), 'b')
    c.fill(band(earL), 'e'); c.fill(band(earR), 'e')
    c.fill(band(head), 'b')
    c.outline(shapes)

    # おなかの しろ
    if kind == 'puppy':
        c.box(17, 20, 8, 15, 'w', only='b')
        c.box(16, 16, 9, 14, 'w', only='b')
    else:
        c.box(14, 18, 7, 16, 'w', only='b')
        c.box(13, 13, 8, 15, 'w', only='b')

    if kind != 'sad':
        # かお
        ey = top + 4
        for ex in (8, 14):
            c.box(ey, ey + 1, ex, ex + 1, 'n')
            c.dot(ey, ex, 'w')
        c.box(top + 7, top + 7, 11, 12, 'n')          # はな
        c.box(top + 8, top + 8, 10, 13, 'p')          # した
        c.box(top + 9, top + 9, 11, 12, 'p')
    return c.rows()


# ================= でんせつの犬（かんむり + マント） =================
def build_hero():
    base = build_dog('adult')
    h = 27
    c = Canvas(h)

    # マント（いぬの うしろ）
    capeL = {16:(2,4),17:(1,4),18:(1,4),19:(1,4),20:(0,4),
             21:(0,4),22:(0,4),23:(0,4),24:(0,3),25:(1,3)}
    capeR = mirror(capeL)
    c.fill(band(capeL), 'v'); c.fill(band(capeR), 'v')
    c.outline([band(capeL), band(capeR)], 'u')

    # いぬを 3ぎょう さげて うわがき
    for y, row in enumerate(base):
        for x, ch in enumerate(row):
            if ch != '.':
                c.g[y + 3][x] = ch

    # かんむり
    crown0 = {0: (8, 8)}
    crown = [(0,8,8), (0,11,12), (0,15,15), (1,7,16), (2,6,17)]
    c.fill(crown, 'y')
    c.outline([crown], 'z')
    c.fill([(1,8,15)], 'y')
    c.fill([(2,7,16)], 'y')
    c.dot(0, 8, 'y'); c.dot(0, 11, 'y'); c.dot(0, 12, 'y'); c.dot(0, 15, 'y')
    return c.rows()


# ================= あしあと =================
def build_paw():
    shape = [
        '..oo..oo..oo.',
        '..oo..oo..oo.',
        '..oo..oo..oo.',
        '.............',
        '..ooooooooo..',
        '.ooooooooooo.',
        '.ooooooooooo.',
        '.ooooooooooo.',
        '..ooooooooo..',
        '...ooooooo...',
    ]
    g = [['.'] * W for _ in range(24)]
    for sx, sy in ((0, 1), (11, 13)):
        for j, rw in enumerate(shape):
            for i, ch in enumerate(rw):
                if ch != '.':
                    g[sy + j][sx + i] = ch
    return [''.join(r) for r in g]


art = {
    'puppy': build_dog('puppy'),
    'adult': build_dog('adult'),
    'hero':  build_hero(),
    'sad':   build_dog('sad'),
    'paw':   build_paw(),
}
for k, v in art.items():
    assert all(len(r) == W for r in v), k
    print('%-6s %2d rows x %d' % (k, len(v), W))

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
assert cnt == 1, 'ART block not found'

if "u:'#8b4fc0'" not in s:
    s = s.replace("  v:'#b06fe0'   /* マント    */",
                  "  v:'#b06fe0',  /* マント    */\n  u:'#7a3fb8'   /* マント ふち */")
io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')

for k in ('puppy', 'adult', 'hero'):
    print('\n--- ' + k)
    for r in art[k]:
        print(r)
