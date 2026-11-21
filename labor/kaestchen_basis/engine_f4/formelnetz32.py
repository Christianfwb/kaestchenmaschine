#!/usr/bin/env python3
"""FORMELNETZ32 - Stufe 1 (Entwurf 20261101T092730Z + Nachtrag N-1/N-2; Ghosts Abgrenzung 18:35/18:36 JST; Christians GO "dann go").

Woerter duerfen Formeln sein. Format (FR-0 Normalform): AUSDRUCK = Symbol + Zahl (mod 2^NB), Koeffizient des Symbols immer +1,
Zahl in [0, 2^NB); Symbol None = reine Zahl. VERBINDUNG = Gleichheit zweier Ausdruecke, links Symbol + 0, rechts Symbol + Zahl;
kein Minus (b - a = 4 nur als (b+0) == (a+4)). Links steht das lexikographisch GROESSERE Symbol (eindeutige Form -> Dublettensperre).

Regeln (alle mit Pruefer-Nachrechnung, Eltern = Buchzeilen):
  FR-0 ausdruck   bucht einen Ausdruck (Normalform geprueft).
  FR-1 konst      B-R5-Addition w = p + K           -> VERB (w+0) == (p+K)
  FR-1b bekannt   B-R6-Addition w = p + q, WORTWERT q = z -> VERB (w+0) == (p+z)   (Eltern: ADD, WORTWERT)
  FR-2 elim       zwei VERB mit gemeinsamem Symbol s (auf beliebiger Seite): s == u + k1 und s == v + k2 -> VERB (u+0) == (v + (k2-k1)).
                  Deckt die VERKETTUNG ab: a = b + c, b = x + d  (s = b)  -> a = x + (c + d). Eigener Test K2.
  FR-3 wert       VERB (u+0) == (v+k), WORTWERT eines Symbols -> WORTWERT des anderen (u = v + k bzw. v = u - k); Kollision ->
                  WIDERSPRUCH (nachgerechnet), kein Ueberschreiben. Danach W-R2 bits (Kern.setze) -> Bitregeln.
  W-R1/W-R2/W-R3  unveraendert aus wortbruecke32 (Pruefer-Zweig wird delegiert).
Speicher/Aktivierung (FN-03..07): Index Symbol -> VERB-ids; Versionsstand je Symbol = Buchzeile des letzten Wissens (WORTWERT oder
  VERB mit diesem Symbol); Zustand je VERB: ruhend | wartend | bereit | bearbeitet | ungueltig; Dublettensperre (vid, eingangsstaende);
  deterministische FIFO-Arbeitsliste; neue Zeilen erst nach kern-interner Pruefung (buche/setze) veroeffentlicht, dann Folge-Trigger;
  neue VERB prueft sofort vorhandenes Wissen (N-2: startet 'bereit', wenn ein Symbol schon Version hat); Budget -> Status OFFEN.
Ereignisprotokoll (FN-10): (ausloeser, vid, regel, eingangsstaende, ergebnis) in self.ereignisse; keine Vertrauensquelle.
Wiederaufnahme (FN-07, Ghost 18:36): aus_buch() prueft das Buch mit dem Pruefer und rekonstruiert Ausdruecke/Verbindungen/Werte/
  offene Arbeit daraus; gespeicherte Zustandskennzeichen werden NICHT geladen.
NICHT in Stufe 1: Uebersetzer Wort -> Bitformen (Stufe 2), Runde-4-Messung (Stufe 3), Skalierung/Inversion, Teilwort, MONOME-Anschluss.
"""
import json
from collections import deque
import bitkern32 as bk
from wortbruecke32 import KernWort, wort_pruefzweig

ZWEIG = 'haupt'


def _norm(symbol, k, nb): return (symbol, k % (1 << nb))


class Budget(Exception): pass


