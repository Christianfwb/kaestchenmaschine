#!/usr/bin/env python3
"""REGRESSION PRUEFSPEICHER (Fable, 2026-10-22), klein, < 120 s / 400 MiB. python -I pruefspeicher_test.py
T1 Streaming-Zeugenpruefung (PaarSpeicher.zeuge_ok) gegen dict-Pruefung (als_dict) auf Mini-Netzen: korrekter Zeuge, absichtlich verbotener
   Zifferwert, absichtlich verbotene Paarbelegung (Maske manipuliert), kanonische Schluessel, Groessen 2/4 (Uebertraege). Gleiche Entscheidung.
T2 Lebenszyklus: Austauschschleife (austausch.py) auf einem kleinen gekoppelten Bit/Ziffern-Fall (zwei SHA-artige Runden, 8 freie Eingangsbits,
   Zielkette auf a2), freigeben=False (alter Stand) gegen freigeben=True: Status, Enddomaenen (Bits und Ziffern) und alle Paarmasken gleich."""
import sys, json, random, time, resource, pathlib
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import ziffern_array as ZA, ziffern_sha as ZS, sha_ziffern as SZ, gatter as G
from ziffern import Netz, TABELLEN
from mininetze import mininetz, zufallsdomaenen
from austausch import austausch
T0 = time.perf_counter(); rnd = random.Random(21); out = {}
# ---- T1 ----
def dict_pruefung(PS, werte, gr):
    return all(m >> (werte[x] * gr[y] + werte[y]) & 1 for (x, y), m in PS.als_dict().items())
c = f = 0; arten = dict(korrekt=0, wert_verboten=0, paar_verboten=0)
for seed in range(120):
    N, eing, ws = mininetz(3000 + seed, 4 if seed % 2 else 8); dom = list(N.dom)
    for v in eing: dom[v] &= 1 << rnd.randrange(N.groesse[v])
    st, dom, _, _ = ZS.e3(N, dom)
    if st != 'FIXPUNKT' or any(m & (m - 1) for m in dom): continue
    loes = [m.bit_length() - 1 for m in dom]
    st, d3, PS, inf = ZA.e4(N, zufallsdomaenen(N, rnd, loesung=loes, p_frei=0.7), max_paare=5000)
    if st != 'FIXPUNKT' or PS is None or len(PS) == 0: continue
    gr = N.groesse
    assert all(x < y for (x, y) in PS.als_dict())                            # kanonische Schluessel
    a, _ = PS.zeuge_ok(loes); b = dict_pruefung(PS, loes, gr); c += 1; f += (a != b) or (a is not True); arten['korrekt'] += 1
    # verbotener Wert: eine Variable eines Paares auf einen Wert setzen, der in diesem Paar verboten ist (Maske hat ein 0-Bit)
    for (x, y), m in PS.als_dict().items():
        voll = (1 << (gr[x] * gr[y])) - 1
        if m != voll:
            for vx in range(gr[x]):
                for vy in range(gr[y]):
                    if not m >> (vx * gr[y] + vy) & 1:
                        w2 = list(loes); w2[x] = vx; w2[y] = vy
                        a, _ = PS.zeuge_ok(w2); b = dict_pruefung(PS, w2, gr); c += 1; f += (a != b) or (a is not False); arten['wert_verboten'] += 1
                        break
                else: continue
                break
            break
    # verbotene Paarbelegung: Maske eines Paares beim Zeugenbit manipulieren (nur im Test, Kopie), beide muessen False liefern
    i = rnd.randrange(len(PS)); x, y = divmod(PS.keys[i], PS.NV); alt = PS.masks[i]; PS.masks[i] = alt & ~(1 << (loes[x] * gr[y] + loes[y]))
    a, p = PS.zeuge_ok(loes); b = dict_pruefung(PS, loes, gr); c += 1; f += (a != b) or (a is not False) or (p != (x, y)); arten['paar_verboten'] += 1
    PS.masks[i] = alt
