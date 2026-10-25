#!/usr/bin/env python3
"""KONTROLLE (Fable, 2026-10-23): Ist die Kante bei 16->17 Runden die Nachrichtenerweiterung oder die Tiefe?
Modell wie runden_kind, aber W[16..R-1] = KONSTANTE (0x5a5a5a5a + i) statt Erweiterung. Alles andere gleich (R Runden, Feed-forward, Padding).
Nur E1 bis Fixpunkt (E1 hat bis 16 Runden alle Faelle allein entschieden). Orakel ueber alle 256 danach. CPU, Kopien, Sekunden."""
import sys, json, struct, hashlib, time, pathlib
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ, pruefung as P
from e1_bit import e1_lauf
def compress_k(state, words, op, trace=None, runden=64):
    w = list(words)
    for i in range(16, runden): w.append(op.const((0x5a5a5a5a + i) & 0xffffffff))
    a,b,c,d,e,f,g,h = state
    for i in range(runden):
        s1 = op.xor(op.rot(e,6),op.rot(e,11),op.rot(e,25)); s0 = op.xor(op.rot(a,2),op.rot(a,13),op.rot(a,22))
        t1 = op.add(h,s1,op.ch(e,f,g),op.const(P.K[i]),w[i]); t2 = op.add(s0,op.maj(a,b,c))
        a,b,c,d,e,f,g,h = op.add(t1,t2),a,b,c,op.add(d,t1),e,f,g
        if trace is not None: trace.append((a,b,c,d,e,f,g,h))
    return tuple(op.add(x,y) for x,y in zip(state,(a,b,c,d,e,f,g,h)))
SZ._comp = lambda R: (lambda state, words, op, trace=None: compress_k(state, words, op, trace, R))
F = json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle'][0]; h76 = bytes.fromhex(F['header_hex_ohne_nonce'])
def ref(nonce, R):
    p = P.padded(h76 + nonce.to_bytes(4, 'little'))
    mid = compress_k(P.IV, struct.unpack('>16I', p[:64]), P.IntegerOps, runden=R); d1 = compress_k(mid, struct.unpack('>16I', p[64:]), P.IntegerOps, runden=R)
    return compress_k(P.IV, list(d1) + [0x80000000] + [0] * 6 + [256], P.IntegerOps, runden=R)
ERG = []
for R in [int(x) for x in sys.argv[1:]] or (16, 17, 18, 20, 24, 32):
    k = int.from_bytes(hashlib.sha256(b'KONTROLLE_ERWEITERUNG_R%d' % R).digest(), 'little') % 256; ziel = ref(k, R); hstar = int.from_bytes(struct.pack('>8I', *ziel), 'little')
    t = time.perf_counter(); g, inputs, _, out, _ = SZ.baue_bitgraph(h76, 0, list(range(8)), 0, runden=R, mit_ziel=False)
    d = [3] * len(g.nodes); d[0] = 1; d[1] = 2
    for i in range(256): SZ.dom_schneiden(d, out['digest2'][(i // 8) // 4][8 * (3 - (i // 8) % 4) + i % 8], 1 << ((hstar >> i) & 1))
    st, sw = e1_lauf(g, d, max_sweeps=10 ** 6); nb = {i: SZ.dom_von(d, x) >> 1 for i, x in enumerate(inputs) if SZ.dom_von(d, x) in (1, 2)}
    treffer = [n for n in range(256) if ref(n, R) == ziel]; abgeleitet = sum(v << i for i, v in nb.items()) if len(nb) == 8 else None
    aus = [n for n in range(256) if any(((n >> i) & 1) != v for i, v in nb.items())]
    assert k in treffer and not any(n in aus for n in treffer), 'FEHLER falscher Ausschluss'
    z = dict(runden=R, knoten=len(g.nodes), e1=st, sweeps=sw, s=round(time.perf_counter() - t, 2), noncebits=len(nb), abgeleitet=abgeleitet, treffer=treffer, kontrolle=k,
             ausgang='TREFFER_ABGELEITET' if abgeleitet is not None and treffer == [abgeleitet] else 'OFFEN'); ERG.append(z)
    print('R%2d ohne Erweiterung: Graph %6d | E1 %s %3d Durchl. %6.2f s | Noncebits %d/8 -> %s | Treffer %s | %s' % (R, z['knoten'], st, sw, z['s'], len(nb), abgeleitet, treffer, z['ausgang']), flush=True)
(HERE / 'ERGEBNIS_ERWEITERUNG_KONTROLLE.json').write_text(json.dumps(dict(beschreibung=__doc__, laeufe=ERG), indent=1))
