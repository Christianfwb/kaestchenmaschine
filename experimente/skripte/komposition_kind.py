#!/usr/bin/env python3
"""KOMPOSITIONSTEST – KINDPROZESS (Fable, 2026-10-22). python -I komposition_kind.py <K1|K2|K3|K4> <ausgabe.json>
K1 Einheit: ROWS/COLS/TRANS-Tabellen und komponiere() gegen die Definition (Brute Force) – vollstaendig fuer kleine Groessen, feste Fallzahl mit Seed fuer 4x4.
K2 Gleichheit: ziffern_komp.e4 gegen ziffern_sha.e4 auf Mini-Netzen (w=4/8, add/xor/rot/ch/maj/neg/alias, x+x, Konstanten, Teil-/leere/volle Domaenen),
   je mit Paarlimit 5000 (unbegrenzt) und 12 (Grenze): Status, Enddomaenen UND alle kanonischen Paare muessen gleich sein; OPEN-Faelle getrennt gezaehlt.
K3 Soundness bei TEILWEISE freien Domaenen: zufaellige Gesamtloesung bleibt in allen Domaenen und Paaren; abschliessende E3-Nachpruefung aendert nichts.
K4 SHA-Netz (F2 Genesis, U-voll, nur E3 + Adapter, kein E4): Nonce-Domaenen teilweise frei um den bekannten Zeugen; Zeuge bleibt in allen Domaenen;
   abgeleitete NonceZIFFERN und NonceBITS getrennt; dazu F1 Wurzel (E3) Ziffern/Bits. Kein Suchlauf."""
