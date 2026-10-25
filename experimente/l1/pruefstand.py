#!/usr/bin/env python3
"""PRUEFSTAND L1 (Fable, 2026-10-24) – Gerueststufe (a). Netze <= 12 freie Bits als Gatterlisten; Darstellungen mit gemeinsamer Schnittstelle;
Orakel = vollstaendige Aufzaehlung, nur Kontrolle. Messdefinition nach Ghost (24.10., 09:21):
  1. ABLEITUNG EINFRIEREN: jede Darstellung liefert nach ihrem Lauf ihre FOLGERUNGEN ohne Kandidaten – feste Werte, Beziehungen, Widerspruch.
  2. KONTROLLE GETRENNT: das Orakel prueft ALLE echten Loesungen gegen die Folgerungen (verletzt = FEHLER/unsound) und liefert nichts zurueck.
  3. SUCHE SEPARAT: Fallunterscheidungen werden nur gezaehlt (hier in (a) nicht enthalten).
Zaehlung der 'erlaubten Belegungen' einer Darstellung = Belegungen, die ihre eingefrorenen Folgerungen erfuellen (NICHT: die alle Gleichungen des
Netzes erfuellen). Scheinloesungen = erlaubt - wahr; verlorene = wahr - erlaubt (muss 0).
Netz: dict(name, n_frei, gatter=[(id, op, a, b)], ziel={knoten: wert}); Knoten 0/1 = Konstanten, 2..n_frei+1 = freie Bits, negative = Negation."""
import os, sys, json, time, itertools, pathlib, resource
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'src' / 'kaestchen'))   # Repo-Fassung: gatter/e1_bit aus src/kaestchen (im Labor: miner_pruefung/sha256d)
import gatter as G
from e1_bit import e1_lauf

# ---------------- Netzbau ----------------
class Netz:
    def __init__(self, name, n_frei):
        self.name = name; self.g = G.Graph(); self.frei = [self.g.input(i) for i in range(n_frei)]; self.ziel = {}; self.stufen = []   # stufen: (x, y, cin, s, cout) Knoten je Additionsstufe
    def xor(self, *xs):
        r = xs[0]
        for x in xs[1:]: r = self.g.gate('xor', r, x)
        return r
    def und(self, a, b): return self.g.gate('and', a, b)
    def oder(self, a, b): return G.inv(self.g.gate('and', G.inv(a), G.inv(b)))
    def maj(self, a, b, c):
        m = self.oder(self.und(a, b), self.oder(self.und(a, c), self.und(b, c)))
        self.maj_kaestchen = getattr(self, 'maj_kaestchen', []) + [(a, b, c, m)]; self.maj_runde = getattr(self, 'maj_runde', []) + [getattr(self, 'runde', None)]   # Beschriftung      # Aufzeichnung (a,b,c,out) je Maj (auch Uebertraege der Addierer), fuer R8m
        return m
    def add_bits(self, xs, ys, cin=0):
        """Ripple-Addition zweier Bitlisten (LSB zuerst); liefert Summenbits, Uebertragsbits (cin je Stufe), cout."""
        s, cs = [], []; c = cin
        for x, y in zip(xs, ys):
            cs.append(c); sb = self.xor(x, y, c); cn = self.maj(x, y, c); self.stufen.append((x, y, c, sb, cn)); s.append(sb); c = cn
        return s, cs, c
    def setze_ziel(self, knoten, wert): self.ziel[knoten] = wert
    def wert(self, belegung):
        """Alle Knotenwerte fuer eine Belegung der freien Bits (Liste 0/1)."""
        v = [0, 1] + [None] * (len(self.g.nodes) - 2)
        def ev(x):
            if x < 0: return 1 - ev(-x)
            if v[x] is None:
                nd = self.g.nodes[x]
                v[x] = belegung[nd[1]] if nd[0] == 'input' else ((ev(nd[1]) & ev(nd[2])) if nd[0] == 'and' else (ev(nd[1]) ^ ev(nd[2])))
            return v[x]
        for i in range(len(self.g.nodes)): ev(i) if i >= 2 else None
        return v
    def erfuellt(self, belegung):
        v = self.wert(belegung); return all((1 - v[-k] if k < 0 else v[k]) == w for k, w in self.ziel.items())

# ---------------- Orakel ----------------
def orakel(N):
    n = len(N.frei); return [b for b in itertools.product((0, 1), repeat=n) if N.erfuellt(b)]

