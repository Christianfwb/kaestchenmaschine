"""Abgeleitete XOR-Zeilen: jede Umformung hat ihre ursprünglichen Eltern.

Keine neuen Eingaben, keine angenommenen Zwischenwerte. Der Prüfer verwendet
keine Inversionsmatrix: er addiert die nachgerechneten Eltern über GF(2).
"""
from functools import lru_cache
import time
import bitkern32 as bk
from kopplung32 import KernKopplung


@lru_cache(None)
def elimination(nb, rot, shr):
    rows = []
    for i in range(nb):
        mask = 0
        for r in rot: mask ^= 1 << ((i+r) % nb)
        for s in shr:
            if i+s < nb: mask ^= 1 << (i+s)
        rows.append([mask, 1 << i])
    rank = 0
    for col in range(nb):
        p = next((j for j in range(rank, nb) if rows[j][0] >> col & 1), None)
        if p is None: continue
        rows[rank], rows[p] = rows[p], rows[rank]
        for j in range(nb):
            if j != rank and rows[j][0] >> col & 1:
                rows[j][0] ^= rows[rank][0]
                rows[j][1] ^= rows[rank][1]
        rank += 1
    return tuple(p for m, p in rows if m and m & (m-1) == 0)


def pruefe_zeile(regel, parents, art, info, gl):
    if regel != 'RB-R1 XOR-Elimination' or art != 'GL':
        raise ValueError('Unbekannte Rückweg-Regel')
    if not parents or len(set(parents)) != len(parents):
        raise ValueError('Fehlende oder doppelte Eltern')
    vs, par = info
    if not isinstance(par, int) or isinstance(par, bool) or par not in (0, 1):
        raise ValueError('Ungültige Parität')
    if list(vs) != sorted(set(vs)) or not vs:
        raise ValueError('Nicht kanonische Gleichung')
    expected, parity = set(), 0
    for p in parents:
        if p not in gl: raise ValueError('Elternteil ist keine geprüfte XOR-Gleichung')
        names, bit = gl[p]
        expected.symmetric_difference_update(names)
        parity ^= bit
    if set(vs) != expected or par != parity:
        raise ValueError('XOR-Summe stimmt nicht mit Eltern überein')
    return tuple(vs), par


class RueckwegMixin:
    def __init__(self, *args, **kwargs):
        self.deadline = time.monotonic() + 90
        self.rueckweg_an = True
        super().__init__(*args, **kwargs)

    def buche(self, *args):
        if len(self.buch) % 2048 == 0:
            if time.monotonic() > self.deadline: raise bk.Budget('Zeitgrenze')
            if len(self.buch) >= 900000: raise bk.Budget('Buchgrenze')
        return super().buche(*args)

    def sigma(self, out, x, rot, shr, regel):
        start = len(self.buch)
        result = super().sigma(out, x, rot, shr, regel)
        if not self.rueckweg_an: return result
        sources = [n for n in range(start, len(self.buch)) if self.buch[n][2] == 'GL']
        if len(sources) != self.NB: raise ValueError('Sigma-Quellstruktur stimmt nicht')
        for mask in elimination(self.NB, tuple(rot), tuple(shr)):
            parents = [sources[i] for i in range(self.NB) if mask >> i & 1]
            names, parity = set(), 0
            for n in parents:
                vs, p = self.buch[n][3]
                names.symmetric_difference_update(vs); parity ^= p
            self.xor_gl(sorted(names), parity, 'RB-R1 XOR-Elimination', parents)
        return result


class KernRueckweg(RueckwegMixin, bk.Kern):
    pass


class KernZweiBit(RueckwegMixin, KernKopplung):
    pass