class KernFormel(KernWort):
    def __init__(self, nb, budget=None, name='FORMEL', max_ereignisse=100000):
        super().__init__(nb, budget, name)
        self.ausdr = {}          # id -> (symbol, konst)
        self.ausdr_nr = {}       # id -> buchzeile
        self.ausdr_index = {}    # (symbol, konst) -> id
        self.verb = {}           # vid -> (links_symbol, rechts_symbol, k, nr)   Bedeutung links == rechts + k
        self.verb_index = {}     # (links, rechts, k) -> vid
        self.sym_verb = {}       # symbol -> set(vid)
        self.version = {}        # symbol -> buchzeile des letzten Wissens
        self.zustand = {}        # vid -> 'ruhend'|'wartend'|'bereit'|'bearbeitet'|'ungueltig'
        self.erledigt = set()    # (vid, eingangsstaende)
        self.arbeit_f = deque()  # (ausloeser_nr, vid)
        self.ereignisse = []
        self.max_ereignisse = max_ereignisse
        self.status = 'LAUFEND'
        self.zb.update(ausdr=0, verb=0, aktivierungen=0, dubletten=0, kein_fortschritt=0)

    # ---------------- FR-0 ----------------
    def ausdruck(self, symbol, k):
        key = _norm(symbol, k, self.NB)
        if key in self.ausdr_index: return self.ausdr_index[key]
        aid = f'X{len(self.ausdr) + 1}'
        nr = self.buche('FR-0 ausdruck', [], 'AUSDR', (aid, key[0], key[1], self.NB))
        self.ausdr[aid] = key; self.ausdr_nr[aid] = nr; self.ausdr_index[key] = aid; self.zb['ausdr'] += 1
        return aid

    def _kanonisch(self, s1, k1, s2, k2):
        """s1 + k1 == s2 + k2  ->  (links, rechts, k) mit links == rechts + k, links lexikographisch groesser (None ist kleinstes)."""
        M = 1 << self.NB
        if (s1 or '') >= (s2 or ''): return s1, s2, (k2 - k1) % M
        return s2, s1, (k1 - k2) % M

    def _verb_buchen(self, links, rechts, k, regel, eltern, ausloeser=None):
        key = (links, rechts, k)
        if links == rechts: raise ValueError('VERB mit gleichem Symbol auf beiden Seiten (Tautologie/Widerspruch, nicht zugelassen)')
        if key in self.verb_index:
            self.zb['kein_fortschritt'] += 1; self._protokoll(ausloeser, self.verb_index[key], regel, (), 'kein_fortschritt: VERB vorhanden'); return self.verb_index[key]
        al = self.ausdruck(links, 0); ar = self.ausdruck(rechts, k)
        vid = f'V{len(self.verb) + 1}'
        nr = self.buche(regel, list(eltern) + [self.ausdr_nr[al], self.ausdr_nr[ar]], 'VERB', (vid, al, ar, self.NB, ZWEIG))
        self.verb[vid] = (links, rechts, k, nr); self.verb_index[key] = vid; self.zb['verb'] += 1
        for s in (links, rechts):
            if s is not None: self.sym_verb.setdefault(s, set()).add(vid); self.version[s] = max(self.version.get(s, -1), nr)
        # N-2: neue Verbindung prueft vorhandenes Wissen -> bereit, wenn ein Symbol schon Version/Wert hat, sonst ruhend
        self.zustand[vid] = 'bereit'; self.arbeit_f.append((nr, vid))
        # Folge-Trigger fuer alle Verbindungen, die ein Symbol teilen (FR-2 Kandidaten)
        for s in (links, rechts):
            if s is None: continue
            for v2 in self.sym_verb[s]:
                if v2 != vid: self.zustand[v2] = 'bereit'; self.arbeit_f.append((nr, v2))
        return vid

    # ---------------- FR-1 / FR-1b ----------------
    def verb_aus_addition(self, kid):
        nr, s = self.additionen[kid]
        if s[0] == 'B-R5':
            _, w, p, K = s
            links, rechts, k = self._kanonisch(w, 0, p, K)
            return self._verb_buchen(links, rechts, k, f'FR-1 konst [{kid}]', [nr])
        _, w, p, q = s
        if q in self.wortwert and p not in self.wortwert: z, wnr = self.wortwert[q]; andere = p
        elif p in self.wortwert and q not in self.wortwert: z, wnr = self.wortwert[p]; andere = q
        else: raise ValueError('FR-1b: genau ein Summand muss WORTWERT haben')
        links, rechts, k = self._kanonisch(w, 0, andere, z)
        return self._verb_buchen(links, rechts, k, f'FR-1b bekannt [{kid}]', [nr, wnr])

    # ---------------- FR-2 ----------------
    def _als(self, vid, s):
        """Verbindung vid nach s aufgeloest: s == other + k."""
        links, rechts, k, nr = self.verb[vid]; M = 1 << self.NB
        if s == links: return rechts, k
        if s == rechts: return links, (-k) % M
        raise ValueError('Symbol nicht in VERB')

    def elimination(self, v1, v2, s, ausloeser=None):
        u, k1 = self._als(v1, s); v, k2 = self._als(v2, s)     # s == u + k1, s == v + k2  ->  u + k1 == v + k2
        if u == v:
            M = 1 << self.NB; diff = (k1 - k2) % M
            if diff == 0:
                self.zb['kein_fortschritt'] += 1; self._protokoll(ausloeser, v1, 'FR-2', (), f'kein_fortschritt: {u} == {v} (Tautologie)'); return None
            # Ghost 19:19 JST: gleiches Symbol, verschiedene Konstanten -> u == u + diff mit diff != 0: WIDERSPRUCH, nachgerechnet
            self.zb['widersprueche'] += 1
            wn = self.buche(f'FR-2 widerspruch [{v1},{v2}] {s}', [self.verb[v1][3], self.verb[v2][3]], 'WIDERSPRUCH', (u, k1, k2, s))
            self.status = 'WIDERSPRUCH'; self._protokoll(ausloeser, v1, 'FR-2', (), f'WIDERSPRUCH: {u} == {u} + {diff} [Zeile {wn}]')
            raise bk.Widerspruch(f'{u} == {u} + {diff} aus {v1},{v2} ueber {s} [{wn}]')
        links, rechts, k = self._kanonisch(u, k1, v, k2)
        return self._verb_buchen(links, rechts, k, f'FR-2 elim [{v1},{v2}] {s}', [self.verb[v1][3], self.verb[v2][3]], ausloeser)

    # ---------------- FR-3 ----------------
    def wert_aus_verb(self, vid, ausloeser=None):
        links, rechts, k, nr = self.verb[vid]; M = 1 << self.NB
        if links in self.wortwert and rechts not in self.wortwert and rechts is not None:
            ziel, zahl, quelle = rechts, (self.wortwert[links][0] - k) % M, self.wortwert[links][1]
        elif rechts in self.wortwert and links not in self.wortwert:
            ziel, zahl, quelle = links, (self.wortwert[rechts][0] + k) % M, self.wortwert[rechts][1]
        elif rechts is None and links not in self.wortwert:
            ziel, zahl, quelle = links, k, None
        else: return None
        eltern = [nr] + ([quelle] if quelle is not None else [])
        regel = f'FR-3 wert [{vid}] {ziel}'
        for i in range(self.NB):
            n = f'{ziel}.{i}'
            if n in self.wert and self.wert[n] != (zahl >> i) & 1:
                self.zb['widersprueche'] += 1
                wn = self.buche(regel, eltern + [self.her[n]], 'WIDERSPRUCH', (n, self.wert[n], (zahl >> i) & 1))
                self.status = 'WIDERSPRUCH'
                raise bk.Widerspruch(f'{n}: {self.wert[n]} bekannt, FR-3 ergibt {(zahl >> i) & 1} [{wn}]')
        wnr = self.buche(regel, eltern, 'WORTWERT', (ziel, zahl))
        self.wortwert[ziel] = (zahl, wnr); self.zb['wortwerte'] += 1
        self._wissen(ziel, wnr)
        self.bits_aus_wort(wnr)
        return wnr

    # ---------------- Trigger ----------------
    def _wissen(self, symbol, nr):
        """Neues Wissen ueber ein Symbol: Version setzen, abhaengige Verbindungen wecken."""
        self.version[symbol] = max(self.version.get(symbol, -1), nr)
        for vid in self.sym_verb.get(symbol, ()):
            if self.zustand.get(vid) != 'ungueltig': self.zustand[vid] = 'bereit'; self.arbeit_f.append((nr, vid))

    def wortwert_aus_bits(self, w):
        neu = w not in self.wortwert
        nr = super().wortwert_aus_bits(w)
        if neu: self._wissen(w, nr)
        return nr

    def _eingaenge(self, vid):
        links, rechts, k, nr = self.verb[vid]
        return tuple((s, self.version.get(s, -1), self.wortwert.get(s, (None,))[0]) for s in (links, rechts) if s is not None)

    def _protokoll(self, ausloeser, vid, regel, eingaenge, ergebnis):
        self.ereignisse.append(dict(ausloeser=ausloeser, vid=vid, regel=regel, eingaenge=eingaenge, ergebnis=ergebnis))
        if len(self.ereignisse) > self.max_ereignisse: self.status = 'OFFEN'; raise Budget('Ereignisbudget')

    def abarbeiten(self):
        """Arbeitsliste bis Fixpunkt der implementierten Regeln (oder Budget). Deterministisch, FIFO, Dublettensperre."""
        if self.status == 'WIDERSPRUCH': return self.status          # belegter Widerspruch: keine weitere Arbeit
        try:
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
            self.fixpunkt()           # Bitregeln auf neuen W-R2-Bits; danach evtl. neue volle Woerter -> W-R2 -> Trigger
            for w in list(self._volle_woerter()):
                if w not in self.wortwert: self.wortwert_aus_bits(w)
            if self.arbeit_f: return self.abarbeiten()
            if self.status == 'LAUFEND': self.status = 'FIXPUNKT'
        except Budget:
            self.status = 'OFFEN'
        except bk.Widerspruch:
            self.status = 'WIDERSPRUCH'; raise
        return self.status

    def _volle_woerter(self):
        """Symbole aus Verbindungen, deren NB Bits alle bekannt sind."""
        for s in list(self.sym_verb):
            if all(f'{s}.{i}' in self.wert for i in range(self.NB)): yield s

    def zusammenfassung(self):
        return dict(status=self.status, ausdruecke=len(self.ausdr), verbindungen=len(self.verb), wortwerte=len(self.wortwert), bits=len(self.wert),
                    aktivierungen=self.zb['aktivierungen'], dubletten=self.zb['dubletten'], kein_fortschritt=self.zb['kein_fortschritt'],
                    offene_arbeit=len(self.arbeit_f), ereignisse=len(self.ereignisse), buchzeilen=len(self.buch),
                    zustaende={z: sum(1 for v in self.zustand.values() if v == z) for z in ('ruhend', 'wartend', 'bereit', 'bearbeitet', 'ungueltig')})


