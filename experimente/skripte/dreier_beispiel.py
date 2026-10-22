#!/usr/bin/env python3
"""UNTERSCHEIDENDES MINI-BEISPIEL fuer Mechanismus 2 (Dreierbeziehung durch Join + Projektion), Fable 2026-10-22.
Netz (w = 4, zwei Ziffern je Wort), x und y frei (256 Eingaben):
    x0 = y XOR x          (XOR je Ziffer)
    r2 = rot3(x0)         (ungerade Rotation -> ROT1 mischt Ziffern: r2[j] = hi(x0[j+1]) | lo(x0[j]) << 1 ... gemaess bausteine.rot)
    m3 = maj(y, x, r2)    (MAJ je Ziffer), Ziel: m3 = 13 fest (beide Ziffern)
Wiedervereinigung: y und x treffen sich in XOR, das Ergebnis kehrt rotiert in MAJ zu y und x zurueck.
Dreierbeziehung D(y[1], x[1], r2[1]) = Join von XOR(y[1], x[1], x0[1]) und ROT1(r2[1], x0[0], x0[1]) ueber die gemeinsame Variable x0[1],
projiziert auf die drei Grenzvariablen (Tabelle ueber volle Domaenen: 32 von 64 Tupeln; Inhalt: niedriges Bit von r2[1] = hohes Bit von y[1] XOR x[1]).
Gemessen: wahre Loesungen 15; E4 (Paare, Radius 1) laesst 144 Eingaben zu; E4 + D laesst 64 zu; beide sound (alle 15 Loesungen enthalten).
Gefunden durch Zufallssuche ueber 400 kleine Netze (Seed 195 des Generators in komposition_kind.mininetz-aehnlicher Form), 1 von 400 mit Gewinn."""
import sys, json, itertools, pathlib
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
from ziffern import Netz, TABELLEN, GROESSEN
import ziffern_komp as ZK, ziffern_sha as ZS, bausteine as BS

def netz(dreier):
    N = Netz(4); x = N.wort('x'); y = N.wort('y')
    x0 = N.xor(y, x, 'x0'); r2 = BS.rot(N, x0, 3, 'r2'); m3 = BS.maj(N, y, x, r2, 'm3')
    N.fest(m3[0], 1); N.fest(m3[1], 3)
    if dreier:
        # Join XOR(y1,x1,x0_1) |><| ROT1(r2_1, x0_0, x0_1) ueber x0_1 -> Projektion (y1, x1, r2_1)
        tab = set()
        for (a, b, z) in TABELLEN['XOR']:
            for (dst, p, q) in TABELLEN['ROT1']:
                if q == z: tab.add((a, b, dst))
        TABELLEN['D_BEISPIEL'] = sorted(tab); GROESSEN['D_BEISPIEL'] = (4, 4, 4)
        N.bez.append(('D_BEISPIEL', [y[1], x[1], r2[1]]))
    return N, x, y
def wahr():
    sol = set()
    for xv in range(16):
        for yv in range(16):
            x0 = xv ^ yv; r2 = ((x0 >> 3) | (x0 << 1)) & 15; m3 = (yv & xv) ^ (yv & r2) ^ (xv & r2)
            if m3 == 13: sol.add((xv, yv))
    return sol
def erlaubt(N, x, y, st, dom):
    if st == 'WIDERSPRUCH': return set()
    return {(xv, yv) for xv in range(16) for yv in range(16) if all((dom[x[j]] >> ((xv >> (2 * j)) & 3)) & 1 and (dom[y[j]] >> ((yv >> (2 * j)) & 3)) & 1 for j in range(2))}
if __name__ == '__main__':
    W = wahr(); out = dict(wahre_loesungen=len(W))
    for name, dr in (('E4_paare', False), ('E4_plus_Dreier', True)):
        N, x, y = netz(dr); st, dom, paare, inf = ZK.e4(N, max_paare=5000, nachpruefung=True); E = erlaubt(N, x, y, st, dom)
        st2, dom2, paare2, _ = ZS.e4(N, max_paare=5000)
        out[name] = dict(status=st, zugelassene_eingaben=len(E), sound=W <= E, paare=len(paare), beziehungen=len(N.bez), dreier_tupel=len(TABELLEN.get('D_BEISPIEL', [])) if dr else 0,
                         gleich_mit_ziffern_sha=(st == st2 and dom == dom2 and paare == paare2), nachpruefung=inf.get('nachpruefung_e3'))
    # Vollstaendigkeitsanker: E3 mit allen Eingaben fest reproduziert genau die wahre Menge
    N, x, y = netz(False); fest = set()
    for xv in range(16):
        for yv in range(16):
            dom = list(N.dom)
            for j in range(2): dom[x[j]] &= 1 << ((xv >> (2 * j)) & 3); dom[y[j]] &= 1 << ((yv >> (2 * j)) & 3)
            if ZS.e3(N, dom)[0] != 'WIDERSPRUCH': fest.add((xv, yv))
    out['E3_alle_eingaben_fest_gleich_wahr'] = fest == W
    (HERE / 'ERGEBNIS_DREIER_BEISPIEL.json').write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
