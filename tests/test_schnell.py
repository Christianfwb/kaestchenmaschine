#!/usr/bin/env python3
"""Schnelltests (< 60 s, CPU, offline): python -I tests/test_schnell.py
T1 Referenz: compress_r mit 64 Runden == hashlib SHA256d (F1 und F2, mehrere Nonces).
T2 Bitgraph: Auswertung des Graphen mit festem Nonce == hashlib (F1, 4 Nonces).
T3 Adapter Bit<->Ziffer: Rundreise aller Masken.
T4 Reduziertes Modell R=4 und R=6: Nonce aus Zielhash abgeleitet == Orakel.
T5 Genesis: bekannter Treffer in keiner E1-Domaene ausgeschlossen."""
import sys, json, struct, hashlib, pathlib
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ, pruefung as P, gatter as G
from e1_bit import e1_lauf
FAELLE = json.loads((HERE.parent / 'experimente' / 'skripte' / 'FAELLE_SHA256D.json').read_text())['faelle']
def sha256d_r(h76, nonce, R):
    p = P.padded(h76 + nonce.to_bytes(4, 'little'))
    mid = SZ.compress_r(P.IV, struct.unpack('>16I', p[:64]), P.IntegerOps, runden=R)
    d1 = SZ.compress_r(mid, struct.unpack('>16I', p[64:]), P.IntegerOps, runden=R)
    return SZ.compress_r(P.IV, list(d1) + [0x80000000] + [0] * 6 + [256], P.IntegerOps, runden=R)
ok = 0
# T1
for F in FAELLE:
    h76 = bytes.fromhex(F['header_hex_ohne_nonce'])
    for n in (0, 1, 12345, F.get('basis_nonce', 0) + 7):
        assert struct.pack('>8I', *sha256d_r(h76, n, 64)) == hashlib.sha256(hashlib.sha256(h76 + n.to_bytes(4, 'little')).digest()).digest()
ok += 1; print('T1 Referenz == hashlib: OK')
# T2
F = FAELLE[0]; h76 = bytes.fromhex(F['header_hex_ohne_nonce']); T = int(F['target_hex'], 16)
g, inputs, _, out, root = SZ.baue_bitgraph(h76, 0, list(range(8)), T)
for n in (0, 3, 77, 255):
    vals = {}
    def ev(x):
        if x < 0: return 1 - ev(-x)
        if x < 2: return x
        if x in vals: return vals[x]
        nd = g.nodes[x]
        if nd[0] == 'input': v = (n >> nd[1]) & 1
        else: v = (ev(nd[1]) & ev(nd[2])) if nd[0] == 'and' else (ev(nd[1]) ^ ev(nd[2]))
        vals[x] = v; return v
    sys.setrecursionlimit(1000000)
    bits = [ev(out['digest2'][b // 4][8 * (3 - b % 4) + k]) for b in range(32) for k in range(8)]
    val = sum(bit << i for i, bit in enumerate(bits))
    ref = int.from_bytes(hashlib.sha256(hashlib.sha256(h76 + n.to_bytes(4, 'little')).digest()).digest(), 'little')
    assert val == ref and ev(root) == (ref <= T)
ok += 1; print('T2 Bitgraph == hashlib: OK')
# T3
for b0 in (1, 2, 3):
    for b1 in (1, 2, 3):
        m = SZ.bits_zu_ziffern(b0, b1); assert SZ.ziffer_zu_bits(m) == (b0, b1)
ok += 1; print('T3 Adapter Rundreise: OK')
# T4
for R in (4, 6):
    kontrolle = 97 + R; ziel = sha256d_r(h76, kontrolle, R); hstar = int.from_bytes(struct.pack('>8I', *ziel), 'little')
    g, inputs, _, out, _ = SZ.baue_bitgraph(h76, 0, list(range(8)), 0, runden=R, mit_ziel=False)
    d = [3] * len(g.nodes); d[0] = 1; d[1] = 2
    for i in range(256): SZ.dom_schneiden(d, out['digest2'][(i // 8) // 4][8 * (3 - (i // 8) % 4) + i % 8], 1 << ((hstar >> i) & 1))
    st, sw = e1_lauf(g, d, max_sweeps=10 ** 6)
    nb = {i: SZ.dom_von(d, x) >> 1 for i, x in enumerate(inputs) if SZ.dom_von(d, x) in (1, 2)}
    assert st == 'FIXPUNKT' and len(nb) == 8 and sum(v << i for i, v in nb.items()) == kontrolle
    assert [n for n in range(256) if sha256d_r(h76, n, R) == ziel] == [kontrolle]
ok += 1; print('T4 Reduziert R=4,6: Nonce abgeleitet == Orakel: OK')
# T5
F2 = next(f for f in FAELLE if f['name'].startswith('F2')); h76 = bytes.fromhex(F2['header_hex_ohne_nonce']); T = int(F2['target_hex'], 16); B = F2['basis_nonce']
g, inputs, _, out, root = SZ.baue_bitgraph(h76, B, list(range(8)), T)
d = [3] * len(g.nodes); d[0] = 1; d[1] = 2; SZ.dom_schneiden(d, root, 2); st, sw = e1_lauf(g, d, max_sweeps=10 ** 6)
tr = 2083236893; assert (tr & ~255) == B
assert st == 'FIXPUNKT'
values = g.values(tr)
assert G.read(values, root)
assert all(mask & (1 << int(value)) for mask, value in zip(d, values))
assert int.from_bytes(hashlib.sha256(hashlib.sha256(h76 + tr.to_bytes(4, 'little')).digest()).digest(), 'little') <= T
ok += 1; print('T5 Genesis-Treffer erhalten (E1 %s, %d Durchlaeufe): OK' % (st, sw))
print('%d/5 Tests bestanden' % ok)
