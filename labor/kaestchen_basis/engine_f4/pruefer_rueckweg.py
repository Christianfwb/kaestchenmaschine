#!/usr/bin/env python3
"""BITKERN32 (BLOCKTEST32, GO-1 "Rechenproben A0-A3", Fable 2026-10-31).

Neues Modul, parametrisch in der Wortbreite NB (4, 8, 32). Gleiches Regelvokabular wie der bestaetigte 4-Bit-Bitkern
(FABLE_AN_GHOST_ADDIERER_F2_KENNUNGEN_20261031), aber eigener, schlanker Bit-Propagationskern:
  START   bekanntes Eingabebit mit Herkunft (HEADER, IV, K, PAD, NULL, AUFGABE, ZIEL, TEST)
  B-R1    bekanntes Wort -> seine NB Bits
  B-R3    Tabelleninstanz (Maj, Ch, Gleich, Kleiner, Oder): Zeilenfilter, erzwungene Spalte -> Bit
  B-R4    XOR-Gleichung ueber GF(2): genau eine Unbekannte -> Bit; keine Unbekannte -> Pruefung/Widerspruch
  B-R5    Addition w = u + konst (Kennung Ak): Summenbits als B-R4, Uebertraege als Maj-Tabellen, Konstantenbits CAk.i
  B-R6    Addition w = u + t      (Kennung Ak): dito, Uebertragsbits cAk.i
  V-R1/2  Vergleichskette H <= T (Gleich-/Kleiner-Tabellen von Bit 255 abwaerts), V-R3 Endurteil = kleiner ODER gleich
  Rotation/Schiebung sind Verdrahtung (Bitindex), keine Regel; Schiebung fuellt mit dem Nullbit N.0 (START NULL).
Keine Pivot-Algebra mod 2^NB: fuer Rechenproben (Eingaben bekannt, Ausgaben hergeleitet) genuegt Einheitspropagation.
Der F4-Wortkern (kontrollkern.py) wird NICHT importiert und nicht veraendert.
Jede Herleitung steht im Buch (Regel, Eltern, Inhalt); herleitung_pruefen() ist eine zweite, getrennt geschriebene Routine.
Kein SHA-Lauf aus diesem Modul; die Verdrahtung von SHA-256 liegt in sha_verdrahtung32.py.
"""
from collections import defaultdict, deque

HERKUNFT_START = ('HEADER', 'IV', 'K', 'PAD', 'NULL', 'AUFGABE', 'ZIEL', 'TEST', 'VERGLEICH')
REGELN = ('START', 'B-R1', 'B-R3', 'B-R4', 'B-R5', 'B-R6', 'V-R1', 'V-R2', 'V-R3')


class Widerspruch(Exception):
    pass


class Budget(Exception):
    pass


def _maj(p, q, r): return (p & q) | (p & r) | (q & r)
def _ch(p, q, r): return (p & q) | ((1 - p) & r)
def _gleich(eq, h, t): return eq & (1 - (h ^ t))
def _kleiner(lt, eq, h, t): return lt | (eq & (1 - h) & t)
def _oder(p, q): return p | q
FUNKTIONEN = {'Maj': (3, _maj), 'Ch': (3, _ch), 'Gleich': (3, _gleich), 'Kleiner': (4, _kleiner), 'Oder': (2, _oder)}
TABELLEN = {}
for _n, (_k, _f) in FUNKTIONEN.items():
    TABELLEN[_n] = [tuple(((i >> j) & 1) for j in range(_k)) + (_f(*[(i >> j) & 1 for j in range(_k)]),) for i in range(1 << _k)]

BUDGET_32 = dict(BB=4_000_000, BX=2_000_000, BT=40_000_000, BA=20_000)


