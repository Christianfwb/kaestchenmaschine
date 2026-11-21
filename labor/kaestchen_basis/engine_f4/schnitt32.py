#!/usr/bin/env python3
"""RT-R3 ZWEITABELLEN-SCHNITT, Fassung 3 (SCHNITT3, Christians GO 2026-11-02): belegte Gleichungen mit teils bekannten Bits als Eingang.

Aenderung gegen Fassung 2 (Ghosts Beispiel: a^b^c=0 und belegt c=1 -> im Schnitt darf a^b=1 verwendet werden):
Fuer jede belegte GL-Zeile werden bekannte Variablen mit ihrem Wert eingesetzt (auch Bits AUSSERHALB des Paars); die Paritaet wird um die
Summe der eingesetzten Werte korrigiert. Die Gleichung ist einsetzbar, wenn ALLE verbleibenden freien Variablen im Paar liegen und es
mindestens zwei sind (eine einzelne wuerde schon B-R4 setzen). Eltern: die Gleichungszeile UND die Belegzeilen aller eingesetzten Bits.
Die urspruengliche Gleichung bleibt unveraendert im Buch; nichts wird ersetzt. Gezaehlt wird, wie viele Gleichungen ERST durch das Einsetzen
verwendbar werden (rt3_gl_erst_durch_einsetzen) gegenueber solchen, die auch ohne Einsetzen ganz im Paar liegen (rt3_gl_ganz_frei).

Aenderung gegen Fassung 1: Als Eingang gelten alle belegten GL-Zeilen mit 2..MAXGL Variablen, deren Variablen ALLE unter den freien Namen des
Paars liegen; ihre gesamte Paritaet wird je Belegung ausgewertet; jede benutzte Gleichung steht als Elternteil. Der Pruefer rechnet dieselbe
Bedingung mit eigener Routine nach. Gleichungen mit Variablen ausserhalb des Paars werden nicht eingesetzt (kein Teilabzug, keine Behauptung).

Regel RT-R3: Zwei Tabellen (Ch/Maj/Uebertrag/Vergleich) mit mindestens ZWEI gemeinsamen freien Bitnamen werden gemeinsam ausgewertet:
  Schnitt = alle Belegungen der freien Namen beider Tabellen, die BEIDE Tabellen erfuellen; vorher eingesetzt: bekannte Bits und
  belegte 2-Variablen-XOR-Gleichungen ueber freie Namen der beiden Tabellen (jeweils mit Beleg als Eltern).
  Aus dem Schnitt: (a) feste Bits        -> BIT  'RT-R3 bit [t1,t2]'
                   (b) feste Paar-XOR     -> GL   'RT-R3 xor [t1,t2]'  (2 Variablen)
                   (c) feste Dreierparitaet, die nicht aus (a)/(b) folgt -> GL 'RT-R3 xor [t1,t2]' (3 Variablen)
                   (d) leerer Schnitt     -> WIDERSPRUCH 'RT-R3 widerspruch [t1,t2]'
Warum mindestens zwei gemeinsame freie Namen: bei einem zerfaellt der Schnitt in ein Produkt; alles, was er ueber den geteilten Namen
sagt, sagt schon die Einzeltabelle (B-R3). Paare mit <2 werden nicht betrachtet (kein Ausschluss, keine Behauptung).
Begrenzung: nur Paare, deren freie Namen zusammen hoechstens MAXFREI Bits umfassen (Durchzaehlen 2^MAXFREI). Dubletten: ein Paar wird je
Eingangsstand (bekannte Bits + Gleichungen ueber seinen Namen) nur einmal ausgewertet. Reihenfolge deterministisch (Tabellenindex).
Nichts aus RT-R3 ersetzt B-R3/B-R4; es sind zusaetzliche Zeilen. Pruefer: bitkern32_schnitt.herleitung_pruefen rechnet jeden Schnitt
mit eigener Routine nach (schnitt_p) und nimmt nur Beziehungen an, die in ALLEN Schnittzeilen gelten."""
from collections import defaultdict
import bitkern32 as bk

MAXFREI = 8
MAXGL = 5          # groesste Zahl FREIER Variablen einer eingesetzten Gleichung; Gleichungen mit mehr freien Variablen werden gezaehlt (rt3_gl_zu_gross), nicht eingesetzt


