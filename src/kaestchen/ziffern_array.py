#!/usr/bin/env python3
"""KOMPAKTE PAARSPEICHERUNG (Option a, Fable 2026-10-22). Gleiche Regeln wie ziffern_komp.e4 (E3 + Grundpaare + Radius-1-Komposition,
Tupel-/Paar-/Domaenenschritte, Reihenfolge, Transposition, Statussemantik), andere Speicherung:
  - Die Menge aller Paare, die die Radius-1-Schliessung je anlegen kann (Grundpaare + alle Nachbarpaare (x,z) eines gemeinsamen y im
    Grundpaar-Graphen), wird VORAB gezaehlt (ohne Allokation der Masken) und gegen die Paargrenze geprueft; erst dann werden
    keys (array 'q', sortiert, Schluessel x*NV+y mit x<y) und masks (array 'H', 16 Bit, Start = universell) allokiert.
    Ein vorab angelegtes, nie geschnittenes Paar ist universell = "fehlendes Paar" der alten Fassung; leere Maske = WIDERSPRUCH.
  - Lookup ueber bisect auf dem sortierten Schluessel-Array; Nachbarschaft (Grundpaar-Graph) als CSR-Arrays ('i').
  - Zeilen-/Spalten-/Transpositionstabellen wie ziffern_komp (je Groessenpaar 2/4 vorberechnet).
Erklaerter Unterschied bei PAARGRENZE: alte Fassung bricht mitten in der Komposition ab (Teilstand), diese Fassung meldet
OPEN_PAARGRENZE VOR der Allokation (Domaenen = E3-Vorpropagation). Ohne Grenzueberschreitung sind die Ergebnisse identisch
(Status, Domaenen, Masken aller Paare der alten Fassung; alle zusaetzlichen Paare universell) – gemessen in array_kind.py.
Speicher: keys 8 B + masks 2 B je Paar + CSR + Tabellen (~10 MiB) + transiente numpy-Puffer beim Aufbau (werden mitgemessen)."""
import array, bisect, sys
import numpy as np
from ziffern import TABELLEN, GROESSEN
from ziffern_sha import e3, grundpaare, _vorbereiten, _kandidaten, _einwert
from ziffern_komp import tabellen, komponiere

class PaarSpeicher:
    def __init__(self, NV, keys, gr):
        self.NV = NV; self.keys = keys; self.gr = gr
        self.masks = array.array('H', bytes(2 * len(keys)))
        for i, k in enumerate(keys):
            x, y = divmod(int(k), NV); self.masks[i] = (1 << (gr[x] * gr[y])) - 1
    def index(self, x, y):
        k = x * self.NV + y; i = bisect.bisect_left(self.keys, k)
        return i if i < len(self.keys) and self.keys[i] == k else -1
    def get(self, x, y):
        """Maske in Orientierung (x,y) oder None (universell / nicht angelegt)."""
        if x < y:
            i = self.index(x, y); return None if i < 0 else self.masks[i]
        i = self.index(y, x)
        if i < 0: return None
        return tabellen(self.gr[y], self.gr[x])[2][self.masks[i]]
    def __len__(self): return len(self.keys)
    def als_dict(self, nur_eingeschraenkt=False):
        out = {}
        for i, k in enumerate(self.keys):
            x, y = divmod(int(k), self.NV); m = self.masks[i]
            if nur_eingeschraenkt and m == (1 << (self.gr[x] * self.gr[y])) - 1: continue
            out[(x, y)] = m
        return out
    def eingeschraenkt(self):
        n = 0
        for i, k in enumerate(self.keys):
            x, y = divmod(int(k), self.NV)
            if self.masks[i] != (1 << (self.gr[x] * self.gr[y])) - 1: n += 1
        return n
    def bytes_gesamt(self): return self.keys.itemsize * len(self.keys) + self.masks.itemsize * len(self.masks)
    def zeuge_ok(self, werte):
        """Streaming-Pruefung (kein dict, keine Kopie): liegt die Belegung werte[v] in ALLEN Paarmasken? Liefert (ok, erstes_verletztes_paar|None)."""
        NV = self.NV; gr = self.gr; keys = self.keys; masks = self.masks
        for i in range(len(keys)):
            x, y = divmod(keys[i], NV)
            if not (masks[i] >> (werte[x] * gr[y] + werte[y])) & 1: return False, (x, y)
        return True, None

