#!/usr/bin/env python3
"""ROTATIONSBAUSTEINE fuer das Ziffernnetz (Fable, 2026-10-22). Rechtsrotation um r Bit: Ergebnisbit i = Quellbit (i + r) mod w.
Ziffer j des Ergebnisses = Bits 2j, 2j+1. Fuer gerades r = 2k: Ergebnisziffer j = Quellziffer (j + k) mod D  -> reine Umbenennung (kein Gatter).
Fuer ungerades r = 2k + 1: Ergebnisziffer j = (hohes Bit der Quellziffer p = (j+k) mod D) | (niedriges Bit der Quellziffer q = (j+k+1) mod D) << 1
-> dreistellige Beziehung ROT1(dst, p, q) mit Tabelle dst == ((p >> 1) & 1) | ((q & 1) << 1), 16 gueltige von 64 Tupeln. Rotation um 0 = Identitaet.
Ch, Maj: ziffernweise dreistellige Tabellen (64 Tupel, alle gueltig). Diese Bausteine werden gegen die direkte Integerrechnung fuer ALLE Eingaben
geprueft (w = 4 und 8, alle r = 0..w-1), inklusive gemeinsamer Variablen (rot(x) XOR x), Alias und Negation."""
import sys, pathlib, itertools, json
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
from ziffern import Netz, TABELLEN, GROESSEN, e3

TABELLEN['ROT1'] = [(((p >> 1) & 1) | ((q & 1) << 1), p, q) for p in range(4) for q in range(4)]
TABELLEN['CH'] = [(e, f, g, ((e & f) ^ ((~e) & g)) & 3) for e in range(4) for f in range(4) for g in range(4)]
TABELLEN['MAJ'] = [(a, b, c, (a & b) ^ (a & c) ^ (b & c)) for a in range(4) for b in range(4) for c in range(4)]
GROESSEN.update(ROT1=(4, 4, 4), CH=(4, 4, 4, 4), MAJ=(4, 4, 4, 4))

def rot(N, x, r, name):
    """Rechtsrotation um r Bit (0 <= r < w) als Ziffern: gerade -> Umbenennung, ungerade -> ROT1-Beziehungen."""
    D = N.D; r %= N.w; k = r // 2
    if r % 2 == 0: return [x[(j + k) % D] for j in range(D)]
    y = N.wort(name)
    for j in range(D): N.bez.append(('ROT1', [y[j], x[(j + k) % D], x[(j + k + 1) % D]]))
    return y
def ch(N, e, f, g, name):
    z = N.wort(name)
    for j in range(N.D): N.bez.append(('CH', [e[j], f[j], g[j], z[j]]))
    return z
def maj(N, a, b, c, name):
    z = N.wort(name)
    for j in range(N.D): N.bez.append(('MAJ', [a[j], b[j], c[j], z[j]]))
    return z

def int_rot(x, r, w): return ((x >> r) | (x << (w - r))) & ((1 << w) - 1) if r else x
def ziffern(x, D): return [(x >> (2 * j)) & 3 for j in range(D)]

def werte_durch_e3(N, feste):
    dom0 = list(N.dom)
    for v, z in feste.items(): N.dom[v] &= 1 << z
    st, dom, _, _ = e3(N); N.dom = dom0
    return st, dom

def pruefe_baustein(w, r, art):
    """art: 'rot' (y = rot(x,r)), 'rotxor' (y = rot(x,r) XOR x, gemeinsame Variable), 'rotneg' (y = rot(~x, r)), 'rotalias' (x2 = x, y = rot(x2,r) + x)."""
    M = 1 << w; fehler = 0; faelle = 0
    for xv in range(M):
        N = Netz(w); x = N.wort('x')
        if art == 'rot': y = rot(N, x, r, 'y'); erw = int_rot(xv, r, w)
        elif art == 'rotxor': y = N.xor(rot(N, x, r, 'r'), x, 'y'); erw = int_rot(xv, r, w) ^ xv
        elif art == 'rotneg': y = rot(N, N.neg(x, 'nx'), r, 'y'); erw = int_rot((M - 1 - xv), r, w)
        elif art == 'rotalias':
            x2 = N.wort('x2'); N.gleich(x, x2); x2 = [N.kanon(v) for v in x2]; y = N.add(rot(N, x2, r, 'r'), x, 'y'); erw = (int_rot(xv, r, w) + xv) % M
        feste = {v: z for v, z in zip(x, ziffern(xv, N.D))}
        st, dom = werte_durch_e3(N, feste); faelle += 1
        if st == 'WIDERSPRUCH': fehler += 1; continue
        got = [dom[v] for v in y]
        if any(bin(m).count('1') != 1 for m in got) or [m.bit_length() - 1 for m in got] != ziffern(erw, N.D): fehler += 1
    return faelle, fehler

def pruefe_chmaj(w):
    M = 1 << w; fehler = 0; faelle = 0
    for a, b, c in itertools.product(range(M), repeat=3):
        N = Netz(w); A = N.wort('a'); B = N.wort('b'); C = N.wort('c'); zc = ch(N, A, B, C, 'ch'); zm = maj(N, A, B, C, 'maj')
        feste = {}
        for word, val in ((A, a), (B, b), (C, c)): feste.update({v: z for v, z in zip(word, ziffern(val, N.D))})
        st, dom = werte_durch_e3(N, feste); faelle += 1
        ec = ((a & b) ^ ((~a) & c)) & (M - 1); em = (a & b) ^ (a & c) ^ (b & c)
        for word, erw in ((zc, ec), (zm, em)):
            got = [dom[v] for v in word]
            if st == 'WIDERSPRUCH' or any(bin(m).count('1') != 1 for m in got) or [m.bit_length() - 1 for m in got] != ziffern(erw, N.D): fehler += 1
    return faelle, fehler

if __name__ == '__main__':
    out = {}
    for w in (4, 8):
        for r in range(w):
            for art in ('rot', 'rotxor', 'rotneg', 'rotalias'):
                f, e = pruefe_baustein(w, r, art); out['w%d_r%d_%s' % (w, r, art)] = dict(faelle=f, fehler=e)
    f, e = pruefe_chmaj(4); out['w4_ch_maj'] = dict(faelle=f, fehler=e)
    gesamt = sum(v['faelle'] for v in out.values()); fehl = sum(v['fehler'] for v in out.values())
    out['_gesamt'] = dict(faelle=gesamt, fehler=fehl, rot1_tabelle_tupel=len(TABELLEN['ROT1']))
    (HERE / 'ERGEBNIS_BAUSTEINE.json').write_text(json.dumps(out, indent=1))
    print('Bausteine: Faelle', gesamt, 'Fehler', fehl)
