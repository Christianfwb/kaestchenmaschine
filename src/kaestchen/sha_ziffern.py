#!/usr/bin/env python3
"""ANBINDUNG DES ZIFFERNNETZES AN DEN VOLLSTAENDIGEN SHA256d (Fable, 2026-10-22, Stufe 0).
Drei Operatorklassen fuer DIESELBE Funktion pruefung.compress (Erweiterung 16..63, 64 Runden, Feed-forward):
  IntLog  : Integer-Referenz (pruefung.IntegerOps) mit Protokoll aller Zwischenwoerter,
  BitLog  : Bitgraph (gatter.Ops, unveraendert) mit demselben Protokoll,
  ZiffernOps: Ziffernnetz (ziffern.Netz, w=32 -> 16 Ziffern je Wort) mit demselben Protokoll.
Alle drei protokollieren jedes Ergebniswort in derselben Aufrufreihenfolge mit Art und Phase ('H1'/'H2'); Zuordnung Bit<->Ziffer
erfolgt ueber diese semantische Reihenfolge (Art + Phase + laufende Nummer), NICHT ueber Knoten-IDs. Zwischensummen n-stelliger
Additionen werden in allen drei Klassen als eigene Woerter ('add2') protokolliert.
Ziffernabbildung: Wort = 16 Ziffern (Ziffer j = Wortbits 2j, 2j+1, big-endian 32-Bit-Wort). rot gerade = Umbenennung, ungerade = ROT1;
shr gerade = Umbenennung mit Nullziffern, ungerade = ROT1 mit Nullziffer; xor dreifach = zwei XOR; ch/maj = 4-stellige Tabellen;
add = Kette von ADD mit Uebertragsvariablen (cin_0 = 0, cout_15 verworfen). Zielvergleich: LE-Kette ueber die 128 Ziffern der
little-endian-Zahl (Bitcoin-Byteordnung), le_out = (d < t) oder (d == t und le_in), exakt; Zahlziffer k <-> Digestwort k//16,
Wortziffer 4*(3-(k//4)%4) + k%4.  Nonce: Header-Bytes 76..79 little-endian -> Wort 3 des zweiten Blocks; Noncebit b -> Wortbit
8*(3-b//8)+b%8 -> Ziffer (8*(3-b//8)+b%8)//2."""
import struct, sys, pathlib
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import pruefung as P
import gatter as G
from ziffern import Netz, TABELLEN, GROESSEN
import bausteine as BS   # registriert ROT1/CH/MAJ-Tabellen

# LE-Tabellen: (d, le_in, le_out) mit Zielziffer t
for t in range(4):
    TABELLEN['LE%d' % t] = [(d, li, 1 if (d < t or (d == t and li)) else 0) for d in range(4) for li in range(2)]
    GROESSEN['LE%d' % t] = (4, 2, 2)

class Protokoll:
    """Gemeinsames Protokoll: liste von (phase, art, nr, wort)."""
    def __init__(self): self.log = []; self.phase = '?'; self.nr = {}
    def merke(self, art, wort):
        k = (self.phase, art); self.nr[k] = self.nr.get(k, 0) + 1
        self.log.append((self.phase, art, self.nr[k], wort)); return wort
    def arten(self): return [(p, a, n) for p, a, n, _ in self.log]

class IntLog(Protokoll):
    def __init__(self): super().__init__()
    def const(self, x): return self.merke('const', P.IntegerOps.const(x))
    def rot(self, x, n): return self.merke('rot%d' % n, P.IntegerOps.rot(x, n))
    def shr(self, x, n): return self.merke('shr%d' % n, P.IntegerOps.shr(x, n))
    def xor(self, a, b, c): return self.merke('xor', P.IntegerOps.xor(a, b, c))
    def ch(self, a, b, c): return self.merke('ch', P.IntegerOps.ch(a, b, c) & P.MASK)
    def maj(self, a, b, c): return self.merke('maj', P.IntegerOps.maj(a, b, c))
    def add(self, *ws):
        r = ws[0]
        for w in ws[1:]: r = self.merke('add2', (r + w) & P.MASK)
        return r

class BitLog(Protokoll):
    """gatter.Ops unveraendert benutzt; nur Protokoll davor."""
    def __init__(self, graph): super().__init__(); self.o = G.Ops(graph)
    def const(self, x): return self.merke('const', self.o.const(x))
    def rot(self, x, n): return self.merke('rot%d' % n, self.o.rot(x, n))
    def shr(self, x, n): return self.merke('shr%d' % n, self.o.shr(x, n))
    def xor(self, a, b, c): return self.merke('xor', self.o.xor(a, b, c))
    def ch(self, a, b, c): return self.merke('ch', self.o.ch(a, b, c))
    def maj(self, a, b, c): return self.merke('maj', self.o.maj(a, b, c))
    def add(self, *ws):
        r = ws[0]
        for w in ws[1:]: r = self.merke('add2', self.o.add(r, w))
        return r

