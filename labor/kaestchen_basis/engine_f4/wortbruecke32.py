#!/usr/bin/env python3
"""WORTBRUECKE32 - begrenzte Bruecke alte Wortalgebra -> heutiger Kern (Ghost BK-11, WB-01..10; Christians GO 2026-11-01 17:28 JST).

Drei Regeln, alle ZUSAETZLICH zu den bestehenden Bit-/Carry-Belegen (WB-02: nichts wird weggelassen):
  W-R1 differenz   zwei registrierte B-R6-Additionen mit GEMEINSAMEM Summanden t:  w1 = p + t  und  w2 = t + q (Reihenfolge egal)
                   -> WREL (w1, w2, p, q, t, nb) mit Bedeutung  w1 - w2 == p - q  (mod 2^nb).  Eltern: die zwei ADD-Zeilen.
                   Strukturregel: gilt fuer JEDE Belegung, ohne Kandidatenaufzaehlung. Aliasfaelle (t doppelt in einer Addition,
                   gleiche Ergebnisnamen, p == q, B-R5-Konstantenadditionen) werden in dieser ersten Fassung ABGELEHNT (WB-04).
  W-R2 wortwert    alle nb Bits eines Wortes als BIT-Zeilen belegt -> WORTWERT (w, zahl); Eltern: die nb BIT-Zeilen (Bit i = 2^i).
  W-R3 wert        WREL + drei WORTWERT -> vierter WORTWERT, Zielposition und Vorzeichen explizit (WB-04):
                      w1 = w2 + p - q | w2 = w1 - p + q | p = w1 - w2 + q | q = w2 + p - w1   (mod 2^nb)
                   Eltern: [WREL, drei WORTWERT]. Steht fuer das Zielwort schon ein WORTWERT oder ein BIT mit anderem Wert:
                   WIDERSPRUCH-Zeile (nachgerechnet), kein Ueberschreiben.
  W-R2 bit         WORTWERT (w, zahl) -> nb BIT-Zeilen (w.i, (zahl>>i)&1) ueber Kern.setze -> bestehende Bitregeln nutzen sie
                   (B-R4/B-R5/B-R6/B-R3 ueber die normale Arbeitsliste). Kollision mit bekanntem Bit -> WIDERSPRUCH ueber setze.
Pruefer: wort_pruefzweig() wird aus der transparenten Kopie bitkern32_wort.herleitung_pruefen aufgerufen (DIFF_bitkern32_wort.patch,
  eine Einfuegung); er rechnet jede W-Zeile aus ihren Eltern nach und traegt W-R2-Bits in 'bekannt' ein, damit nachfolgende
  Bitregeln sie als Eltern nutzen koennen (WB-05). Kein Umnummerieren, kein Herausfiltern, kein START.
NICHT enthalten (WB-03): Substitution/Normalisierung ueber Summenketten mit Konstanten (B-R5), also KEINE Behauptung 'e4 = W3 + E'.
  Das ist als Nachtrag W-R4 nur beschrieben (BERICHT), nicht gebaut."""
import bitkern32 as bk


def _nb_mask(nb): return (1 << nb) - 1