# ======================================================================================
# WIEDERAUFNAHME aus dem Buch (Ghost 18:36): Buch pruefen, Wissen und offene Arbeit rekonstruieren; keine Zustandskennzeichen laden.
# ======================================================================================
def aus_buch(nb, buch, vertrag, pruefer):
    """pruefer: herleitung_pruefen aus bitkern32_formel. Liefert (kern, fehler). Bei Fehlern kein Kern."""
    from types import SimpleNamespace
    ns = SimpleNamespace(NB=nb, buch=list(buch)); fehler = pruefer(ns, vertrag)
    if fehler: return None, fehler
    k = KernFormel(nb); k.buch = list(buch)
    for nr, (regel, eltern, art, info) in enumerate(buch):
        rk = regel.split()[0]
        if art == 'BIT': k.wert[info[0]] = info[1]; k.her[info[0]] = nr; k.arbeit.append(info[0])
        elif art == 'ADD': kid, schl = info; k.additionen[kid] = (nr, tuple(schl)); k.entfaltet[tuple(schl)] = kid
        elif art == 'GL': k.xor.append([list(info[0]), info[1], nr]); [k.x_index[v].append(len(k.xor) - 1) for v in info[0]]
        elif art == 'TAF': k.taf.append((info[0], tuple(info[1]), nr)); [k.t_index[n].append(len(k.taf) - 1) for n in info[1]]
        elif art == 'WORT': k.worte[info[0]] = nr
        elif art == 'AUSDR': aid, s, c, _ = info; k.ausdr[aid] = (s, c); k.ausdr_nr[aid] = nr; k.ausdr_index[(s, c)] = aid
        elif art == 'VERB':
            vid, al, ar, _, _ = info; (ls, lk), (rs, rk_) = k.ausdr[al], k.ausdr[ar]
            k.verb[vid] = (ls, rs, rk_, nr); k.verb_index[(ls, rs, rk_)] = vid
            for s in (ls, rs):
                if s is not None: k.sym_verb.setdefault(s, set()).add(vid); k.version[s] = max(k.version.get(s, -1), nr)
            k.zustand[vid] = 'ruhend'
        elif art == 'WORTWERT': k.wortwert[info[0]] = (info[1], nr); k.version[info[0]] = max(k.version.get(info[0], -1), nr)
        elif art == 'WREL': k.wrel[nr] = tuple(info[:5])
        elif art == 'WIDERSPRUCH': k.status = 'WIDERSPRUCH'; k.zb['widersprueche'] += 1   # Ghost 19:42: belegter Widerspruch bleibt aus dem Buch erhalten
    k.zb['bits'] = len(k.wert)
    if k.status == 'WIDERSPRUCH':
        # keine offene Arbeit: ein geprueftes Buch mit Widerspruch bleibt WIDERSPRUCH, nichts wird erneut 'laufend'
        for vid in k.verb: k.zustand[vid] = 'ruhend'
        return k, []
    # offene Arbeit: jede Verbindung einmal pruefen (Dublettensperre leer -> sie laeuft, bucht aber nur, was wirklich neu ist)
    for vid in sorted(k.verb, key=lambda x: int(x[1:])): k.zustand[vid] = 'bereit'; k.arbeit_f.append(('wiederaufnahme', vid))
    return k, []