class Kern:
    def __init__(self, nb, budget=None, name='K'):
        self.NB = nb
        self.M = 1 << nb
        self.name = name
        self.budget = dict(BUDGET_32 if budget is None else budget)
        self.wert = {}                 # Bitname -> 0/1
        self.her = {}                  # Bitname -> Buchnummer
        self.buch = []                 # Eintraege: (regel, eltern, art, info)
        self.xor = []                  # Gleichungen: [vars(list), paritaet, nr]
        self.x_index = defaultdict(list)
        self.taf = []                  # Tabellen: (name, namen, nr)
        self.t_index = defaultdict(list)
        self.additionen = {}           # Kennung -> (nr, schluessel)
        self.entfaltet = {}            # schluessel -> Kennung
        self.worte = {}                # Wortname -> Herkunft/Regel (nur Buchfuehrung)
        self.zb = dict(bits=0, xor=0, tabellen=0, tabellenpruefungen=0, additionen=0, widersprueche=0)
        self.arbeit = deque()
        self.protokoll = []

    # ---------------- Buch ----------------
    def buche(self, regel, eltern, art, info):
        self.buch.append((regel, tuple(eltern), art, info))
        return len(self.buch) - 1

    def nr(self, name): return self.her[name]

    # ---------------- Bits ----------------
    def bit(self, name): return self.wert.get(name)

    def setze(self, name, wert, regel, eltern):
        """Bit festlegen. Liefert True, wenn neu; Widerspruch bei anderem bekanntem Wert."""
        alt = self.wert.get(name)
        if alt is not None:
            if alt == wert:
                return False
            self.zb['widersprueche'] += 1
            nr = self.buche(regel, list(eltern) + [self.her[name]], 'WIDERSPRUCH', (name, alt, wert))
            raise Widerspruch(f"{name}: {alt} bekannt [{self.her[name]}], {wert} verlangt durch {regel} [{nr}]")
        self.zb['bits'] += 1
        if self.zb['bits'] > self.budget['BB']:
            raise Budget(f"BB Bits {self.budget['BB']} bei {self.name}")
        self.wert[name] = wert
        self.her[name] = self.buche(regel, eltern, 'BIT', (name, wert))
        self.arbeit.append(name)
        return True

    def start(self, name, wert, herkunft):
        if herkunft not in HERKUNFT_START:
            raise ValueError(f"unzulaessige Herkunft {herkunft}")
        return self.setze(name, wert, f"START {herkunft}", [])

    def null(self):
        if 'N.0' not in self.wert:
            self.start('N.0', 0, 'NULL')
        return 'N.0'

    def wort_start(self, w, wert, herkunft, nb=None):
        """B-R1: bekanntes Wort als START buchen, seine Bits ableiten."""
        nb = nb or self.NB
        if herkunft not in HERKUNFT_START:
            raise ValueError(f"unzulaessige Herkunft {herkunft}")
        nr = self.buche(f"START {herkunft}", [], 'WORT', (w, wert, nb))
        self.worte[w] = nr
        for i in range(nb):
            self.setze(f"{w}.{i}", (wert >> i) & 1, f"B-R1 {w} bit {i}", [nr])
        return nr

    def wort(self, w):
        """Bits eines Worts (0/1/None), Bit 0 zuerst."""
        return [self.wert.get(f"{w}.{i}") for i in range(self.NB)]

    def wort_wert(self, w):
        b = self.wort(w)
        if any(x is None for x in b): return None
        return sum(x << i for i, x in enumerate(b))

    # ---------------- Gleichungen und Tabellen ----------------
    def xor_gl(self, namen, paritaet, regel, eltern):
        """B-R4-Gleichung: Summe der Bits = paritaet mod 2. Doppelte Variablen heben sich auf."""
        z = defaultdict(int)
        for n in namen: z[n] ^= 1
        vs = [n for n, k in z.items() if k]
        self.zb['xor'] += 1
        if self.zb['xor'] > self.budget['BX']:
            raise Budget(f"BX Gleichungen {self.budget['BX']} bei {self.name}")
        nr = self.buche(regel, eltern, 'GL', (tuple(vs), paritaet))
        gid = len(self.xor)
        self.xor.append([vs, paritaet, nr])
        for v in vs: self.x_index[v].append(gid)
        self.arbeit.append(('GL', gid))
        return nr

    def tabelle(self, tname, namen, regel, eltern):
        """B-R3-Instanz: namen = Eingaenge..., Ausgang."""
        k = FUNKTIONEN[tname][0]
        assert len(namen) == k + 1, (tname, namen)
        self.zb['tabellen'] += 1
        nr = self.buche(regel, eltern, 'TAF', (tname, tuple(namen)))
        tid = len(self.taf)
        self.taf.append((tname, tuple(namen), nr))
        for v in namen: self.t_index[v].append(tid)
        self.arbeit.append(('TAF', tid))
        return nr

    # ---------------- Addierer ----------------
    def _kennung(self, schluessel, nr_quelle, regel):
        if schluessel in self.entfaltet:
            return self.entfaltet[schluessel], None
        self.zb['additionen'] += 1
        if self.zb['additionen'] > self.budget['BA']:
            raise Budget(f"BA Additionen {self.budget['BA']} bei {self.name}")
        kid = f"A{len(self.additionen) + 1}"
        nr = self.buche(regel, [nr_quelle] if nr_quelle is not None else [], 'ADD', (kid, schluessel))
        self.additionen[kid] = (nr, schluessel); self.entfaltet[schluessel] = kid
        return kid, nr

    def addition(self, w, u, t, nr_quelle=None):
        """B-R6: w = u + t mod 2^NB. Kennung Ak. Liefert Kennung."""
        kid, nr = self._kennung(('B-R6', w, u, t), nr_quelle, f"B-R6 {w} = {u} + {t}")
        if nr is None: return kid
        kopf = f"B-R6 {kid}"; c = f"c{kid}"; NB = self.NB
        self.setze(f"{c}.0", 0, f"{kopf} carry0", [nr])
        for i in range(NB):
            self.xor_gl([f"{w}.{i}", f"{u}.{i}", f"{t}.{i}", f"{c}.{i}"], 0, f"{kopf} summe {i}", [nr])
            if i + 1 < NB:
                self.tabelle('Maj', [f"{u}.{i}", f"{t}.{i}", f"{c}.{i}", f"{c}.{i+1}"], f"{kopf} carry {i+1}", [nr])
        return kid

    def addition_konst(self, w, u, konst, herkunft, nr_quelle=None):
        """B-R5: w = u + konst mod 2^NB, konst mit Herkunft. Kennung Ak."""
        konst %= self.M
        kid, nr = self._kennung(('B-R5', w, u, konst), nr_quelle, f"B-R5 {w} = {u} + {konst:#x} [{herkunft}]")
        if nr is None: return kid
        kopf = f"B-R5 {kid}"; c = f"c{kid}"; C = f"C{kid}"; NB = self.NB
        for i in range(NB):
            self.setze(f"{C}.{i}", (konst >> i) & 1, f"{kopf} konst {i} {herkunft}", [nr])
        self.setze(f"{c}.0", 0, f"{kopf} carry0", [nr])
        for i in range(NB):
            self.xor_gl([f"{w}.{i}", f"{u}.{i}", f"{C}.{i}", f"{c}.{i}"], 0, f"{kopf} summe {i}", [nr])
            if i + 1 < NB:
                self.tabelle('Maj', [f"{u}.{i}", f"{C}.{i}", f"{c}.{i}", f"{c}.{i+1}"], f"{kopf} carry {i+1}", [nr])
        return kid

    # ---------------- Verdrahtung: XOR von Rotationen/Schiebungen ----------------
    def rotr_bit(self, x, i, n): return f"{x}.{(i + n) % self.NB}"
    def shr_bit(self, x, i, n): return f"{x}.{i + n}" if i + n < self.NB else self.null()

    def sigma(self, out, x, rot, shr, regel):
        """out.i = XOR ueber rotr(x, r) fuer r in rot und shr(x, s) fuer s in shr. Verdrahtung, als B-R4-Gleichungen gebucht."""
        for i in range(self.NB):
            namen = [f"{out}.{i}"] + [self.rotr_bit(x, i, r) for r in rot] + [self.shr_bit(x, i, s) for s in shr]
            self.xor_gl(namen, 0, f"{regel} bit {i}", [])

    def bitfunktion(self, tname, out, xs, regel):
        """out.i = Tabelle(xs[0].i, xs[1].i, ...) fuer alle i (Ch, Maj)."""
        for i in range(self.NB):
            self.tabelle(tname, [f"{x}.{i}" for x in xs] + [f"{out}.{i}"], f"{regel} bit {i}", [])

    # ---------------- Vergleichskette H <= T ----------------
    def vergleich(self, hbits, ziel, breite, praefix='V'):
        """hbits: Bitnamen der Zahl H, Index i = Stellenwert 2^i, len = breite. ziel: Ganzzahl T.
        Kette von Bit breite-1 abwaerts: eq_i = eq_(i+1) AND (h_i == t_i); lt_i = lt_(i+1) OR (eq_(i+1) AND NOT h_i AND t_i).
        Treffer = lt_0 OR eq_0 (Gleichheit zaehlt). Liefert den Namen des Trefferbits."""
        assert len(hbits) == breite
        nrz = self.buche('START ZIEL', [], 'WORT', (f"{praefix}_T", ziel, breite))
        for i in range(breite):
            self.setze(f"{praefix}_T.{i}", (ziel >> i) & 1, f"B-R1 {praefix}_T bit {i}", [nrz])
        self.start(f"{praefix}_eq.{breite}", 1, 'VERGLEICH')
        self.start(f"{praefix}_lt.{breite}", 0, 'VERGLEICH')
        for i in range(breite - 1, -1, -1):
            self.tabelle('Gleich', [f"{praefix}_eq.{i+1}", hbits[i], f"{praefix}_T.{i}", f"{praefix}_eq.{i}"], f"V-R1 gleich {i}", [nrz])
            self.tabelle('Kleiner', [f"{praefix}_lt.{i+1}", f"{praefix}_eq.{i+1}", hbits[i], f"{praefix}_T.{i}", f"{praefix}_lt.{i}"], f"V-R2 kleiner {i}", [nrz])
        self.tabelle('Oder', [f"{praefix}_lt.0", f"{praefix}_eq.0", f"{praefix}_treffer"], 'V-R3 treffer', [nrz])
        return f"{praefix}_treffer"

    # ---------------- Propagation ----------------
    def fixpunkt(self):
        """Einheitspropagation bis nichts Neues. Widerspruch/Budget als Ausnahme."""
        wert, xor, taf = self.wert, self.xor, self.taf
        offen = deque()
        while self.arbeit or offen:
            while self.arbeit:
                a = self.arbeit.popleft()
                if isinstance(a, tuple):
                    offen.append(a)
                else:
                    for gid in self.x_index.get(a, ()): offen.append(('GL', gid))
                    for tid in self.t_index.get(a, ()): offen.append(('TAF', tid))
            while offen and not self.arbeit:
                art, idx = offen.popleft()
                if art == 'GL':
                    vs, par, nr = xor[idx]
                    unbekannt = [v for v in vs if v not in wert]
                    if len(unbekannt) > 1:
                        continue
                    s = par
                    for v in vs:
                        if v in wert: s ^= wert[v]
                    eltern = [nr] + [self.her[v] for v in vs if v in wert]
                    if not unbekannt:
                        if s != 0:
                            nr2 = self.buche(f"B-R4 [{nr}]", eltern, 'WIDERSPRUCH', (tuple(vs), par))
                            self.zb['widersprueche'] += 1
                            raise Widerspruch(f"Gleichung [{nr}] verletzt [{nr2}]")
                        continue
                    self.setze(unbekannt[0], s, f"B-R4 [{nr}]", eltern)
                else:
                    tname, namen, nr = taf[idx]
                    self.zb['tabellenpruefungen'] += 1
                    if self.zb['tabellenpruefungen'] > self.budget['BT']:
                        raise Budget(f"BT Tabellenpruefungen {self.budget['BT']} bei {self.name}")
                    bel = [wert.get(n) for n in namen]
                    zeilen = [r for r in TABELLEN[tname] if all(b is None or b == r[j] for j, b in enumerate(bel))]
                    eltern = [nr] + [self.her[n] for n, b in zip(namen, bel) if b is not None]
                    if not zeilen:
                        nr2 = self.buche(f"B-R3 {tname} [{nr}]", eltern, 'WIDERSPRUCH', (tname, namen))
                        self.zb['widersprueche'] += 1
                        raise Widerspruch(f"Tabelle {tname} [{nr}] ohne vertraegliche Zeile [{nr2}]")
                    for j, b in enumerate(bel):
                        if b is None:
                            werte = {r[j] for r in zeilen}
                            if len(werte) == 1:
                                self.setze(namen[j], werte.pop(), f"B-R3 {tname} [{nr}]", eltern)
        return self

    def groesse(self):
        return dict(bits=len(self.wert), gleichungen=len(self.xor), tabellen=len(self.taf), additionen=len(self.additionen),
                    buch=len(self.buch), variablen=len(set(v for g in self.xor for v in g[0]) | set(n for t in self.taf for n in t[1]) | set(self.wert)))


# ======================================================================================
# VERTRAG - was die Aufgabe festlegt. Wird von der PRUEFSTELLE aus der AUFGABE gebaut (eigener Kern ohne Propagation),
# nie aus dem Loeserbuch. Der Pruefer bindet jeden START, jede Verdrahtungsgleichung, jede Tabelle und jede Addition daran.
# ======================================================================================
def vertrag_aus(kern):
    """Strukturvertrag eines Kerns: nur START-Werte und Verdrahtung (keine hergeleiteten Bits). Der Kern darf dafuer
    nicht propagiert haben; die Pruefstelle ruft die Verdrahtung auf einem frischen Kern auf und bildet daraus den Vertrag."""
    v = dict(nb=kern.NB, starts={}, worte={}, gl=set(), taf=set(), add=set(), verdeckt=set(getattr(kern, 'verdeckt', ())),
             lf=bool(getattr(kern, 'lf', False)), spaet=dict(getattr(kern, 'spaet', {})), monome=bool(getattr(kern, 'monome', False)))
    for regel, eltern, art, info in kern.buch:
        rk = regel.split()[0]
        if rk == 'START' and art == 'WORT':
            v['worte'][info[0]] = (info[1], info[2])
        elif rk == 'START' and art == 'BIT':
            v['starts'][info[0]] = info[1]
        elif art == 'GL' and rk == 'B-R4':
            v['gl'].add((tuple(sorted(info[0])), info[1]))
        elif art == 'TAF' and rk in ('B-R3', 'V-R1', 'V-R2', 'V-R3'):
            v['taf'].add((info[0], tuple(info[1])))
        elif art == 'ADD':
            v['add'].add(tuple(info[1]))
    return v