def radius1_schluessel(grund, NV):
    """Alle Schluessel (x<y) der Radius-1-Schliessung aus den Grundpaaren: numpy, sortiert, eindeutig. Liefert (keys ndarray int64, csr_ptr, csr_idx)."""
    g = np.fromiter((x * NV + y for (x, y) in grund), dtype=np.int64, count=len(grund))
    xs = g // NV; ys = g % NV
    # Nachbarschaft (beide Richtungen) als CSR
    a = np.concatenate([xs, ys]); b = np.concatenate([ys, xs]); o = np.argsort(a, kind='stable'); a = a[o]; b = b[o]
    ptr = np.zeros(NV + 1, dtype=np.int64); np.add.at(ptr, a + 1, 1); ptr = np.cumsum(ptr)
    teile = [g]
    for y in np.flatnonzero(np.diff(ptr) >= 2):
        ns = np.sort(b[ptr[y]:ptr[y + 1]]); i, j = np.triu_indices(len(ns), 1)
        teile.append(ns[i] * NV + ns[j])
    keys = np.unique(np.concatenate(teile)); del teile
    return keys, ptr, b

def zaehle_radius1(grund, NV):
    keys, ptr, b = radius1_schluessel(grund, NV); return int(len(keys))

def e4(N, dom=None, max_runden=200, max_paare=20000, pruef=None, nachpruefung=False):
    st, dom, _, info0 = e3(N, dom, max_runden=max_runden, pruef=pruef)
    if st != 'FIXPUNKT': return st, dom, None, dict(runden=info0['runden'], tupelops=info0['tupelops'], paare=0, phase='E3-Vorpropagation')
    gr = N.groesse; NV = len(dom)
    grund, bez_mit, pst = grundpaare(N, dom, max_paare)
    if pst != 'OK': return pst, dom, None, dict(runden=0, tupelops=info0['tupelops'], paare=len(grund), phase='Grundpaare')
    keys_np, ptr, nbr = radius1_schluessel(grund, NV); gesamt = int(len(keys_np))
    if gesamt > max_paare:                                   # Grenze VOR Allokation der Masken
        return 'OPEN_PAARGRENZE', dom, None, dict(runden=0, tupelops=info0['tupelops'], paare=gesamt, grundpaare=len(grund), phase='Zaehlung vor Allokation', grenze=max_paare)
    keys = array.array('q', keys_np.tolist()); del keys_np
    PS = PaarSpeicher(NV, keys, gr); masks = PS.masks; index = PS.index
    bez = []
    for vs, typ, tab, dup in _vorbereiten(N):
        if sum(1 for v in dict.fromkeys(vs) if not _einwert(dom[v])) < 2: continue
        pp = []
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                a, b = vs[i], vs[j]
                if a == b: continue
                key = (a, b) if a < b else (b, a)
                if key in grund: pp.append((i, j, index(*key), a > b, gr[a], gr[b]))
        bez.append((vs, typ, tab, dup, pp))
    # Reihenfolge der Kompositionszentren y wie ziffern_komp (Einfuegereihenfolge des Grundpaar-Graphen), Nachbarn sortiert
    ordnung = []; seen = set()
    for (x, y) in grund:
        for v in (x, y):
            if v not in seen: seen.add(v); ordnung.append(v)
    yl = [y for y in ordnung if ptr[y + 1] - ptr[y] >= 2]; del seen, ordnung, grund
    def zeilen(x, y):
        if x < y:
            i = index(x, y); return None if i < 0 else tabellen(gr[x], gr[y])[0][masks[i]]
        i = index(y, x); return None if i < 0 else tabellen(gr[y], gr[x])[1][masks[i]]
    runden = 0; ops = info0['tupelops']
    while True:
        runden += 1; geaendert = False
        folge = bez if runden % 2 == 1 else bez[::-1]
        for vs, typ, tab, dup, pp in folge:
            n = len(vs); neu_dom = [0] * n; neu_paar = {}; d = [dom[v] for v in vs]
            for tup in _kandidaten(typ, tab, d):
                ops += 1
                ok = True
                for i in range(n):
                    if not (d[i] >> tup[i]) & 1: ok = False; break
                if not ok: continue
                if dup and any(tup[i] != tup[j] for i, j in dup): continue
                for i, j, ix, flip, gi, gj in pp:
                    idx = (tup[j] * gi + tup[i]) if flip else (tup[i] * gj + tup[j])
                    if not (masks[ix] >> idx) & 1: ok = False; break
                if not ok: continue
                for i in range(n): neu_dom[i] |= 1 << tup[i]
                for i, j, ix, flip, gi, gj in pp:
                    idx = (tup[j] * gi + tup[i]) if flip else (tup[i] * gj + tup[j])
                    neu_paar[ix] = neu_paar.get(ix, 0) | (1 << idx)
            for i in range(n):
                v = vs[i]; m = dom[v] & neu_dom[i]
                if m != dom[v]:
                    dom[v] = m; geaendert = True
                    if m == 0: return 'WIDERSPRUCH', dom, PS, dict(runden=runden, tupelops=ops, paare=len(PS), leer=N.name[v])
            for ix, m in neu_paar.items():
                neu = masks[ix] & m
                if neu != masks[ix]:
                    masks[ix] = neu; geaendert = True
                    if neu == 0: return 'WIDERSPRUCH', dom, PS, dict(runden=runden, tupelops=ops, paare=len(PS))
            if pruef is not None and ops % 100000 < len(tab): pruef(runden, ops)
        for y in yl:
            ns = sorted(nbr[ptr[y]:ptr[y + 1]].tolist()); dy = dom[y]; gy = gr[y]
            for ia in range(len(ns)):
                x = ns[ia]; zx = zeilen(x, y); gx = gr[x]; dx = dom[x]
                for ib in range(ia + 1, len(ns)):
                    z = ns[ib]; gz = gr[z]; dz = dom[z]
                    ops += gx; m = komponiere(zx, zeilen(y, z), dx, dy, dz, gx, gy, gz)
                    ix = index(x, z)
                    neu = masks[ix] & m
                    if neu != masks[ix]:
                        masks[ix] = neu; geaendert = True
                        if neu == 0: return 'WIDERSPRUCH', dom, PS, dict(runden=runden, tupelops=ops, paare=len(PS))
            if pruef is not None: pruef(runden, ops)
        for i in range(len(keys)):
            x, y = divmod(keys[i], NV); m = masks[i]; rows, cols, _ = tabellen(gr[x], gr[y]); dx = dom[x]; dy = dom[y]; mx = 0; my = 0
            for vx in range(gr[x]):
                if dx >> vx & 1 and rows[m][vx] & dy: mx |= 1 << vx
            for vy in range(gr[y]):
                if dy >> vy & 1 and cols[m][vy] & dx: my |= 1 << vy
            if mx != dx: dom[x] = mx; geaendert = True
            if my != dy: dom[y] = my; geaendert = True
            if mx == 0 or my == 0: return 'WIDERSPRUCH', dom, PS, dict(runden=runden, tupelops=ops, paare=len(PS))
        if not geaendert:
            info = dict(runden=runden, tupelops=ops, paare=len(PS), paare_eingeschraenkt=PS.eingeschraenkt(), bez_mit_paaren=len(bez), speicher_paare_bytes=PS.bytes_gesamt())
            if nachpruefung:
                st2, dom2, _, inf2 = e3(N, dom); info['nachpruefung_e3'] = dict(status=st2, geaendert=(dom2 != dom), runden=inf2['runden'])
            return 'FIXPUNKT', dom, PS, info
        if runden >= max_runden: return 'OFFEN', dom, PS, dict(runden=runden, tupelops=ops, paare=len(PS))