class KernWort(bk.Kern):
    """Kern (Bits) + Wortzeilen. Keine Aenderung an Kern/KernLF/KernMonome; ADD-Zeilen werden nur gelesen."""
    def __init__(self, nb, budget=None, name='WORT'):
        super().__init__(nb, budget, name)
        self.wrel = {}        # nr -> (w1, w2, p, q, t)
        self.wortwert = {}    # wortname -> (zahl, nr)
        self.zb.update(wrel=0, wortwerte=0, wortbits=0)

    # ---- W-R1 ----
    def wrel_differenz(self, kid1, kid2):
        (nr1, s1), (nr2, s2) = self.additionen[kid1], self.additionen[kid2]
        if s1[0] != 'B-R6' or s2[0] != 'B-R6': raise ValueError('W-R1 nur fuer B-R6 (zwei Wortoperanden); B-R5 abgelehnt')
        w1, a1, b1 = s1[1:]; w2, a2, b2 = s2[1:]
        if a1 == b1 or a2 == b2: raise ValueError('W-R1 Alias: gleicher Summand doppelt in einer Addition')
        gemeinsam = {a1, b1} & {a2, b2}
        if len(gemeinsam) != 1: raise ValueError('W-R1: genau ein gemeinsamer Summand noetig')
        t = gemeinsam.pop(); p = a1 if b1 == t else b1; q = a2 if b2 == t else b2
        if w1 == w2 or p == q or t in (w1, w2) or p in (w1, w2) or q in (w1, w2): raise ValueError('W-R1 Alias: Namen nicht paarweise verschieden')
        info = (w1, w2, p, q, t, self.NB)
        nr = self.buche(f'W-R1 differenz [{kid1},{kid2}]', [nr1, nr2], 'WREL', info)
        self.wrel[nr] = info[:5]; self.zb['wrel'] += 1
        return nr

    # ---- W-R2 Wort aus Bits ----
    def wortwert_aus_bits(self, w):
        if w in self.wortwert: return self.wortwert[w][1]
        namen = [f'{w}.{i}' for i in range(self.NB)]
        if any(n not in self.wert for n in namen): raise ValueError(f'W-R2: nicht alle {self.NB} Bits von {w} belegt')
        zahl = sum(self.wert[n] << i for i, n in enumerate(namen))
        nr = self.buche('W-R2 wortwert', [self.her[n] for n in namen], 'WORTWERT', (w, zahl))
        self.wortwert[w] = (zahl, nr); self.zb['wortwerte'] += 1
        return nr

    # ---- W-R3 ----
    def wrel_wert(self, wrel_nr):
        w1, w2, p, q, t = self.wrel[wrel_nr]; M = 1 << self.NB
        bekannt = {n: self.wortwert[n] for n in (w1, w2, p, q) if n in self.wortwert}
        offen = [n for n in (w1, w2, p, q) if n not in bekannt]
        if len(offen) != 1: raise ValueError(f'W-R3: genau drei der vier Woerter muessen WORTWERT haben, offen: {offen}')
        ziel = offen[0]; v = {n: z for n, (z, _) in bekannt.items()}
        if ziel == w1: zahl = (v[w2] + v[p] - v[q]) % M
        elif ziel == w2: zahl = (v[w1] - v[p] + v[q]) % M
        elif ziel == p: zahl = (v[w1] - v[w2] + v[q]) % M
        else: zahl = (v[w2] + v[p] - v[w1]) % M
        eltern = [wrel_nr] + [bekannt[n][1] for n in (w1, w2, p, q) if n in bekannt]
        regel = f'W-R3 wert [{wrel_nr}] {ziel}'
        # Kollision mit schon bekannten Bits des Zielworts: nachgerechneter Widerspruch, kein Ueberschreiben (WB-04)
        for i in range(self.NB):
            n = f'{ziel}.{i}'
            if n in self.wert and self.wert[n] != (zahl >> i) & 1:
                self.zb['widersprueche'] += 1
                wn = self.buche(regel, eltern + [self.her[n]], 'WIDERSPRUCH', (n, self.wert[n], (zahl >> i) & 1))
                raise bk.Widerspruch(f'{n}: {self.wert[n]} bekannt, W-R3 ergibt {(zahl >> i) & 1} [{wn}]')
        nr = self.buche(regel, eltern, 'WORTWERT', (ziel, zahl))
        self.wortwert[ziel] = (zahl, nr); self.zb['wortwerte'] += 1
        return nr

    # ---- W-R2 Bits aus Wort ----
    def bits_aus_wort(self, wortwert_nr):
        w, zahl = self.buch[wortwert_nr][3]; neu = 0
        for i in range(self.NB):
            if self.setze(f'{w}.{i}', (zahl >> i) & 1, f'W-R2 bit {i}', [wortwert_nr]): neu += 1
        self.zb['wortbits'] += neu
        return neu


