"""BLOCKWEISER EXAKTER ABGLEICH (GO Christian 2026-10-25 15:07; Entwurf + Ghosts drei Korrekturen: nur Variante A, 600 s hart).
Relation einer Gruppe = bytearray mit 2^k Bits (Position b = Summe wert(v_j) << j wie bisher). Block = die niedrigsten w = min(m, k) Variablen (2^w Bit, Standard m = 12 -> 512 Byte);
Blockindex t = Belegung der hohen Variablen. Einzige gespeicherte Masken: EINS/NULL fuer j < w ueber 2^w Bit, je Blockbreite einmal, fuer alle Gruppen gemeinsam.
Nachricht ueber S (Reihenfolge wie in der Kante): bytes mit 2^s Bit, Position c = Summe wert(s_i) << i. Je (Gruppe, S) werden kleine Indextabellen gehalten (S_low-Offsets, 2^|S_low| ints) – kein 2^k-Bit-Objekt.
Projektion: je Block t: base(t) aus den S_high-Werten; fuer jedes c_low mit Block & maske_c_low != 0 Bit base + offs[c_low] in P setzen. Semijoin: je Block erlaubt = ODER der maske_c_low mit gesetztem M-Bit; Block &= erlaubt; in Ort und Stelle.
Zwischenobjekte je Aufruf: Tabelle der maske_c_low (2^|S_low| x 2^w Bit, <= 2 MiB bei m = 12), ein Block, erlaubt, P/M (2^s Bit). Nullbloecke werden uebersprungen. Zeilenzahl wird mitgefuehrt (keine Vollzaehlung ueber die Relation).
Gleiche Mathematik wie bitmenge_schlank; Selbsttest gegen bitmenge_schlank.SchlankBitGruppe und gruppen.Gruppe (Tupel)."""
import sys, os, json, itertools, random, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gruppen, bitmenge, bitmenge_schlank
OPS = dict(und=0, oder=0, bloecke=0, nullbloecke=0, masken_tabellen=0, masken_tabellen_bytes_max=0, semijoins=0, projektionen=0)
_MASKEN = {}
def eins_schnell(w, j):
    x = ((1 << (1 << j)) - 1) << (1 << j); W = 1 << (j + 1)
    while W < (1 << w): x |= x << W; W <<= 1
    return x
def masken(w):
    if w not in _MASKEN:
        alle = (1 << (1 << w)) - 1; E = [eins_schnell(w, j) for j in range(w)]; _MASKEN[w] = (E, [alle & ~e for e in E], alle)
    return _MASKEN[w]
POP = bytes(bin(i).count('1') for i in range(256))

class BlockZeilen:
    def __init__(self, g): self.g = g
    def __len__(self): return self.g.n
    def __bool__(self): return self.g.n > 0
    def __iter__(self):
        g = self.g
        for t in range(g.T):
            blk = g.block(t)
            if not blk: continue
            b = 0
            while blk:
                if blk & 1: yield tuple(((t << g.w | b) >> j) & 1 for j in range(g.k))
                blk >>= 1; b += 1
    def __eq__(self, o): return set(self) == set(o)

