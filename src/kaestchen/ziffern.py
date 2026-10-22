#!/usr/bin/env python3
"""GEKOPPELTE 2-BIT-STUECKE (Fable, 2026-10-22). Woerter der Breite w (gerade) als D = w/2 Basis-4-Ziffern.
Netz: Variablen (Ziffern 0..3, Uebertraege 0..1) mit Domaenenmasken; Beziehungen als Tupeltabellen:
  ADD  (a_j, b_j, cin_j, z_j, cout_j): a + b + cin = z + 4*cout         (5-stellig; gueltige Zeilen = 4*4*2 = 32 von 256 Tupeln)
  NEG  (x_j, y_j): x = 3 - y                                              (2-stellig)
  XOR  (a_j, b_j, z_j): z = a XOR b                                        (3-stellig)
  Konstanten = Ziffern mit Einwertdomaene. Gleiche Variable in einer Beziehung (z. B. x + x) wird als wiederholte Position gefuehrt.
Lineare Gleichungen werden in ADD/NEG mit Zwischenwoertern uebersetzt: k*x = x+x (k=2), -x = NEG(x) mit Eingangsuebertrag 1 in der
folgenden Addition (a + ~x + 1 = a - x), -2x = NEG(x+x) ebenso; Summe aller
Terme + Konstante = 0 mod 2^w, letzter Uebertrag verworfen (cout der letzten Ziffer frei).
E3 = verallgemeinerte Bogenkonsistenz ueber die Tupeltabellen (Tupel gueltig <=> alle Werte in Domaenen; Domaene := Projektion).
E4 = E3 + Paarbeziehungen R(x,y) als 4x4-Masken fuer ALLE ungeordneten Paare innerhalb einer Beziehung sowie abgeleitete Paare
     (Schliessung: Paar (x,z) wird angelegt, wenn x und z ueber ein y beide Paare haben; Radius = wiederholte Schliessung bis Fixpunkt
     oder Paarobergrenze -> OPEN). Fortpflanzung: Tupel gueltig <=> alle Werte in Domaenen UND alle Paare des Tupels erlaubt;
     Paare := Projektion der gueltigen Tupel; Komposition R(x,z) &= R(x,y) o R(y,z); Domaenen := Projektion der Paare; bis Fixpunkt.
Fehlendes Paar = universell. Paare mit x<y gespeichert; vertauscht = transponiert. Kein Selbstpaar.
Korrektheit (sound): Jede Operation entfernt nur Werte/Paare/Tupel, die in keiner Gesamtloesung vorkommen koennen (Projektion/Schnitt)."""
import itertools

ALLE = {4: 0b1111, 2: 0b11}

def tabelle(typ):
    if typ == 'ADD': return [(a, b, ci, (a + b + ci) & 3, (a + b + ci) >> 2) for a in range(4) for b in range(4) for ci in range(2)]
    if typ == 'NEG': return [(x, 3 - x) for x in range(4)]
    if typ == 'XOR': return [(a, b, a ^ b) for a in range(4) for b in range(4)]
    raise ValueError(typ)
TABELLEN = {t: tabelle(t) for t in ('ADD', 'NEG', 'XOR')}
GROESSEN = {'ADD': (4, 4, 2, 4, 2), 'NEG': (4, 4), 'XOR': (4, 4, 4)}

