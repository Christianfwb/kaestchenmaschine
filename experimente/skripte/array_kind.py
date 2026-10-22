#!/usr/bin/env python3
"""GLEICHHEITSREIHE ARRAY-PAARE (Fable, 2026-10-22). python -I array_kind.py A1 <ausgabe.json>
Vergleich ziffern_array.e4 gegen ziffern_komp.e4: Mini-Netze (w=4/8; add, xor, rot gerade/ungerade, ch, maj, neg, x+x, Konstanten, Alias),
zufaellige Teil-/leere/volle Domaenen, Paarlimits 5000 (keine Grenze) und sehr kleine Limits (3, 12). Vergleichsregel:
  Status immer gleich (Ausnahme: PAARGRENZE – erklaerter Unterschied: Array-Fassung meldet vor Allokation; dann Status beider = OPEN_PAARGRENZE, Domaenen nicht verglichen);
  bei FIXPUNKT: alle Enddomaenen gleich, Masken aller Paare der alten Fassung gleich, alle zusaetzlichen (vorab angelegten) Paare universell;
  bei WIDERSPRUCH/OFFEN: nur Status (Abbruchzeitpunkt/Reihenfolge in Schritt 3 erklaert verschieden). Dazu Soundness: bekannte Loesung bleibt in Domaenen und Masken.
Zusaetzlich groessere Netze (1 und 6 SHA-Runden, 32 Bit) und das Dreier-Mini-Beispiel. Kein Wurzellauf."""
import sys, json, time, random, resource, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import ziffern_komp as ZK, ziffern_array as ZA, ziffern_sha as ZS, sha_ziffern as SZ
from ziffern import Netz
from mininetze import mininetz, zufallsdomaenen
PHASE, AUS = sys.argv[1], sys.argv[2]; T0 = time.perf_counter()
ERG = dict(phase=PHASE, python=platform.python_version(), rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU, Python + numpy 2.5.3 (nur Aufbau)', schritte=[])
def peak(): return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
def fort(t): sys.stderr.write('\r' + PHASE + ' ' + t[:100].ljust(100)); sys.stderr.flush()
def schritt(name, **k): k.update(name=name, t_s=round(time.perf_counter() - T0, 2), peak_mib=round(peak(), 1)); ERG['schritte'].append(k); return k
def vergleich(N, dom, limit):
    a = ZK.e4(N, dom, max_paare=limit); b = ZA.e4(N, dom, max_paare=limit)
    sa, sb = a[0], b[0]
    if sa == 'OPEN_PAARGRENZE' or sb == 'OPEN_PAARGRENZE': return ('grenze', sa == sb == 'OPEN_PAARGRENZE' or (sa == 'OPEN_PAARGRENZE' and sb == 'OPEN_PAARGRENZE'), sa, sb)
    if sa != sb: return ('status', False, sa, sb)
    if sa != 'FIXPUNKT': return ('status', True, sa, sb)
    if a[1] != b[1]: return ('domaenen', False, sa, sb)
    alt = a[2]; neu = b[2].als_dict(); gr = N.groesse
    for k, m in alt.items():
        if neu.get(k) != m: return ('paarmaske', False, sa, sb)
    for k, m in neu.items():
        if k not in alt and m != (1 << (gr[k[0]] * gr[k[1]])) - 1: return ('zusatzpaar_nicht_universell', False, sa, sb)
    return ('fixpunkt', True, sa, sb)
def a1():
    rnd = random.Random(11); z = {}; f = 0; c = 0; grenz_versch = 0
    for seed in range(160):
        N, eing, ws = mininetz(seed, 4 if seed % 2 else 8)
        for limit in (5000, 12, 3):
            dom = zufallsdomaenen(N, rnd); c += 1; art, ok, sa, sb = vergleich(N, dom, limit)
            z[art + '_' + sa] = z.get(art + '_' + sa, 0) + 1
            if art == 'grenze' and sa != sb: grenz_versch += 1      # einer an der Grenze, der andere nicht -> gezaehlt, nicht Fehler (erklaert)
            elif not ok: f += 1
        if seed % 20 == 0: fort('A1 Netz %d' % seed)
    schritt('A1 Gleichheit Array gegen komp (Mini-Netze, Limits 5000/12/3)', faelle=c, fehler=f, grenze_nur_eine_fassung=grenz_versch, zaehlung=z)
    # Soundness mit Loesung
    f2 = 0; c2 = 0
    for seed in range(200):
        N, eing, ws = mininetz(1000 + seed, 4 if seed % 2 else 8); dom = list(N.dom)
        for v in eing: dom[v] &= 1 << rnd.randrange(N.groesse[v])
        st, dom, _, _ = ZS.e3(N, dom)
        if st != 'FIXPUNKT' or any(m & (m - 1) for m in dom): continue
        loes = [m.bit_length() - 1 for m in dom]; dom2 = zufallsdomaenen(N, rnd, loesung=loes, p_frei=0.6); c2 += 1
        st, d3, PS, inf = ZA.e4(N, dom2, max_paare=5000, nachpruefung=True)
        if st == 'WIDERSPRUCH' or any(not (d3[v] >> loes[v]) & 1 for v in range(len(d3))): f2 += 1; continue
        for (x, y), m in PS.als_dict().items():
            if not m >> (loes[x] * N.groesse[y] + loes[y]) & 1: f2 += 1; break
        if inf['nachpruefung_e3']['geaendert'] or inf['nachpruefung_e3']['status'] != 'FIXPUNKT': f2 += 1
    schritt('A1 Soundness (Loesung in Domaenen und Masken, Nachpruefung)', faelle=c2, fehler=f2)
    # groessere Netze: 1 und 6 SHA-Runden
    for runden_n in (1, 6):
        N = Netz(32); ops = SZ.ZiffernOps(N); ops.phase = 'T'; r = random.Random(2); st_ = [N.wort(n) for n in 'abcdefgh']; a, b, c_, d, e, f_, g, h = st_
        for i in range(runden_n):
            s1 = ops.xor(ops.rot(e, 6), ops.rot(e, 11), ops.rot(e, 25)); s0 = ops.xor(ops.rot(a, 2), ops.rot(a, 13), ops.rot(a, 22))
            t1 = ops.add(h, s1, ops.ch(e, f_, g), ops.const(0x428a2f98 + i), N.wort('w%d' % i)); t2 = ops.add(s0, ops.maj(a, b, c_))
            a, b, c_, d, e, f_, g, h = ops.add(t1, t2), a, b, c_, ops.add(d, t1), e, f_, g
        dom = list(N.dom)
        for wd in (e, f_, g):
            for v in wd: dom[v] = 1 << r.randrange(4)
        t = time.perf_counter(); A = ZK.e4(N, dom, max_paare=10**6); ta = time.perf_counter() - t
        t = time.perf_counter(); B = ZA.e4(N, dom, max_paare=10**6); tb = time.perf_counter() - t
        art, ok, sa, sb = vergleich(N, dom, 10**6)
        schritt('A1 SHA-%d-Runden-Netz' % runden_n, variablen=len(N.dom), beziehungen=len(N.bez), status_komp=sa, status_array=sb, gleich=ok, art=art,
                paare_komp=len(A[2]) if A[2] else None, paare_array=len(B[2]) if B[2] else None, s_komp=round(ta, 2), s_array=round(tb, 2))
        if not ok: f += 1
    # Dreier-Mini-Beispiel
    import dreier_beispiel as DB
    for dr in (False, True):
        N, x, y = DB.netz(dr); art, ok, sa, sb = vergleich(N, list(N.dom), 5000)
        schritt('A1 Dreier-Beispiel dreier=%s' % dr, gleich=ok, art=art, status=sa)
        if not ok: f += 1
    ERG['status'] = 'OK' if f == 0 and f2 == 0 else 'FEHLER'
a1()
ERG['gesamt_s'] = round(time.perf_counter() - T0, 2); ERG['peak_mib_kind'] = round(peak(), 1)
(HERE / AUS).write_text(json.dumps(ERG, indent=1, default=str)); fort('fertig ' + ERG['status']); sys.stderr.write('\n')