# ======================================================================================
# PRUEFER - zweite, getrennt geschriebene Routine. Liest nur das Buch und den Vertrag, rechnet jede Herleitung nach.
# Fassung F2 (nach Ghost B32-02..05): START nur mit Vertrag, Verdrahtung nur mit Vertrag, Widerspruch nachgerechnet,
# jede Regel/Art-Kombination ausdruecklich zugelassen, Formfehler kontrolliert abgewiesen.
# ======================================================================================
def _direkt(tname, eingaben):
    """Zweite Fassung der Tabellenfunktionen als Arithmetik, nicht als Tabelle."""
    if tname == 'Maj': p, q, r = eingaben; return 1 if p + q + r >= 2 else 0
    if tname == 'Ch': p, q, r = eingaben; return q if p == 1 else r
    if tname == 'Gleich': eq, h, t = eingaben; return 1 if (eq == 1 and h == t) else 0
    if tname == 'Kleiner': lt, eq, h, t = eingaben; return 1 if (lt == 1 or (eq == 1 and h == 0 and t == 1)) else 0
    if tname == 'Oder': p, q = eingaben; return 1 if (p == 1 or q == 1) else 0
    raise ValueError(tname)


ZULAESSIG = {('START', 'WORT'), ('START', 'BIT'), ('START', 'WIDERSPRUCH'), ('B-R1', 'BIT'), ('B-R1', 'WIDERSPRUCH'),
             ('B-R3', 'TAF'), ('B-R3', 'BIT'), ('B-R3', 'WIDERSPRUCH'), ('B-R4', 'GL'), ('B-R4', 'BIT'), ('B-R4', 'WIDERSPRUCH'),
             ('B-R5', 'ADD'), ('B-R5', 'GL'), ('B-R5', 'TAF'), ('B-R5', 'BIT'), ('B-R5', 'WIDERSPRUCH'),
             ('B-R6', 'ADD'), ('B-R6', 'GL'), ('B-R6', 'TAF'), ('B-R6', 'BIT'), ('B-R6', 'WIDERSPRUCH'),
             ('V-R1', 'TAF'), ('V-R2', 'TAF'), ('V-R3', 'TAF')}


class _Abbruch(Exception):
    pass


def kanonisch(namen):
    """Sortiertes Tupel der Variablen mit ungerader Vielfachheit (GF(2)-Kuerzung) - zweite Fassung, unabhaengig von Kern.xor_gl."""
    z = {}
    for n in namen: z[n] = z.get(n, 0) + 1
    return tuple(sorted(n for n, k in z.items() if k % 2 == 1))