class Netz:
    def __init__(self, w):
        assert w % 2 == 0; self.w = w; self.D = w // 2
        self.dom = []; self.groesse = []; self.name = []; self.bez = []      # bez: (typ, [var-ids])
        self.woerter = {}; self.geteilt = {}                                 # strukturelles Teilen identischer Teilausdruecke (wie gatter.py)
    def var(self, name, groesse):
        self.dom.append(ALLE[groesse]); self.groesse.append(groesse); self.name.append(name); return len(self.dom) - 1
    def wort(self, name):
        ids = [self.var('%s[%d]' % (name, j), 4) for j in range(self.D)]; self.woerter[name] = ids; return ids
    def konst(self, wert, name='k'):
        key = ('KONST', wert)
        if key in self.geteilt: return self.geteilt[key]
        ids = self.wort('%s=%d' % (name, wert)); self.geteilt[key] = ids
        for j, v in enumerate(ids): self.dom[v] = 1 << ((wert >> (2 * j)) & 3)
        return ids
    def fest(self, v, wert): self.dom[v] &= 1 << wert
    def add(self, a, b, name, cin0=0):
        """z = a + b + cin0 mod 2^w; liefert Ziffern von z. Uebertraege als eigene Variablen, cin_0 = cin0 (0 normal, 1 fuer a + ~b + 1 = a - b),
        cout_(D-1) frei (verworfen)."""
        key = ('ADD', tuple(sorted((tuple(a), tuple(b)))), cin0)
        if key in self.geteilt: return self.geteilt[key]
        z = self.wort(name); cin = self.var('c0_' + name, 2); self.fest(cin, cin0)
        for j in range(self.D):
            cout = self.var('c%d_%s' % (j + 1, name), 2)
            self.bez.append(('ADD', [a[j], b[j], cin, z[j], cout])); cin = cout
        self.geteilt[key] = z; return z
    def neg(self, x, name):
        key = ('NEG', tuple(x))
        if key in self.geteilt: return self.geteilt[key]
        y = self.wort(name)
        for j in range(self.D): self.bez.append(('NEG', [y[j], x[j]]))
        self.geteilt[key] = y; return y
    def xor(self, a, b, name):
        z = self.wort(name)
        for j in range(self.D): self.bez.append(('XOR', [a[j], b[j], z[j]]))
        return z
    def gleich(self, x, y):
        """x = y (Alias) durch Verschmelzen der Variablen (gleiche Knoten, wie gatter.py). Kanonisch ueber bereits verschmolzene Knoten."""
        x = [self.kanon(v) for v in x]; y = [self.kanon(v) for v in y]
        umb = {y[j]: x[j] for j in range(self.D) if y[j] != x[j]}
        if not umb: return
        self.bez = [(t, [umb.get(v, v) for v in vs]) for t, vs in self.bez]
        for j in range(self.D):
            if y[j] != x[j]: self.dom[x[j]] &= self.dom[y[j]]
        self._umb = getattr(self, '_umb', {})
        for k in list(self._umb): self._umb[k] = umb.get(self._umb[k], self._umb[k])
        self._umb.update(umb)
    def kanon(self, v):
        u = getattr(self, '_umb', {})
        while v in u: v = u[v]
        return v

def kompiliere(w, n, gls, fakten, extra=()):
    """Lineare Gleichungen sum k_i x_i = c (k in -2..2), Fakten (x,y,neg), extra: ('XOR', x, y, c) z=x XOR y = c | ('INC', x, z): z = x+1.
    Liefert Netz und die Ziffern-IDs der Originalwoerter."""
    N = Netz(w); M = 1 << w
    X = [N.wort('x%d' % i) for i in range(n)]
    for x, y, neg in fakten:
        if neg: N.bez.extend(('NEG', [X[x][j], X[y][j]]) for j in range(N.D))
        else: N.gleich(X[x], X[y])
    X = [[N.kanon(v) for v in xs] for xs in X]      # nach Alias-Verschmelzung kanonische IDs verwenden
    for gi, (ko, c) in enumerate(gls):
        terme = []                                      # (ziffern, plus_eins): plus_eins=True fuer negierte Terme (x - y = x + ~y + 1)
        for v, k in ko.items():
            k = k % M
            if k == 0: continue
            if k == 1: terme.append((X[v], False))
            elif k == 2: terme.append((N.add(X[v], X[v], 'g%d_2x%d' % (gi, v)), False))
            elif k == M - 1: terme.append((N.neg(X[v], 'g%d_nx%d' % (gi, v)), True))
            elif k == M - 2: terme.append((N.neg(N.add(X[v], X[v], 'g%d_2x%d' % (gi, v)), 'g%d_n2x%d' % (gi, v)), True))
            else: raise ValueError('Koeffizient %d nicht vorgesehen' % k)
        if not terme:
            s = N.konst(0, 'null')
        else:
            (s, p1) = terme[0]
            if p1: s = N.add(s, N.konst(0, 'null'), 'g%d_p1' % gi, cin0=1)       # einzelner negierter Term: ~x + 1
            for t_i, (t, p) in enumerate(terme[1:]): s = N.add(s, t, 'g%d_s%d' % (gi, t_i), cin0=1 if p else 0)
        for j in range(N.D): N.fest(s[j], (c >> (2 * j)) & 3)
    for e in extra:
        if e[0] == 'XOR':
            z = N.xor(X[e[1]], X[e[2]], 'xor%d_%d' % (e[1], e[2]))
            for j in range(N.D): N.fest(z[j], (e[3] >> (2 * j)) & 3)
        elif e[0] == 'INC':
            z = N.add(X[e[1]], N.konst(1, 'eins'), 'inc%d' % e[1]); N.gleich(X[e[2]], z); X = [[N.kanon(v) for v in xs] for xs in X]
    return N, [[N.kanon(v) for v in xs] for xs in X]

