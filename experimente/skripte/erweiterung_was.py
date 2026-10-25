#!/usr/bin/env python3
"""WAS in der Erweiterung reisst? Variante A 'ohne Drehen': sigma0/sigma1 = Identitaet, Additionen echt.
Variante B 'ohne Addieren': sigma echt, die vier Summanden per XOR statt + verknuepft. Beide Anwendungen erweitert. E1 bis Fixpunkt, Orakel danach."""
import sys, json, struct, hashlib, time, pathlib
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ, pruefung as P
from e1_bit import e1_lauf
def comp(state, words, op, trace, R, var):
    w = list(words)
    for i in range(16, R):
        if var == 'ohne Drehen': s0, s1 = w[i-15], w[i-2]
        else:
            s0 = op.xor(op.rot(w[i-15],7),op.rot(w[i-15],18),op.shr(w[i-15],3)); s1 = op.xor(op.rot(w[i-2],17),op.rot(w[i-2],19),op.shr(w[i-2],10))
        if var == 'ohne Addieren': w.append(op.xor(op.xor(w[i-16], s0, w[i-7]), s1, op.const(0)))
        else: w.append(op.add(w[i-16], s0, w[i-7], s1))
    a,b,c,d,e,f,g,h = state
    for i in range(R):
        s1 = op.xor(op.rot(e,6),op.rot(e,11),op.rot(e,25)); s0 = op.xor(op.rot(a,2),op.rot(a,13),op.rot(a,22))
        t1 = op.add(h,s1,op.ch(e,f,g),op.const(P.K[i]),w[i]); t2 = op.add(s0,op.maj(a,b,c))
        a,b,c,d,e,f,g,h = op.add(t1,t2),a,b,c,op.add(d,t1),e,f,g
        if trace is not None: trace.append((a,b,c,d,e,f,g,h))
    return tuple(op.add(x,y) for x,y in zip(state,(a,b,c,d,e,f,g,h)))
F = json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle'][0]; h76 = bytes.fromhex(F['header_hex_ohne_nonce'])
ERG = []
for var in ('ohne Drehen', 'ohne Addieren'):
    for R in (17, 18, 20, 24, 32):
        SZ._comp = lambda R_, v=var: (lambda state, words, op, trace=None: comp(state, words, op, trace, R_, v))
        def ref(nonce):
            p = P.padded(h76 + nonce.to_bytes(4, 'little'))
            mid = comp(P.IV, struct.unpack('>16I', p[:64]), P.IntegerOps, None, R, var); d1 = comp(mid, struct.unpack('>16I', p[64:]), P.IntegerOps, None, R, var)
            return comp(P.IV, list(d1) + [0x80000000] + [0] * 6 + [256], P.IntegerOps, None, R, var)
        k = int.from_bytes(hashlib.sha256(('WAS_%s_R%d' % (var, R)).encode()).digest(), 'little') % 256; ziel = ref(k); hstar = int.from_bytes(struct.pack('>8I', *ziel), 'little')
        t = time.perf_counter(); g, inputs, _, out, _ = SZ.baue_bitgraph(h76, 0, list(range(8)), 0, runden=R, mit_ziel=False)
        d = [3] * len(g.nodes); d[0] = 1; d[1] = 2
        for i in range(256): SZ.dom_schneiden(d, out['digest2'][(i // 8) // 4][8 * (3 - (i // 8) % 4) + i % 8], 1 << ((hstar >> i) & 1))
        st, sw = e1_lauf(g, d, max_sweeps=10 ** 6); nb = {i: SZ.dom_von(d, x) >> 1 for i, x in enumerate(inputs) if SZ.dom_von(d, x) in (1, 2)}
        treffer = [n for n in range(256) if ref(n) == ziel]; abgeleitet = sum(v << i for i, v in nb.items()) if len(nb) == 8 else None
        aus = [n for n in range(256) if any(((n >> i) & 1) != v for i, v in nb.items())]; assert k in treffer and not any(n in aus for n in treffer)
        z = dict(variante=var, runden=R, graph=len(g.nodes), e1=st, sweeps=sw, s=round(time.perf_counter() - t, 1), noncebits=len(nb), abgeleitet=abgeleitet, treffer=treffer, ausgang='TREFFER_ABGELEITET' if abgeleitet is not None and treffer == [abgeleitet] else 'OFFEN'); ERG.append(z)
        print('%-14s R%2d | Graph %6d | E1 %s %3d | %5.1f s | Noncebits %d/8 | Treffer %s | %s' % (var, R, len(g.nodes), st, sw, z['s'], len(nb), treffer, z['ausgang']), flush=True)
(HERE / 'ERGEBNIS_ERWEITERUNG_WAS.json').write_text(json.dumps(dict(beschreibung=__doc__, laeufe=ERG), indent=1))