import sys, json, time, random, itertools, resource, pathlib, platform, struct
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
from ziffern import Netz, TABELLEN, GROESSEN
import ziffern_sha as ZS, ziffern_komp as ZK, bausteine as BS, sha_ziffern as SZ, pruefung as P
PHASE, AUS = sys.argv[1], sys.argv[2]; T0 = time.perf_counter()
ERG = dict(phase=PHASE, python=platform.python_version(), rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU, reines Python', schritte=[])
def peak(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
def fort(t): sys.stderr.write('\r' + PHASE + ' ' + t[:100].ljust(100)); sys.stderr.flush()
def schritt(name, **k): k.update(name=name, t_s=round(time.perf_counter() - T0, 2), peak_mib=round(peak(), 1)); ERG['schritte'].append(k); return k
def ende(status):
    ERG['status'] = status; ERG['gesamt_s'] = round(time.perf_counter() - T0, 2); ERG['peak_mib_kind'] = round(peak(), 1)
    (HERE / AUS).write_text(json.dumps(ERG, indent=1, default=str)); fort('fertig ' + status); sys.stderr.write('\n'); sys.exit(0 if status == 'OK' else 2)

def brute_kompos(mxy, myz, dx, dy, dz, gx, gy, gz):
    m = 0
    for vx in range(gx):
        for vz in range(gz):
            if dx >> vx & 1 and dz >> vz & 1 and any(dy >> vy & 1 and (mxy is None or mxy >> (vx * gy + vy) & 1) and (myz is None or myz >> (vy * gz + vz) & 1) for vy in range(gy)):
                m |= 1 << (vx * gz + vz)
    return m

def k1():
    rnd = random.Random(20261022); f = 0; c = 0
    for gx, gy in itertools.product((2, 4), repeat=2):
        rows, cols, trans = ZK.tabellen(gx, gy)
        for m in range(1 << (gx * gy)):
            c += 1
            r = [sum(1 << vy for vy in range(gy) if m >> (vx * gy + vy) & 1) for vx in range(gx)]
            cc = [sum(1 << vx for vx in range(gx) if m >> (vx * gy + vy) & 1) for vy in range(gy)]
            t = sum(1 << (vy * gx + vx) for vx in range(gx) for vy in range(gy) if m >> (vx * gy + vy) & 1)
            if rows[m] != tuple(r) or cols[m] != tuple(cc) or trans[m] != t: f += 1
    schritt('K1 Tabellen ROWS/COLS/TRANS alle Masken (2x2,2x4,4x2,4x4)', faelle=c, fehler=f)
    f = 0; c = 0; plan = {}
    for gx, gy, gz in itertools.product((2, 4), repeat=3):
        nx = 1 << (gx * gy); nz = 1 << (gy * gz); doms = list(itertools.product(range(1 << gx), range(1 << gy), range(1 << gz)))
        if nx * nz <= 256 * 256 // 4:   # vollstaendig: alle Maskenpaare x alle Domaenen (nur kleine Groessen)
            faelle = [(a, b) for a in range(nx) for b in range(nz)]; art = 'vollstaendig'
        else:
            rand = [0, nx - 1] ; randz = [0, nz - 1]
            eins_x = [sum(1 << (v * gy + v) for v in range(min(gx, gy)))]; eins_z = [sum(1 << (v * gz + v) for v in range(min(gy, gz)))]
            faelle = [(a, b) for a in rand + eins_x for b in randz + eins_z] + [(rnd.getrandbits(gx * gy), rnd.getrandbits(gy * gz)) for _ in range(3000)]
            faelle += [(None, rnd.getrandbits(gy * gz)) for _ in range(200)] + [(rnd.getrandbits(gx * gy), None) for _ in range(200)]
            art = 'Rand + 3000 Zufall (Seed) + 400 universell'
        plan['%dx%dx%d' % (gx, gy, gz)] = dict(art=art, maskenpaare=len(faelle), domaenen=len(doms))
        for a, b in faelle:
            for dx, dy, dz in (doms if len(faelle) * len(doms) <= 3000000 else rnd.sample(doms, 40)):
                c += 1
                zx = None if a is None else ZK.tabellen(gx, gy)[0][a]; zy = None if b is None else ZK.tabellen(gy, gz)[0][b]
                if ZK.komponiere(zx, zy, dx, dy, dz, gx, gy, gz) != brute_kompos(a, b, dx, dy, dz, gx, gy, gz): f += 1
        fort('K1 %dx%dx%d' % (gx, gy, gz))
    schritt('K1 komponiere() gegen Definition', faelle=c, fehler=f, plan=plan)
    ende('OK' if all(s['fehler'] == 0 for s in ERG['schritte']) else 'FEHLER')

def mininetz(seed, w):
    r = random.Random(seed); N = Netz(w); x = N.wort('x'); y = N.wort('y'); ws = [x, y]; eing = list(x) + list(y)
    for i in range(r.randint(2, 5)):
        a = r.choice(ws); b = r.choice(ws); art = r.choice(['add', 'xor', 'rot', 'ch', 'maj', 'neg', 'addself', 'konst', 'alias'])
        if art == 'add': w_ = N.add(a, b, 'a%d' % i)
        elif art == 'addself': w_ = N.add(a, a, 's%d' % i)
        elif art == 'xor': w_ = N.xor(a, b, 'x%d' % i)
        elif art == 'rot': w_ = BS.rot(N, a, r.randrange(1, w), 'r%d' % i)
        elif art == 'ch': w_ = BS.ch(N, a, b, r.choice(ws), 'c%d' % i)
        elif art == 'maj': w_ = BS.maj(N, a, b, r.choice(ws), 'm%d' % i)
        elif art == 'neg': w_ = N.neg(a, 'n%d' % i)
        elif art == 'konst': w_ = N.add(a, N.konst(r.getrandbits(w), 'k%d' % i), 'k%d' % i)
        else: w_ = N.wort('al%d' % i); N.gleich(a, w_); w_ = [N.kanon(v) for v in w_]
        ws.append(w_)
    ws = [[N.kanon(v) for v in ww] for ww in ws]; eing = [N.kanon(v) for v in eing]
    return N, eing, ws
def zufallsdomaenen(N, r, loesung=None, p_frei=0.5):
    dom = list(N.dom)
    for v in range(len(dom)):
        g = N.groesse[v]
        if loesung is not None:
            m = 1 << loesung[v]
            if r.random() < p_frei: m |= r.getrandbits(g)
            dom[v] &= m
        else:
            if r.random() < 0.3: dom[v] &= r.getrandbits(g)       # auch leer moeglich
    return dom
def k2():
    f = 0; c = 0; off = 0; staende = {}; rnd = random.Random(5)
    for seed in range(160):
        N, eing, ws = mininetz(seed, 4 if seed % 2 else 8)
        for limit in (5000, 12):
            dom = zufallsdomaenen(N, rnd); c += 1
            a = ZS.e4(N, dom, max_paare=limit); b = ZK.e4(N, dom, max_paare=limit)
            staende[a[0]] = staende.get(a[0], 0) + 1
            if a[0] != b[0] or a[1] != b[1] or a[2] != b[2]: f += 1
            if a[0] in ('OPEN', 'OPEN_PAARGRENZE'): off += 1
        if seed % 20 == 0: fort('K2 Netz %d' % seed)
    schritt('K2 Gleichheit ziffern_komp.e4 == ziffern_sha.e4 (Status, Domaenen, alle Paare)', faelle=c, fehler=f, offene_faelle_gezaehlt=off, stati=staende)
    ende('OK' if f == 0 else 'FEHLER')
def k3():
    f = 0; c = 0; nf = 0; rnd = random.Random(9); stati = {}
    for seed in range(200):
        N, eing, ws = mininetz(1000 + seed, 4 if seed % 2 else 8); dom = list(N.dom)
        for v in eing: dom[v] &= 1 << rnd.randrange(N.groesse[v])
        st, dom, _, _ = ZS.e3(N, dom)
        if st != 'FIXPUNKT' or any(m & (m - 1) for m in dom): continue        # keine volle Loesung bestimmbar -> Netz ueberspringen
        loes = [m.bit_length() - 1 for m in dom]
        dom2 = zufallsdomaenen(N, rnd, loesung=loes, p_frei=0.6); c += 1
        st, d3, paare, inf = ZK.e4(N, dom2, max_paare=5000, nachpruefung=True); stati[st] = stati.get(st, 0) + 1
        if st == 'WIDERSPRUCH' or any(not (d3[v] >> loes[v]) & 1 for v in range(len(d3))): f += 1
        for (x, y), m in paare.items():
            if not m >> (loes[x] * N.groesse[y] + loes[y]) & 1: f += 1; break
        if inf.get('nachpruefung_e3', {}).get('geaendert'): nf += 1
    schritt('K3 Soundness teilweise freie Domaenen + E3-Nachpruefung', faelle=c, fehler_zeuge_verloren=f, nachpruefung_e3_geaendert=nf, stati=stati)
    ende('OK' if f == 0 and nf == 0 else 'FEHLER')
def k4():
    F = json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle']; rnd = random.Random(3)
    for Fd in F:
        h76 = bytes.fromhex(Fd['header_hex_ohne_nonce']); T = int(Fd['target_hex'], 16); base = Fd['basis_nonce']; bits = Fd['freie_nonce_bits']
        N, ops, out, eing, le = SZ.baue_ziffernnetz(h76, base, bits, T, 'voll'); g, inputs, blog, bout, root = SZ.baue_bitgraph(h76, base, bits, T)
        frei = [v for v in eing if N.dom[v] == 15]
        konf = []
        if Fd['referenz_treffer']:
            z = Fd['referenz_treffer'][0]; w3 = struct.unpack('>16I', P.padded(h76 + z.to_bytes(4, 'little'))[64:])[3]; zz = [(w3 >> (2 * j)) & 3 for j in range(12, 16)]
            konf = [('zeuge_plus_zufall', [1 << zz[i] | rnd.getrandbits(4) for i in range(4)]), ('zeuge_nur_bits', [1 << zz[i] | 1 << (zz[i] ^ 1) for i in range(4)]), ('wurzel', [15] * 4)]
        else: konf = [('wurzel', [15] * 4)]
        for name, masken in konf:
            dom = list(N.dom); dom[le] &= 2
            for v, m in zip(frei, masken): dom[v] = m
            t = time.perf_counter(); st, d3, _, inf = ZS.e3(N, dom, max_runden=60); t3 = time.perf_counter() - t
            ziff = sum(1 for v in frei if d3[v] & (d3[v] - 1) == 0 and dom[v] & (dom[v] - 1)); bitsfest = 0; bits_vorher = 0
            for v in frei:
                b0, b1 = SZ.ziffer_zu_bits(d3[v]); a0, a1 = SZ.ziffer_zu_bits(dom[v])
                bitsfest += (b0 in (1, 2)) + (b1 in (1, 2)); bits_vorher += (a0 in (1, 2)) + (a1 in (1, 2))
            zeuge_ok = None
            if Fd['referenz_treffer']: zeuge_ok = st != 'WIDERSPRUCH' and all(d3[v] >> zz[i] & 1 for i, v in enumerate(frei))
            # Adapter-Weg: E1 mit denselben Teildomaenen auf den Noncebits, dann Bits -> Ziffern schneiden, E3, Ziffern -> Bits schneiden
            d = [3] * len(g.nodes); d[0] = 1; d[1] = 2
            for i, node in enumerate(inputs):
                j = SZ.nonce_wortbit(bits[i]) // 2; bb = SZ.nonce_wortbit(bits[i]) % 2; m = masken[frei.index(eing[j])]
                d[node] = SZ.ziffer_zu_bits(m)[bb]
            SZ.dom_schneiden(d, root, 2); import e1_bit as E1
            st1, sw = E1.e1_lauf(g, d)
            dom2 = list(dom)
            for j, v in enumerate(eing):
                wb = bout['H1_words'][3]; dom2[v] &= SZ.bits_zu_ziffern(SZ.dom_von(d, wb[2 * j]), SZ.dom_von(d, wb[2 * j + 1]))
            st2, d4, _, _ = ZS.e3(N, dom2, max_runden=60)
            zeuge_ok2 = None
            if Fd['referenz_treffer']: zeuge_ok2 = st1 != 'WIDERSPRUCH' and st2 != 'WIDERSPRUCH' and all(d4[v] >> zz[i] & 1 for i, v in enumerate(frei)) and all(SZ.dom_von(d, node) >> ((z >> bits[i]) & 1) & 1 for i, node in enumerate(inputs))
            schritt('K4 %s %s' % (Fd['name'], name), masken_nonceziffern=masken, E3_status=st, E3_runden=inf['runden'], E3_s=round(t3, 2), nonceziffern_neu_fest=ziff,
                    noncebits_fest_vorher=bits_vorher, noncebits_fest_nachher=bitsfest, zeuge_in_allen_domaenen=zeuge_ok,
                    adapterweg=dict(E1_status=st1, E1_sweeps=sw, E3_status=st2, zeuge_erhalten=zeuge_ok2, noncebits_fest_E1=sum(1 for node in inputs if SZ.dom_von(d, node) in (1, 2))))
            if zeuge_ok is False or zeuge_ok2 is False: ende('FEHLER')
            fort('K4 %s %s' % (Fd['name'], name))
    ende('OK')
{'K1': k1, 'K2': k2, 'K3': k3, 'K4': k4}[PHASE]()
