"""SCHLANKE MASKEN (GO Christian 2026-10-25 12:50). Dieselbe Bitdarstellung wie bitmenge.py (Position b = Summe_j wert(v_j) << j), dieselben Nachrichten (2^s-Bit-Zahl, Position c = Summe_i wert(s_i) << i, in frozenset({(zahl,)})).
NEU: statt 2^s Masken je (Gruppe, Schnittmenge S) haelt jede Gruppe nur VARIABLENMASKEN, unabhaengig von S und fuer alle Kanten gemeinsam:
  EINS[j]  = Bitmenge aller Positionen b mit Bit j = 1  (v_j = 1),   NULL[j] = Bitmenge aller b mit Bit j = 0.      -> 2k Masken zu je 2^k Bits je Gruppe.
Die Schnittmengenmaske fuer eine Belegung c von S = (s_0..s_{m-1}) wird bei Bedarf berechnet: maske_c = UND ueber i von (EINS[idx_i] wenn c_i = 1 sonst NULL[idx_i]); m - 1 UND-Operationen, kurzlebig, nicht gespeichert.
Projektion: Bit c gesetzt <=> rel & maske_c != 0 (fuer alle 2^m c).  Semijoin mit M: rel &= ODER ueber c in M von maske_c.  S = (): maske = ALLE (alle 2^k Bits).
Mathematisch identisch zu bitmenge.BitGruppe (maske_c ist dort vorab gespeichert) – wird im Selbsttest und im Vergleichslauf geprueft. Mehr Rechenschritte je Aufruf, weniger gespeicherte Masken.
Vertauschte Variablenreihenfolge in S: ueber idx_i = self.vars.index(s_i) abgebildet; leere Relation: rel = 0 -> alle Projektionen 0; leere Schnittstelle: ein Bit."""
import sys, os, json, itertools, random, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gruppen, bitmenge
OPS = dict(und=0, oder=0, popcount=0, maske_c_berechnet=0, varmasken_gebaut=0, varmasken_bits=0, varmasken_bau_s=0.0, zwischen_bytes_max=0)
class SchlankBitGruppe(bitmenge.BitGruppe):
    def __init__(self, name, vars_): super().__init__(name, vars_); self.EINS = None; self.NULL = None; self.ALLE = (1 << (1 << len(vars_))) - 1
    def varmasken(self):
        if self.EINS is None:
            t = time.perf_counter(); k = len(self.vars); self.EINS = []; self.NULL = []
            for j in range(k):
                e = 0
                for b in range(1 << k):
                    if (b >> j) & 1: e |= 1 << b
                self.EINS.append(e); self.NULL.append(self.ALLE & ~e)
            OPS['varmasken_gebaut'] += 2 * k; OPS['varmasken_bits'] += 2 * k * (1 << k); OPS['varmasken_bau_s'] += time.perf_counter() - t
        return self.EINS, self.NULL
    def masken(self, S): raise RuntimeError('SchlankBitGruppe speichert keine Schnittmengenmasken')
    def _maske_c(self, idx, c):
        E, N0 = self.varmasken(); m = self.ALLE if not idx else (E[idx[0]] if c & 1 else N0[idx[0]])
        for i in range(1, len(idx)): m &= (E[idx[i]] if (c >> i) & 1 else N0[idx[i]]); OPS['und'] += 1
        OPS['maske_c_berechnet'] += 1; OPS['zwischen_bytes_max'] = max(OPS['zwischen_bytes_max'], sys.getsizeof(m)); return m
    def proj(self, S):
        idx = [self.vars.index(v) for v in S]; P = 0
        for c in range(1 << len(idx)):
            OPS['und'] += 1
            if self.rel & self._maske_c(idx, c): P |= 1 << c
        return (P,)
    def semijoin(self, S, M):
        P = next(iter(M)) if isinstance(M, (set, frozenset)) else M
        P = P[0] if isinstance(P, tuple) else P
        idx = [self.vars.index(v) for v in S]; erlaubt = 0; c = 0; PP = P
        while PP:
            if PP & 1: erlaubt |= self._maske_c(idx, c); OPS['oder'] += 1; OPS['zwischen_bytes_max'] = max(OPS['zwischen_bytes_max'], sys.getsizeof(erlaubt))
            PP >>= 1; c += 1
        vorher = bitmenge.popcount(self.rel); self.rel &= erlaubt; OPS['und'] += 1; return vorher - bitmenge.popcount(self.rel)

