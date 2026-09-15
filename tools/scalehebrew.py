"""Scale the Hebrew block so it sits at a normal optical size against Inter's Latin.

DejaVu's Hebrew was merged at its own x-height (1120), which is also Inter's x-height,
so Hebrew renders at the height of a lowercase 'x' next to 1490-tall Latin capitals.
"""
from fontTools.ttLib import TTFont

RANGES = ((0x0590, 0x05FF), (0xFB1D, 0xFB4F))


def hebrew_glyphs(font):
    cm = font.getBestCmap()
    names = set()
    for lo, hi in RANGES:
        for cp in range(lo, hi + 1):
            if cp in cm:
                names.add(cm[cp])
    return names


def scale(src, dst, k):
    f = TTFont(src)
    glyf, hmtx = f['glyf'], f['hmtx']
    names = hebrew_glyphs(f)
    simple = composite = 0
    for n in names:
        g = glyf[n]
        if g.isComposite():
            for c in g.components:
                c.x, c.y = round(c.x * k), round(c.y * k)
            composite += 1
        elif g.numberOfContours:
            g.coordinates = type(g.coordinates)([(round(x * k), round(y * k)) for x, y in g.coordinates])
            simple += 1
        adv, lsb = hmtx[n]
        hmtx[n] = (round(adv * k), round(lsb * k))
    for n in names:
        glyf[n].recalcBounds(glyf)
    f.save(dst)
    return len(names), simple, composite


if __name__ == "__main__":
    import sys
    for k in (1.08, 1.12, 1.16):
        tag = str(int(round(k * 100)))
        n, s, c = scale("out_fix/Inter-Unicode-Regular.ttf", "heb%s.ttf" % tag, k)
        print("k=%.2f  glyphs=%d (simple %d, composite %d) -> heb%s.ttf" % (k, n, s, c, tag))
