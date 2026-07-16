#!/usr/bin/env python3
"""
render_board.py - dump the PCB to a plain SVG so routing can be eyeballed
(and reviewed) without opening KiCad.

Draws: board outline, pads (by layer), tracks (coloured per net), vias.
Optionally highlight specific nets: python render_board.py out.svg hv,dp,dm

Uses the same parser as layout_check.py (note the pad-rotation gotcha documented
there: pad local coords rotate by the NEGATIVE of the footprint angle).
"""
import importlib.util, os, sys, math

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("lc", os.path.join(HERE, "layout_check.py"))
lc = importlib.util.module_from_spec(spec); spec.loader.exec_module(lc)

PCB = os.path.join(HERE, "..", "layout", "default", "default.kicad_pcb")
OUT = sys.argv[1] if len(sys.argv) > 1 else "board.svg"
HILITE = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else set()

tree = lc.load(PCB)
pads, edge = lc.collect(tree)
fa, f, rot = lc.fa, lc.f, lc.rot

netmap = {n[1]: n[2].strip('"') for n in fa(tree, "net") if len(n) >= 3}
def netname(nt):
    if not nt or len(nt) < 2: return ""
    return netmap.get(nt[1], nt[-1].strip('"'))

segs, vias = [], []
for g in tree:
    if not isinstance(g, list) or not g: continue
    if g[0] == "segment":
        st, en, w, ly = f(g,"start"), f(g,"end"), f(g,"width"), f(g,"layer")
        segs.append((netname(f(g,"net")), ly[1].strip('"') if ly else "?",
                     float(st[1]), float(st[2]), float(en[1]), float(en[2]),
                     float(w[1]) if w else 0.2))
    if g[0] == "via":
        at = f(g,"at")
        vias.append((netname(f(g,"net")), float(at[1]), float(at[2])))

L, R, T, B = edge
PAD = 6
W, H = (R-L)+2*PAD, (B-T)+2*PAD
SC = 8  # px per mm

def X(x): return (x - L + PAD) * SC
def Y(y): return (y - T + PAD) * SC

# stable colour per net
PALETTE = ["#e6194b","#3cb44b","#4363d8","#f58231","#911eb4","#46f0f0","#f032e6",
           "#bcf60c","#fabebe","#008080","#9a6324","#800000","#808000","#000075"]
nets = sorted({s[0] for s in segs})
color = {n: PALETTE[i % len(PALETTE)] for i, n in enumerate(nets)}

o = []
o.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*SC/8:.0f}" height="{H*SC/8:.0f}" '
         f'viewBox="0 0 {W*SC:.0f} {H*SC:.0f}" style="background:#1b2030">')
# board outline
o.append(f'<rect x="{X(L):.1f}" y="{Y(T):.1f}" width="{(R-L)*SC:.1f}" height="{(B-T)*SC:.1f}" '
         f'fill="#20263a" stroke="#c8c8a0" stroke-width="2"/>')
# pads
for p in pads:
    hl = p["net"] in HILITE
    o.append(f'<rect x="{X(p["x"]-p["sx"]):.1f}" y="{Y(p["y"]-p["sy"]):.1f}" '
             f'width="{2*p["sx"]*SC:.1f}" height="{2*p["sy"]*SC:.1f}" rx="1" '
             f'fill="{"#ffd166" if hl else "#c9736b"}" opacity="{1 if hl else .75}"/>')
# tracks
for n, ly, x1, y1, x2, y2, w in segs:
    dim = HILITE and n not in HILITE
    c = "#555b70" if dim else color.get(n, "#aaa")
    dash = ' stroke-dasharray="4,3"' if ly == "B.Cu" else ""
    o.append(f'<line x1="{X(x1):.1f}" y1="{Y(y1):.1f}" x2="{X(x2):.1f}" y2="{Y(y2):.1f}" '
             f'stroke="{c}" stroke-width="{max(w*SC,1.5):.1f}" stroke-linecap="round" '
             f'opacity="{.25 if dim else .95}"{dash}/>')
for n, x, y in vias:
    o.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{0.3*SC:.1f}" fill="#fff" stroke="#333"/>')
# refs
for ref in sorted({p["ref"] for p in pads}):
    ps = [p for p in pads if p["ref"] == ref]
    cx = sum(p["x"] for p in ps)/len(ps); cy = sum(p["y"] for p in ps)/len(ps)
    o.append(f'<text x="{X(cx):.1f}" y="{Y(cy):.1f}" fill="#eaeaea" font-size="11" '
             f'font-family="monospace" text-anchor="middle">{ref}</text>')
o.append('</svg>')
open(OUT, "w", encoding="utf-8").write("\n".join(o))
print(f"wrote {OUT}  ({len(segs)} segments, {len(vias)} vias, {len(pads)} pads)")
