#!/usr/bin/env python3
"""KOPPLUNG (Ghost 2026-11-01 23:11, Christians GO): Wort-, Formel- und Teilwortschicht sprechen WAEHREND der Bitrechnung.

Kein neues Wissen, keine neue Regel: dieselben Bausteine (W-R2, FR-1/1b, FR-2, FR-3, FR-4, TW-1..3), nur frueher geweckt.
KernKopplung erbt KernTeilwort; alle Quellmodule bleiben unveraendert, der Pruefer bleibt bitkern32_teilwort.herleitung_pruefen.

Weckregeln (K-R1..K-R3), ausgeloest in setze() fuer jedes neu gesetzte Bit eines beobachteten Wortes:
  K-R1 ganzes Wort bekannt  -> W-R2 Wortwert; FR-1b fuer jede Zweiwortaddition, in der es Summand ist und Summe/anderer Summand
                               nicht voll bekannt sind; Verbindungen des Wortes werden geweckt (FR-2/FR-3).
  K-R2 neues Teilwissen     -> untere lueckenlose Bits: TW-1 sammeln, TW-2 sicht durch jede Verbindung, TW-3 zurueck (Teilwortweg).
  K-R3 neue Verbindung      -> sofort FR-4 (Addierinstanz im Bitkern); Bitformen fliessen dann durch deren Tabellen,
                               ohne weiteren Haken. Identische/umgestellte Dubletten werden nicht instanziiert.
  Start: FR-1 fuer jede Konstantenaddition (B-R5) vor dem Fixpunkt (Verdrahtungswissen, kein Bitwissen noetig).
Wiedereintritt: der Haken ist waehrend seiner eigenen Arbeit gesperrt (FR-3/TW-3 setzen selbst Bits).
kopplung=False: identischer Kern, aber kein Haken; Wortanschluss erst nach dem Bit-Fixpunkt (Reihenfolge aus Z-09).

Messung: Entscheidungsmarke = erste WELTEN-Zeile mit genau einer Welt (Zeit, Tabellenpruefungen, Wortarbeit); Fixpunktende ebenso.
Wortarbeit = Verbindungen + Aktivierungen + FR-4-Instanzen + Teilwortschritte + Wortwerte (getrennt ausgewiesen)."""
import time
from collections import defaultdict
import bitkern32 as bk
from teilwort32 import KernTeilwort
from z09_verdrahtung import volle


