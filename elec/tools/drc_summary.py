#!/usr/bin/env python3
"""
drc_summary.py - summarise a kicad-mcp-pro run_drc JSON report.

The Pro server's run_drc dumps a big JSON to a file. This collapses it to:
  * finding categories with counts
  * unconnected items grouped by net (the actionable "what's left to route")
  * every non-unconnected violation with its location (clearance, annular, edge...)

Usage: python elec/tools/drc_summary.py <report.json> [net1,net2,...]
If nets are given, prints the detailed missing-connection endpoints for those nets.
"""
import json, re, sys, collections

F = sys.argv[1]
FOCUS = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else set()
d = json.load(open(F, encoding="utf-8"))
fnd = d.get("findings", [])
STRIP = re.compile(r'\s*\[.*')
def netof(s):
    m = re.search(r'\[([^\]]*)\]', s); return m.group(1) if m else "?"
def ref(s): return STRIP.sub('', s)

cats = collections.Counter()
unc_by_net = collections.Counter()
unc_detail = []          # (nets, [(ref,pos)])
other = []               # (desc, [(ref,pos)])
for f in fnd:
    desc = f["description"]
    items = []
    for ev in f.get("evidence", []):
        for it in ev.get("entry", {}).get("items", []):
            items.append((ref(it.get("description", "")), it.get("pos", {})))
    if "Missing connection" in desc:
        cats["unconnected"] += 1
        nets = {netof(it.get("description","")) for ev in f.get("evidence",[])
                for it in ev.get("entry",{}).get("items",[])}
        for n in nets: unc_by_net[n] += 1
        unc_detail.append((nets, items))
    else:
        key = desc.split("(")[0].strip()[:42]
        cats[key] += 1
        other.append((desc, items))

print("=== categories ===")
for k, c in cats.most_common():
    print(f"  {c:3d}  {k}")

print("\n=== unconnected by net ===")
for n, c in unc_by_net.most_common():
    tag = "  <-- POWER" if n in ("hv","input_cap-power-hv") else ""
    print(f"  {c:3d}  [{n}]{tag}")

if other:
    print("\n=== non-connectivity violations ===")
    for desc, items in other:
        loc = "  ".join(f"{r}({p.get('x','?')},{p.get('y','?')})" for r, p in items[:2])
        print(f"  {desc[:72]}")
        if loc: print(f"        {loc}")

if FOCUS:
    print(f"\n=== missing connections for {sorted(FOCUS)} ===")
    any_ = False
    for nets, items in unc_detail:
        if nets & FOCUS:
            any_ = True
            print("   " + "  <->  ".join(f"{r}({p.get('x','?')},{p.get('y','?')})" for r, p in items))
    if not any_:
        print("   none - fully connected")
