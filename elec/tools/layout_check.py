#!/usr/bin/env python3
"""
layout_check.py - quick geometric sanity checks on the atopile-generated KiCad PCB.

Reads the board .kicad_pcb directly (no KiCad/pcbnew needed) and reports:
  * board outline (Edge.Cuts) extent and size
  * per-footprint pad clearance to the nearest board edge (flags parts poking out)
  * decoupling-cap -> owning-chip power/ground pin distances

Why this exists: atopile owns the schematic; placement/routing happen by hand in
KiCad. This gives a text readout of things that are otherwise only visible in the
GUI, so layout feedback can be given without eyeballing screenshots.

Notes on the KiCad s-expr format as emitted by atopile:
  * nets are stored on each pad *by name*: (net "sck")  -- NOT (net <n> "sck")
  * footprint rotation: pad local (at) coords must be rotated by the NEGATIVE of
    the footprint angle to get board coords (KiCad's Y-down convention). Getting
    this sign wrong mirrors every part -- verify against a known-good pad.

Usage:
  python elec/tools/layout_check.py [path/to/board.kicad_pcb]
"""
import re, math, sys

DEFAULT_PCB = "elec/layout/default/default.kicad_pcb"

# Decoupling map: cap ref -> (owner ref, power-net, gnd-net).
# Power/gnd nets are matched by the cap's own pad nets, so this only needs the owner.
DECOUPLING = {
    "C1": "U6",  # LDO input cap
    "C2": "U6",  # LDO output cap
    "C3": "U7",  # ESP bulk
    "C4": "U7",  # ESP bulk
    "C5": "U7",  # ESP 100nF
}

def load(path):
    txt = open(path, "r", encoding="utf-8").read()
    toks = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+').findall(txt)
    pos = 0
    def parse():
        nonlocal pos
        t = toks[pos]; pos += 1
        if t == '(':
            lst = []
            while toks[pos] != ')':
                lst.append(parse())
            pos += 1
            return lst
        return t
    return parse()

def fa(n, k): return [c for c in n if isinstance(c, list) and c and c[0] == k]
def f(n, k):
    for c in n:
        if isinstance(c, list) and c and c[0] == k:
            return c
    return None
def rot(x, y, deg):
    r = math.radians(deg)
    return (x*math.cos(r) - y*math.sin(r), x*math.sin(r) + y*math.cos(r))

def net_of(pad):
    n = f(pad, "net")
    return n[-1].strip('"') if n and len(n) >= 2 else ""

def collect(tree):
    """Return (pads, edge) where pads = list of dict(ref,num,net,x,y,val)."""
    pads = []
    for fp in fa(tree, "footprint"):
        at = f(fp, "at"); fx, fy = float(at[1]), float(at[2])
        fr = float(at[3]) if len(at) > 3 else 0.0
        ref = val = ""
        for pr in fa(fp, "property"):
            if len(pr) > 2 and pr[1] == '"Reference"': ref = pr[2].strip('"')
            if len(pr) > 2 and pr[1] == '"Value"':     val = pr[2].strip('"')
        for pad in fa(fp, "pad"):
            pat = f(pad, "at")
            gx, gy = rot(float(pat[1]), float(pat[2]), -fr)   # note: -fr (see header)
            sz = f(pad, "size")
            sx = float(sz[1])/2 if sz else 0.25
            sy = float(sz[2])/2 if sz else 0.25
            pads.append(dict(ref=ref, num=pad[1].strip('"'), net=net_of(pad),
                             x=fx+gx, y=fy+gy, sx=sx, sy=sy, val=val))
    # edge cuts
    exs, eys = [], []
    for g in tree:
        if isinstance(g, list) and g and g[0] in ("gr_line","gr_rect","gr_poly","gr_arc"):
            lay = f(g, "layer")
            if lay and lay[1].strip('"') == "Edge.Cuts":
                for sub in g:
                    if isinstance(sub, list) and sub and sub[0] in ("start","end","center","mid"):
                        exs.append(float(sub[1])); eys.append(float(sub[2]))
                    if isinstance(sub, list) and sub and sub[0] == "pts":
                        for p in sub:
                            if isinstance(p, list) and p and p[0] == "xy":
                                exs.append(float(p[1])); eys.append(float(p[2]))
    edge = (min(exs), max(exs), min(eys), max(eys)) if exs else None
    return pads, edge

def dist(a, b):
    return math.hypot(a["x"]-b["x"], a["y"]-b["y"])

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PCB
    pads, edge = collect(load(path))
    refs = sorted({p["ref"] for p in pads})

    print(f"# layout_check: {path}\n")
    if edge:
        L, R, T, B = edge
        print(f"Board outline: x[{L:.1f}..{R:.1f}] y[{T:.1f}..{B:.1f}]  = {R-L:.1f} x {B-T:.1f} mm\n")

    # edge clearance per footprint (pad copper vs board edge)
    if edge:
        L, R, T, B = edge
        print("Edge clearance (nearest pad-copper to board edge; negative = OUTSIDE):")
        rows = []
        for ref in refs:
            ps = [p for p in pads if p["ref"] == ref]
            gaps = []
            for p in ps:
                gaps += [p["x"]-p["sx"]-L, R-(p["x"]+p["sx"]), p["y"]-p["sy"]-T, B-(p["y"]+p["sy"])]
            rows.append((min(gaps), ref))
        for g, ref in sorted(rows)[:10]:
            flag = "  <-- OUTSIDE" if g < 0 else ("  (tight)" if g < 0.5 else "")
            print(f"  {ref:5s} {g:6.2f} mm{flag}")
        print()

    # decoupling distances
    print("Decoupling: cap pad -> nearest owner pad on same net (want <~3mm for the 100nF):")
    for cap, owner in DECOUPLING.items():
        cps = [p for p in pads if p["ref"] == cap]
        if not cps:
            print(f"  {cap}: not found"); continue
        val = cps[0]["val"]
        parts = []
        for cp in cps:
            cands = [op for op in pads if op["ref"] == owner and op["net"] == cp["net"] and cp["net"]]
            if cands:
                best = min(cands, key=lambda op: dist(cp, op))
                parts.append(f"{cp['net']}->{owner}.{best['num']} {dist(cp,best):.1f}mm")
            else:
                parts.append(f"{cp['net']}->(no match)")
        print(f"  {cap} ({val}) -> " + " | ".join(parts))

if __name__ == "__main__":
    main()