def herleitung_pruefen(kern, vertrag, max_fehler=20):
    """Prueft jeden Bucheintrag gegen den Vertrag und rechnet jede Herleitung und jeden Widerspruch nach.
    Ohne Vertrag ist nichts belegt: dann ist jeder START/GL/TAF/ADD ein Fehler. Liefert Fehlerliste (leer = bestanden)."""
    fehler = []
    bekannt = {}            # Bitname -> (wert, nr)
    worte = {}              # nr -> (wort, wert, nb)
    gl = {}                 # nr -> (vars, par)
    taf = {}                # nr -> (tname, namen)
    add = {}                # kid -> [nr, schluessel, summen, carries]
    widersprueche = []      # nr der nachgerechneten Widersprueche
    teil_zustand = {}
    formel_zustand = {}     # [FORMELNETZ] Zustand des Pruefers fuer Wort- und Formelzeilen
    def formel_entry(nr, regel, rk, eltern, art, info):           # [FORMELNETZ] Nachrechnung; Schreibrecht nur auf bekannt/widersprueche
        from formelnetz32 import pruefzweig
        pruefzweig(kern, vertrag, nr, regel, rk, eltern, art, info, bekannt, add, widersprueche, formel_zustand)
    if vertrag is None:
        vertrag = dict(nb=kern.NB, starts={}, worte={}, gl=set(), taf=set(), add=set())
    NB = kern.NB
    if vertrag.get('nb') != NB:
        return [f"Vertrag: Wortbreite {vertrag.get('nb')} statt {NB}"]

    def f(nr, text):
        fehler.append(f"B#{nr}: {text}")
        if len(fehler) >= max_fehler:
            raise _Abbruch()

    def wert_von(name, eltern, nr):
        """Bekannter Bitwert, nur wenn sein Eintrag unter den Eltern ist."""
        if name not in bekannt or bekannt[name][1] not in eltern:
            raise ValueError(f"{name} nicht aus den Eltern belegt")
        return bekannt[name][0]

    def nachrechnen(regel, eltern, name, nr):
        """Wert, den die Regel fuer name aus den Eltern erzwingt (oder Ausnahme)."""
        rk = regel.split()[0]
        if rk == 'B-R1':
            if len(eltern) != 1 or eltern[0] not in worte: raise ValueError('B-R1 ohne Wort-START')
            w, wwert, nb = worte[eltern[0]]
            if not name.startswith(w + '.'): raise ValueError(f'B-R1 {name} gehoert nicht zu {w}')
            i = int(name.split('.')[1])
            if i >= nb: raise ValueError('B-R1 Bitnummer ausserhalb')
            return (wwert >> i) & 1
        if rk == 'B-R4':
            qnr = int(regel.split('[')[1].rstrip(']'))
            if qnr not in gl or qnr not in eltern: raise ValueError(f'B-R4 ohne Gleichung [{qnr}]')
            vs, par = gl[qnr]
            if name not in vs: raise ValueError(f'{name} nicht in Gleichung [{qnr}]')
            s = par
            for v in vs:
                if v != name: s ^= wert_von(v, eltern, nr)
            return s
        if rk == 'B-R3':
            qnr = int(regel.split('[')[1].rstrip(']'))
            if qnr not in taf or qnr not in eltern: raise ValueError(f'B-R3 ohne Tabelle [{qnr}]')
            tname, namen = taf[qnr]
            if name not in namen: raise ValueError(f'{name} nicht in Tabelle [{qnr}]')
            k = FUNKTIONEN[tname][0]
            feste = {n: bekannt[n][0] for n in namen if n in bekannt and bekannt[n][1] in eltern}
            frei = [n for n in namen if n not in feste]
            moeglich = set()
            for m in range(1 << len(frei)):
                bel = dict(feste); bel.update({n: (m >> j) & 1 for j, n in enumerate(frei)})
                if _direkt(tname, [bel[n] for n in namen[:k]]) == bel[namen[k]]:
                    moeglich.add(bel[name])
            if len(moeglich) != 1: raise ValueError(f'Tabelle {tname} erzwingt {sorted(moeglich)}, nicht eindeutig')
            return moeglich.pop()
        if rk in ('B-R5', 'B-R6'):
            teile = regel.split(); kid = teile[1]
            if kid not in add or add[kid][0] not in eltern: raise ValueError(f'{rk} ohne registrierte Addition {kid}')
            if teile[2] == 'carry0':
                if name != f"c{kid}.0": raise ValueError('carry0 falscher Name')
                return 0
            if teile[2] == 'konst':
                i = int(teile[3]); konst = add[kid][1][3]
                if name != f"C{kid}.{i}": raise ValueError('Konstantenbit falscher Name')
                return (konst >> i) & 1
            raise ValueError(f'unbekannter Additionsschritt {regel}')
        raise ValueError(f'Regel {rk} setzt keine Bits')

    # ---------------- F4 Linearformen: Zustand und Nachrechnung (zweite Routine) ----------------
    verdeckt = set(vertrag.get('verdeckt', ()))
    formen = {}             # aktive FORM: name -> (k, frozenset V, nr)
    bez = {}                # nr -> (frozenset V, k)
    bindungen = {}          # taf nr -> (h, nr)
    gebunden = set()        # h-Namen
    l0 = set()

    def lesart_p(name, eltern):
        """Aktive Lesart mit Belegpflicht: BIT (Eltern enthalten seinen Eintrag) oder FORM (Eltern enthalten ihren Eintrag)."""
        if name in bekannt:
            if bekannt[name][1] not in eltern: raise ValueError(f"{name}: BIT-Beleg nicht in den Eltern")
            return (bekannt[name][0], frozenset())
        if name in formen:
            if formen[name][2] not in eltern: raise ValueError(f"{name}: FORM-Beleg nicht in den Eltern")
            return (formen[name][0], formen[name][1])
        raise ValueError(f"{name} ohne Lesart")

    def nf(k, V): return (tuple(sorted(V)), k & 1)

    def zweifall_p(tname, ein, u):
        w0 = _direkt(tname, [k for k, V in ein]); w1 = _direkt(tname, [k ^ (1 if u in V else 0) for k, V in ein])
        return (w0, frozenset()) if w0 == w1 else (w0, frozenset([u]))

    def setze_form_p(name, k, V, nr):
        if name in bekannt: raise ValueError(f"{name} hat BIT und erhaelt FORM")
        for u in V:
            if u not in verdeckt and u not in gebunden: raise ValueError(f"fremde Unbekannte {u} in Form von {name}")
        formen[name] = (k & 1, frozenset(V), nr)

    def setze_bit_p(name, wert, nr):
        if name in bekannt: raise ValueError(f"{name} doppelt gebucht")
        bekannt[name] = (wert, nr); formen.pop(name, None)

    def lf_eintrag(nr, regel, rk, eltern, art, info):
        if regel == 'START spaet':
            name, wert = info
            if art != 'BIT' or name in verdeckt or vertrag.get('spaet', {}).get(name) != wert:
                raise ValueError(f"START spaet {name} = {wert} nicht im Vertrag oder verdeckt")
            setze_bit_p(name, wert, nr); return
        if rk == 'L-R0':
            name, k, V = info
            if art != 'FORM' or name not in verdeckt or k != 0 or tuple(V) != (name,) or name in l0 or eltern:
                raise ValueError(f"L-R0 ungueltig fuer {name}")
            l0.add(name); setze_form_p(name, 0, [name], nr); return
        if rk == 'L-R1':
            qnr = int(regel.split('[')[1].rstrip(']'))
            if qnr not in gl or qnr not in eltern: raise ValueError(f"L-R1 ohne Gleichung [{qnr}]")
            vs, par = gl[qnr]
            if art == 'FORM':
                name, k, V = info
                if name not in vs: raise ValueError(f"{name} nicht in Gleichung")
                kk, VV = par, frozenset()
                for v in vs:
                    if v != name:
                        l = lesart_p(v, eltern); kk ^= l[0]; VV ^= l[1]
                if (kk & 1, VV) != (k & 1, frozenset(V)): raise ValueError(f"L-R1 Form {name}: nachgerechnet {nf(kk, VV)}, gebucht {nf(k, V)}")
                setze_form_p(name, k, V, nr); return
            if art == 'BEZIEHUNG':
                kk, VV = par, frozenset()
                for v in vs:
                    l = lesart_p(v, eltern); kk ^= l[0]; VV ^= l[1]
                if nf(kk, VV) != (tuple(info[0]), info[1]) or (not VV and not vertrag.get('monome')): raise ValueError(f"L-R1 Beziehung: nachgerechnet {nf(kk, VV)}, gebucht {info}")
                bez[nr] = (VV, kk & 1); return
            if art == 'BIT':                       # Formen der anderen Bits heben sich auf: Ergebnis konstant
                name, wert = info
                if name not in vs: raise ValueError(f"{name} nicht in Gleichung")
                kk, VV = par, frozenset()
                for v in vs:
                    if v != name:
                        l = lesart_p(v, eltern); kk ^= l[0]; VV ^= l[1]
                if VV or (kk & 1) != wert: raise ValueError(f"L-R1 Bit {name}: nachgerechnet {nf(kk, VV)}, gebucht {wert}")
                setze_bit_p(name, wert, nr); return
            raise ValueError(f"L-R1 mit Art {art}")
        if rk in ('L-R2', 'L-R3', 'L-R6') and regel.split()[-1].startswith('['):
            tnr = int(regel.split('[')[-1].rstrip(']'))
            if tnr not in taf: raise ValueError(f"{rk} ohne Tabelle [{tnr}]")
            tname, namen = taf[tnr]; kk = FUNKTIONEN[tname][0]
            if rk == 'L-R3' and art == 'FORM':
                name, k, V = info
                if name != namen[kk] or len(eltern) != 1 or eltern[0] not in bindungen: raise ValueError('L-R3 Form ohne Bindung')
                h, t2 = bindungen[eltern[0]]
                if t2 != tnr or (k, tuple(V)) != (0, (h,)): raise ValueError('L-R3 Form passt nicht zur Bindung')
                setze_form_p(name, 0, [h], nr); return
            if tnr not in eltern: raise ValueError(f"{rk}: Tabelle [{tnr}] nicht in den Eltern")
            if rk == 'L-R6' and regel.split()[1].startswith('filter'):
                ein, U, u, F_neu = None, frozenset(), None, None
            else:
                ein = [lesart_p(n, eltern) for n in namen[:kk]]
                U = frozenset().union(*[e[1] for e in ein])
            if rk == 'L-R3':
                h, t2 = info
                if art != 'BINDUNG' or t2 != tnr or len(U) < 2: raise ValueError('L-R3 Bindung: Art/Instanz/Unbekannte passen nicht')
                if any(b[0] == h for b in bindungen.values()) or h in verdeckt or h in bekannt or h in formen or h in gebunden:
                    raise ValueError(f"Bindungsname {h} nicht frisch")
                if any(t == tnr for t in [b_t for b_t in [v[1] for v in bindungen.values()]]): raise ValueError('zweite Bindung fuer Instanz')
                if namen[kk] in bekannt or namen[kk] in formen: raise ValueError('L-R3 bei vorhandenem Ausgangsbeleg')
                bindungen[nr] = (h, tnr); gebunden.add(h); return
            if len(U) > 1: raise ValueError(f"{rk} mit {len(U)} freien Unbekannten")
            if ein is not None:
                u = next(iter(U)) if U else None
                F_neu = zweifall_p(tname, ein, u) if u is not None else (_direkt(tname, [e[0] for e in ein]), frozenset())
            if rk == 'L-R2':
                name = info[0]
                if name != namen[kk] or name in bekannt or name in formen: raise ValueError('L-R2 bei vorhandenem Ausgangsbeleg oder falschem Namen')
                if art == 'BIT':
                    if F_neu[1] or F_neu[0] != info[1]: raise ValueError(f"L-R2 Wert: nachgerechnet {F_neu}, gebucht {info}")
                    setze_bit_p(name, info[1], nr); return
                if art == 'FORM':
                    if (F_neu[0], F_neu[1]) != (info[1] & 1, frozenset(info[2])): raise ValueError(f"L-R2 Form: nachgerechnet {F_neu}, gebucht {info}")
                    setze_form_p(name, info[1], info[2], nr); return
                raise ValueError('L-R2 Art')
            # L-R6 abgleich/filter: Ausgangsbeleg Pflicht
            if regel.split()[1].startswith('filter'):
                j0 = int(regel.split()[1][6:])
                bel = [bekannt[n][0] if (n in bekannt and bekannt[n][1] in eltern) else None for n in namen]
                zeilen = [r for r in TABELLEN[tname] if all(b is None or b == r[j] for j, b in enumerate(bel))]
                werte = {r[j0] for r in zeilen}
                if len(werte) != 1 or namen[j0] not in formen: raise ValueError('L-R6 filter: Bit nicht erzwungen oder ohne Form')
                F_neu = (werte.pop(), frozenset()); aus = lesart_p(namen[j0], eltern)
            else:
                aus = lesart_p(namen[kk], eltern)
            diff = (aus[0] ^ F_neu[0], aus[1] ^ F_neu[1])
            if art == 'BEZIEHUNG':
                if not diff[1] or nf(*diff) != (tuple(info[0]), info[1]): raise ValueError(f"L-R6: nachgerechnet {nf(*diff)}, gebucht {info}")
                bez[nr] = (diff[1], diff[0] & 1); return
            if art == 'WIDERSPRUCH':
                if diff[1] or diff[0] != 1: raise ValueError('L-R6 Widerspruch nicht nachrechenbar')
                widersprueche.append(nr); return
            raise ValueError('L-R6 Art')
        if regel == 'L-R6 start':
            if art != 'BEZIEHUNG' or len(eltern) != 2: raise ValueError('L-R6 start Form')
            fnr, bnr = eltern
            fe_ = kern.buch[fnr]; be_ = kern.buch[bnr]
            if fe_[2] != 'FORM' or be_[2] != 'BIT' or fe_[3][0] != be_[3][0]: raise ValueError('L-R6 start: Eltern passen nicht')
            V = frozenset(fe_[3][2]); k = fe_[3][1] ^ be_[3][1]
            if nf(k, V) != (tuple(info[0]), info[1]): raise ValueError('L-R6 start: Normalform')
            bez[nr] = (V, k & 1); return
        if regel == 'L-R4 pivot':
            if art != 'BEZIEHUNG' or len(eltern) != 2: raise ValueError('L-R4 pivot Form')
            a, b = eltern
            if a not in bez: raise ValueError('L-R4 pivot: erste Beziehung fehlt')
            if b in bez: V2, k2 = bez[b]
            elif b in bekannt_nr: V2, k2 = frozenset([bekannt_nr[b][0]]), bekannt_nr[b][1]
            else: raise ValueError('L-R4 pivot: zweiter Elternteil weder Beziehung noch Unbekanntenwert')
            V = bez[a][0] ^ V2; k = bez[a][1] ^ k2
            if nf(k, V) != (tuple(info[0]), info[1]): raise ValueError(f"L-R4 pivot: nachgerechnet {nf(k, V)}, gebucht {info}")
            bez[nr] = (V, k & 1); return
        if regel == 'L-R4 wert':
            if art != 'BIT' or len(eltern) != 1 or eltern[0] not in bez: raise ValueError('L-R4 wert ohne Beziehung')
            V, k = bez[eltern[0]]; name, wert = info
            if V != frozenset([name]) or k != wert: raise ValueError(f"L-R4 wert {name}: Beziehung {nf(k, V)} erzwingt nicht {wert}")
            if name not in verdeckt and name not in gebunden: raise ValueError(f"L-R4 wert fuer Nicht-Unbekannte {name}")
            setze_bit_p(name, wert, nr); bekannt_nr[nr] = (name, wert); return
        if regel == 'L-R4 widerspruch':
            if art != 'WIDERSPRUCH': raise ValueError('L-R4 widerspruch Art')
            if len(eltern) == 1:
                if eltern[0] not in bez or bez[eltern[0]][0] or bez[eltern[0]][1] != 1: raise ValueError('L-R4 widerspruch: Beziehung nicht leer/1')
            elif len(eltern) == 2:
                a, b = eltern
                if a not in bez or b not in bekannt_nr: raise ValueError('L-R4 widerspruch: Eltern')
                V, k = bez[a]; name, w = bekannt_nr[b]
                if V != frozenset([name]) or k == w: raise ValueError('L-R4 widerspruch: kein Wertkonflikt')
            else: raise ValueError('L-R4 widerspruch Eltern')
            widersprueche.append(nr); return
        if regel == 'L-R5 einsetzen':
            if len(eltern) != 2: raise ValueError('L-R5 Eltern')
            fnr, wnr = eltern
            fe_ = kern.buch[fnr]
            if fe_[2] != 'FORM' or wnr not in bekannt_nr: raise ValueError('L-R5: Eltern passen nicht')
            name, k, V = fe_[3]; u, w = bekannt_nr[wnr]
            if u not in V: raise ValueError('L-R5: Unbekannte nicht in der Form')
            if name in formen and formen[name][2] != fnr: raise ValueError('L-R5: alte Form ist nicht die aktive')
            k2, V2 = k ^ w, frozenset(V) - {u}
            if art == 'BIT':
                if V2 or info != (name, k2 & 1): raise ValueError(f"L-R5 Bit: nachgerechnet {(name, k2 & 1)}, gebucht {info}")
                setze_bit_p(name, k2 & 1, nr); return
            if art == 'FORM':
                if (info[0], info[1] & 1, frozenset(info[2])) != (name, k2 & 1, V2): raise ValueError('L-R5 Form: nachgerechnet passt nicht')
                setze_form_p(name, k2, V2, nr); return
            raise ValueError('L-R5 Art')
        raise ValueError(f"unbekannte L-Regel {regel} / {art}")

    # MONOME replay: all original checked relationships and value evidence retained.
    product_nr = None
    world_proofs = {}
    previous_worlds = {(0,0), (0,1), (1,0), (1,1)}
    xy = tuple(sorted(verdeckt))
    zname = '*'.join(xy)

    def mon_eval(c, symbols, world):
        # Direct Boolean evaluation, independently of solver's ANF transform.
        x, y = world
        result = c
        for symbol in symbols:
            if symbol == xy[0]: result = (result + x) % 2
            elif symbol == xy[1]: result = (result + y) % 2
            elif symbol == zname: result = (result + (1 if x == y == 1 else 0)) % 2
            else: raise ValueError('foreign monomial')
        return result

    def mon_entry(nr, regel, eltern, art, info):
        nonlocal product_nr, previous_worlds
        if not vertrag.get('monome') or len(xy) != 2 or not vertrag.get('lf'):
            raise ValueError('MONOME not in contract')
        rk = regel.split()[0]
        if rk == 'M-R0':
            if regel != 'M-R0 produkt' or art != 'BINDUNG' or eltern or tuple(info) != (zname, *xy) or product_nr is not None:
                raise ValueError('invalid or duplicate product binding')
            product_nr = nr
            gebunden.add(zname)
            return
        if product_nr is None:
            raise ValueError('missing product binding')
        if rk == 'M-R1':
            if regel.startswith('M-R1 spaet '):
                name = regel[len('M-R1 spaet '):]
                if name in verdeckt or name == zname or name not in vertrag.get('spaet', {}):
                    raise ValueError('late conflict outside contract')
                old = wert_von(name, eltern, nr)
                if art != 'BEZIEHUNG' or tuple(info[0]) or info[1] != 1 or old == vertrag['spaet'][name]:
                    raise ValueError('late conflict not proved')
                bez[nr] = (frozenset(), 1)
                return
            tnr = int(regel.split('[')[-1].rstrip(']'))
            if tnr not in taf or tnr not in eltern or product_nr not in eltern:
                raise ValueError('table/product evidence absent')
            tname, names = taf[tnr]
            inputs = [lesart_p(n, eltern) for n in names[:-1]]
            if regel.startswith('M-R1 abgleich '):
                if art != 'BEZIEHUNG': raise ValueError('comparison kind')
                old = lesart_p(names[-1], eltern)
                V, c = tuple(info[0]), info[1]
                if len(V) != len(set(V)) or c not in (0,1): raise ValueError('noncanonical relation')
                for world in ((0,0),(0,1),(1,0),(1,1)):
                    expected = _direkt(tname, [mon_eval(*f,world) for f in inputs]) ^ mon_eval(*old,world)
                    if mon_eval(c,V,world) != expected: raise ValueError('table comparison mismatch')
                bez[nr] = (frozenset(V), c)
                return
            if regel != f'M-R1 form [{tnr}]' or art not in ('FORM','BIT') or info[0] != names[-1]:
                raise ValueError('table form rule/output')
            if info[0] in bekannt or info[0] in formen: raise ValueError('output already has evidence')
            c, V = info[1], (info[2] if art == 'FORM' else ())
            if c not in (0,1) or len(V) != len(set(V)): raise ValueError('noncanonical form')
            for world in ((0,0),(0,1),(1,0),(1,1)):
                expected = _direkt(tname,[mon_eval(*f,world) for f in inputs])
                if mon_eval(c,V,world) != expected: raise ValueError('table value mismatch')
            if art == 'FORM': setze_form_p(info[0],c,V,nr)
            else: setze_bit_p(info[0],c,nr)
            return
        if regel == 'M-R2 welten':
            if art != 'WELTEN' or product_nr not in eltern: raise ValueError('world kind or binding')
            # Require all original constraints, not only a convenient subset of pivots.
            required = set(bez) | set(bekannt_nr) | {product_nr}
            if set(eltern) != required or len(eltern) != len(required):
                raise ValueError('incomplete world basis')
            worlds = set()
            for world in ((0,0),(0,1),(1,0),(1,1)):
                if any(mon_eval(c,V,world) for V,c in bez.values()): continue
                if any(mon_eval(0,(n,),world) != c for n,c in bekannt_nr.values()): continue
                worlds.add(world)
            stated = tuple(tuple(w) for w in info)
            if len(stated) != len(set(stated)) or set(stated) != worlds: raise ValueError('world set mismatch')
            if not worlds <= previous_worlds: raise ValueError('world set grew')
            previous_worlds = worlds
            world_proofs[nr] = worlds
            return
        if regel == 'M-R2 wert':
            if art != 'BIT' or len(eltern) != 1 or eltern[0] not in world_proofs: raise ValueError('value without world proof')
            worlds = world_proofs[eltern[0]]
            if len(worlds) != 1: raise ValueError('not a unique world')
            n,c = info
            if n not in (*xy,zname) or c not in (0,1) or mon_eval(0,(n,),next(iter(worlds))) != c:
                raise ValueError('incorrect world value')
            setze_bit_p(n,c,nr)
            bekannt_nr[nr] = (n,c)
            return
        if regel == 'M-R2 widerspruch':
            if art != 'WIDERSPRUCH' or tuple(info) or len(eltern) != 1 or eltern[0] not in world_proofs or world_proofs[eltern[0]]:
                raise ValueError('unproved empty world set')
            widersprueche.append(nr)
            return
        raise ValueError('unknown MONOME rule')

    bekannt_nr = {}         # nr eines Unbekannten-Werts -> (name, wert)
    ziel_cache = set()

    try:
        for nr, eintrag in enumerate(kern.buch):
            # ---- Form ----
            try:
                regel, eltern, art, info = eintrag
                if not isinstance(regel, str) or not regel: raise ValueError
                eltern = tuple(eltern)
                if any((not isinstance(e, int)) or isinstance(e, bool) or e < 0 or e >= nr for e in eltern):
                    f(nr, f"Eltern ungueltig oder nicht frueher: {eltern}"); continue
                rk = regel.split()[0]
            except Exception:
                f(nr, 'Formfehler im Eintrag'); continue
            if rk == 'RT-R3':
                try:
                    from rt3_adapter import pruefen as rt3_pruefen
                    rt3_pruefen(nr,regel,eltern,art,info,bekannt,gl,taf,widersprueche)
                except (ValueError,TypeError,KeyError,IndexError) as e:f(nr,f'RT-R3: {e}')
                continue
            if rk in ('RT-R1','RT-R2'):
                try:
                    from relationstabellen import pruefen as rt_pruefen
                    rt_pruefen(nr,regel,eltern,art,info,bekannt,gl,taf,widersprueche)
                except (ValueError,TypeError,KeyError,IndexError) as e:
                    f(nr,f'RT-R1: {e}')
                continue
            if rk == 'Z-R3':
                try:
                    from zielrelation import pruefen as paar_pruefen
                    gl[nr]=paar_pruefen(nr,regel,eltern,art,info,vertrag,worte,bekannt,add,ziel_cache)
                except (ValueError,TypeError,KeyError,IndexError) as e:
                    f(nr,f'Z-R3: {e}')
                continue
            if rk == 'Z-R2':
                try:
                    from zielteil import pruefen as teilziel_pruefen
                    teilziel_pruefen(nr,regel,eltern,art,info,vertrag,worte,bekannt,add,ziel_cache)
                except (ValueError,TypeError,KeyError,IndexError) as e:
                    f(nr,f'Z-R2: {e}')
                continue
            if rk == 'Z-R1':
                try:
                    from zielbits import pruefen as ziel_pruefen
                    ziel_pruefen(nr,regel,eltern,art,info,vertrag,worte,bekannt,ziel_cache)
                except (ValueError,TypeError,KeyError,IndexError) as e:
                    f(nr,f'Z-R1: {e}')
                continue
            if rk == 'RB-R1':
                try:
                    from rueckweg import pruefe_zeile
                    gl[nr] = pruefe_zeile(regel, eltern, art, info, gl)
                except (ValueError, TypeError, KeyError, IndexError) as e:
                    f(nr, f'RB-R1: {e}')
                continue
            if rk.startswith('TW-'):
                try:
                    from teilwort32 import pruefen as teil_pruefen
                    teil_pruefen(nr, regel, eltern, art, info, NB, bekannt, formen,
                                 bez, formel_zustand, teil_zustand, widersprueche)
                except (ValueError, KeyError, TypeError, IndexError) as e: f(nr, f'{rk}: {e}')
                continue
            if rk == 'FR-4':
                try:
                    if regel != 'FR-4 addition': raise ValueError('unknown FR-4 rule')
                    from uebersetzer32 import fr4_pruefen
                    kid, key = fr4_pruefen(kern, vertrag, eltern, art, info, add, formel_zustand)
                    add[kid] = [nr, key, [], []]
                except (ValueError, KeyError, TypeError, IndexError) as e: f(nr, f'FR-4: {e}')
                continue
            if rk.startswith(('W-R', 'FR-')):                         # [FORMELNETZ] Zweig fuer W-R1..3 und FR-0..3, siehe formelnetz32.pruefzweig
                try: formel_entry(nr, regel, rk, eltern, art, info)
                except (ValueError, KeyError, TypeError, IndexError) as e: f(nr, f"{rk}: {e}")
                continue
            if rk.startswith('M-R'):
                try: mon_entry(nr, regel, eltern, art, info)
                except (ValueError, KeyError, TypeError, IndexError) as e: f(nr, f"{rk}: {e}")
                continue
            if vertrag.get('monome') and rk in ('L-R2', 'L-R3', 'L-R4'):
                f(nr, 'legacy value/helper rule forbidden in MONOME'); continue
            if vertrag.get('lf') and (rk.startswith('L-R') or (rk == 'START' and regel == 'START spaet')):
                try:
                    if vertrag.get('monome') and art in ('FORM', 'BEZIEHUNG'):
                        symbols = info[2] if art == 'FORM' else info[0]
                        c = info[1]
                        if c not in (0,1) or len(symbols) != len(set(symbols)) or not set(symbols) <= set((*xy,zname)):
                            raise ValueError('foreign/noncanonical monomial')
                        if zname in symbols and product_nr is None: raise ValueError('unbound product')
                    lf_eintrag(nr, regel, rk, eltern, art, info)
                except (ValueError, KeyError, TypeError, IndexError) as e:
                    f(nr, f"{rk}: {e}")
                continue
            if (rk, art) not in ZULAESSIG:
                f(nr, f"Regel/Art nicht zugelassen: {regel} / {art}"); continue
            try:
                # ---- START: nur, was der Vertrag festlegt ----
                if rk == 'START':
                    teile = regel.split()
                    if len(teile) != 2 or teile[1] not in HERKUNFT_START or eltern:
                        f(nr, f"START ohne zulaessige Herkunft oder mit Eltern: {regel} {eltern}"); continue
                    if art == 'WORT':
                        w, wwert, nb = info
                        if vertrag['worte'].get(w) != (wwert, nb):
                            f(nr, f"START-Wort {w} = {wwert:#x} ({nb} Bit) nicht im Aufgabenvertrag"); continue
                        worte[nr] = (w, wwert, nb)
                    elif art == 'BIT':
                        name, wert = info
                        if name in vertrag.get('verdeckt', ()):
                            f(nr, f"verdecktes Bit {name} als START eingespeist"); continue
                        if vertrag['starts'].get(name) != wert:
                            f(nr, f"START-Bit {name} = {wert} nicht im Aufgabenvertrag"); continue
                        if name in bekannt: f(nr, f"{name} doppelt gebucht"); continue
                        bekannt[name] = (wert, nr)
                    else:   # WIDERSPRUCH aus einem START gegen bekanntes Bit
                        name, alt, neu = info
                        if vertrag['starts'].get(name) != neu: f(nr, 'Widerspruch-START nicht im Vertrag'); continue
                        if name not in bekannt or bekannt[name][1] not in eltern or bekannt[name][0] != alt or alt == neu:
                            f(nr, f"Widerspruch {name} nicht belegt"); continue
                        widersprueche.append(nr)
                    continue
                # ---- Struktur: Gleichungen, Tabellen, Additionen ----
                if art == 'GL':
                    vs, par = tuple(info[0]), int(info[1])
                    if len(set(vs)) != len(vs) or par not in (0, 1):      # B32F2-02: nur kanonische GF(2)-Zeilen
                        f(nr, f"Gleichung nicht kanonisch (Variable mehrfach oder Paritaet ungueltig): {vs} = {par}"); continue
                    if rk == 'B-R4':
                        if (tuple(sorted(vs)), par) not in vertrag['gl']:
                            f(nr, f"Gleichung {vs} = {par} ohne Verdrahtungsvertrag"); continue
                    else:
                        kid = regel.split()[1]
                        if kid not in add or add[kid][0] not in eltern:
                            f(nr, f"Summengleichung ohne registrierte Addition {kid}"); continue
                        add[kid][2].append((vs, par))
                    gl[nr] = (vs, par); continue
                if art == 'TAF':
                    tname, namen = info[0], tuple(info[1])
                    if tname not in FUNKTIONEN or len(namen) != FUNKTIONEN[tname][0] + 1:
                        f(nr, f"Tabelle {tname} falsche Stelligkeit"); continue
                    if rk in ('B-R5', 'B-R6'):
                        kid = regel.split()[1]
                        if kid not in add or add[kid][0] not in eltern or tname != 'Maj':
                            f(nr, f"Uebertragstabelle ohne Addition oder nicht Maj: {kid} {tname}"); continue
                        add[kid][3].append(namen)
                    else:
                        if (tname, namen) not in vertrag['taf']:
                            f(nr, f"Tabelle {tname} {namen} ohne Verdrahtungsvertrag"); continue
                        if (rk, tname) in (('V-R1', 'Ch'),) or (rk.startswith('V-') and (rk, tname) not in (('V-R1', 'Gleich'), ('V-R2', 'Kleiner'), ('V-R3', 'Oder'))):
                            f(nr, f"Vergleichsregel mit falscher Tabelle {rk} {tname}"); continue
                    taf[nr] = (tname, namen); continue
                if art == 'ADD':
                    kid, schluessel = info[0], tuple(info[1])
                    if schluessel not in vertrag['add']:
                        f(nr, f"Addition {kid} {schluessel} ohne Aufgabenvertrag"); continue
                    if kid in add: f(nr, f"Kennung {kid} doppelt"); continue
                    add[kid] = [nr, schluessel, [], []]; continue
                # ---- Hergeleitete Bits ----
                if art == 'BIT':
                    name, wert = info
                    if name in bekannt: f(nr, f"{name} doppelt gebucht (erst B#{bekannt[name][1]})"); continue
                    if rk == 'B-R1' and name in vertrag.get('verdeckt', ()):
                        f(nr, f"verdecktes Bit {name} per B-R1 aus einem Wort eingespeist"); continue
                    if vertrag.get('lf') and name in formen: f(nr, f"{name} traegt eine aktive FORM; BIT nur ueber L-R4/L-R5/START spaet"); continue
                    soll = nachrechnen(regel, eltern, name, nr)
                    if soll != wert: f(nr, f"{rk} {name}: nachgerechnet {soll}, gebucht {wert}"); continue
                    bekannt[name] = (wert, nr); continue
                # ---- Widersprueche: muessen aus gepruefteten Eltern nachrechenbar sein ----
                if art == 'WIDERSPRUCH':
                    if rk == 'B-R4' and len(info) == 2:            # Gleichung mit allen Bits bekannt verletzt
                        qnr = int(regel.split('[')[1].rstrip(']'))
                        if qnr not in gl or qnr not in eltern: f(nr, 'Widerspruch ohne Gleichung'); continue
                        vs, par = gl[qnr]; s = par
                        for v in vs: s ^= wert_von(v, eltern, nr)
                        if s == 0: f(nr, f"Widerspruch behauptet, Gleichung [{qnr}] ist aber erfuellt"); continue
                    elif rk == 'B-R3' and len(info) == 2:          # Tabelle ohne vertraegliche Zeile
                        qnr = int(regel.split('[')[1].rstrip(']'))
                        if qnr not in taf or qnr not in eltern: f(nr, 'Widerspruch ohne Tabelle'); continue
                        tname, namen = taf[qnr]; k = FUNKTIONEN[tname][0]
                        feste = {n: wert_von(n, eltern, nr) for n in namen if n in bekannt and bekannt[n][1] in eltern}
                        frei = [n for n in namen if n not in feste]; moeglich = False
                        for m in range(1 << len(frei)):
                            bel = dict(feste); bel.update({n: (m >> j) & 1 for j, n in enumerate(frei)})
                            if _direkt(tname, [bel[n] for n in namen[:k]]) == bel[namen[k]]: moeglich = True; break
                        if moeglich: f(nr, f"Widerspruch behauptet, Tabelle [{qnr}] hat aber eine vertraegliche Zeile"); continue
                    elif len(info) == 3:                             # Bit doppelt mit anderem Wert: (name, alt, neu)
                        name, alt, neu = info
                        if name not in bekannt or bekannt[name][1] not in eltern or bekannt[name][0] != alt or alt == neu:
                            f(nr, f"Widerspruch {name}: alter Wert nicht belegt"); continue
                        soll = nachrechnen(regel, tuple(e for e in eltern if e != bekannt[name][1]), name, nr)
                        if soll != neu: f(nr, f"Widerspruch {name}: Regel ergibt {soll}, behauptet {neu}"); continue
                    else:
                        f(nr, f"Widerspruch in unbekannter Form {info}"); continue
                    widersprueche.append(nr); continue
                f(nr, f"unbehandelte Art {art}")
            except (ValueError, KeyError, TypeError, IndexError) as e:
                f(nr, f"{rk}: {e}")
    except _Abbruch:
        return fehler
    kern.formel_checked = dict(verb={k: v[:3] for k, v in formel_zustand.get('verb', {}).items()}, wortwerte={k: v[0] for k, v in formel_zustand.get('wortwert', {}).items()}, ausdr=dict(formel_zustand.get('ausdr', {})))   # [FORMELNETZ]
    if vertrag.get('lf'):
        for x in verdeckt:
            if x not in l0: fehler.append(f"verdecktes Bit {x} ohne Identitaetsform L-R0")
    if vertrag.get('monome'):
        if product_nr is None: fehler.append('missing product binding')
        covered = set()
        for wn in world_proofs:
            covered.update(kern.buch[wn][1])
        if not set(bez) <= covered: fehler.append('relationship without world check')
        # Expose only independently reconstructed evidence to release logic.
        kern.monome_checked = dict(worlds=sorted(previous_worlds),
                                  bits={n: bekannt[n][0] for n in xy if n in bekannt},
                                  contradictions=list(widersprueche))
    # ---- Struktur jeder Addition ----
    for kid, (nr, schl, summen, carries) in add.items():
        w, u = schl[1], schl[2]
        t = schl[3] if schl[0] == 'B-R6' else f"C{kid}"
        if len(summen) != NB or len(carries) != NB - 1:
            fehler.append(f"{kid}: {len(summen)} Summen, {len(carries)} Uebertraege statt {NB}/{NB-1}"); continue
        for i in range(NB):
            soll = kanonisch([f"{w}.{i}", f"{u}.{i}", f"{t}.{i}", f"c{kid}.{i}"])   # Aliase (u == t) kuerzen in GF(2)
            if not any(tuple(sorted(vs)) == soll and par == 0 for vs, par in summen):
                fehler.append(f"{kid}: Summengleichung {i} fehlt oder falsch"); break
            if i + 1 < NB and (f"{u}.{i}", f"{t}.{i}", f"c{kid}.{i}", f"c{kid}.{i+1}") not in carries:
                fehler.append(f"{kid}: Uebertragstabelle {i+1} fehlt oder falsch"); break
    return fehler