def auswerten_wort(w, n, bel, gls, fakten, extra=()):
    """Unabhaengige Referenz direkt auf Woertern."""
    M = 1 << w
    ok = all(sum(k * bel[v] for v, k in ko.items()) % M == c % M for ko, c in gls)
    ok = ok and all((bel[x] == bel[y]) if not neg else (bel[x] == M - 1 - bel[y]) for x, y, neg in fakten)
    for e in extra:
        if e[0] == 'XOR': ok = ok and (bel[e[1]] ^ bel[e[2]]) == e[3]
        elif e[0] == 'INC': ok = ok and bel[e[2]] == (bel[e[1]] + 1) % M
    return ok

# ---------------- E3: Bogenkonsistenz ueber Tupel ----------------
def e3(N, max_runden=200):
    dom = list(N.dom); runden = 0; ops = 0
    if any(m == 0 for m in dom): return 'WIDERSPRUCH', dom, {}, dict(runden=0, tupelops=0)   # schon beim Aufbau geleerte Domaene
    while True:
        runden += 1; geaendert = False
        for typ, vs in N.bez:
            neu = [0] * len(vs)
            for tup in TABELLEN[typ]:
                ops += 1
                if all(dom[v] >> val & 1 for v, val in zip(vs, tup)) and all(tup[i] == tup[j] for i in range(len(vs)) for j in range(i + 1, len(vs)) if vs[i] == vs[j]):
                    for i, val in enumerate(tup): neu[i] |= 1 << val
            for i, v in enumerate(vs):
                m = dom[v] & neu[i]
                if m != dom[v]: dom[v] = m; geaendert = True
                if m == 0: return 'WIDERSPRUCH', dom, {}, dict(runden=runden, tupelops=ops)
        if not geaendert: return 'FIXPUNKT', dom, {}, dict(runden=runden, tupelops=ops)
        if runden >= max_runden: return 'OFFEN', dom, {}, dict(runden=runden, tupelops=ops)