# ======================================================================================
# PRUEFERZWEIG - aufgerufen aus bitkern32_wort.herleitung_pruefen fuer jede Zeile mit Regel W-R*. Schreibt nur in bekannt
# (W-R2-Bits) und widersprueche; eigener Zustand in wort_zustand. Alles wird aus den Eltern nachgerechnet.
# ======================================================================================
def wort_pruefzweig(kern, vertrag, nr, regel, rk, eltern, art, info, bekannt, add, widersprueche, zustand):
    NB = vertrag['nb']; M = 1 << NB
    wrel = zustand.setdefault('wrel', {}); ww = zustand.setdefault('wortwert', {})
    add_nr = {v[0]: (kid, v[1]) for kid, v in add.items()}            # ADD-Zeilennummer -> (kid, schluessel)
    if rk == 'W-R1':
        if art != 'WREL' or len(eltern) != 2 or len(info) != 6: raise ValueError('WREL-Form')
        w1, w2, p, q, t, nb = info
        if nb != NB: raise ValueError(f'Modulus {nb} passt nicht zum Vertrag {NB}')
        if eltern[0] not in add_nr or eltern[1] not in add_nr: raise ValueError('Eltern sind keine registrierten ADD-Zeilen')
        (kid1, s1), (kid2, s2) = add_nr[eltern[0]], add_nr[eltern[1]]
        if regel != f'W-R1 differenz [{kid1},{kid2}]': raise ValueError('Regeltext passt nicht zu den Eltern')
        if s1[0] != 'B-R6' or s2[0] != 'B-R6': raise ValueError('nur B-R6-Eltern')
        if tuple(s1[1:]) not in ((w1, p, t), (w1, t, p)) or tuple(s2[1:]) not in ((w2, q, t), (w2, t, q)): raise ValueError('Operanden/Seite stimmen nicht zu den Eltern')
        if len({w1, w2, p, q, t}) != 5: raise ValueError('Alias: Namen nicht paarweise verschieden')
        wrel[nr] = (w1, w2, p, q, t); return
    if rk == 'W-R2' and art == 'WORTWERT':
        if regel != 'W-R2 wortwert' or len(eltern) != NB: raise ValueError('W-R2 wortwert Form')
        w, zahl = info
        if w in ww: raise ValueError(f'{w} hat schon WORTWERT [B#{ww[w][1]}]')
        soll = 0
        for i in range(NB):
            n = f'{w}.{i}'
            if n not in bekannt or bekannt[n][1] != eltern[i]: raise ValueError(f'Bit {n} nicht aus Elternteil {i} belegt')
            soll |= bekannt[n][0] << i
        if soll != zahl: raise ValueError(f'{w}: aus Bits {soll:#x}, gebucht {zahl:#x}')
        ww[w] = (zahl, nr); return
    if rk == 'W-R3':
        teile = regel.split()
        if len(teile) != 4 or teile[1] != 'wert': raise ValueError('W-R3 Regeltext')
        wrel_nr = int(teile[2].strip('[]')); ziel = teile[3]
        if wrel_nr not in wrel or eltern[0] != wrel_nr: raise ValueError('W-R3 ohne WREL-Elternteil')
        w1, w2, p, q, t = wrel[wrel_nr]
        if ziel not in (w1, w2, p, q): raise ValueError('Zielwort nicht in der WREL')
        andere = [n for n in (w1, w2, p, q) if n != ziel]
        v = {}
        for n in andere:
            if n not in ww or ww[n][1] not in eltern: raise ValueError(f'WORTWERT von {n} nicht aus den Eltern')
            v[n] = ww[n][0]
        if ziel == w1: soll = (v[w2] + v[p] - v[q]) % M
        elif ziel == w2: soll = (v[w1] - v[p] + v[q]) % M
        elif ziel == p: soll = (v[w1] - v[w2] + v[q]) % M
        else: soll = (v[w2] + v[p] - v[w1]) % M
        if art == 'WORTWERT':
            if info[0] != ziel or info[1] != soll: raise ValueError(f'W-R3 {ziel}: nachgerechnet {soll:#x}, gebucht {info}')
            if ziel in ww: raise ValueError(f'{ziel} hat schon WORTWERT')
            for i in range(NB):
                n = f'{ziel}.{i}'
                if n in bekannt and bekannt[n][0] != (soll >> i) & 1: raise ValueError(f'W-R3 {ziel}: Bit {n} widerspricht, aber kein WIDERSPRUCH gebucht')
            ww[ziel] = (soll, nr); return
        if art == 'WIDERSPRUCH':
            n, alt, neu = info
            if not n.startswith(ziel + '.'): raise ValueError('Widerspruchsbit gehoert nicht zum Zielwort')
            i = int(n.split('.')[-1])
            if n not in bekannt or bekannt[n][1] not in eltern or bekannt[n][0] != alt: raise ValueError('alter Bitwert nicht belegt')
            if (soll >> i) & 1 != neu or alt == neu: raise ValueError('Widerspruch nicht nachgerechnet')
            widersprueche.append(nr); return
        raise ValueError('W-R3 Art')
    if rk == 'W-R2' and art in ('BIT', 'WIDERSPRUCH'):
        teile = regel.split()
        if len(teile) != 3 or teile[1] != 'bit': raise ValueError('W-R2 bit Regeltext')
        i = int(teile[2])
        if art == 'BIT':
            n, wert = info
            if len(eltern) != 1: raise ValueError('W-R2 bit: genau ein Elternteil (WORTWERT)')
        else:
            n, alt, neu = info; wert = neu
            if len(eltern) != 2: raise ValueError('W-R2 Widerspruch: Eltern [WORTWERT, alter BIT]')
        wnr = eltern[0]; wz = kern.buch[wnr]
        if wz[2] != 'WORTWERT': raise ValueError('Elternteil ist kein WORTWERT')
        w, zahl = wz[3]
        if w not in ww or ww[w][1] != wnr: raise ValueError('WORTWERT nicht geprueft')
        if n != f'{w}.{i}' or not (0 <= i < NB): raise ValueError('falsche Bitnummer/Name')
        if (zahl >> i) & 1 != wert: raise ValueError(f'{n}: aus Wort {(zahl >> i) & 1}, gebucht {wert}')
        if art == 'BIT':
            if n in bekannt: raise ValueError(f'{n} doppelt gebucht (erst B#{bekannt[n][1]})')
            bekannt[n] = (wert, nr); return
        if n not in bekannt or bekannt[n][1] != eltern[1] or bekannt[n][0] != alt or alt == neu: raise ValueError('Widerspruch nicht belegt')
        widersprueche.append(nr); return
    raise ValueError(f'unbekannte Wortregel/Art {regel} / {art}')