class KernSchnitt(bk.Kern):
    def __init__(self, nb, budget=None, name='SCHNITT', maxfrei=MAXFREI, paarfilter=None):
        super().__init__(nb, budget, name)
        self.maxfrei = maxfrei
        self.paarfilter = paarfilter          # optional: Funktion (tabelle1, tabelle2) -> bool, welche Paare betrachtet werden
        self.erledigt = set()                 # (tid1, tid2, eingangsstand)
        self.zb.update(rt3_paare=0, rt3_ausgewertet=0, rt3_bits=0, rt3_xor2=0, rt3_xor3=0, rt3_widersprueche=0, rt3_gl_eingesetzt=0, rt3_gl_zu_gross=0, rt3_gl_ganz_frei=0, rt3_gl_erst_durch_einsetzen=0)
        self.rt3_protokoll = []

    def _gl_reduziert(self):
        """Jede belegte Gleichung nach Einsetzen der bekannten Bits: Liste (freie_vars (sortiert), paritaet_rest, gl_nr, beleg_nrs, erst_durch_einsetzen).
        Gleichungen mit < 2 oder > MAXGL freien Variablen werden nicht geliefert (zu klein: B-R4-Sache; zu gross: gezaehlt)."""
        out = []
        for vs, par, nr in self.xor:
            bek = [v for v in vs if v in self.wert]; frei = sorted(v for v in vs if v not in self.wert)
            if len(frei) < 2: continue
            if len(frei) > MAXGL: self.zb['rt3_gl_zu_gross'] += 1; continue
            rest = (par + sum(self.wert[v] for v in bek)) % 2
            out.append((tuple(frei), rest, nr, [self.her[v] for v in bek], bool(bek)))
        return out

    def _gl_vorhanden(self, vs):
        key = tuple(sorted(vs))
        cache = getattr(self, '_rt3_scoped_gl_index', None)
        if cache is None:
            return any(tuple(sorted(v)) == key for v, p, n in self.xor)
        # Only active inside one adapter invocation: xor is append-only there.
        # Same name-only test as before (parity is intentionally not changed).
        keys, seen = cache
        for index in range(seen, len(self.xor)):
            keys.add(tuple(sorted(self.xor[index][0])))
        cache[1] = len(self.xor)
        return key in keys

    def schnitt(self, tid1, tid2, glr):
        """Wertet ein Tabellenpaar aus und bucht. Liefert Anzahl neuer Zeilen."""
        tn1, nm1, nr1 = self.taf[tid1]; tn2, nm2, nr2 = self.taf[tid2]
        namen = list(dict.fromkeys(list(nm1) + list(nm2)))
        frei = [n for n in namen if n not in self.wert]
        gemeinsam = [n for n in frei if n in nm1 and n in nm2]
        if len(gemeinsam) < 2 or len(frei) > self.maxfrei: return 0
        feste = {n: self.wert[n] for n in namen if n in self.wert}
        gln = []; gesehen = set()
        for fv, rest, nr, belege, erst in glr:                      # reduzierte Gleichungen, deren freie Variablen ALLE im Paar liegen
            if not all(v in frei for v in fv) or (fv, rest) in gesehen: continue
            gesehen.add((fv, rest)); gln.append((fv, rest, nr, belege, erst))
        stand = (tuple(sorted(feste.items())), tuple((vs, p) for vs, p, _, _, _ in gln))
        if (tid1, tid2, stand) in self.erledigt: return 0
        self.erledigt.add((tid1, tid2, stand)); self.zb['rt3_ausgewertet'] += 1; self.zb['rt3_gl_eingesetzt'] += len(gln)
        self.zb['rt3_gl_erst_durch_einsetzen'] += sum(1 for g in gln if g[4]); self.zb['rt3_gl_ganz_frei'] += sum(1 for g in gln if not g[4])
        eltern = [nr1, nr2] + [self.her[n] for n in feste] + [n for _, _, n, _, _ in gln] + sorted({b for _, _, _, bel, _ in gln for b in bel})
        eltern=list(dict.fromkeys(eltern))
        k1, k2 = bk.FUNKTIONEN[tn1][0], bk.FUNKTIONEN[tn2][0]
        zeilen = []
        for m in range(1 << len(frei)):
            bel = dict(feste); bel.update({n: (m >> j) & 1 for j, n in enumerate(frei)})
            if bk._direkt(tn1, [bel[n] for n in nm1[:k1]]) != bel[nm1[k1]]: continue
            if bk._direkt(tn2, [bel[n] for n in nm2[:k2]]) != bel[nm2[k2]]: continue
            if any(sum(bel[v] for v in vs) % 2 != p for vs, p, _, _, _ in gln): continue    # Restparitaet jeder reduzierten Gleichung
            zeilen.append({n: bel[n] for n in frei})
        regel = f'[{nr1},{nr2}]'
        if not zeilen:
            self.zb['rt3_widersprueche'] += 1; self.zb['widersprueche'] += 1
            wn = self.buche(f'RT-R3 widerspruch {regel}', eltern, 'WIDERSPRUCH', (tid1, tid2))
            raise bk.Widerspruch(f'RT-R3: Schnitt der Tabellen {nr1},{nr2} leer [{wn}]')
        vor = len(self.buch); neu_fest = {}
        for n in frei:                                            # (a) feste Bits
            w = {z[n] for z in zeilen}
            if len(w) == 1: neu_fest[n] = w.pop()
        for n, w in neu_fest.items():
            if n not in self.wert: self.setze(n, w, f'RT-R3 bit {regel}', eltern); self.zb['rt3_bits'] += 1
        rest = [n for n in frei if n not in neu_fest]
        paare = set()
        for i in range(len(rest)):                                # (b) Paar-XOR
            for j in range(i + 1, len(rest)):
                a, b = rest[i], rest[j]; ps = {z[a] ^ z[b] for z in zeilen}
                if len(ps) == 1:
                    paare.add(frozenset((a, b)))
                    if not self._gl_vorhanden((a, b)): self.xor_gl([a, b], ps.pop(), f'RT-R3 xor {regel}', eltern); self.zb['rt3_xor2'] += 1
        for i in range(len(rest)):                                # (c) Dreierparitaet, nicht aus Paaren ableitbar
            for j in range(i + 1, len(rest)):
                for l in range(j + 1, len(rest)):
                    a, b, c = rest[i], rest[j], rest[l]
                    if any(frozenset(x) in paare for x in ((a, b), (a, c), (b, c))): continue
                    ps = {z[a] ^ z[b] ^ z[c] for z in zeilen}
                    if len(ps) == 1 and not self._gl_vorhanden((a, b, c)): self.xor_gl([a, b, c], ps.pop(), f'RT-R3 xor {regel}', eltern); self.zb['rt3_xor3'] += 1
        n_neu = len(self.buch) - vor
        if n_neu: self.rt3_protokoll.append(dict(tabellen=(nr1, nr2), frei=len(frei), gemeinsam=len(gemeinsam), zeilen=len(zeilen), neu=n_neu))
        return n_neu

    def schnittrunde(self):
        """Alle zulaessigen Paare einmal (deterministisch); liefert Anzahl neuer Zeilen."""
        glr = self._gl_reduziert(); neu = 0
        for v, tids in sorted(self.t_index.items()):
            for i in range(len(tids)):
                for j in range(i + 1, len(tids)):
                    t1, t2 = sorted((tids[i], tids[j]))
                    if self.paarfilter and not self.paarfilter(self.taf[t1], self.taf[t2]): continue
                    nm1, nm2 = self.taf[t1][1], self.taf[t2][1]
                    if v != min(n for n in nm1 if n in nm2): continue      # jedes Paar genau einmal (ueber seinen kleinsten gemeinsamen Namen)
                    self.zb['rt3_paare'] += 1
                    neu += self.schnitt(t1, t2, glr)
        return neu

    def fixpunkt_mit_schnitt(self, max_runden=50):
        """Bit-Fixpunkt, dann RT-R3-Runde, bis nichts Neues (oder Rundengrenze -> OFFEN)."""
        self.fixpunkt()
        for r in range(max_runden):
            if self.schnittrunde() == 0: return 'FIXPUNKT'
            self.fixpunkt()
        return 'OFFEN'