# ---------------- Darstellungen: gemeinsame Schnittstelle ----------------
class Darstellung:
    name = '?'
    def laufen(self, N): raise NotImplementedError          # -> status, folgerungen (dict), groesse (dict)
    def erlaubt(self, N, belegung, folgerungen): raise NotImplementedError   # prueft Belegung NUR gegen eingefrorene Folgerungen

class D1_Einzelbits(Darstellung):
    name = 'D1 Einzelbits (E1)'
    def laufen(self, N):
        d = [3] * len(N.g.nodes); d[0] = 1; d[1] = 2
        for k, w in N.ziel.items():
            kk, ww = (-k, 1 - w) if k < 0 else (k, w); d[kk] &= 1 << ww
        t = time.perf_counter(); st, sw = e1_lauf(N.g, d, max_sweeps=10 ** 6)
        fest = {i: (d[i] >> 1) for i in range(2, len(d)) if d[i] in (1, 2)}
        frei_fest = {idx: fest[k] for idx, k in enumerate(N.frei) if k in fest}      # PROJEKTION: nur Folgerungen ueber freie Bits zaehlen
        return st, dict(frei_fest=frei_fest, widerspruch=(st == 'WIDERSPRUCH')), dict(domaenen=len(d), feste_knoten=len(fest), feste_freie_bits=len(frei_fest), durchlaeufe=sw, s=round(time.perf_counter() - t, 4))
    def erlaubt(self, N, belegung, F):
        if F['widerspruch']: return False
        return all(belegung[i] == w for i, w in F['frei_fest'].items())

class D2_Paare(Darstellung):
    """Bitpaare direkt am Gatternetz: Paarmasken (4 Bit) fuer jedes Variablenpaar, das ein Gatter teilt (Radius 1 = ueber gemeinsamen Nachbarn komponiert)."""
    name = 'D2 Paare (Radius 1, Bitebene)'
    def laufen(self, N):
        import ziffern_komp as ZK
        from ziffern import Netz as ZN
        t = time.perf_counter(); g = N.g; Z = ZN(32); var = {}
        def v(x):
            x0 = abs(x)
            if x0 not in var: var[x0] = Z.var('k%d' % x0, 2)
            return var[x0]
        # Konstanten 0/1 ausdruecklich als feste Variablen (Ghost-Korrektur 3)
        Z.fest(v(0), 0); Z.fest(v(1), 1)
        for k in N.ziel: v(abs(k))                      # alle Zielvariablen VOR der Domaenenkopie anlegen
        from ziffern import TABELLEN, GROESSEN
        TABELLEN.setdefault('AND2', [(a, b, a & b) for a in (0, 1) for b in (0, 1)]); GROESSEN['AND2'] = (2, 2, 2)
        TABELLEN.setdefault('XOR2', [(a, b, a ^ b) for a in (0, 1) for b in (0, 1)]); GROESSEN['XOR2'] = (2, 2, 2)
        TABELLEN.setdefault('NOT', [(a, 1 - a) for a in (0, 1)]); GROESSEN['NOT'] = (2, 2)
        for i in range(2, len(g.nodes)):
            nd = g.nodes[i]
            if nd[0] == 'input': continue
            a, b = nd[1], nd[2]; va, vb = v(a), v(b)
            if a < 0: na = Z.var('n%d' % i + 'a', 2); Z.bez.append(('NOT', [va, na])); va = na
            if b < 0: nb = Z.var('n%d' % i + 'b', 2); Z.bez.append(('NOT', [vb, nb])); vb = nb
            Z.bez.append(('AND2' if nd[0] == 'and' else 'XOR2', [va, vb, v(i)]))
        dom = list(Z.dom)
        for k, w in N.ziel.items():
            kk, ww = (-k, 1 - w) if k < 0 else (k, w); dom[v(kk)] &= 1 << ww
        st, dom, paare, info = ZK.e4(Z, dom, max_runden=200, max_paare=200000)
        fest = {x: (dom[var[x]] >> 1) for x in var if dom[var[x]] in (1, 2)}
        zid2frei = {var[k]: idx for idx, k in enumerate(N.frei) if k in var}
        frei_fest = {idx: fest[k] for idx, k in enumerate(N.frei) if k in fest}
        frei_paare = {(zid2frei[x], zid2frei[y]): m for (x, y), m in paare.items() if x in zid2frei and y in zid2frei and m != 15}   # PROJEKTION auf freie Bits
        return st, dict(frei_fest=frei_fest, frei_paare=frei_paare, widerspruch=(st == 'WIDERSPRUCH')),\
               dict(paare=len(paare), eingeschraenkt=sum(1 for m in paare.values() if m != 15), feste_knoten=len(fest), feste_freie_bits=len(frei_fest), paare_zwischen_freien=len(frei_paare), runden=info.get('runden'), s=round(time.perf_counter() - t, 4))
    def erlaubt(self, N, belegung, F):
        if F['widerspruch']: return False
        if not all(belegung[i] == w for i, w in F['frei_fest'].items()): return False
        return all((m >> (belegung[i] * 2 + belegung[j])) & 1 for (i, j), m in F['frei_paare'].items())

