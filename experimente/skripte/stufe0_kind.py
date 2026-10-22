#!/usr/bin/env python3
"""STUFE 0 – KINDPROZESS JE PHASE (Fable, 2026-10-22). Aufruf: python -I stufe0_kind.py <PHASE> <ausgabe.json>
Phasen: P0 Bausteine/Komparator/Adapter, P1 Aufbau+Zuordnung, P2F1/P2F2 Digestpruefung aller 256 Nonces je Fall (freier Zielausgang),
P3 Fixpunkt-Stichproben E1/E3 (freier und gesetzter Zielausgang), P4 Grundpaarzaehlung an der Wurzel (nur E3, KEIN E4).
Kein Suchlauf. Referenz (hashlib, Integerrechnung) nur als Orakel; keine Referenzwerte werden in Netze eingespeist.
Elternprozess (lauf_stufe0.py) ueberwacht Zeit/RAM extern; hier zusaetzlich Zeiten je Schritt. Fortschritt: eine ueberschreibende Zeile."""
import sys, os, json, time, struct, hashlib, random, resource, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ, ziffern_sha as Z, gatter as G, pruefung as P, bausteine as BS
from ziffern import Netz, TABELLEN
PHASE, AUS = sys.argv[1], sys.argv[2]
FAELLE = json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle']
T0 = time.perf_counter(); ERG = dict(phase=PHASE, python=platform.python_version(), rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU, reines Python', schritte=[])
def peak(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
def fort(txt): sys.stderr.write('\r' + PHASE + ' ' + txt[:110].ljust(110)); sys.stderr.flush()
def schritt(name, **k):
    k.update(name=name, t_s=round(time.perf_counter() - T0, 2), peak_mib=round(peak(), 1)); ERG['schritte'].append(k); return k
def fehler(name, **k):
    schritt(name, FEHLER=True, **k); ERG['status'] = 'FEHLER'; ERG['fehler'] = dict(name=name, **k)
    (HERE / AUS).write_text(json.dumps(ERG, indent=1, default=str)); fort('FEHLER ' + name); sys.exit(2)
def fall_daten(F):
    return bytes.fromhex(F['header_hex_ohne_nonce']), int(F['target_hex'], 16), F['basis_nonce'], F['freie_nonce_bits']
def sha256d(h76, n): return hashlib.sha256(hashlib.sha256(h76 + n.to_bytes(4, 'little')).digest()).digest()
def ziffern(x, D): return [(x >> (2 * j)) & 3 for j in range(D)]
def wert(dom, ids):
    if any(dom[v] & (dom[v] - 1) for v in ids) or any(dom[v] == 0 for v in ids): return None
    return sum((dom[v].bit_length() - 1) << (2 * j) for j, v in enumerate(ids))

# ---------- E1 auf dem Gatter-Graphen (aus lauf_m4.e1_lauf) ----------
TAB = {}
for opn in ('and', 'xor'):
    for A in range(4):
        for B in range(4):
            for Zm in range(4):
                sa = sb = sz = 0
                for u in (0, 1):
                    for v in (0, 1):
                        out = (u ^ v) if opn == 'xor' else (u & v)
                        if (A >> u) & 1 and (B >> v) & 1 and (Zm >> out) & 1: sa |= 1 << u; sb |= 1 << v; sz |= 1 << out
                TAB[(opn, A, B, Zm)] = (sa, sb, sz)
def e1_lauf(g, d, max_sweeps=12):
    n = len(g.nodes)
    def get(x): return (((d[-x] & 1) << 1) | ((d[-x] & 2) >> 1)) if x < 0 else d[x]
    def assign(x, v):
        if x < 0: x = -x; v = ((v & 1) << 1) | ((v & 2) >> 1)
        old = d[x]; d[x] &= v; return old != d[x]
    sweeps = 0
    while True:
        sweeps += 1; changed = False
        for order in (range(2, n), range(n - 1, 1, -1)):
            for i in order:
                nd = g.nodes[i]
                if nd[0] == 'input': continue
                opn, a, b = nd; A, B, Zm = get(a), get(b), get(i); sa, sb, sz = TAB[(opn, A, B, Zm)]
                if not A or not B or not Zm or not sa: return 'WIDERSPRUCH', sweeps
                changed |= assign(a, sa); changed |= assign(b, sb); changed |= assign(i, sz)
        if not changed: return 'FIXPUNKT', sweeps
        if sweeps >= max_sweeps: return 'OFFEN', sweeps
def e1_start(g, inputs, base, mask):
    d = [3] * len(g.nodes); d[0] = 1; d[1] = 2
    for i, node in enumerate(inputs):
        if not (mask >> i) & 1: d[node] = 1 << ((base >> i) & 1)
    return d
def bits_parallel(g, inputs, K=256):
    """Bitparallele Funktionsauswertung: Knotenwert = Python-int mit Bit n = Wert bei Eingabebelegung n (n = 0..K-1)."""
    M = (1 << K) - 1; vals = [0, M]
    inp = {node: sum(1 << n for n in range(K) if (n >> i) & 1) for i, node in enumerate(inputs)}
    def read(x): return (M ^ vals[-x]) if x < 0 else vals[x]
    for i in range(2, len(g.nodes)):
        nd = g.nodes[i]
        if nd[0] == 'input': vals.append(inp[i])
        elif nd[0] == 'and': vals.append(read(nd[1]) & read(nd[2]))
        else: vals.append(read(nd[1]) ^ read(nd[2]))
    return vals, read
def wort_aus_parallel(read, bits, n): return sum(((read(b) >> n) & 1) << i for i, b in enumerate(bits))

# ======================= P0 =======================
def p0():
    zaehl = {}
    # shr/rot/xor/ch/maj/add ueber ZiffernOps: w=8 erschoepfend (shr/rot alle n), w=32 Zufall
    def pruefe_op(w, art, n, xs):
        N = Netz(w); ops = SZ.ZiffernOps(N); ops.phase = 'T'; D = N.D; M = (1 << w) - 1
        X = [N.wort('x%d' % i) for i in range(len(xs))]
        if art == 'shr': y = ops.shr(X[0], n); erw = xs[0] >> n
        elif art == 'rot': y = ops.rot(X[0], n); erw = ((xs[0] >> n) | (xs[0] << (w - n))) & M
        elif art == 'xor': y = ops.xor(*X); erw = xs[0] ^ xs[1] ^ xs[2]
        elif art == 'ch': y = ops.ch(*X); erw = ((xs[0] & xs[1]) ^ (~xs[0] & xs[2])) & M
        elif art == 'maj': y = ops.maj(*X); erw = (xs[0] & xs[1]) ^ (xs[0] & xs[2]) ^ (xs[1] & xs[2])
        elif art == 'add': y = ops.add(*X); erw = sum(xs) & M
        dom = list(N.dom)
        for word, val in zip(X, xs):
            for v, z in zip(word, ziffern(val, D)): dom[v] &= 1 << z
        st, dom, _, _ = Z.e3(N, dom)
        return st != 'WIDERSPRUCH' and wert(dom, y) == erw
    f = 0; c = 0
    for n in range(1, 8):
        for x in range(256):
            for art in ('shr', 'rot'):
                c += 1; f += not pruefe_op(8, art, n, [x])
    zaehl['w8_shr_rot_alle_n_alle_x'] = dict(faelle=c, fehler=f); fort('P0 w8 fertig')
    rnd = random.Random(20261022); f = 0; c = 0
    for _ in range(150):
        for n in (3, 10):
            c += 1; f += not pruefe_op(32, 'shr', n, [rnd.getrandbits(32)])
        for n in (2, 6, 7, 11, 13, 17, 18, 19, 22, 25):
            c += 1; f += not pruefe_op(32, 'rot', n, [rnd.getrandbits(32)])
        for art, k in (('xor', 3), ('ch', 3), ('maj', 3), ('add', 5), ('add', 2)):
            c += 1; f += not pruefe_op(32, art, 0, [rnd.getrandbits(32) for _ in range(k)])
    zaehl['w32_zufall_shr_rot_xor_ch_maj_add'] = dict(faelle=c, fehler=f); fort('P0 w32 fertig')
    # Vergleichsketten (Ziffern-LE und Bitkette) fuer beide Ziele
    for F in FAELLE:
        T = int(F['target_hex'], 16); werte = [0, T - 1, T, T + 1, (1 << 256) - 1] + [T ^ (1 << k) for k in range(256)]
        werte += [T + (1 << (8 * b)) for b in range(32)] + [max(T - (1 << (8 * b)), 0) for b in range(32)]
        werte += [rnd.getrandbits(256) for _ in range(1500)] + [rnd.getrandbits(256 - F['target_nullbits']) for _ in range(1500)]
        werte += [rnd.getrandbits(256 - F['target_nullbits'] - 8) for _ in range(500)]
        N = Netz(32); ops = SZ.ZiffernOps(N); dig = [N.wort('d%d' % i) for i in range(8)]; kette, le = ops.ziel(dig, T)
        gb, ginp, groot = SZ.bitkomparator(T); fz = fb = 0
        for v in werte:
            raw = v.to_bytes(32, 'little'); words = struct.unpack('>8I', raw); erw = int(v <= T)
            dom = list(N.dom)
            for word, val in zip(dig, words):
                for x, z in zip(word, ziffern(val, 16)): dom[x] &= 1 << z
            st, dom, _, _ = Z.e3(N, dom)
            if st == 'WIDERSPRUCH' or dom[le] != (1 << erw): fz += 1
            vals = gb.values(v)
            if int(G.read(vals, groot)) != erw: fb += 1
        zaehl['komparator_' + F['name']] = dict(werte=len(werte), fehler_ziffernkette=fz, fehler_bitkette=fb, le_beziehungen=128)
        fort('P0 Komparator ' + F['name'])
    # Adapter Bit<->Ziffer, Negation, Alias, Nonce-Rundreise
    f = 0; c = 0
    for m in range(1, 16):
        b0, b1 = SZ.ziffer_zu_bits(m); back = SZ.bits_zu_ziffern(b0, b1); c += 1
        if back & m != m: f += 1                                             # Rundreise muss Obermenge sein (Schnitt bleibt sound)
        produkt = all(((b0 >> (z & 1)) & 1 and (b1 >> (z >> 1)) & 1) <= bool(m >> z & 1) for z in range(4))
        if produkt and back != m: f += 1                                     # Produktmengen exakt
    for b0 in range(1, 4):
        for b1 in range(1, 4):
            c += 1
            if SZ.ziffer_zu_bits(SZ.bits_zu_ziffern(b0, b1)) != (b0, b1): f += 1
    for dm in range(1, 4):
        for mk in range(1, 4):
            d = [3, 3, dm]; c += 1
            if SZ.dom_von(d, -2) != {1: 2, 2: 1, 3: 3}[dm]: f += 1           # negierter Knoten: Domaene gespiegelt
            d2 = [3, 3, dm]; SZ.dom_schneiden(d2, -2, mk); c += 1
            if d2[2] != (dm & {1: 2, 2: 1, 3: 3}[mk]): f += 1
    zaehl['adapter_bit_ziffer_negation'] = dict(faelle=c, fehler=f)
    N = Netz(8); x = N.wort('x'); y = N.wort('y'); N.gleich(x, y); z = N.add([N.kanon(v) for v in y], N.konst(5, 'k'), 's'); f = 0
    for xv in range(256):
        dom = list(N.dom)
        for v, zz in zip(x, ziffern(xv, 4)): dom[N.kanon(v)] &= 1 << zz
        st, dom, _, _ = Z.e3(N, dom); f += (st == 'WIDERSPRUCH' or wert(dom, z) != (xv + 5) & 255)
    zaehl['alias_gleich'] = dict(faelle=256, fehler=f)
    for F in FAELLE:
        h76, T, base, bits = fall_daten(F); f = 0
        for n in range(256):
            nonce = (base & ~0xff) | n; w3 = struct.unpack('>16I', P.padded(h76 + nonce.to_bytes(4, 'little'))[64:])[3]
            bd = [1 << ((w3 >> i) & 1) for i in range(32)]
            zd = [SZ.bits_zu_ziffern(bd[2 * j], bd[2 * j + 1]) for j in range(16)]
            if [m.bit_length() - 1 for m in zd] != ziffern(w3, 16): f += 1
            if [SZ.ziffer_zu_bits(m) for m in zd] != [(bd[2 * j], bd[2 * j + 1]) for j in range(16)]: f += 1
            if any(((w3 >> SZ.nonce_wortbit(b)) & 1) != ((nonce >> b) & 1) for b in range(32)): f += 1   # Noncebit-Lage
        zaehl['nonce_rundreise_' + F['name']] = dict(nonces=256, fehler=f)
    ERG['zaehlung'] = zaehl; ERG['status'] = 'OK' if all(v.get('fehler', 0) == 0 and v.get('fehler_ziffernkette', 0) == 0 and v.get('fehler_bitkette', 0) == 0 for v in zaehl.values()) else 'FEHLER'
    schritt('P0 gesamt')

# ======================= P1 =======================
def aufbau(F, umfang_liste=('voll', 'lokal'), mit_ziel=True):
    h76, T, base, bits = fall_daten(F); t = time.perf_counter()
    g, inputs, blog, bout, root = SZ.baue_bitgraph(h76, base, bits, T); tb = time.perf_counter() - t
    netze = {}
    for u in umfang_liste:
        t = time.perf_counter(); N, zops, zout, eing, le = SZ.baue_ziffernnetz(h76, base, bits, T, u, mit_ziel=mit_ziel)
        netze[u] = dict(N=N, ops=zops, out=zout, eing=eing, le=le, t_s=round(time.perf_counter() - t, 2))
    return dict(g=g, inputs=inputs, blog=blog, bout=bout, root=root, t_bit_s=round(tb, 2)), netze
def p1():
    for F in FAELLE:
        h76, T, base, bits = fall_daten(F)
        t = time.perf_counter(); g0, i0, d0, le0 = G.build(base, bits, h76 + b'\0' * 4, T); t0 = time.perf_counter() - t
        B, netze = aufbau(F)
        gleich = len(g0.nodes) == len(B['g'].nodes) and le0 == B['root'] and d0 == B['bout']['digest2'] and i0 == B['inputs']
        if not gleich: fehler('P1 Bitgraph != gatter.build', fall=F['name'])
        info = dict(fall=F['name'], gatter_build_knoten=len(g0.nodes), gatter_build_s=round(t0, 2), bitgraph_knoten=len(B['g'].nodes), bitgraph_root=B['root'],
                    bitgraph_identisch_mit_gatter_build=gleich, bitgraph_s=B['t_bit_s'], protokoll_woerter=len(B['blog'].log))
        for u, Nd in netze.items():
            N = Nd['N']; from collections import Counter
            typen = Counter(typ for typ, _ in N.bez); konst = sum(1 for m in N.dom if m & (m - 1) == 0)
            zu = SZ.wortzuordnung(B['blog'], Nd['ops']) if u == 'voll' else None
            info[u] = dict(variablen=len(N.dom), ziffern=sum(1 for gsz in N.groesse if gsz == 4), uebertraege_le=sum(1 for gsz in N.groesse if gsz == 2),
                           beziehungen=len(N.bez), je_typ=dict(typen), konstante_variablen_vor_propagation=konst, aufbau_s=Nd['t_s'],
                           protokoll_woerter=len(Nd['ops'].log), zuordnung_bit_ziffer_semantisch=(len(zu) if zu else 'nur H2 (lokal), Zuordnung ueber Phase/Art/Nr'),
                           eingangsvariablen=len(Nd['eing']) if u == 'lokal' else [N.name[v] for v in Nd['eing'] if N.dom[v] == 15])
        schritt('P1 ' + F['name'], **info)
    ERG['status'] = 'OK'

# ======================= P2 =======================
def p2(F):
    h76, T, base, bits = fall_daten(F); K = 256
    B, netze = aufbau(F)
    g, inputs, blog, bout = B['g'], B['inputs'], B['blog'], B['bout']
    # Referenz: IntLog je Nonce (unabhaengig: hashlib fuer Enddigest)
    t = time.perf_counter(); refs = []; ref_dig = []; ref_le = []
    for n in range(K):
        nonce = (base & ~0xff) | n; il = SZ.IntLog(); w3 = struct.unpack('>16I', P.padded(h76 + nonce.to_bytes(4, 'little'))[64:])[3]
        o = SZ.rechenweg(il, h76, base, bits, 'voll', nonce_wort=w3)
        refs.append([w for _, _, _, w in il.log]); h = sha256d(h76, nonce)
        if struct.pack('>8I', *o['digest2']) != h: fehler('P2 IntegerOps-Digest != hashlib', nonce=nonce)
        ref_dig.append(h); ref_le.append(int(int.from_bytes(h, 'little') <= T))
    if blog.arten() != il.arten(): fehler('P2 Protokollfolge Bit != Int')
    schritt('P2 Referenz (IntLog + hashlib)', nonces=K, woerter_je_nonce=len(refs[0]), s=round(time.perf_counter() - t, 2))
    # Bitgraph: bitparallel, freier Zielausgang
    t = time.perf_counter(); vals, read = bits_parallel(g, inputs, K); fw = 0; fd = 0; fl = 0; erstes = None
    for wi, (_, _, _, bitsw) in enumerate(blog.log):
        ints = [read(b) for b in bitsw]
        for n in range(K):
            v = sum(((ints[i] >> n) & 1) << i for i in range(32))
            if v != refs[n][wi]:
                fw += 1
                if erstes is None: erstes = dict(wort=blog.log[wi][:3], nonce=(base & ~0xff) | n, netz=v, referenz=refs[n][wi])
    for n in range(K):
        dig = struct.pack('>8I', *[wort_aus_parallel(read, w, n) for w in bout['digest2']])
        if dig != ref_dig[n]: fd += 1
        if int(bool((read(B['root']) >> n) & 1)) != ref_le[n]: fl += 1
    schritt('P2 Bitgraph bitparallel, Ziel frei', nonces=K, woerter=len(blog.log), wort_fehler=fw, digest_fehler_gegen_hashlib=fd, zielvergleich_fehler=fl, erstes_gegenbeispiel=erstes, s=round(time.perf_counter() - t, 2))
    if fw or fd or fl: fehler('P2 Bitgraph', erstes=erstes)
    digest1_bits = [[wort_aus_parallel(read, w, n) for w in bout['digest1']] for n in range(K)]   # aus dem Bitgraphen (nicht Referenz) fuer U-lokal
    # Ziffernnetz voll: eine Vorwaertsrunde E3 (Ermittlung aus dem Netz), Ziel frei
    for u in ('voll', 'lokal'):
        Nd = netze[u]; N = Nd['N']; zlog = Nd['ops'].log; t = time.perf_counter(); fw = fd = fl = unbest = 0; erstes = None; runden = []
        ref_idx = [i for i, (p, _, _, _) in enumerate(zlog)] if u == 'voll' else None
        if u == 'lokal':
            # Zuordnung lokal: H2-Eintraege der Referenz (IntLog) nach (phase, art, nr)
            pos = {k: i for i, k in enumerate(il.arten())}; ref_idx = [pos[(p, a, nr)] for p, a, nr, _ in zlog]
        for n in range(K):
            dom = list(N.dom)
            if u == 'voll':
                for j, v in enumerate(Nd['eing']):
                    if dom[v] == 15: dom[v] = 1 << ((wort_aus_parallel(read, bout['H1_words'][3], n) >> (2 * j)) & 3)   # Nonce-Wort aus Bitgraph-Eingaben
            else:
                for wi, word in enumerate(Nd['eing']):
                    for j, v in enumerate(word): dom[v] = 1 << ((digest1_bits[n][wi] >> (2 * j)) & 3)
            st, dom, _, inf = Z.e3(N, dom, nur_eine_runde=True); runden.append(inf['tupelops'])
            for wi, (p, a, nr, ids) in enumerate(zlog):
                v = wert(dom, ids)
                if v is None: unbest += 1; continue
                if v != refs[n][ref_idx[wi]]:
                    fw += 1
                    if erstes is None: erstes = dict(wort=(p, a, nr), nonce=(base & ~0xff) | n, netz=v, referenz=refs[n][ref_idx[wi]])
            dig = struct.pack('>8I', *[wert(dom, w) if wert(dom, w) is not None else -1 for w in Nd['out']['digest2']]) if all(wert(dom, w) is not None for w in Nd['out']['digest2']) else None
            if dig != ref_dig[n]: fd += 1
            if dom[Nd['le']] != (1 << ref_le[n]): fl += 1
            if n % 16 == 0: fort('P2 %s %s nonce %d' % (F['name'], u, n))
        schritt('P2 Ziffernnetz %s, eine Vorwaertsrunde E3, Ziel frei' % u, nonces=K, woerter=len(zlog), wort_fehler=fw, unbestimmte_woerter=unbest,
                digest_fehler_gegen_hashlib=fd, zielvergleich_fehler=fl, tupelops_je_nonce=round(sum(runden) / K), erstes_gegenbeispiel=erstes, s=round(time.perf_counter() - t, 2))
        if fw or fd or fl or unbest: fehler('P2 Ziffernnetz ' + u, erstes=erstes, unbestimmt=unbest)
    ERG['status'] = 'OK'; ERG['fall'] = F['name']; ERG['referenz_treffer'] = F['referenz_treffer']

# ======================= P3 =======================
def p3():
    proben = {'F1_ECHTE_VORLAGE': [0, 255], 'F2_GENESIS_HISTORISCH': [2083236893, 2083236864]}
    for F in FAELLE:
        h76, T, base, bits = fall_daten(F); B, netze = aufbau(F); g, inputs, blog, bout = B['g'], B['inputs'], B['blog'], B['bout']
        for nonce in proben[F['name']]:
            n = nonce - (base & ~0xff); assert 0 <= n < 256; h = sha256d(h76, nonce); erw_le = int(int.from_bytes(h, 'little') <= T)
            il = SZ.IntLog(); w3 = struct.unpack('>16I', P.padded(h76 + nonce.to_bytes(4, 'little'))[64:])[3]; SZ.rechenweg(il, h76, base, bits, 'voll', nonce_wort=w3)
            ref = {k: w for k, w in zip(il.arten(), [w for _, _, _, w in il.log])}
            # E1, Ziel frei
            t = time.perf_counter(); d = e1_start(g, inputs, n, 0); st, sw = e1_lauf(g, d); t1 = time.perf_counter() - t
            unbest = sum(1 for _, _, _, bw in blog.log for b in bw if SZ.dom_von(d, b) == 3)
            fw = sum(1 for (p, a, nr, bw) in blog.log if sum((SZ.dom_von(d, b) >> 1) << i for i, b in enumerate(bw)) != ref[(p, a, nr)])
            dig = struct.pack('>8I', *[sum((SZ.dom_von(d, b) >> 1) << i for i, b in enumerate(w)) for w in bout['digest2']])
            r = dict(fall=F['name'], nonce=nonce, erwartet_le=erw_le, E1_ziel_frei=dict(status=st, sweeps=sw, unbestimmte_wortbits=unbest, wort_fehler=fw, digest_gleich_hashlib=dig == h, root_domaene=SZ.dom_von(d, B['root']), s=round(t1, 2)))
            # E1, Ziel gesetzt
            t = time.perf_counter(); d = e1_start(g, inputs, n, 0); SZ.dom_schneiden(d, B['root'], 2); st2, sw2 = e1_lauf(g, d)
            r['E1_ziel_1'] = dict(status=st2, sweeps=sw2, s=round(time.perf_counter() - t, 2))
            # E3 voll, Ziel frei / gesetzt
            Nd = netze['voll']; N = Nd['N']; le_voll = Nd['le']
            dom = list(N.dom)
            for j, v in enumerate(Nd['eing']):
                if dom[v] == 15: dom[v] = 1 << ((w3 >> (2 * j)) & 3)
            t = time.perf_counter(); st3, dom3, _, inf3 = Z.e3(N, dom); t3 = time.perf_counter() - t
            fw3 = sum(1 for (p, a, nr, ids) in Nd['ops'].log if wert(dom3, ids) != ref[(p, a, nr)])
            dig3 = all(wert(dom3, w) is not None for w in Nd['out']['digest2']) and struct.pack('>8I', *[wert(dom3, w) for w in Nd['out']['digest2']]) == h
            r['E3_voll_ziel_frei'] = dict(status=st3, runden=inf3['runden'], tupelops=inf3['tupelops'], wort_fehler=fw3, digest_gleich_hashlib=dig3, le_domaene=dom3[Nd['le']], s=round(t3, 2))
            dom[Nd['le']] &= 2; t = time.perf_counter(); st4, dom4, _, inf4 = Z.e3(N, dom)
            r['E3_voll_ziel_1'] = dict(status=st4, runden=inf4['runden'], leer=inf4.get('leer'), s=round(time.perf_counter() - t, 2))
            # E3 lokal: Digest1 aus E1 (Austauschpfad), Ziel frei / gesetzt
            Nd = netze['lokal']; N = Nd['N']; le_lokal = Nd['le']; d = e1_start(g, inputs, n, 0); e1_lauf(g, d); dom = list(N.dom)
            for wi, word in enumerate(Nd['eing']):
                for j, v in enumerate(word): dom[v] &= SZ.bits_zu_ziffern(SZ.dom_von(d, bout['digest1'][wi][2 * j]), SZ.dom_von(d, bout['digest1'][wi][2 * j + 1]))
            t = time.perf_counter(); st5, dom5, _, inf5 = Z.e3(N, dom); t5 = time.perf_counter() - t
            fw5 = sum(1 for (p, a, nr, ids) in Nd['ops'].log if wert(dom5, ids) != ref[(p, a, nr)])
            dig5 = all(wert(dom5, w) is not None for w in Nd['out']['digest2']) and struct.pack('>8I', *[wert(dom5, w) for w in Nd['out']['digest2']]) == h
            r['E3_lokal_ziel_frei'] = dict(status=st5, runden=inf5['runden'], wort_fehler=fw5, digest_gleich_hashlib=dig5, le_domaene=dom5[Nd['le']], s=round(t5, 2))
            dom[Nd['le']] &= 2; t = time.perf_counter(); st6, _, _, inf6 = Z.e3(N, dom)
            r['E3_lokal_ziel_1'] = dict(status=st6, runden=inf6['runden'], s=round(time.perf_counter() - t, 2))
            r['bewertung'] = dict(ziel_frei_korrekt=(st == 'FIXPUNKT' and unbest == 0 and fw == 0 and dig == h and st3 == 'FIXPUNKT' and fw3 == 0 and dig3 and st5 == 'FIXPUNKT' and fw5 == 0 and dig5
                                                    and r['E1_ziel_frei']['root_domaene'] == (1 << erw_le) and dom3[le_voll] == (1 << erw_le) and dom5[le_lokal] == (1 << erw_le)),   # Lauf 1: hier stand Nd['le'] des lokalen Netzes fuer dom3 (Auswertungsfehler, nicht Netzfehler)
                                  ziel_1_erwartet=('FIXPUNKT' if erw_le else 'WIDERSPRUCH'), ziel_1_E1=st2, ziel_1_E3_voll=st4, ziel_1_E3_lokal=st6)
            if not r['bewertung']['ziel_frei_korrekt']: fehler('P3 Stichprobe', **r)
            schritt('P3 %s nonce %d' % (F['name'], nonce), **r); fort('P3 %s %d fertig' % (F['name'], nonce))
    ERG['status'] = 'OK'

# ======================= P4 =======================
def p4():
    MAXP = 500000
    for F in FAELLE:
        h76, T, base, bits = fall_daten(F); B, netze = aufbau(F)
        for u in ('voll', 'lokal'):
            Nd = netze[u]; N = Nd['N']; dom = list(N.dom); dom[Nd['le']] &= 2       # Suchnetz: Ziel gesetzt, Nonce (voll) bzw. Digest1 (lokal) frei
            t = time.perf_counter(); st, dom, _, inf = Z.e3(N, dom, max_runden=60, pruef=lambda r, o: fort('P4 %s %s E3 Runde %d ops %d' % (F['name'], u, r, o))); t3 = time.perf_counter() - t
            frei = sum(1 for m in dom if m & (m - 1)); fest_eing = [N.name[v] for v in Nd['eing'] if N.dom[v] == 15 and dom[v] & (dom[v] - 1) == 0] if u == 'voll' else None
            t = time.perf_counter(); paare, bez_mit, pst = Z.grundpaare(N, dom, MAXP); tp = time.perf_counter() - t
            from collections import Counter
            je_typ = Counter(typ for typ, vs in N.bez if sum(1 for v in dict.fromkeys(vs) if dom[v] & (dom[v] - 1)) >= 2)
            schritt('P4 %s %s' % (F['name'], u), E3_status=st, E3_runden=inf['runden'], E3_tupelops=inf['tupelops'], E3_s=round(t3, 2), unbestimmte_variablen=frei,
                    durch_E3_festgelegte_eingangsziffern=fest_eing, beziehungen_mit_paaren=bez_mit, beziehungen_mit_paaren_je_typ=dict(je_typ), grundpaare=len(paare),
                    grundpaare_status=pst, paargrenze=MAXP, grundpaare_s=round(tp, 2), hinweis='nur E3 + Zaehlung, keine E4-Propagation')
            del paare
    ERG['status'] = 'OK'

try:
    if PHASE == 'P0': p0()
    elif PHASE == 'P1': p1()
    elif PHASE.startswith('P2'): p2(next(F for F in FAELLE if F['name'].startswith(PHASE[2:])))
    elif PHASE == 'P3': p3()
    elif PHASE == 'P4': p4()
    else: raise SystemExit('Phase?')
except (MemoryError, RecursionError) as e:
    fehler('Ausnahme', art=type(e).__name__, text=str(e))
ERG['gesamt_s'] = round(time.perf_counter() - T0, 2); ERG['peak_mib_kind'] = round(peak(), 1)
(HERE / AUS).write_text(json.dumps(ERG, indent=1, default=str)); fort('fertig ' + ERG['status']); sys.stderr.write('\n')
