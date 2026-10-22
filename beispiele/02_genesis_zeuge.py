#!/usr/bin/env python3
"""Beispiel 2: Vollstaendiges SHA256d, Genesis-Block, 8 freie Noncebits so gelegt, dass der bekannte Treffer 2083236893 in der Gruppe liegt.
Bitregeln (E1) bis zum Fixpunkt. Zeigt: 0 Noncebits abgeleitet, keine Nonce ausgeschlossen, der bekannte Treffer bleibt erhalten
(jedes Kaestchen enthaelt seinen Wert). Offline, CPU, ~5 s, ~60 MiB. Das Orakel (hashlib) wird erst nach der Propagation benutzt."""
import sys, json, hashlib, time, pathlib
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ
from e1_bit import e1_lauf
F = next(f for f in json.loads((HERE.parent / 'experimente' / 'skripte' / 'FAELLE_SHA256D.json').read_text())['faelle'] if f['name'].startswith('F2'))
h76 = bytes.fromhex(F['header_hex_ohne_nonce']); T = int(F['target_hex'], 16); BITS = list(range(8)); BASIS = F['basis_nonce']
t = time.perf_counter(); g, inputs, _, out, root = SZ.baue_bitgraph(h76, BASIS, BITS, T)
d = [3] * len(g.nodes); d[0] = 1; d[1] = 2; SZ.dom_schneiden(d, root, 2)       # Wurzel "Hash <= Target" = 1
status, sweeps = e1_lauf(g, d, max_sweeps=10 ** 6)
fest = [(i, SZ.dom_von(d, n) >> 1) for i, n in enumerate(inputs) if SZ.dom_von(d, n) in (1, 2)]
gruppe = [BASIS | sum(((n >> i) & 1) << BITS[i] for i in range(8)) for n in range(256)]
treffer = [n for n in gruppe if int.from_bytes(hashlib.sha256(hashlib.sha256(h76 + n.to_bytes(4, 'little')).digest()).digest(), 'little') <= T]
ausgeschlossen = [n for n in gruppe if any(((n >> BITS[i]) & 1) != v for i, v in fest)]
werte_erhalten = all(
    all(mask & (1 << int(value)) for mask, value in zip(d, g.values(n)))
    for n in treffer
)
assert 2083236893 in treffer and werte_erhalten
assert all(n not in ausgeschlossen for n in treffer)
print('Genesis, Gruppe %d..%d | Graph %d Knoten | E1 %s nach %d Durchlaeufen, %.1f s' % (gruppe[0], gruppe[-1], len(g.nodes), status, sweeps, time.perf_counter() - t))
print('Noncebits abgeleitet: %d | ausgeschlossen: %d von 256 | Orakel-Treffer: %s | Treffer erhalten: %s' % (len(fest), len(ausgeschlossen), treffer, werte_erhalten))