# ---------------- Netze ----------------
def N1():
    N = Netz('N1 Fall A ungeteilt', 4); x = N.frei
    N.setze_ziel(N.xor(N.xor(x[0], x[1]), x[2]), 1); N.setze_ziel(N.xor(N.xor(x[0], x[3]), x[1]), 1); N.setze_ziel(N.xor(x[2], x[3]), 1); return N
def N1g():
    N = Netz('N1g Fall A geteilt', 4); x = N.frei
    N.setze_ziel(N.xor(x[0], x[1], x[2]), 1); N.setze_ziel(N.xor(x[0], x[1], x[3]), 1); N.setze_ziel(N.xor(x[2], x[3]), 1); return N
def N2():
    N = Netz('N2 Dreieck', 3); x = N.frei
    N.setze_ziel(N.xor(x[0], x[1]), 0); N.setze_ziel(N.xor(x[1], x[2]), 0); N.setze_ziel(N.xor(x[0], x[2]), 1); return N
# Loesbare Gegenproben (Ghost-Korrektur 1): Negation, Konstanten, Uebertraege
def L1():
    N = Netz('L1 loesbar: Negation+Konstante', 3); x = N.frei      # (NOT x0) AND x1 = 1 ; x2 XOR 1 = x0  -> x0=0,x1=1,x2=1 : genau 1 Loesung
    N.setze_ziel(N.und(G.inv(x[0]), x[1]), 1); N.setze_ziel(N.xor(x[2], 1), 0); return N
def L2():
    N = Netz('L2 loesbar: 2-Bit-Addierer, Summe vorgegeben', 4); x = N.frei   # x0x1 + x2x3 = 3 (binaer 11, cout=0): Loesungen (0+3),(1+2),(2+1),(3+0) = 4
    s_, cs, cout = N.add_bits([x[0], x[1]], [x[2], x[3]]); N.setze_ziel(s_[0], 1); N.setze_ziel(s_[1], 1); N.setze_ziel(cout, 0); return N
def L3():
    N = Netz('L3 loesbar: 3-Bit-Addierer mit Uebertrag, nur Summe', 6); x = N.frei  # a+b = 5 mod 8, cout frei: 8 Loesungen
    s_, cs, cout = N.add_bits(x[0:3], x[3:6]); N.setze_ziel(s_[0], 1); N.setze_ziel(s_[1], 0); N.setze_ziel(s_[2], 1); return N
def L4():
    N = Netz('L4 loesbar: Fall A mit erfuellbarer Parität', 4); x = N.frei  # x0^x1^x2=1, x0^x3^x1=1, x2^x3=0 -> x2=x3=1^x0^x1: 4 Loesungen
    N.setze_ziel(N.xor(N.xor(x[0], x[1]), x[2]), 1); N.setze_ziel(N.xor(N.xor(x[0], x[3]), x[1]), 1); N.setze_ziel(N.xor(x[2], x[3]), 0); return N
def N3():
    """Zwei 3-Bit-Additionen mit ZWEI geteilten Eingangsbits: A = (x0,x1,x2) + (x3,x4,x5), B = (x0,x1,x6) + (x7,x8,x9); x0,x1 in beiden.
    Ziel: Summe A = 5, Summe B = 6 (mod 8), und Ausgangsuebertrag A = Ausgangsuebertrag B (Kopplung ueber die Uebertraege). 10 freie Bits."""
    N = Netz('N3 zwei gekoppelte Additionen (2 geteilte Bits, cout gleich)', 10); x = N.frei
    sA, _, cA = N.add_bits([x[0], x[1], x[2]], [x[3], x[4], x[5]]); sB, _, cB = N.add_bits([x[0], x[1], x[6]], [x[7], x[8], x[9]])
    for s_, v in ((sA[0], 1), (sA[1], 0), (sA[2], 1), (sB[0], 0), (sB[1], 1), (sB[2], 1)): N.setze_ziel(s_, v)
    N.setze_ziel(N.xor(cA, cB), 0); return N
