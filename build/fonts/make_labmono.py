"""Make LabMono-Regular.ttf: Source Code Pro with an invisible baseline mark on every glyph.

    uv run --with fonttools build/fonts/make_labmono.py <path to SourceCodePro-Regular.ttf>

Why. When you copy text out of a PDF in macOS Preview, Safari or Quick Look, those
viewers (Apple's PDFKit) decide which line a character is on from its glyph's bounding
box. A character whose box does not overlap its neighbours' vertically is pasted onto a
line of its own. An underscore (wholly below the baseline) does that, and so does a
comma that follows a quote (the quote is high, the comma low):

    MATCH (al:Alert)-[:FIRED
    _
    ON]->(d:Datastore)
    WHERE c.name IN ['profile-cache'
    'entitlements-svc'
    ,
    ,

which is not Cypher. The fix is to give every printable glyph a tiny triangle (2 font
units, 0.002 of an em: invisible at any zoom) sitting on the baseline. Every glyph's box
then crosses the baseline, so all of them overlap and stay on one line. Nothing about
how the font looks changes.

Licence. Source Code Pro is (c) 2010-2020 Adobe, under the SIL Open Font License 1.1
(http://scripts.sil.org/OFL), with Reserved Font Name "Source". A modified version may not
use that name, so the result is renamed "Lab Mono". See NOTICE.md.
"""

import sys
from pathlib import Path

from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

src = Path(sys.argv[1])
out = Path(__file__).with_name("LabMono-Regular.ttf")

font = TTFont(src)
glyf = font["glyf"]
cmap = font.getBestCmap()
glyphs = font.getGlyphSet()
marked = 0
for code in range(0x21, 0x7F):                       # printable ASCII; the space has no outline
    name = cmap[code]
    pen = TTGlyphPen(glyphs)
    glyphs[name].draw(pen)                           # copies the outline; flattens composites such as "
    old = glyf[name]
    old.recalcBounds(glyf)
    x = (old.xMin + old.xMax) // 2
    pen.moveTo((x, 0))                               # a 2-unit triangle on the baseline, wound clockwise
    pen.lineTo((x + 2, 2))                           # like the outer contours, so where it overlaps a
    pen.lineTo((x + 2, 0))                           # letter it merges and never cuts a hole in it
    pen.closePath()
    g = pen.glyph()
    g.recalcBounds(glyf)
    assert g.yMin <= 0 <= g.yMax, (chr(code), g.yMin, g.yMax)   # the box crosses the baseline
    glyf[name] = g
    marked += 1

# Rename (OFL Reserved Font Name). Keep the copyright and licence records.
names = {1: "Lab Mono", 3: "LabMono-Regular", 4: "Lab Mono", 6: "LabMono-Regular"}
for rec in list(font["name"].names):
    if rec.nameID in names:
        rec.string = names[rec.nameID]
    elif rec.nameID in (16, 17, 21, 22, 25):          # family names that would still say "Source"
        font["name"].removeNames(nameID=rec.nameID)
font.save(out)
print(f"wrote {out}: {marked} glyphs marked")