def widersprueche_belegt(kern, vertrag):
    """Fuer ein Urteil KEINE_LOESUNG: Liste der nachgerechneten Widerspruchseintraege, nur wenn der Pruefer 0 Fehler meldet."""
    if herleitung_pruefen(kern, vertrag):
        return []
    return [nr for nr, (regel, eltern, art, info) in enumerate(kern.buch) if art == 'WIDERSPRUCH']


# ======================================================================================
# F4 - LINEARFORMEN (Entwurf 6d2f/8c15/b9e4, Ghost e48b/a593/b71c, Christians GO "LINEARFORMEN_F4" 2026-10-31 22:02 JST)
# Additiv: KernLF erweitert Kern um Formen (k, V) ueber Unbekannte. Ohne Sperrliste verhaelt sich KernLF wie Kern.
#   L-R0 identitaet      verdecktes Bit x -> FORM (0,{x}); feste Bits gelten als konstante Formen (Lesart, kein Doppeleintrag)
#   L-R1 form/beziehung  XOR-Gleichung: eine Lesart fehlt -> FORM; keine fehlt -> BEZIEHUNG ueber Unbekannte (oder Widerspruch)
#   L-R2 form            Tabelle mit <= 1 freier Unbekannter, Ausgang ohne Beleg -> symbolische Zweifallauswertung -> FORM/BIT
#   L-R3 bindung         Tabelle mit >= 2 Unbekannten, Ausgang ohne Beleg -> frische Unbekannte h_t, einmal je Instanz
#   L-R4 pivot/wert      Beziehungen in reduzierter Stufenform ueber Unbekannte; eine Unbekannte allein -> Wert (BIT)
#   L-R5 einsetzen       bestimmte Unbekannte in alle Formen einsetzen; konstant gewordene Form -> BIT
#   L-R6 abgleich        Tabelle mit <= 1 freier Unbekannter und bestehendem Ausgangsbeleg (BIT/FORM/Bindung) -> BEZIEHUNG F_alt xor F_neu = 0
#   START spaet          zugelassene spaete Eingabe (Name UND Wert im Vertrag), nie ein verdecktes Bit
# ======================================================================================
def normalform_lf(k, V):
    return (k & 1, frozenset(V))