def N3u():
    """Wie N3, aber Ziel so, dass es UNERREICHBAR ist: Summe A = 5, Summe B = 6, cout A = 1, cout B = 0 und Kopplung cA = NOT cB ... (A: 5 mit Uebertrag -> a+b = 13;
    B: 6 ohne Uebertrag). Pruefung durch Orakel, ob wirklich 0 Loesungen."""
    N = Netz('N3u gekoppelte Additionen, Variante', 10); x = N.frei
    sA, _, cA = N.add_bits([x[0], x[1], x[2]], [x[3], x[4], x[5]]); sB, _, cB = N.add_bits([x[0], x[1], x[6]], [x[7], x[8], x[9]])
    for s_, v in ((sA[0], 1), (sA[1], 0), (sA[2], 1), (sB[0], 0), (sB[1], 1), (sB[2], 1)): N.setze_ziel(s_, v)
    N.setze_ziel(cA, 1); N.setze_ziel(cB, 1); N.setze_ziel(N.xor(x[2], x[6]), 1); return N
# ---------------- N4 Mini-Leine: SHA-Rundenfunktion auf 4-Bit-Woertern ----------------
def _mini_runden(N, W, K, IV, runden=3):
    """3 Runden SHA-Rundenfunktion auf 4-Bit-Registern (Bitlisten LSB zuerst). Sigma0(a)=rot1^rot2, Sigma1(e)=rot1^rot3, Ch, Maj, Additionen mod 16 (Stufen aufgezeichnet)."""
    def konst(v): return [1 if (v >> i) & 1 else 0 for i in range(4)]
    def rot(x, n): return x[n:] + x[:n]
    def xorw(a, b): return [N.xor(p, q) for p, q in zip(a, b)]
    def chw(e, f, g):
        zs = [N.xor(N.und(p, q), N.und(G.inv(p), r)) for p, q, r in zip(e, f, g)]
        N.ch_kaestchen = getattr(N, 'ch_kaestchen', []) + [(p, q, r, z) for (p, q, r), z in zip(zip(e, f, g), zs)]; N.ch_runde = getattr(N, 'ch_runde', []) + [getattr(N, 'runde', None)] * 4   # Aufzeichnung (e,f,g,z) je Bit + Runde
        return zs
    def majw(a, b, c): return [N.maj(p, q, r) for p, q, r in zip(a, b, c)]
    def addw(a, b): s_, _, _ = N.add_bits(a, b); return s_
    a, b, c, d, e, f, g, h = [konst(v) for v in IV]
    for i in range(runden):
        N.runde = i + 1                                    # Beschriftung fuer Karte
        S1 = xorw(rot(e, 1), rot(e, 3)); S0 = xorw(rot(a, 1), rot(a, 2))
        t1 = addw(addw(addw(addw(h, S1), chw(e, f, g)), konst(K[i])), W[i]); t2 = addw(S0, majw(a, b, c))
        a, b, c, d, e, f, g, h = addw(t1, t2), a, b, c, addw(d, t1), e, f, g
    return [a, b, c, d, e, f, g, h]
_IV4 = (0x6, 0xB, 0x3, 0xA, 0x5, 0x9, 0x1, 0x5); _K4 = (0x4, 0x7, 0xB, 0xE, 0x3, 0x5, 0x9, 0xC, 0x2, 0x6, 0xD, 0x8)
def _n4(name, wiederverwendung):
    import hashlib
    N = Netz(name, 8); x = N.frei; W0 = x[0:4]; W1 = x[4:8]
    W2 = W0 if wiederverwendung else [1, 0, 1, 1]            # Leine: W2 = W0 (dasselbe Wort in Runde 1 und 3) – sonst Konstante 0xD
    regs = _mini_runden(N, [W0, W1, W2], _K4, _IV4)
    k = int.from_bytes(hashlib.sha256(name.encode()).digest(), 'little') % 256     # versteckte Kontrollbelegung (nur fuer Zielbau)
    bel = [(k >> i) & 1 for i in range(8)]; v = N.wert(bel)
    for r in regs:
        for node in r:
            val = (1 - v[-node]) if node < 0 else v[node]
            if node in (0, 1): assert val == node; continue
            N.setze_ziel(node, val)
    return N