out['T1'] = dict(faelle=c, fehler=f, arten=arten, groessen_2_und_4=True)
# ---- T2: kleiner gekoppelter Fall ----
def mini_kopplung(T, freie_bits=8, runden=2):
    g = G.Graph(); bl = SZ.BitLog(g); bl.phase = 'M'; N = Netz(32); zo = SZ.ZiffernOps(N); zo.phase = 'M'
    K = [0x428a2f98, 0x71374491]; reg = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
    w0 = 0x12345600; wb = list(G.Ops.const(w0)); inputs = []
    for i in range(freie_bits):
        node = g.input(i); inputs.append(node); wb[i] = node
    wz = N.wort('M_w0')
    for j in range(16):
        if j >= freie_bits // 2: N.fest(wz[j], (w0 >> (2 * j)) & 3)
    def rechnen(ops, wort):
        a, b, c_, d, e, f_, gg, h = [ops.const(x) for x in reg]
        for i in range(runden):
            s1 = ops.xor(ops.rot(e, 6), ops.rot(e, 11), ops.rot(e, 25)); s0 = ops.xor(ops.rot(a, 2), ops.rot(a, 13), ops.rot(a, 22))
            t1 = ops.add(h, s1, ops.ch(e, f_, gg), ops.const(K[i]), wort); t2 = ops.add(s0, ops.maj(a, b, c_))
            a, b, c_, d, e, f_, gg, h = ops.add(t1, t2), a, b, c_, ops.add(d, t1), e, f_, gg
        return a
    ab = rechnen(bl, tuple(wb)); az = rechnen(zo, wz)
    le = 1
    for i, x in enumerate(ab):
        if T >> i & 1: le = G.inv(g.gate('and', x, G.inv(le)))
        else: le = g.gate('and', G.inv(x), le)
    lz = N.var('le0', 2); N.fest(lz, 1)
    for k in range(16):
        t = (T >> (2 * k)) & 3; nle = N.var('le%d' % (k + 1), 2); N.bez.append(('LE%d' % t, [az[k], lz, nle])); lz = nle
    zu = SZ.wortzuordnung(bl, zo); zu.append(('M_w0', tuple(wb), list(wz)))
    return g, inputs, le, N, zu, lz
erg2 = {}
for frei in (False, True):
    g, inputs, root, N, zu, lz = mini_kopplung(T=0x0000ffff)
    d = [3] * len(g.nodes); d[0] = 1; d[1] = 2; SZ.dom_schneiden(d, root, 2)
    from e1_bit import e1_lauf
    e1_lauf(g, d); zd = list(N.dom); zd[lz] &= 2
    R = austausch(g, inputs, root, d, N, zu, zd, ZA.e4, 200000, frei)
    erg2[frei] = dict(status=R['status'], d=R['d'], zd=R['zd'], paare=R['paare'].als_dict() if R['paare'] is not None else None, runden=R['stat']['austausch'], knoten=len(g.nodes), vars=len(N.dom))
gleich = all(erg2[False][k] == erg2[True][k] for k in ('status', 'd', 'zd', 'paare', 'runden'))
out['T2'] = dict(status=erg2[True]['status'], austauschrunden=erg2[True]['runden'], bitknoten=erg2[True]['knoten'], ziffernvariablen=erg2[True]['vars'],
                 paare=len(erg2[True]['paare'] or {}), gleich_status_domaenen_paare=gleich,
                 bits_fest=sum(1 for x in erg2[True]['d'][2:] if x in (1, 2)), ziffern_fest=sum(1 for m in erg2[True]['zd'] if m & (m - 1) == 0))
out['status'] = 'OK' if f == 0 and gleich and c > 0 else 'FEHLER'; out['gesamt_s'] = round(time.perf_counter() - T0, 1); out['peak_mib'] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
(HERE / 'ERGEBNIS_PRUEFSPEICHER_TEST.json').write_text(json.dumps(out, indent=1)); print(json.dumps(out, indent=1))