class KernLF(Kern):
    def __init__(self, nb, budget=None, name='K', verdeckt=()):
        super().__init__(nb, budget, name)
        self.lf = True
        self.verdeckt = set(verdeckt)
        self.form = {}                    # Bitname -> (k, frozenset V), nur nichtkonstante Formen
        self.form_nr = {}                 # Bitname -> Buchnummer der aktiven FORM
        self.unbekannte = set(self.verdeckt)
        self.bindung = {}                 # TAF-Index -> (h, nr)
        self.reaktiviert = defaultdict(set)   # TAF-Index -> Menge gebuchter Normalformen
        self.u_index = defaultdict(set)   # Unbekannte -> Bits, deren Form sie enthaelt
        self.pivot = {}                   # Unbekannte -> (frozenset V, k, nr)  reduzierte Stufenform: Pivotvariable kommt in keiner anderen Beziehung vor
        self.u_wert = {}                  # Unbekannte -> (wert, nr)
        self.spaet = {}                   # zugelassene spaete Eingaben Name -> Wert (Vertrag)
        self.budget.setdefault('BF', 50_000); self.budget.setdefault('BG', 2_000_000)
        self.zb.update(formen=0, bindungen=0, beziehungen=0, pivotschritte=0, abgleiche=0)
        for x in sorted(self.verdeckt):
            self.form[x] = (0, frozenset([x])); self.form_nr[x] = self.buche('L-R0 identitaet', [], 'FORM', (x, 0, (x,)))
            self.u_index[x].add(x); self.zb['formen'] += 1
            self.arbeit.append(x)

    # ---------- Lesart ----------
    def lesart(self, name):
        """(k, V) oder None. BIT hat Vorrang; FORM nur, solange kein BIT."""
        w = self.wert.get(name)
        if w is not None: return (w, frozenset())
        return self.form.get(name)

    def beleg_nr(self, name):
        return self.her[name] if name in self.wert else self.form_nr[name]

    def setze_form(self, name, k, V, regel, eltern):
        V = frozenset(V)
        if not V:
            return self.setze(name, k & 1, regel, eltern)
        if name in self.wert:
            raise Widerspruch(f"{name} hat BIT und soll FORM erhalten ({regel})")
        self.zb['formen'] += 1
        if self.zb['formen'] > self.budget['BF'] * 40:
            raise Budget(f"BF Formen bei {self.name}")
        alt = self.form.get(name)
        self.form[name] = (k & 1, V)
        self.form_nr[name] = self.buche(regel, eltern, 'FORM', (name, k & 1, tuple(sorted(V))))
        if alt:
            for u in alt[1] - V: self.u_index[u].discard(name)
        for u in V: self.u_index[u].add(name)
        self.arbeit.append(name)
        return True

    def start_spaet(self, name, wert):
        if name in self.verdeckt: raise ValueError('verdecktes Bit als spaete Eingabe')
        self.spaet[name] = wert
        f = self.form.pop(name, None)
        self.setze(name, wert, 'START spaet', [])
        if f is not None:
            for u in f[1]: self.u_index[u].discard(name)
            self.beziehung(f[1], f[0] ^ wert, 'L-R6 start', [self.form_nr[name], self.her[name]])
        return True

    # ---------- Beziehungen (L-R4) ----------
    def beziehung(self, V, k, regel, eltern):
        """Neue Beziehung XOR(V) = k ueber Unbekannte; gegen Pivots reduzieren; leere -> ok/Widerspruch; eine -> Wert; sonst Pivot."""
        V = frozenset(V); k &= 1
        self.zb['beziehungen'] += 1
        nr = self.buche(regel, eltern, 'BEZIEHUNG', (tuple(sorted(V)), k))
        # gegen bekannte Werte und Pivots reduzieren
        geaendert = True
        while geaendert:
            geaendert = False
            for u in sorted(V):
                if u in self.u_wert:
                    V = V - {u}; k ^= self.u_wert[u][0]
                    nr = self.buche('L-R4 pivot', [nr, self.u_wert[u][1]], 'BEZIEHUNG', (tuple(sorted(V)), k)); geaendert = True; break
                if u in self.pivot:
                    pV, pk, pnr = self.pivot[u]
                    V = V ^ pV; k ^= pk
                    self.zb['pivotschritte'] += 1
                    if self.zb['pivotschritte'] > self.budget['BG']: raise Budget(f"BG Pivotschritte bei {self.name}")
                    nr = self.buche('L-R4 pivot', [nr, pnr], 'BEZIEHUNG', (tuple(sorted(V)), k)); geaendert = True; break
        if not V:
            if k == 1:
                nr2 = self.buche('L-R4 widerspruch', [nr], 'WIDERSPRUCH', ((), 1)); self.zb['widersprueche'] += 1
                raise Widerspruch(f"Beziehung leer mit Konstante 1 [{nr2}]")
            return
        if len(V) == 1:
            self._unbekannte_bestimmt(next(iter(V)), k, nr)
            return
        p = min(V)
        # bestehende Pivots von p befreien (reduzierte Stufenform)
        for q, (qV, qk, qnr) in list(self.pivot.items()):
            if p in qV:
                nV = qV ^ V; nk = qk ^ k
                self.zb['pivotschritte'] += 1
                nnr = self.buche('L-R4 pivot', [qnr, nr], 'BEZIEHUNG', (tuple(sorted(nV)), nk))
                del self.pivot[q]
                if len(nV) == 1:
                    self._unbekannte_bestimmt(next(iter(nV)), nk, nnr)
                elif not nV:
                    if nk == 1:
                        nr2 = self.buche('L-R4 widerspruch', [nnr], 'WIDERSPRUCH', ((), 1)); raise Widerspruch(f"[{nr2}]")
                else:
                    self.pivot[min(nV)] = (nV, nk, nnr)
        self.pivot[p] = (V, k, nr)

    def _unbekannte_bestimmt(self, u, wert, nr_bez):
        if u in self.u_wert:
            if self.u_wert[u][0] != wert:
                nr2 = self.buche('L-R4 widerspruch', [nr_bez, self.u_wert[u][1]], 'WIDERSPRUCH', (u, self.u_wert[u][0], wert)); raise Widerspruch(f"{u} [{nr2}]")
            return
        if u in self.wert: return
        # Wert buchen (BIT der Unbekannten); verdeckte Bits erhalten damit ihren BIT-Beleg
        self.zb['bits'] += 1
        self.wert[u] = wert; self.her[u] = self.buche('L-R4 wert', [nr_bez], 'BIT', (u, wert)); self.u_wert[u] = (wert, self.her[u])
        self.form.pop(u, None)
        self.arbeit.append(u)
        # L-R5: in alle Formen einsetzen
        for name in list(self.u_index.get(u, ())):
            if name == u: continue
            f = self.form.get(name)
            if f is None or u not in f[1]: continue
            k, V = f[0] ^ wert, f[1] - {u}
            if not V:
                self.form.pop(name, None)
                self.setze(name, k, 'L-R5 einsetzen', [self.form_nr[name], self.her[u]])
            else:
                self.setze_form(name, k, V, 'L-R5 einsetzen', [self.form_nr[name], self.her[u]])
        self.u_index.pop(u, None)
        # Pivots, die u enthalten, reduzieren
        for q, (qV, qk, qnr) in list(self.pivot.items()):
            if u in qV:
                nV = qV - {u}; nk = qk ^ wert
                nnr = self.buche('L-R4 pivot', [qnr, self.her[u]], 'BEZIEHUNG', (tuple(sorted(nV)), nk))
                del self.pivot[q]
                if len(nV) == 1: self._unbekannte_bestimmt(next(iter(nV)), nk, nnr)
                elif not nV:
                    if nk == 1:
                        nr2 = self.buche('L-R4 widerspruch', [nnr], 'WIDERSPRUCH', ((), 1)); raise Widerspruch(f"[{nr2}]")
                else: self.pivot[min(nV)] = (nV, nk, nnr)

    # ---------- Propagation ----------
    def _gleichung(self, idx):
        vs, par, nr = self.xor[idx]
        les = {v: self.lesart(v) for v in vs}
        fehlend = [v for v in vs if les[v] is None]
        if len(fehlend) > 1: return
        if len(fehlend) == 1:
            v0 = fehlend[0]
            if all(not les[v][1] for v in vs if v != v0):
                s = par
                for v in vs:
                    if v != v0: s ^= les[v][0]
                self.setze(v0, s, f"B-R4 [{nr}]", [nr] + [self.her[v] for v in vs if v != v0]); return
            k = par; V = frozenset()
            for v in vs:
                if v != v0: k ^= les[v][0]; V = V ^ les[v][1]
            self.setze_form(v0, k, V, f"L-R1 form [{nr}]", [nr] + [self.beleg_nr(v) for v in vs if v != v0]); return
        k = par; V = frozenset()
        for v in vs: k ^= les[v][0]; V = V ^ les[v][1]
        eltern = [nr] + [self.beleg_nr(v) for v in vs]
        if not V:
            if k != 0:
                nr2 = self.buche(f"B-R4 [{nr}]", eltern, 'WIDERSPRUCH', (tuple(vs), par)); self.zb['widersprueche'] += 1
                raise Widerspruch(f"Gleichung [{nr}] verletzt [{nr2}]")
            return
        self.beziehung(V, k, f"L-R1 beziehung [{nr}]", eltern)

    def _zweifall(self, tname, ein, u):
        """Ausgangsform einer Tabelle mit Eingangsformen ein (Liste (k,V) mit V subset {u}) - beide Werte von u."""
        f = FUNKTIONEN[tname][1]
        w0 = f(*[k for k, V in ein])                                          # u = 0: Wert = k
        w1 = f(*[k ^ (1 if u in V else 0) for k, V in ein])                    # u = 1: Wert = k xor 1 wenn u in V
        if w0 == w1: return (w0, frozenset())
        return (w0, frozenset([u]))                                            # Wert = w0 xor u

    def _tabelle(self, idx):
        tname, namen, nr = self.taf[idx]
        k_ = FUNKTIONEN[tname][0]
        self.zb['tabellenpruefungen'] += 1
        if self.zb['tabellenpruefungen'] > self.budget['BT']: raise Budget(f"BT bei {self.name}")
        les = [self.lesart(n) for n in namen]
        ein, aus = les[:k_], les[k_]
        if any(e is None for e in ein):
            # F3-Filter ueber Konstanten; FORM-Bits zaehlen als unbekannt; erzwungener Wert an einem FORM-Bit -> Abgleich
            bel = [self.wert.get(n) for n in namen]
            zeilen = [r for r in TABELLEN[tname] if all(b is None or b == r[j] for j, b in enumerate(bel))]
            eltern = [nr] + [self.her[n] for n, b in zip(namen, bel) if b is not None]
            if not zeilen:
                nr2 = self.buche(f"B-R3 {tname} [{nr}]", eltern, 'WIDERSPRUCH', (tname, namen)); self.zb['widersprueche'] += 1
                raise Widerspruch(f"Tabelle {tname} [{nr}] ohne vertraegliche Zeile [{nr2}]")
            for j, b in enumerate(bel):
                if b is None:
                    werte = {r[j] for r in zeilen}
                    if len(werte) == 1:
                        w = werte.pop()
                        if namen[j] in self.form:
                            fk, fV = self.form[namen[j]]
                            self._abgleich(idx, nr, (fk ^ w, fV), eltern + [self.form_nr[namen[j]]], f'filter{j}')
                        else:
                            self.setze(namen[j], w, f"B-R3 {tname} [{nr}]", eltern)
            return
        U = frozenset().union(*[e[1] for e in ein])
        eltern = [nr] + [self.beleg_nr(n) for n in namen[:k_]]
        if len(U) >= 2:
            if aus is None and idx not in self.bindung:
                self.zb['bindungen'] += 1
                if self.zb['bindungen'] > self.budget['BF']: raise Budget(f"BF Bindungen bei {self.name}")
                h = f"h{idx}"
                if h in self.unbekannte or h in self.wert or h in self.form: raise Widerspruch(f"Bindungsname {h} kollidiert")
                bnr = self.buche(f"L-R3 bindung [{nr}]", eltern, 'BINDUNG', (h, nr))
                self.bindung[idx] = (h, bnr); self.unbekannte.add(h)
                self.setze_form(namen[k_], 0, [h], f"L-R3 form [{nr}]", [bnr])
            return
        u = next(iter(U)) if U else None
        F_neu = self._zweifall(tname, ein, u) if u is not None else (FUNKTIONEN[tname][1](*[e[0] for e in ein]), frozenset())
        if aus is None:
            if not F_neu[1]: self.setze(namen[k_], F_neu[0], f"L-R2 [{nr}]", eltern)
            else: self.setze_form(namen[k_], F_neu[0], F_neu[1], f"L-R2 form [{nr}]", eltern)
            return
        if aus == F_neu: return
        self._abgleich(idx, nr, (aus[0] ^ F_neu[0], aus[1] ^ F_neu[1]), eltern + [self.beleg_nr(namen[k_])], 'abgleich')

    def _abgleich(self, idx, nr, diff, eltern, art):
        """BEZIEHUNG Normalform(F_alt xor F_neu) = 0 je Instanz hoechstens einmal je Normalform."""
        k, V = diff[0] & 1, frozenset(diff[1])
        if not V:
            if k == 1:
                nr2 = self.buche(f"L-R6 {art} [{nr}]", eltern, 'WIDERSPRUCH', ((), 1)); self.zb['widersprueche'] += 1
                raise Widerspruch(f"Abgleich Tabelle [{nr}]: Konstante 1 [{nr2}]")
            return
        nf = (tuple(sorted(V)), k)
        if nf in self.reaktiviert[idx]: return
        self.reaktiviert[idx].add(nf); self.zb['abgleiche'] += 1
        self.beziehung(V, k, f"L-R6 {art} [{nr}]", eltern)

    def fixpunkt(self):
        offen = deque()
        while self.arbeit or offen:
            while self.arbeit:
                a = self.arbeit.popleft()
                if isinstance(a, tuple): offen.append(a)
                else:
                    for gid in self.x_index.get(a, ()): offen.append(('GL', gid))
                    for tid in self.t_index.get(a, ()): offen.append(('TAF', tid))
            while offen and not self.arbeit:
                art, idx = offen.popleft()
                if art == 'GL': self._gleichung(idx)
                else: self._tabelle(idx)
        return self

    def groesse(self):
        g = super().groesse(); g.update(formen=len(self.form), bindungen=len(self.bindung), pivots=len(self.pivot), unbekannte_bestimmt=len(self.u_wert))
        return g

# MONOME: isolated additive extension; original Kern/KernLF remain regression targets.
import sys as _sys
from monome_extension import install as _install_monome
KernMonome = _install_monome(_sys.modules[__name__])
