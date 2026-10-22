#!/usr/bin/env python3
"""Beispiel 1: Reduziertes SHA256d (R Runden je Kompression) – Nonce aus dem exakten Zielhash ableiten, ohne Kandidatensuche.
Aufruf: python -I 01_reduzierte_runden.py [R]   (Standard R = 8; 4..16 laufen in Sekunden; R = 64 ist das echte SHA256d und bleibt OFFEN)
Offline, CPU, keine Netzverbindung. Der Loeser bekommt nur Vorlage, 8 freie Noncebits und den Zielhash – die Kontrollnonce erst das Orakel danach."""
import sys, json, struct, hashlib, time, pathlib
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ, pruefung as P
from e1_bit import e1_lauf
R = int(sys.argv[1]) if len(sys.argv) > 1 else 8
F = json.loads((HERE.parent / 'experimente' / 'skripte' / 'FAELLE_SHA256D.json').read_text())['faelle'][0]
h76 = bytes.fromhex(F['header_hex_ohne_nonce']); BITS = list(range(8))
def sha256d_r(nonce):                                   # Integer-Referenz, getrennt vom Bitgraphen
    p = P.padded(h76 + nonce.to_bytes(4, 'little'))
    mid = SZ.compress_r(P.IV, struct.unpack('>16I', p[:64]), P.IntegerOps, runden=R)
    d1 = SZ.compress_r(mid, struct.unpack('>16I', p[64:]), P.IntegerOps, runden=R)
    return SZ.compress_r(P.IV, list(d1) + [0x80000000] + [0] * 6 + [256], P.IntegerOps, runden=R)
kontrolle = int.from_bytes(hashlib.sha256(b'KONTROLLE_BEISPIEL_R%d' % R).digest(), 'little') % 256
ziel = sha256d_r(kontrolle); hstar = int.from_bytes(struct.pack('>8I', *ziel), 'little')
t = time.perf_counter()
g, inputs, _, out, _ = SZ.baue_bitgraph(h76, 0, BITS, 0, runden=R, mit_ziel=False)
d = [3] * len(g.nodes); d[0] = 1; d[1] = 2                 # Kaestchen: 1={0}, 2={1}, 3={0,1}
for i in range(256):                                        # Zielhash festlegen (Bit i der little-endian-Zahl)
    node = out['digest2'][(i // 8) // 4][8 * (3 - (i // 8) % 4) + i % 8]
    SZ.dom_schneiden(d, node, 1 << ((hstar >> i) & 1))
status, sweeps = e1_lauf(g, d, max_sweeps=10 ** 6)
nonce_bits = {i: SZ.dom_von(d, n) >> 1 for i, n in enumerate(inputs) if SZ.dom_von(d, n) in (1, 2)}
abgeleitet = sum(v << i for i, v in nonce_bits.items()) if len(nonce_bits) == 8 else None
treffer = [n for n in range(256) if sha256d_r(n) == ziel]  # Orakel erst jetzt
print('R = %d Runden | Graph %d Knoten | E1 %s nach %d Durchlaeufen, %.2f s' % (R, len(g.nodes), status, sweeps, time.perf_counter() - t))
print('abgeleitete Noncebits: %d von 8 -> Nonce %s | Orakel-Treffer %s | Kontrollnonce %d' % (len(nonce_bits), abgeleitet, treffer, kontrolle))
print('ERGEBNIS:', 'TREFFER_ABGELEITET (vom Orakel bestaetigt)' if abgeleitet is not None and treffer == [abgeleitet] else 'OFFEN (keine vollstaendige Ableitung)')