class KernKopplung(KernTeilwort):
    def __init__(self, nb, verdeckt, kopplung=True, budget=None, max_ereignisse=200000, teilbudget=100000):
        super().__init__(nb, verdeckt, budget, max_ereignisse, teilbudget)
        self.kopplung = kopplung
        self.wort_add = defaultdict(list)     # Wort -> Kennungen der B-R6-Additionen, in denen es Summand ist
        self.verb_kid = set()                 # Additionen, die schon eine Verbindung haben
        self.beobachtet = set()
        self._haken_aktiv = False
        self.kopp_events = []
        self.marken = {}
        self.t0 = time.monotonic()
        self.zb.update(fr4_instanzen=0, haken=0, haken_mit_wirkung=0)

    # ---------- Anschluss vor dem Fixpunkt ----------
    def anschluss_start(self):
        """FR-1 fuer alle B-R5; Index der B-R6-Summanden fuer K-R1. Nach der Verdrahtung, vor dem Fixpunkt aufrufen."""
        prot = []
        for kid, (nr, s) in list(self.additionen.items()):
            if s[0] == 'B-R5':
                if volle(self, s[1]) and volle(self, s[2]): continue
                vid = self.verb_aus_addition(kid); self.verb_kid.add(kid); prot.append((kid, vid))
            else:
                for w in (s[2], s[3]): self.wort_add[w].append(kid); self.beobachtet.add(w)
        self._uebersetze_neue()
        return prot

    def anschluss_nachtraeglich(self):
        """Reihenfolge aus Z-09 (kopplung=False): FR-1b fuer alle passenden Additionen nach dem Fixpunkt."""
        for w in list(self.beobachtet):
            if volle(self, w): self._k_r1(w)
        self._formelarbeit(); self._drain_partial(); self._uebersetze_neue()

    # ---------- Haken ----------
    def setze(self, name, wert, regel, eltern):
        r = super().setze(name, wert, regel, eltern)
        if r and self.kopplung and not self._haken_aktiv: self._haken(name)
        return r

    def _haken(self, name):
        w = name.rsplit('.', 1)[0]
        if w not in self.beobachtet and w not in self.teil_watched and w not in self.sym_verb: return
        self._haken_aktiv = True; self.zb['haken'] += 1; vor = len(self.buch)
        try:
            if volle(self, w): self._k_r1(w)                            # K-R1
            else: self._wake(w, self.her.get(name))                    # K-R2 (Teilwortweg, nur wenn ein VERB das Wort beobachtet)
            self._formelarbeit(); self._drain_partial(); self._uebersetze_neue()   # FR-2/FR-3, TW, K-R3
            if len(self.buch) > vor:
                self.zb['haken_mit_wirkung'] += 1
                self.kopp_events.append(dict(ausloeser=name, zeile=vor, neu=len(self.buch) - vor, bit_arbeit_offen=len(self.arbeit), t=round(time.monotonic() - self.t0, 4)))
        finally:
            self._haken_aktiv = False

    def _k_r1(self, w):
        for kid in self.wort_add.get(w, ()):
            if kid in self.verb_kid: continue
            nr, s = self.additionen[kid]; _, ws, p, q = s; andere = q if p == w else p
            if volle(self, andere) or volle(self, ws): continue
            if w not in self.wortwert: self.wortwert_aus_bits(w)
            self.verb_aus_addition(kid); self.verb_kid.add(kid)
        if w in self.sym_verb and w not in self.wortwert: self.wortwert_aus_bits(w)

    def _formelarbeit(self):
        """FR-2/FR-3 ueber die Formelarbeitsliste, ohne den Bit-Fixpunkt aufzurufen (der laeuft gerade)."""
        while self.arbeit_f:
            ausloeser, vid = self.arbeit_f.popleft()
            if self.zustand.get(vid) == 'ungueltig': continue
            ein = self._eingaenge(vid)
            if (vid, ein) in self.erledigt:
                self.zb['dubletten'] += 1; self._protokoll(ausloeser, vid, '-', ein, 'dublette: gleiche Eingangsstaende'); self.zustand[vid] = 'ruhend'; continue
            self.zb['aktivierungen'] += 1; self.zustand[vid] = 'bearbeitet'; fortschritt = []
            r = self.wert_aus_verb(vid, ausloeser)
            if r is not None: fortschritt.append(f'FR-3 -> Zeile {r}')
            links, rechts, k, nr = self.verb[vid]
            for s in (links, rechts):
                if s is None: continue
                for v2 in sorted(self.sym_verb.get(s, ()), key=lambda x: int(x[1:])):
                    if v2 == vid or self.zustand.get(v2) == 'ungueltig': continue
                    vor = len(self.verb); self.elimination(vid, v2, s, ausloeser)
                    if len(self.verb) > vor: fortschritt.append(f'FR-2 ueber {s} mit {v2} -> V{len(self.verb)}')
            self.erledigt.add((vid, ein))
            self._protokoll(ausloeser, vid, 'FR-2/FR-3', ein, ('neu: ' + '; '.join(fortschritt)) if fortschritt else 'kein_fortschritt')
            if not fortschritt: self.zb['kein_fortschritt'] += 1
            self.zustand[vid] = 'ruhend'

    def _uebersetze_neue(self):
        M = 1 << self.NB
        for vid in sorted(self.verb, key=lambda x: int(x[1:])):
            if vid in getattr(self, '_fr4_gesehen', set()): continue
            self._fr4_gesehen = getattr(self, '_fr4_gesehen', set()); self._fr4_gesehen.add(vid)
            links, rechts, c, nr = self.verb[vid]
            if rechts is None: continue
            if ('B-R5', links, rechts, c) in self.entfaltet or ('B-R5', rechts, links, (-c) % M) in self.entfaltet: continue
            self.uebersetzen(vid); self.zb['fr4_instanzen'] += 1

    # ---------- Messung ----------
    def buche(self, regel, eltern, art, info):
        nr = super().buche(regel, eltern, art, info)
        if art == 'WELTEN' and len(info) == 1 and 'entscheidung' not in self.marken: self.marken['entscheidung'] = self.marke(nr)
        return nr

    def marke(self, nr=None):
        return dict(zeile=nr if nr is not None else len(self.buch), t=round(time.monotonic() - self.t0, 4), tabellenpruefungen=self.zb['tabellenpruefungen'],
                    bits=len(self.wert), formen=len(self.form), welten=len(self.worlds),
                    wortarbeit=dict(verbindungen=len(self.verb), aktivierungen=self.zb['aktivierungen'], fr4_instanzen=self.zb['fr4_instanzen'],
                                    teilschritte=self.teilschritte, wortwerte=len(self.wortwert), haken=self.zb['haken'], haken_mit_wirkung=self.zb['haken_mit_wirkung']))