def N4(): return _n4('N4 Mini-Leine (W2 = W0, 3 Runden, 4-Bit)', True)
def N4o(): return _n4('N4o ohne Leine (W2 = Konstante, sonst gleich)', False)
def _n4r(runden, leine):
    """Mini-Leine mit R Runden: W0, W1, W2 frei (12 Bits); W_i = W_(i-3) (Wiederverwendung im Abstand 3) bzw. ohne Leine W_i = Konstante."""
    import hashlib
    name = 'N4r%02d %s' % (runden, 'Leine W_i=W_(i-3)' if leine else 'ohne Leine (Konstanten)')
    N = Netz(name, 12); x = N.frei; W = [x[0:4], x[4:8], x[8:12]]
    for i in range(3, runden): W.append(W[i - 3] if leine else [(0xD5A3 >> ((i * 4 + b) % 16)) & 1 for b in range(4)])
    regs = _mini_runden(N, W, _K4, _IV4, runden)
    k = int.from_bytes(hashlib.sha256(name.encode()).digest(), 'little') % 4096; bel = [(k >> i) & 1 for i in range(12)]; v = N.wert(bel)
    for r in regs:
        for node in r:
            val = (1 - v[-node]) if node < 0 else v[node]
            if node in (0, 1): continue
            N.setze_ziel(node, val)
    return N
def N4r09k():
    """GEGENPROBE (GO 2026-10-24 15:16): N4r09 unveraendert, aber EIN Zielbit vorab festgelegt und umgedreht: Register a, Bit 0 (erstes Zielbit in Aufzeichnungsreihenfolge).
    Festgelegt VOR dem Lauf, nicht nach Ergebnis. Ob das veraenderte Ziel loesbar ist, entscheidet allein das Orakel (alle 4096)."""
    N = _n4r(9, True); N.name = 'N4r09k (Zielbit Register a Bit 0 gekippt)'
    erster = next(iter(N.ziel)); N.ziel[erster] ^= 1; N.gekippt = erster; return N
for _R in (4, 5, 6, 7, 8, 9, 10, 12):
    globals()['N4r%02d' % _R] = (lambda R: (lambda: _n4r(R, True)))(_R); globals()['N4r%02do' % _R] = (lambda R: (lambda: _n4r(R, False)))(_R)
NETZE = {f.__name__: f for f in (N1, N1g, N2, L1, L2, L3, L4, N3, N3u, N4, N4o)}
NETZE['N4r09k'] = N4r09k
if os.environ.get('PRUEFSTAND_NETZE_MODUL'):                      # Haken (2026-10-24, M2): weitere Netze aus einem Modul, das NETZE_N5 (oder NETZE) bereitstellt
    import importlib.util as _ilu; _pf = os.environ['PRUEFSTAND_NETZE_MODUL']; _sp = _ilu.spec_from_file_location('_zusatznetze', _pf); _m = _ilu.module_from_spec(_sp); _sp.loader.exec_module(_m)
    NETZE.update(getattr(_m, 'NETZE_N5', getattr(_m, 'NETZE', {}))); _ZUSATZMODUL = _m
else: _ZUSATZMODUL = None
for _R in (4, 5, 6, 7, 8, 9, 10, 12): NETZE['N4r%02d' % _R] = globals()['N4r%02d' % _R]; NETZE['N4r%02do' % _R] = globals()['N4r%02do' % _R]
class Dx_Sabotage(Darstellung):
    """NUR PRUEFSTAND-TEST: behauptet unsound 'freies Bit 0 = 0'. Muss auf loesbaren Netzen FEHLER und Stopp ausloesen."""
    name = 'Dx Sabotage (absichtlich unsound)'
    def laufen(self, N): return 'FIXPUNKT', dict(frei_fest={0: 0}, widerspruch=False), dict(hinweis='Testdarstellung')
    def erlaubt(self, N, belegung, F): return belegung[0] == 0
class Dt_Zeit(Darstellung):
    """PRUEFSTAND-TEST: ueberschreitet die Zeitgrenze (schlaeft). Erwartet: OFFEN (Grenze)."""
    name = 'Dt Zeit'
    def laufen(self, N): time.sleep(GRENZE_S_TEST + 2); return 'FIXPUNKT', dict(frei_fest={}, widerspruch=False), {}
    def erlaubt(self, N, b, F): return True