# ---------------- E4: + Paarbeziehungen ----------------
def _paarmaske(gx, gy): return (1 << (gx * gy)) - 1
def e4(N, max_runden=200, max_paare=20000, schliessung='voll'):
    """schliessung='voll': Komposition entlang ALLER vorhandenen Paare (auch abgeleiteter), bis Fixpunkt (teuer, Paare ~ quadratisch).
    schliessung='radius1': Komposition nur ueber gemeinsame Nachbarn y im URSPRUENGLICHEN Beziehungsgraphen (Paare aus Beziehungen);
    abgeleitete Paare werden angelegt und geschnitten, aber nicht als Kompositionspfade benutzt. Beides sound (nur Schnitte/Projektionen)."""
    dom = list(N.dom); gr = N.groesse
    if any(m == 0 for m in dom): return 'WIDERSPRUCH', dom, {}, dict(runden=0, tupelops=0, paare=0)
    paare = {}                      # (x,y) x<y -> Maske ueber (vx*gy + vy)
    def key(x, y): return (x, y) if x < y else (y, x)
    def hole(x, y):
        k = key(x, y); return paare.get(k)
    def setze(x, y, maske_xy):
        """maske_xy ueber (vx, vy) in Reihenfolge der Argumente; speichert kanonisch x<y."""
        if x == y: return False
        if x > y:  # transponieren
            m = 0
            for vx in range(gr[x]):
                for vy in range(gr[y]):
                    if maske_xy >> (vx * gr[y] + vy) & 1: m |= 1 << (vy * gr[x] + vx)
            maske_xy = m; x, y = y, x
        alt = paare.get((x, y))
        neu = maske_xy if alt is None else (alt & maske_xy)
        if alt is None and len(paare) >= max_paare: return None
        if neu != alt: paare[(x, y)] = neu; return True
        return False
    def erlaubt(x, y, vx, vy):
        if x == y: return vx == vy
        k = key(x, y); m = paare.get(k)
        if m is None: return True
        return (m >> (vx * gr[y] + vy) & 1) if x < y else (m >> (vy * gr[x] + vx) & 1)
    # Paare aller Beziehungen anlegen (universell)
    for typ, vs in N.bez:
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                if vs[i] != vs[j] and key(vs[i], vs[j]) not in paare: paare[key(vs[i], vs[j])] = _paarmaske(gr[vs[i]], gr[vs[j]]) if vs[i] < vs[j] else _paarmaske(gr[vs[j]], gr[vs[i]])
    runden = 0; ops = 0; status = None; nachbarn = {}
    basis_nb = {}
    for (x, y) in list(paare): basis_nb.setdefault(x, set()).add(y); basis_nb.setdefault(y, set()).add(x)
    def nachbar_index():
        if schliessung == 'radius1': return basis_nb
        nb = {}
        for (x, y) in paare: nb.setdefault(x, set()).add(y); nb.setdefault(y, set()).add(x)
        return nb
    while True:
        runden += 1; geaendert = False
        # (1) Tupel gegen Domaenen UND Paare; Projektion auf Domaenen und Paare
        for typ, vs in N.bez:
            neu_dom = [0] * len(vs); neu_paar = {}
            for tup in TABELLEN[typ]:
                ops += 1
                if not all(dom[v] >> val & 1 for v, val in zip(vs, tup)): continue
                if not all(erlaubt(vs[i], vs[j], tup[i], tup[j]) for i in range(len(vs)) for j in range(i + 1, len(vs))): continue
                for i, val in enumerate(tup): neu_dom[i] |= 1 << val
                for i in range(len(vs)):
                    for j in range(i + 1, len(vs)):
                        if vs[i] != vs[j]: neu_paar[(i, j)] = neu_paar.get((i, j), 0) | (1 << (tup[i] * gr[vs[j]] + tup[j]))
            for i, v in enumerate(vs):
                m = dom[v] & neu_dom[i]
                if m != dom[v]: dom[v] = m; geaendert = True
                if m == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
            for (i, j), m in neu_paar.items():
                r = setze(vs[i], vs[j], m)
                if r: geaendert = True
                if hole(vs[i], vs[j]) == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
        # (2) Komposition / Schliessung: R(x,z) &= R(x,y) o R(y,z)
        nb = nachbar_index()
        for y, ns in list(nb.items()):
            ns = sorted(ns)
            for ia in range(len(ns)):
                for ib in range(ia + 1, len(ns)):
                    x, z = ns[ia], ns[ib]
                    # Komposition: erlaubt(x=vx, z=vz) wenn ex. vy mit erlaubt(x,y,vx,vy) und erlaubt(y,z,vy,vz) und vy in dom[y]
                    m = 0
                    for vx in range(gr[x]):
                        if not dom[x] >> vx & 1: continue
                        for vz in range(gr[z]):
                            if not dom[z] >> vz & 1: continue
                            ops += 1
                            if any(dom[y] >> vy & 1 and erlaubt(x, y, vx, vy) and erlaubt(y, z, vy, vz) for vy in range(gr[y])): m |= 1 << (vx * gr[z] + vz)
                    r = setze(x, z, m)
                    if r is None: status = 'OPEN_PAARGRENZE'; continue
                    if r: geaendert = True
                    if hole(x, z) == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
        # (3) Domaenen aus Paaren
        for (x, y), m in paare.items():
            mx = 0; my = 0
            for vx in range(gr[x]):
                for vy in range(gr[y]):
                    if m >> (vx * gr[y] + vy) & 1 and dom[x] >> vx & 1 and dom[y] >> vy & 1: mx |= 1 << vx; my |= 1 << vy
            if (dom[x] & mx) != dom[x]: dom[x] &= mx; geaendert = True
            if (dom[y] & my) != dom[y]: dom[y] &= my; geaendert = True
            if dom[x] == 0 or dom[y] == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
        if not geaendert: return (status or 'FIXPUNKT'), dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
        if runden >= max_runden: return 'OFFEN', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
