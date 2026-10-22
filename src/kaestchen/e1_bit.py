#!/usr/bin/env python3
"""E1 (Bogenkonsistenz) auf dem gatter-Graphen, Kopie aus stufe0_kind.py / lauf_m4.py (unveraendert)."""
# ---------- E1 auf dem Gatter-Graphen (aus lauf_m4.e1_lauf) ----------
TAB = {}
for opn in ('and', 'xor'):
    for A in range(4):
        for B in range(4):
            for Zm in range(4):
                sa = sb = sz = 0
                for u in (0, 1):
                    for v in (0, 1):
                        out = (u ^ v) if opn == 'xor' else (u & v)
                        if (A >> u) & 1 and (B >> v) & 1 and (Zm >> out) & 1: sa |= 1 << u; sb |= 1 << v; sz |= 1 << out
                TAB[(opn, A, B, Zm)] = (sa, sb, sz)
def e1_lauf(g, d, max_sweeps=12):
    n = len(g.nodes)
    def get(x): return (((d[-x] & 1) << 1) | ((d[-x] & 2) >> 1)) if x < 0 else d[x]
    def assign(x, v):
        if x < 0: x = -x; v = ((v & 1) << 1) | ((v & 2) >> 1)
        old = d[x]; d[x] &= v; return old != d[x]
    sweeps = 0
    while True:
        sweeps += 1; changed = False
        for order in (range(2, n), range(n - 1, 1, -1)):
            for i in order:
                nd = g.nodes[i]
                if nd[0] == 'input': continue
                opn, a, b = nd; A, B, Zm = get(a), get(b), get(i); sa, sb, sz = TAB[(opn, A, B, Zm)]
                if not A or not B or not Zm or not sa: return 'WIDERSPRUCH', sweeps
                changed |= assign(a, sa); changed |= assign(b, sb); changed |= assign(i, sz)
        if not changed: return 'FIXPUNKT', sweeps
        if sweeps >= max_sweeps: return 'OFFEN', sweeps