class BlockGruppe(gruppen.Gruppe):
    def __init__(self, name, vars_, m=12):
        super().__init__(name, vars_); self.k = len(self.vars); self.w = min(m, self.k); self.T = 1 << (self.k - self.w); self.B = max(1, (1 << self.w) >> 3)
        self.rel = None; self.n = 0; self._idx = {}
    @property
    def zeilen(self): return BlockZeilen(self) if self.rel is not None else None
    @zeilen.setter
    def zeilen(self, v): pass
    def block(self, t): return int.from_bytes(self.rel[t * self.B:(t + 1) * self.B], 'little')
    def setblock(self, t, val): self.rel[t * self.B:(t + 1) * self.B] = val.to_bytes(self.B, 'little')
    def _tab(self, S):
        """Indextabellen je (Gruppe, S): low-Positionen, high-Positionen mit S-Index, offs[c_low]; dazu maske_c_low-Tabelle (kurzlebig, nicht gecached)."""
        S = tuple(S)
        if S not in self._idx:
            low = [(i, self.vars.index(v)) for i, v in enumerate(S) if self.vars.index(v) < self.w]; high = [(i, self.vars.index(v) - self.w) for i, v in enumerate(S) if self.vars.index(v) >= self.w]
            offs = []
            for c in range(1 << len(low)):
                o = 0
                for q, (i, j) in enumerate(low):
                    if (c >> q) & 1: o |= 1 << i
                offs.append(o)
            self._idx[S] = (low, high, offs)
        return self._idx[S]
    def _masktab(self, low):
        E, N0, alle = masken(self.w); tab = []
        for c in range(1 << len(low)):
            mk = alle
            for q, (i, j) in enumerate(low): mk &= (E[j] if (c >> q) & 1 else N0[j]); OPS['und'] += 1
            tab.append(mk)
        OPS['masken_tabellen'] += 1; OPS['masken_tabellen_bytes_max'] = max(OPS['masken_tabellen_bytes_max'], len(tab) * (28 + 4 * ((1 << self.w) // 30 + 1)))
        return tab
    def _base(self, t, high):
        b = 0
        for i, j in high:
            if (t >> j) & 1: b |= 1 << i
        return b
    def init_zeilen(self):
        E, N0, alle = masken(self.w); self.rel = bytearray(b'\xff' * (self.B * self.T))
        if (1 << self.w) < 8:
            for t in range(self.T): self.setblock(t, alle)          # Bloecke unter 8 Bit: nur die gueltigen Bits setzen
        for kst in self.kaestchen:
            idx = [self.vars.index(v) for v in kst.vars]; low = [(q, j) for q, j in enumerate(idx) if j < self.w]; high = [(q, j - self.w) for q, j in enumerate(idx) if j >= self.w]
            for t in range(self.T):
                mk = 0
                for row in kst.zeilen:
                    if any(row[q] != ((t >> j) & 1) for q, j in high): continue
                    z = alle
                    for q, j in low: z &= (E[j] if row[q] else N0[j])
                    mk |= z
                blk = self.block(t) & mk
                self.setblock(t, blk)
        self.n = sum(POP[b] for b in self.rel); self.init_zeilen_zahl = self.n; return self.n > 0
    def proj(self, S):
        OPS['projektionen'] += 1; low, high, offs = self._tab(S); tab = self._masktab(low); s = len(S); P = bytearray(max(1, (1 << s) >> 3))
        for t in range(self.T):
            blk = self.block(t); OPS['bloecke'] += 1
            if not blk: OPS['nullbloecke'] += 1; continue
            base = self._base(t, high)
            for c, mk in enumerate(tab):
                OPS['und'] += 1
                if blk & mk: i = base | offs[c]; P[i >> 3] |= 1 << (i & 7)
        return (bytes(P),)
    def semijoin(self, S, M):
        OPS['semijoins'] += 1; Mb = next(iter(M)) if isinstance(M, (set, frozenset)) else M; Mb = Mb[0] if isinstance(Mb, tuple) else Mb
        low, high, offs = self._tab(S); tab = self._masktab(low); entfernt = 0
        for t in range(self.T):
            blk = self.block(t); OPS['bloecke'] += 1
            if not blk: OPS['nullbloecke'] += 1; continue
            base = self._base(t, high); erl = 0
            for c, mk in enumerate(tab):
                i = base | offs[c]
                if (Mb[i >> 3] >> (i & 7)) & 1: erl |= mk; OPS['oder'] += 1
            neu = blk & erl; OPS['und'] += 1
            if neu != blk: entfernt += blk.bit_count() - neu.bit_count(); self.setblock(t, neu)
        self.n -= entfernt; return entfernt
    def als_int(self):
        if (1 << self.w) >= 8: return int.from_bytes(self.rel, 'little')
        return sum(self.block(t) << (t << self.w) for t in range(self.T))
    def als_tupel(self): return set(self.zeilen)

def selbsttest(seed=20261025, m_test=2):
    """Block gegen bitmenge_schlank und Tupel; m_test = 2 (Bloecke zu 4 Bit, damit schon bei k = 3 mehrere Bloecke entstehen); zusaetzlich m = 12 (ein Block) fuer k <= 8."""
    rnd = random.Random(seed); faelle = 0; fehler = []
    def pruefe(vars_, rows, S, M_rows, m):
        nonlocal faelle
        T = gruppen.Gruppe('T', vars_); T.zeilen = set(rows); A = bitmenge_schlank.SchlankBitGruppe('A', vars_); A.rel = sum(1 << A._bit(r) for r in rows)
        from stern import Kaestchen; Bk = BlockGruppe('B', vars_, m); Bk.kaestchen = [Kaestchen('K', vars_, set(rows))]; Bk.init_zeilen()
        if Bk.als_int() != A.rel: fehler.append(dict(art='init', vars=vars_, rows=sorted(rows), m=m)); faelle += 1; return
        pa = A.proj(S)[0]; pb = int.from_bytes(Bk.proj(S)[0], 'little'); mS = len(S); pt = T.proj(S)
        if pa != pb: fehler.append(dict(art='proj', vars=vars_, rows=sorted(rows), S=S, m=m, schlank=pa, block=pb, tupel=sorted(pt)))
        Mi = sum(1 << sum(r[i] << i for i in range(mS)) for r in M_rows); Mbytes = Mi.to_bytes(max(1, (1 << mS) >> 3), 'little')
        sa = A.semijoin(S, frozenset({(Mi,)})); sb = Bk.semijoin(S, frozenset({(Mbytes,)})); st = T.semijoin(S, set(M_rows))
        if sa != sb or A.rel != Bk.als_int() or st != sb or T.zeilen != Bk.als_tupel() or Bk.n != len(T.zeilen): fehler.append(dict(art='semijoin', vars=vars_, rows=sorted(rows), S=S, M=sorted(M_rows), m=m, schlank=A.rel, block=Bk.als_int(), n=Bk.n))
        faelle += 1
    for m in (m_test, 12):
        for k in (1, 2, 3):
            vars_ = tuple('abc'[:k]); allrows = list(itertools.product((0, 1), repeat=k))
            for mask in range(1 << (1 << k)):
                rows = [allrows[b] for b in range(1 << k) if (mask >> b) & 1]
                for mS in range(0, k + 1):
                    for S in itertools.permutations(vars_, mS):
                        Mall = list(itertools.product((0, 1), repeat=mS)); pruefe(vars_, rows, S, [r for r in Mall if rnd.random() < 0.6], m)
        for _ in range(400):
            k = rnd.randint(4, 8 if m == 12 else 6); vars_ = tuple(rnd.sample('abcdefgh', k)); allrows = list(itertools.product((0, 1), repeat=k)); rows = [r for r in allrows if rnd.random() < 0.5]
            if rnd.random() < 0.1: rows = []
            if rnd.random() < 0.1: rows = allrows
            if rnd.random() < 0.1: rows = [rnd.choice(allrows)]
            art = rnd.choice(('gemischt', 'nur_hoch', 'nur_niedrig', 'leer'))
            w = min(m, k); lowv = list(vars_[:w]); highv = list(vars_[w:])
            if art == 'leer': S = ()
            elif art == 'nur_hoch' and highv: S = tuple(rnd.sample(highv, rnd.randint(1, len(highv))))
            elif art == 'nur_niedrig': S = tuple(rnd.sample(lowv, rnd.randint(1, len(lowv))))
            else: S = tuple(rnd.sample(vars_, rnd.randint(0, k)))
            Mall = list(itertools.product((0, 1), repeat=len(S))); pruefe(vars_, rows, S, [r for r in Mall if rnd.random() < 0.6], m)
    return dict(faelle=faelle, fehler=fehler[:10], fehler_gesamt=len(fehler), bestanden=(not fehler), seed=seed, m_test=m_test)
if __name__ == '__main__':
    r = selbsttest(); json.dump(r, open(os.path.join(HERE, 'ERGEBNIS_BLOCK_SELBSTTEST.json'), 'w'), indent=1, default=str)
    print('Selbsttest blockweise gegen schlanke Bitmengen und Tupel: %d Faelle, %d Fehler -> %s' % (r['faelle'], r['fehler_gesamt'], 'BESTANDEN' if r['bestanden'] else 'FEHLER')); sys.exit(0 if r['bestanden'] else 3)