class ZiffernOps(Protokoll):
    def __init__(self, N):
        super().__init__(); self.N = N; self.D = N.D; self.null = N.konst(0, 'null')[0]; self.zaehler = 0
    def _name(self, art):
        self.zaehler += 1; return '%s_%s_%d' % (self.phase, art, self.zaehler)
    def const(self, x): return self.merke('const', list(self.N.konst(x, 'k')))
    def rot(self, x, n):
        return self.merke('rot%d' % n, list(BS.rot(self.N, x, n, self._name('rot%d' % n))))
    def shr(self, x, n):
        D = self.D; k = n // 2; N = self.N; null = self.null
        def q(j): return x[j] if j < D else null
        if n % 2 == 0: y = [q(j + k) for j in range(D)]
        else:
            y = []
            for j in range(D):
                if j + k >= D: y.append(null); continue
                v = N.var('%s[%d]' % (self._name('shr%d' % n), j), 4); N.bez.append(('ROT1', [v, q(j + k), q(j + k + 1)])); y.append(v)
        return self.merke('shr%d' % n, y)
    def xor(self, a, b, c):
        N = self.N; return self.merke('xor', list(N.xor(N.xor(a, b, self._name('xorA')), c, self._name('xor'))))
    def ch(self, a, b, c): return self.merke('ch', list(BS.ch(self.N, a, b, c, self._name('ch'))))
    def maj(self, a, b, c): return self.merke('maj', list(BS.maj(self.N, a, b, c, self._name('maj'))))
    def add(self, *ws):
        r = list(ws[0])
        for w in ws[1:]: r = self.merke('add2', list(self.N.add(r, list(w), self._name('add'))))
        return r
    def ziel(self, digest, target):
        """LE-Kette; liefert (le_ids[0..128], le_128). le_0 fest 1."""
        N = self.N; le = N.var('le_0', 2); N.fest(le, 1); kette = [le]
        for k in range(128):
            t = (target >> (2 * k)) & 3; d = digest[k // 16][4 * (3 - (k // 4) % 4) + k % 4]
            nle = N.var('le_%d' % (k + 1), 2); N.bez.append(('LE%d' % t, [d, le, nle])); le = nle; kette.append(le)
        return kette, le

def nonce_wortbit(b): return 8 * (3 - b // 8) + b % 8

def compress_r(state, words, op, trace=None, runden=64):
    """REDUZIERTES SHA-256 (Rundenkurve, 2026-10-23): wie pruefung.compress, aber nur die ersten `runden` Runden und die
    Erweiterung nur bis W[runden-1]. Feed-forward und Rundenfolge unveraendert. runden=64 ist textgleich zu pruefung.compress."""
    w = list(words)
    for i in range(16, runden):
        s0 = op.xor(op.rot(w[i-15],7),op.rot(w[i-15],18),op.shr(w[i-15],3))
        s1 = op.xor(op.rot(w[i-2],17),op.rot(w[i-2],19),op.shr(w[i-2],10))
        w.append(op.add(w[i-16],s0,w[i-7],s1))
    a,b,c,d,e,f,g,h = state
    for i in range(runden):
        s1 = op.xor(op.rot(e,6),op.rot(e,11),op.rot(e,25))
        s0 = op.xor(op.rot(a,2),op.rot(a,13),op.rot(a,22))
        t1 = op.add(h,s1,op.ch(e,f,g),op.const(P.K[i]),w[i])
        t2 = op.add(s0,op.maj(a,b,c))
        a,b,c,d,e,f,g,h = op.add(t1,t2),a,b,c,op.add(d,t1),e,f,g
        if trace is not None: trace.append((a,b,c,d,e,f,g,h))
    return tuple(op.add(x,y) for x,y in zip(state,(a,b,c,d,e,f,g,h)))

def _comp(runden):
    if runden == 64: return P.compress
    return lambda state, words, op, trace=None: compress_r(state, words, op, trace, runden)

def rechenweg(ops, header76, base, bits, umfang, nonce_wort=None, digest1=None, runden=64):
    """Fuehrt die Bitcoin-Rechnung mit der Operatorklasse aus. umfang 'voll': ab Midstate (Konstante) mit Block 2 (Nonce-Wort frei),
    'lokal': ab Digest1 (uebergeben, 8 Woerter) nur zweite Anwendung. Liefert dict mit Woertern."""
    masked = base & ~sum(1 << b for b in bits)
    out = {}; comp = _comp(runden)
    if umfang == 'voll':
        padded = P.padded(header76 + masked.to_bytes(4, 'little'))
        mid = comp(P.IV, struct.unpack('>16I', padded[:64]), P.IntegerOps)    # noncefreier Block 1: Konstante (zulaessig)
        ops.phase = 'H1'
        words = [ops.const(x) for x in struct.unpack('>16I', padded[64:])]
        if nonce_wort is not None: words[3] = nonce_wort
        out['mid'] = mid; out['H1_words'] = list(words)
        tr1 = []; d1 = comp(tuple(ops.const(x) for x in mid), words, ops, trace=tr1); out['H1_trace'] = tr1
    else:
        ops.phase = 'H1'; d1 = digest1
    out['digest1'] = d1
    ops.phase = 'H2'
    words2 = list(d1) + [ops.const(0x80000000)] + [ops.const(0)] * 6 + [ops.const(256)]
    tr2 = []; d2 = comp(tuple(ops.const(x) for x in P.IV), words2, ops, trace=tr2); out['H2_trace'] = tr2; out['digest2'] = d2
    return out

def baue_bitgraph(header76, base, bits, target, runden=64, mit_ziel=True):
    """Wie gatter.build (gleiche Schritte), aber mit BitLog-Protokoll; liefert graph, inputs, log, out, root."""
    graph = G.Graph(); ops = BitLog(graph)
    masked = base & ~sum(1 << b for b in bits)
    padded = P.padded(header76 + masked.to_bytes(4, 'little'))
    nonce_w = list(G.Ops.const(struct.unpack('>16I', padded[64:])[3]))
    inputs = []
    for index, bit in enumerate(bits):
        node = graph.input(index); inputs.append(node); nonce_w[nonce_wortbit(bit)] = node
    out = rechenweg(ops, header76, base, bits, 'voll', nonce_wort=tuple(nonce_w), runden=runden)
    digest = out['digest2']
    numeric = [digest[byte // 4][8 * (3 - byte % 4) + bit] for byte in range(32) for bit in range(8)]
    le = 1
    if not mit_ziel: return graph, inputs, ops, out, None
    for i, x in enumerate(numeric):
        if target >> i & 1: le = G.inv(graph.gate('and', x, G.inv(le)))
        else: le = graph.gate('and', G.inv(x), le)
    return graph, inputs, ops, out, le

def baue_ziffernnetz(header76, base, bits, target, umfang, mit_ziel=True, runden=64):
    """Ziffernnetz; liefert N, ops, out, nonce_ziffern (voll) bzw. digest1-Ziffern (lokal), le."""
    N = Netz(32); ops = ZiffernOps(N)
    masked = base & ~sum(1 << b for b in bits)
    if umfang == 'voll':
        padded = P.padded(header76 + masked.to_bytes(4, 'little')); w3 = struct.unpack('>16I', padded[64:])[3]
        ops.phase = 'H1'; nonce_w = N.wort('H1_nonce')
        freie_ziffern = sorted({nonce_wortbit(b) // 2 for b in bits})
        for j in range(16):
            if j not in freie_ziffern: N.fest(nonce_w[j], (w3 >> (2 * j)) & 3)
        out = rechenweg(ops, header76, base, bits, 'voll', nonce_wort=nonce_w, runden=runden); eing = nonce_w
    else:
        ops.phase = 'H1'; d1 = [N.wort('H1_digest%d' % i) for i in range(8)]
        out = rechenweg(ops, header76, base, bits, 'lokal', digest1=d1, runden=runden); eing = d1
    le = None
    if mit_ziel:
        kette, le = ops.ziel(out['digest2'], target); out['le_kette'] = kette
        if mit_ziel == 'fest': N.fest(le, 1)
    return N, ops, out, eing, le

def bitkomparator(target):
    """Eigenstaendige Vergleichskette wie gatter.build ueber 256 Eingangsbits (Zahlbit i = Eingang i); liefert graph, inputs, root."""
    graph = G.Graph(); inputs = [graph.input(i) for i in range(256)]; le = 1
    for i, x in enumerate(inputs):
        if target >> i & 1: le = G.inv(graph.gate('and', x, G.inv(le)))
        else: le = graph.gate('and', G.inv(x), le)
    return graph, inputs, le

# ---------------- Adapter Bit <-> Ziffer (aus lauf_m4.py, Korrekturen 2/3 enthalten) ----------------
def bits_zu_ziffern(b0, b1): return sum(1 << z for z in range(4) if (b0 >> (z & 1)) & 1 and (b1 >> (z >> 1)) & 1)
def ziffer_zu_bits(m):
    b0 = b1 = 0
    for z in range(4):
        if m >> z & 1: b0 |= 1 << (z & 1); b1 |= 1 << (z >> 1)
    return b0, b1
def dom_von(d, b): return (((d[-b] & 1) << 1) | ((d[-b] & 2) >> 1)) if b < 0 else d[b]
def dom_schneiden(d, b, mk):
    if b < 0: mk = ((mk & 1) << 1) | ((mk & 2) >> 1); b = -b
    d[b] &= mk; return d[b]

def wortzuordnung(bitlog, zlog):
    """Semantische Zuordnung: gleiche (phase, art, nr)-Folge -> Liste (name, bits(32 Knoten), ziffern(16 ids))."""
    assert bitlog.arten() == zlog.arten(), 'Protokollfolgen verschieden'
    return [('%s_%s_%d' % (p, a, n), bw, zw) for (p, a, n, bw), (_, _, _, zw) in zip(bitlog.log, zlog.log)]