# ======================================================================================
# PRUEFERZWEIG (aus bitkern32_formel.herleitung_pruefen): W-R* -> wortbruecke32, FR-* hier. Alles aus Eltern nachgerechnet.
# ======================================================================================
def pruefzweig(kern, vertrag, nr, regel, rk, eltern, art, info, bekannt, add, widersprueche, zustand):
    if rk.startswith('W-R'):
        return wort_pruefzweig(kern, vertrag, nr, regel, rk, eltern, art, info, bekannt, add, widersprueche, zustand)
    NB = vertrag['nb']; M = 1 << NB
    ausdr = zustand.setdefault('ausdr', {}); verb = zustand.setdefault('verb', {}); ww = zustand.setdefault('wortwert', {})
    add_nr = {v[0]: (kid, v[1]) for kid, v in add.items()}
    def kanon(s1, k1, s2, k2):
        if (s1 or '') >= (s2 or ''): return s1, s2, (k2 - k1) % M
        return s2, s1, (k1 - k2) % M
    if rk == 'FR-0':
        if regel != 'FR-0 ausdruck' or art != 'AUSDR' or eltern or len(info) != 4: raise ValueError('AUSDR-Form')
        aid, s, c, nb = info
        if nb != NB or not (0 <= c < M) or aid in ausdr or (s is not None and not isinstance(s, str)): raise ValueError('AUSDR Normalform/Modulus/Kennung')
        ausdr[aid] = (s, c); return
    if art == 'VERB':
        vid, al, ar, nb, zweig = info
        if nb != NB or zweig != ZWEIG or vid in verb or al not in ausdr or ar not in ausdr: raise ValueError('VERB-Form/Zweig/Kennung')
        (ls, lk), (rs, rk_) = ausdr[al], ausdr[ar]
        if lk != 0 or ls is None or ls == rs or (ls or '') < (rs or ''): raise ValueError('VERB nicht in Normalform (links Symbol+0, links groesser)')
        if len(eltern) < 2: raise ValueError('VERB: AUSDR-Eltern fehlen')
        # die letzten beiden Eltern sind die AUSDR-Zeilen
        if kern.buch[eltern[-2]][2] != 'AUSDR' or kern.buch[eltern[-2]][3][0] != al or kern.buch[eltern[-1]][2] != 'AUSDR' or kern.buch[eltern[-1]][3][0] != ar: raise ValueError('AUSDR-Eltern fehlen')
        belege = eltern[:-2]
        if rk == 'FR-1':
            kid = regel.split('[')[1].rstrip(']')
            if len(belege) != 1 or belege[0] not in add_nr or add_nr[belege[0]][0] != kid: raise ValueError('FR-1 ohne ADD-Elternteil')
            s = add_nr[belege[0]][1]
            if s[0] != 'B-R5': raise ValueError('FR-1 nur B-R5')
            _, w, p, K = s; soll = kanon(w, 0, p, K)
        elif rk == 'FR-1b':
            kid = regel.split('[')[1].rstrip(']')
            if len(belege) != 2 or belege[0] not in add_nr or add_nr[belege[0]][0] != kid: raise ValueError('FR-1b ohne ADD-Elternteil')
            s = add_nr[belege[0]][1]
            if s[0] != 'B-R6': raise ValueError('FR-1b nur B-R6')
            _, w, p, q = s; wz = kern.buch[belege[1]]
            if wz[2] != 'WORTWERT' or wz[3][0] not in (p, q) or wz[3][0] not in ww or ww[wz[3][0]][1] != belege[1]: raise ValueError('FR-1b: WORTWERT-Elternteil fehlt/ungeprueft')
            bek = wz[3][0]; z = wz[3][1]; andere = q if bek == p else p; soll = kanon(w, 0, andere, z)
        elif rk == 'FR-2':
            inner = regel.split('[')[1].split(']')[0]; v1, v2 = inner.split(','); s = regel.split(']')[1].strip()
            if len(belege) != 2 or v1 not in verb or v2 not in verb or belege[0] != verb[v1][3] or belege[1] != verb[v2][3]: raise ValueError('FR-2 Eltern-VERB fehlen')
            def als(v):
                l_, r_, k_ = verb[v][:3]
                if s == l_: return r_, k_
                if s == r_: return l_, (-k_) % M
                raise ValueError('Symbol nicht in VERB')
            (u, k1), (v, k2) = als(v1), als(v2)
            if u == v: raise ValueError('FR-2 Kreis/Tautologie')
            soll = kanon(u, k1, v, k2)
        else: raise ValueError(f'unbekannte VERB-Regel {rk}')
        if (ls, rs, rk_) != soll: raise ValueError(f'VERB {vid}: nachgerechnet {soll}, gebucht {(ls, rs, rk_)}')
        if (ls, rs, rk_) in [v[:3] for v in verb.values()]: raise ValueError('VERB doppelt (Dublette)')
        verb[vid] = (ls, rs, rk_, nr); return
    if rk == 'FR-2' and art == 'WIDERSPRUCH':
        inner = regel.split('[')[1].split(']')[0]; v1, v2 = inner.split(','); s = regel.split(']')[1].strip()
        if len(eltern) != 2 or v1 not in verb or v2 not in verb or eltern[0] != verb[v1][3] or eltern[1] != verb[v2][3]: raise ValueError('FR-2 Widerspruch: Eltern-VERB fehlen')
        def als(v):
            l_, r_, k_ = verb[v][:3]
            if s == l_: return r_, k_
            if s == r_: return l_, (-k_) % M
            raise ValueError('Symbol nicht in VERB')
        (u, k1), (v, k2) = als(v1), als(v2)
        if u != v or (k1 - k2) % M == 0 or tuple(info) != (u, k1, k2, s): raise ValueError('FR-2 Widerspruch nicht nachgerechnet (kein gleiches Symbol mit verschiedener Konstante)')
        widersprueche.append(nr); return
    if rk == 'FR-3':
        teile = regel.split(); vid = teile[2].strip('[]'); ziel = teile[3]
        if vid not in verb or eltern[0] != verb[vid][3]: raise ValueError('FR-3 ohne VERB-Elternteil')
        ls, rs, k, _ = verb[vid]
        if ziel == rs and ls in ww and ww[ls][1] in eltern: soll = (ww[ls][0] - k) % M
        elif ziel == ls and rs is not None and rs in ww and ww[rs][1] in eltern: soll = (ww[rs][0] + k) % M
        elif ziel == ls and rs is None and len(eltern) == 1: soll = k
        else: raise ValueError('FR-3: Quelle nicht aus den Eltern belegt')
        if art == 'WORTWERT':
            if info[0] != ziel or info[1] != soll or ziel in ww: raise ValueError(f'FR-3 {ziel}: nachgerechnet {soll:#x}, gebucht {info}')
            for i in range(NB):
                n = f'{ziel}.{i}'
                if n in bekannt and bekannt[n][0] != (soll >> i) & 1: raise ValueError('FR-3: Bit widerspricht, aber kein WIDERSPRUCH gebucht')
            ww[ziel] = (soll, nr); return
        if art == 'WIDERSPRUCH':
            n, alt, neu = info; i = int(n.split('.')[-1])
            if not n.startswith(ziel + '.') or n not in bekannt or bekannt[n][1] not in eltern or bekannt[n][0] != alt or (soll >> i) & 1 != neu or alt == neu: raise ValueError('FR-3 Widerspruch nicht nachgerechnet')
            widersprueche.append(nr); return
    raise ValueError(f'unbekannte Formelregel/Art {regel} / {art}')