class Dt_Speicher(Darstellung):
    """PRUEFSTAND-TEST: ueberschreitet die Speicherschwelle (belegt Speicher). Erwartet: OFFEN (Grenze) oder FEHLER durch harte RLIMIT."""
    name = 'Dt Speicher'
    def laufen(self, N):
        m = []
        for _ in range(40): m.append(bytearray(16 * 1024 * 1024)); time.sleep(0.05)
        return 'FIXPUNKT', dict(frei_fest={}, widerspruch=False), {}
    def erlaubt(self, N, b, F): return True
class Dt_Absturz(Darstellung):
    """PRUEFSTAND-TEST: Programmfehler. Erwartet: FEHLER und Stopp, nicht OFFEN."""
    name = 'Dt Absturz'
    def laufen(self, N): raise RuntimeError('absichtlicher Programmfehler')
    def erlaubt(self, N, b, F): return True
GRENZE_S_TEST = 3.0
sys.path.insert(0, str(HERE)); from d6 import D6_Rueckwaertsleine, D6_ohne_R4, D6_ohne_R3, D6_nur_R4, D6_R5, D6_R56, D6_R567, D6_R567b, D6_R567bC_20_22, D6_R567bC, D6_R567bCM, D6_R9_Auswahl, D6_R9, D6_R9a_Spiegel, D6_R9b_Spiegel, D6_Vollscan, D6_Vollscan_ohne_R9, D6_Vollscan_ohne_R9a, D6_Vollscan_ohne_R9b, D6_Vollscan_ohne_Br, D6_Vollscan_nur_R9, D6_Vollscan_nur_R9a, D6_Vollscan_nur_R9b, D6_Vollscan_ohne_R7, D6_Vollscan_nur_R9b_ohneBr, D6_Vollscan_ohne_R9_Br
DARSTELLUNGEN = {'D1': D1_Einzelbits, 'D2': D2_Paare, 'D6': D6_Rueckwaertsleine, 'D6-R4': D6_ohne_R4, 'D6-R3': D6_ohne_R3, 'D6nurR4': D6_nur_R4, 'D6+R5': D6_R5, 'D6+R5+R6': D6_R56, 'D6+R5+R6+R7': D6_R567, 'D6+R5+R6+R7+R1b': D6_R567b, 'D6+R1b+R8c(20,22)': D6_R567bC_20_22, 'D6+R1b+R8c': D6_R567bC, 'D6+R1b+R8c+R8m': D6_R567bCM, 'D6+R9(5)': D6_R9_Auswahl, 'D6+R9': D6_R9, 'D6+R9a(Spiegel)': D6_R9a_Spiegel, 'D6+R9b(Spiegel)': D6_R9b_Spiegel, 'D6+Vollscan': D6_Vollscan, 'V-R9': D6_Vollscan_ohne_R9, 'V-R9a': D6_Vollscan_ohne_R9a, 'V-R9b': D6_Vollscan_ohne_R9b, 'V-Br': D6_Vollscan_ohne_Br, 'VnurR9': D6_Vollscan_nur_R9, 'VnurR9a': D6_Vollscan_nur_R9a, 'VnurR9b': D6_Vollscan_nur_R9b, 'V-R7': D6_Vollscan_ohne_R7, 'VnurR9b-Br': D6_Vollscan_nur_R9b_ohneBr, 'V-R9-Br': D6_Vollscan_ohne_R9_Br, 'Dx': Dx_Sabotage, 'Dt_Zeit': Dt_Zeit, 'Dt_Speicher': Dt_Speicher, 'Dt_Absturz': Dt_Absturz}
if _ZUSATZMODUL is not None: DARSTELLUNGEN.update(getattr(_ZUSATZMODUL, 'DARSTELLUNGEN_ZUSATZ', {}))   # Haken: zusaetzliche Darstellungen (z.B. R10b aus dem Offline-Labor)
GRENZE_S, GRENZE_MIB = 120.0, 400.0

