"""BITMENGEN-SPEICHERUNG (GO Christian 2026-10-25 08:52; Entwurf + Ghosts vier Ergaenzungen).
FESTLEGUNG: Gruppe mit Variablen (v_0..v_{k-1}) in der Gruppenreihenfolge self.vars. Belegung -> Bitposition b = Summe_j wert(v_j) << j (v_0 = niedrigstes Bit).
Relation = Python-Ganzzahl mit 2^k Bits; Bit b = 1 heisst Belegung erlaubt. Nachricht ueber Schnittmenge S = (s_0..s_{m-1}) in Kantenreihenfolge: Ganzzahl mit 2^m Bits, Position c = Summe_i wert(s_i) << i.
Masken: je (Gruppe, S) eine Liste maske[c] (c = 0..2^m-1) = Bitmenge aller Gruppenbelegungen, deren S-Teil = c. Bedarf: 2^s Masken zu je bis zu 2^k Bits (s = |S|).
Projektion: Bit c gesetzt <=> rel & maske[c] != 0 (2^m UND). Semijoin mit M: rel &= ODER_{c in M} maske[c] (<= 2^m ODER + 1 UND). Projektion auf S = () : eine Maske (alles), Ergebnis Bit 0 <=> rel != 0.
Die Arbeitsliste (ereignis.py, unveraendert) huellt Nachrichten in frozenset(...); deshalb liefert proj() ein 1-Tupel (zahl,), die Nachricht ist frozenset({zahl}); semijoin() entpackt sie. Dokumentiert, kein Trick.
SELBSTTEST (vorab, gegen Tupelmengen): alle Relationen mit k<=3 (erschoepfend) und Stichproben k=4,5: leer, vollstaendig, einzelne Zeile, vertauschte Variablenreihenfolge, Projektion auf keine Variable; proj und semijoin muessen uebereinstimmen."""
import sys, os, json, itertools, random, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gruppen
OPS = dict(und=0, oder=0, popcount=0, masken_gebaut=0, masken_bits=0, masken_bau_s=0.0)
def popcount(x): OPS['popcount'] += 1; return bin(x).count('1')

class BitZeilen:
    """Sicht auf eine Bit-Relation wie eine Menge von Tupeln (len/bool/iter), ohne sie zu materialisieren."""
    def __init__(self, g): self.g = g
    def __len__(self): return bin(self.g.rel).count('1')
    def __bool__(self): return self.g.rel != 0
    def __iter__(self):
        k = len(self.g.vars); r = self.g.rel; b = 0
        while r:
            if r & 1: yield tuple((b >> j) & 1 for j in range(k))
            r >>= 1; b += 1
    def __eq__(self, o): return set(self) == set(o)

class BitGruppe(gruppen.Gruppe):
    def __init__(self, name, vars_): super().__init__(name, vars_); self.rel = 0; self._masken = {}
    @property
    def zeilen(self): return BitZeilen(self) if self.rel is not None else None
    @zeilen.setter
    def zeilen(self, v): pass                      # Basisklasse setzt None; ignoriert
    def _bit(self, bel): return sum(bel[j] << j for j in range(len(self.vars)))
    def masken(self, S):
        S = tuple(S)
        if S not in self._masken:
            t = time.perf_counter(); k = len(self.vars); idx = [self.vars.index(v) for v in S]; m = [0] * (1 << len(S))
            for b in range(1 << k):
                c = sum(((b >> idx[i]) & 1) << i for i in range(len(S))); m[c] |= 1 << b
            self._masken[S] = m; OPS['masken_gebaut'] += len(m); OPS['masken_bits'] += len(m) * (1 << k); OPS['masken_bau_s'] += time.perf_counter() - t
        return self._masken[S]
    def init_zeilen(self):
        if len(self.vars) > gruppen.MAX_VARS: raise gruppen.Offen('Gruppe %s: %d Variablen > %d' % (self.name, len(self.vars), gruppen.MAX_VARS))
        k = len(self.vars); self.rel = (1 << (1 << k)) - 1
        for kst in self.kaestchen:                 # Kaestchen bleiben Tupelmengen; einmalige Uebersetzung in eine Maske
            idx = [self.vars.index(v) for v in kst.vars]; m = 0
            for b in range(1 << k):
                if tuple((b >> i) & 1 for i in idx) in kst.zeilen: m |= 1 << b
            self.rel &= m; OPS['und'] += 1
        n = popcount(self.rel)
        if n > gruppen.MAX_ZEILEN: raise gruppen.Offen('Gruppe %s: %d Zeilen > %d' % (self.name, n, gruppen.MAX_ZEILEN))
        self.init_zeilen_zahl = n; return n > 0
    def proj(self, S):
        m = self.masken(S); P = 0
        for c in range(len(m)):
            OPS['und'] += 1
            if self.rel & m[c]: P |= 1 << c
        return (P,)
    def semijoin(self, S, M):
        P = next(iter(M)) if isinstance(M, (set, frozenset)) else M
        P = P[0] if isinstance(P, tuple) else P
        m = self.masken(S); erlaubt = 0; c = 0; PP = P
        while PP:
            if PP & 1: erlaubt |= m[c]; OPS['oder'] += 1
            PP >>= 1; c += 1
        vorher = popcount(self.rel); self.rel &= erlaubt; OPS['und'] += 1; return vorher - popcount(self.rel)
    def als_tupel(self): return set(self.zeilen)