def selbsttest(seed=20261025):
    """Schlank gegen bisherige Bitmengen (bitmenge.BitGruppe) UND gegen Tupelmengen; gleiche Faelle wie bitmenge.selbsttest (k<=3 erschoepfend, k=4,5 Stichproben, leer/voll/Einzelzeile/S=()/vertauschte Reihenfolge)."""
    rnd = random.Random(seed); faelle = 0; fehler = []
    def pruefe(vars_, rows, S, M_rows):
        nonlocal faelle
        T = gruppen.Gruppe('T', vars_); T.zeilen = set(rows)
        A = bitmenge.BitGruppe('A', vars_); A.rel = sum(1 << A._bit(r) for r in rows); B = SchlankBitGruppe('B', vars_); B.rel = A.rel
        pa, pb = A.proj(S), B.proj(S); m = len(S); pt = T.proj(S); pb_rows = {tuple(((c >> i) & 1) for i in range(m)) for c in range(1 << m) if (pb[0] >> c) & 1}
        if pa != pb or pt != pb_rows: fehler.append(dict(art='proj', vars=vars_, rows=sorted(rows), S=S, bisher=pa, schlank=pb, tupel=sorted(pt)))
        Mb = sum(1 << sum(r[i] << i for i in range(m)) for r in M_rows); M = frozenset({(Mb,)})
        sa, sb, st = A.semijoin(S, M), B.semijoin(S, M), T.semijoin(S, set(M_rows))
        if sa != sb or A.rel != B.rel or st != sb or T.zeilen != B.als_tupel(): fehler.append(dict(art='semijoin', vars=vars_, rows=sorted(rows), S=S, M=sorted(M_rows), bisher=A.rel, schlank=B.rel, tupel=sorted(T.zeilen)))
        faelle += 1
    for k in (1, 2, 3):
        vars_ = tuple('abc'[:k]); allrows = list(itertools.product((0, 1), repeat=k))
        for mask in range(1 << (1 << k)):
            rows = [allrows[b] for b in range(1 << k) if (mask >> b) & 1]
            for m in range(0, k + 1):
                for S in itertools.permutations(vars_, m):
                    Mall = list(itertools.product((0, 1), repeat=m)); pruefe(vars_, rows, S, [r for r in Mall if rnd.random() < 0.6])
    for k in (4, 5):
        for _ in range(300):
            vars_ = tuple(rnd.sample('abcdefgh', k)); allrows = list(itertools.product((0, 1), repeat=k)); rows = [r for r in allrows if rnd.random() < 0.5]
            if rnd.random() < 0.1: rows = []
            if rnd.random() < 0.1: rows = allrows
            if rnd.random() < 0.1: rows = [rnd.choice(allrows)]
            m = rnd.randint(0, k); S = tuple(rnd.sample(vars_, m)); Mall = list(itertools.product((0, 1), repeat=m)); pruefe(vars_, rows, S, [r for r in Mall if rnd.random() < 0.6])
    return dict(faelle=faelle, fehler=fehler[:20], fehler_gesamt=len(fehler), bestanden=(not fehler), seed=seed)
if __name__ == '__main__':
    r = selbsttest(); json.dump(r, open(os.path.join(HERE, 'ERGEBNIS_SCHLANK_SELBSTTEST.json'), 'w'), indent=1, default=str)
    print('Selbsttest schlanke Masken gegen bisherige Bitmengen und Tupel: %d Faelle, %d Fehler -> %s' % (r['faelle'], r['fehler_gesamt'], 'BESTANDEN' if r['bestanden'] else 'FEHLER')); sys.exit(0 if r['bestanden'] else 3)