# ---------------- Kindprozess: eine Darstellung auf einem Netz ----------------
HART_MIB = 1024   # harte Obergrenze im Kind (RLIMIT_AS); die 400 MiB sind eine UEBERWACHTE Schwelle (0,1 s), keine harte Garantie
def kind(netzname, dname, aus):
    try: resource.setrlimit(resource.RLIMIT_AS, (HART_MIB * 1024 * 1024, HART_MIB * 1024 * 1024)); rlimit_aktiv = resource.getrlimit(resource.RLIMIT_AS)[0] == HART_MIB * 1024 * 1024
    except (ValueError, OSError) as e: rlimit_aktiv = False
    N = NETZE[netzname](); D = DARSTELLUNGEN[dname](); n = len(N.frei)
    def peak(): return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    t0 = time.perf_counter(); st, F, gr = D.laufen(N); t_ableitung = round(time.perf_counter() - t0, 4); peak_ableitung = peak()
    # eingefrorene Folgerungen speichern (serialisierbar), DANN erst Kontrollzaehlung
    F_ser = {k: ({str(kk): vv for kk, vv in v.items()} if isinstance(v, dict) else (sorted(v) if isinstance(v, set) else v)) for k, v in F.items() if k != 'var'}
    moment = json.dumps(F_ser, default=str, sort_keys=True)                      # UNVERAENDERLICHE MOMENTAUFNAHME der Folgerungen VOR der Kontrolle
    pathlib.Path(str(aus) + '.ableitung').write_text(json.dumps(dict(status=st, groesse=gr, folgerungen=json.loads(moment), ableitung_s=t_ableitung, ableitung_peak_mib=peak_ableitung, rlimit_aktiv=rlimit_aktiv, rlimit_mib=HART_MIB), default=str))
    t1 = time.perf_counter(); erl = [i for i, b in enumerate(itertools.product((0, 1), repeat=n)) if D.erlaubt(N, b, F)]; t_kontrolle = round(time.perf_counter() - t1, 4)
    assert json.dumps(F_ser, default=str, sort_keys=True) == moment, 'Folgerungen haben sich waehrend der Kontrolle veraendert'
    pathlib.Path(aus).write_text(json.dumps(dict(status=st, erlaubt=erl, groesse=gr, folgerungen=json.loads(moment), ableitung_s=t_ableitung, ableitung_peak_mib=peak_ableitung,
                                                 kontrolle_s=t_kontrolle, peak_mib_kind=peak(), rlimit_aktiv=rlimit_aktiv, rlimit_mib=HART_MIB), default=str))

def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024
    except FileNotFoundError: return 0.0
    return 0.0