def selbsttest(seed=20261025):
    """Vorabpruefung gegen gruppen.Gruppe (Tupelmengen)."""
    rnd = random.Random(seed); faelle = 0; fehler = []
    def pruefe(vars_, rows, S, M_rows):
        nonlocal faelle
        T = gruppen.Gruppe('T', vars_); T.zeilen = set(rows); B = BitGruppe('B', vars_); B.rel = sum(1 << B._bit(r) for r in rows)
        pt = T.proj(S); pb = B.proj(S)[0]; m = len(S); pb_rows = {tuple(((c >> i) & 1) for i in range(m)) for c in range(1 << m) if (pb >> c) & 1}
        if pt != pb_rows: fehler.append(dict(art='proj', vars=vars_, rows=sorted(rows), S=S, tupel=sorted(pt), bit=sorted(pb_rows)))
        Mb = sum(1 << sum(r[i] << i for i in range(m)) for r in M_rows)
        st = T.semijoin(S, set(M_rows)); sb = B.semijoin(S, frozenset({(Mb,)}))
        if st != sb or T.zeilen != B.als_tupel(): fehler.append(dict(art='semijoin', vars=vars_, rows=sorted(rows), S=S, M=sorted(M_rows), tupel=sorted(T.zeilen), bit=sorted(B.als_tupel())))
        faelle += 1
    for k in (1, 2, 3):                            # erschoepfend: alle Relationen, alle Schnittmengen (inkl. leer, voll, Einzelzeile, S=())
        vars_ = tuple('abc'[:k]); allrows = list(itertools.product((0, 1), repeat=k))
        for mask in range(1 << (1 << k)):
            rows = [allrows[b] for b in range(1 << k) if (mask >> b) & 1]
            for m in range(0, k + 1):
                for S in itertools.permutations(vars_, m):
                    Mall = list(itertools.product((0, 1), repeat=m)); M_rows = [r for r in Mall if rnd.random() < 0.6]
                    pruefe(vars_, rows, S, M_rows)
    for k in (4, 5):                               # Stichproben, auch vertauschte Variablenreihenfolge
        for _ in range(300):
            vars_ = tuple(rnd.sample('abcdefgh', k)); allrows = list(itertools.product((0, 1), repeat=k)); rows = [r for r in allrows if rnd.random() < 0.5]
            if rnd.random() < 0.1: rows = []
            if rnd.random() < 0.1: rows = allrows
            if rnd.random() < 0.1: rows = [rnd.choice(allrows)]
            m = rnd.randint(0, k); S = tuple(rnd.sample(vars_, m)); Mall = list(itertools.product((0, 1), repeat=m)); M_rows = [r for r in Mall if rnd.random() < 0.6]
            pruefe(vars_, rows, S, M_rows)
    return dict(faelle=faelle, fehler=fehler[:20], fehler_gesamt=len(fehler), bestanden=(not fehler), seed=seed)

if __name__ == '__main__':
    r = selbsttest(); json.dump(r, open(os.path.join(HERE, 'ERGEBNIS_BIT_SELBSTTEST.json'), 'w'), indent=1, default=str)
    print('Selbsttest Bitmengen gegen Tupelmengen: %d Faelle, %d Fehler -> %s' % (r['faelle'], r['fehler_gesamt'], 'BESTANDEN' if r['bestanden'] else 'FEHLER')); sys.exit(0 if r['bestanden'] else 3)