# ---------------- Messung (Elternprozess, Grenzen je Darstellung – Ghost-Korrektur 4) ----------------
def messen(netzname, dnamen, grenze_s=None, grenze_mib=None):
    grenze_s = grenze_s or GRENZE_S; grenze_mib = grenze_mib or GRENZE_MIB
    import subprocess
    N = NETZE[netzname](); n = len(N.frei); alle = list(itertools.product((0, 1), repeat=n))
    wahr = None; orakel_s = None; zeilen = []          # Orakel wird ERST NACH der ersten Ableitung gerechnet (Korrektur 2026-10-24 15:23): Ableitung -> Einfrieren -> Orakel
    print('%s | %d freie Bits, %d Knoten | Orakel folgt nach der Ableitung' % (N.name, n, len(N.g.nodes)))
    for dn in dnamen:
        aus = HERE / ('_kind_%s_%s.json' % (netzname, dn)); aus.unlink(missing_ok=True); pathlib.Path(str(aus) + '.ableitung').unlink(missing_ok=True)
        t = time.perf_counter(); p = subprocess.Popen([sys.executable, '-I', str(HERE / 'pruefstand.py'), '--kind', netzname, dn, str(aus)]); peak = 0.0; grund = None
        while p.poll() is None:
            time.sleep(0.1); r = rss(p.pid); peak = max(peak, r)
            if r > grenze_mib: grund = 'RAM %.0f MiB > %.0f' % (r, grenze_mib)
            elif time.perf_counter() - t > grenze_s: grund = 'Zeit > %.0f s' % grenze_s
            if grund: p.kill(); p.wait(); break
        wall = time.perf_counter() - t; k = json.loads(aus.read_text()) if aus.exists() else None
        if grund:
            z = dict(darstellung=dn, status='OFFEN', abbruch=grund, wall_s=round(wall, 2), peak_mib=round(peak, 1)); zeilen.append(z)
            print('  %-6s OFFEN (Grenze: %s)' % (dn, grund)); continue
        if k is None or p.returncode != 0:
            z = dict(darstellung=dn, status='FEHLER', abbruch='Absturz/keine Ausgabe, Rueckgabe %s' % p.returncode, wall_s=round(wall, 2), peak_mib=round(peak, 1)); zeilen.append(z)
            print('  %-6s FEHLER (%s). REIHE GESTOPPT.' % (dn, z['abbruch'])); raise SystemExit(3)
        if wahr is None:                                   # unabhaengiges Orakel: vollstaendige Auswertung des Netzes fuer alle Eingaben, NACH Ableitung und Einfrieren
            t0 = time.perf_counter(); wahr = {i for i, b in enumerate(alle) if N.erfuellt(b)}; orakel_s = round(time.perf_counter() - t0, 4)
            print('  Orakel (nach Ableitung): wahre Loesungen %d von %d, %.3f s' % (len(wahr), len(alle), orakel_s))
        erl = set(k['erlaubt']); schein = len(erl - wahr); verloren = len(wahr - erl)
        z = dict(darstellung=dn, status=k['status'], erlaubt=len(erl), scheinloesungen=schein, verlorene=verloren, entschieden=(schein == 0 and verloren == 0),
                 groesse=k['groesse'], folgerungen=k['folgerungen'], ableitung_s=k['ableitung_s'], ableitung_peak_mib=k['ableitung_peak_mib'],
                 orakel_s=orakel_s, folgerungen_pruefung_s=k['kontrolle_s'], kontrolle_s=k['kontrolle_s'],
                 wall_s=round(wall, 2), peak_mib_extern=round(peak, 1), rlimit_aktiv=k['rlimit_aktiv'], rlimit_mib=k['rlimit_mib']); zeilen.append(z)
        print('  %-6s %-11s erlaubt %3d | Schein %3d | verloren %d | Ableitung %6.3f s %5.1f MiB | Orakel %6.3f s | Folgerungen-Pruefung %6.4f s | harte Grenze %s | %s' % (dn, k['status'], len(erl), schein, verloren, k['ableitung_s'], k['ableitung_peak_mib'], orakel_s, k['kontrolle_s'], 'aktiv %d MiB' % k['rlimit_mib'] if k['rlimit_aktiv'] else 'NICHT AKTIV', k['groesse']))
        if verloren:
            z['status'] = 'FEHLER'; z['entschieden'] = False
            print('  FEHLER: %s verliert %d echte Loesungen – unsound. REIHE GESTOPPT.' % (dn, verloren)); raise SystemExit(2)
    return dict(netz=N.name, frei=n, knoten=len(N.g.nodes), wahr=(len(wahr) if wahr is not None else None), orakel_s=orakel_s, zeilen=zeilen)

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--kind': kind(sys.argv[2], sys.argv[3], sys.argv[4]); sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == '--tests':
        # Kontrolltests der Grenz- und Fehlerfaelle; jeder muss das erwartete Verhalten zeigen
        prot = []; alle_ok = True
        for dn, erwartet in (('Dx', 'STOPP Rueckgabe 2'), ('Dt_Zeit', 'OFFEN Zeit'), ('Dt_Speicher', 'OFFEN RAM'), ('Dt_Absturz', 'STOPP Rueckgabe 3')):
            try: r = messen('L2', [dn], grenze_s=GRENZE_S_TEST, grenze_mib=200.0); ergebnis = r['zeilen'][0]['status'] + ' ' + str(r['zeilen'][0].get('abbruch', ''))
            except SystemExit as e: ergebnis = 'STOPP Rueckgabe %s' % e.code
            ok = ergebnis.startswith(erwartet); alle_ok &= ok
            prot.append(dict(test=dn, erwartet=erwartet, ergebnis=ergebnis, bestanden=ok)); print('  TEST %-11s erwartet: %-20s erhalten: %-28s %s' % (dn, erwartet, ergebnis, 'BESTANDEN' if ok else 'GESCHEITERT'))
        (HERE / 'ERGEBNIS_L1_KONTROLLTESTS.json').write_text(json.dumps(dict(alle_bestanden=alle_ok, tests=prot), indent=1))
        if not alle_ok: print('KONTROLLTESTS GESCHEITERT'); sys.exit(1)
        print('alle Kontrolltests bestanden'); sys.exit(0)
    netze = sys.argv[1:] or list(NETZE)
    erg = [messen(nz, ['D1', 'D2', 'D6', 'D6-R4', 'D6-R3', 'D6nurR4', 'D6+R5', 'D6+R5+R6', 'D6+R5+R6+R7']) for nz in netze]
    for f in list(HERE.glob('_kind_*.json')) + list(HERE.glob('_kind_*.ableitung')): f.unlink()
    (HERE / 'ERGEBNIS_L1_SELBSTTEST.json').write_text(json.dumps(dict(stufe='a2', grenzen=dict(zeit_s=GRENZE_S, ram_mib=GRENZE_MIB), ergebnisse=erg), indent=1, default=str))
