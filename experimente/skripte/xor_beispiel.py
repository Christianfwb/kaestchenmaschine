#!/usr/bin/env python3
"""KLEINES BEISPIEL: ERKENNEN GEMEINSAME XOR-GLEICHUNGEN EINEN KONFLIKT, DEN BIT- UND PAARREGELN UEBERSEHEN? (Fable, 2026-10-22)
Ghosts Auftrag. Zwei Faelle, beide mit vier freien Eingangsbits, beide OHNE Loesung (erschoepfend nachgeprueft):
  FALL A (dreistellige Paritaeten): x1^x2^x3 = 1, x1^x2^x4 = 1, x3^x4 = 1.
    Aus den ersten beiden folgt x3^x4 = 0 – Widerspruch zur dritten. Jede einzelne Gleichung ist erfuellbar, und bei den
    dreistelligen Gleichungen ist JEDES Variablenpaar voellig frei (alle vier Kombinationen moeglich) – Paare koennen hier
    per Bauart nichts sehen.
  FALL B (nur zweistellige Paritaeten): x1^x2 = 0, x2^x3 = 0, x1^x3 = 1.
    Auch unloesbar, aber alle drei Gleichungen sind BINAER – eine Paarrechnung mit Radius-1-Komposition sollte das finden.
    Dient als Gegenprobe, damit der Unterschied nicht behauptet, sondern gemessen ist.
Verglichen werden: E1 (Bogenkonsistenz auf dem Gattergraphen), E1+E4 (Ziffernnetz mit Paaren, Radius 1) und
GF(2)-Elimination (gemeinsame XOR-Gleichungen, Gauss ueber dem Zweierkoerper). Referenz: alle 16 Belegungen durchgerechnet.
Graphgroesse und Art der Wurzel werden berichtet, damit Vereinfachung beim Aufbau nicht mit Ableitung verwechselt wird."""
import sys, json, time, itertools, resource, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import gatter as G, sha_ziffern as SZ, ziffern_komp as ZK, ziffern_sha as ZS
from ziffern import Netz, TABELLEN, GROESSEN
from e1_bit import e1_lauf
T0 = time.perf_counter()
def peak(): return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
# Gleichungen: (Liste der Variablenindizes 0..3, rechte Seite)
FAELLE = {
 'A_dreistellig': [([0, 1, 2], 1), ([0, 1, 3], 1), ([2, 3], 1)],
 'B_zweistellig': [([0, 1], 0), ([1, 2], 0), ([0, 2], 1)],
}
def referenz(gln):
    return [b for b in itertools.product((0, 1), repeat=4) if all(sum(b[v] for v in vs) % 2 == r for vs, r in gln)]
def gf2(gln, n=4):
    """Gauss ueber GF(2): liefert (loesbar, Schritte, abgeleitete feste Variablen)."""
    zeilen = [(sum(1 << v for v in vs), r) for vs, r in gln]; schritte = 0; pivots = {}
    for spalte in range(n):
        p = next((i for i, (m, r) in enumerate(zeilen) if (m >> spalte) & 1 and all((m >> q) & 1 == 0 for q in pivots)), None)
        if p is None: continue
        pm, pr = zeilen.pop(p); pivots[spalte] = (pm, pr)
        for i, (m, r) in enumerate(zeilen):
            schritte += 1
            if (m >> spalte) & 1: zeilen[i] = (m ^ pm, r ^ pr)
    for m, r in zeilen:
        schritte += 1
        if m == 0 and r == 1: return False, schritte, {}
    fest = {s: pr for s, (pm, pr) in pivots.items() if pm == (1 << s)}
    return True, schritte, fest
def bitgraph(gln):
    g = G.Graph(); x = [g.input(i) for i in range(4)]; root = 1
    for vs, r in gln:
        acc = 0
        for v in vs: acc = g.gate('xor', acc, x[v])
        root = g.gate('and', root, acc if r else G.inv(acc))
    return g, x, root
def ziffernnetz(gln):
    N = Netz(2); x = [N.wort('x%d' % i) for i in range(4)]
    for w in x: N.dom[w[0]] &= 0b0011                      # je Wort eine Ziffer, nur Werte 0 und 1 = ein Bit
    for k, (vs, r) in enumerate(gln):
        acc = x[vs[0]]
        for v in vs[1:]: acc = N.xor(acc, x[v], 'e%d_%d' % (k, v))
        N.fest(acc[0], r)
    return N, [w[0] for w in x]
ERG = dict(messung='Gemeinsame XOR-Gleichungen gegen Bit- und Paarregeln', python=platform.python_version(),
           rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU', faelle=[])
for name, gln in FAELLE.items():
    ref = referenz(gln)
    g, x, root = bitgraph(gln)
    art = {0: 'KONSTANTE 0 (beim Aufbau entschieden)', 1: 'KONSTANTE 1'}.get(root) or ('Eingangsbit' if root in x else 'echter Gatterknoten')
    # E1
    d = [3] * len(g.nodes); d[0] = 1; d[1] = 2
    erkannt_aufbau = (root == 0)
    if not erkannt_aufbau: SZ.dom_schneiden(d, root, 2)
    t = time.perf_counter(); st1, sw = e1_lauf(g, d); t_e1 = time.perf_counter() - t
    e1_erlaubt = [b for b in itertools.product((0, 1), repeat=4) if all((SZ.dom_von(d, x[i]) >> b[i]) & 1 for i in range(4))] if st1 != 'WIDERSPRUCH' else []
    # E1 + E4
    N, xv = ziffernnetz(gln)
    t = time.perf_counter(); st4, dom, paare, inf = ZK.e4(N, list(N.dom), max_paare=10000); t_e4 = time.perf_counter() - t
    e4_erlaubt = [b for b in itertools.product((0, 1), repeat=4) if all((dom[xv[i]] >> b[i]) & 1 for i in range(4))] if st4 != 'WIDERSPRUCH' else []
    paar_universell = sum(1 for (a, b2), m in paare.items() if m == (1 << (N.groesse[a] * N.groesse[b2])) - 1)
    # GF(2)
    t = time.perf_counter(); loesbar, schritte, fest = gf2(gln); t_gf = time.perf_counter() - t
    ERG['faelle'].append(dict(fall=name, gleichungen=[[vs, r] for vs, r in gln], referenz_loesungen=len(ref),
        graph=dict(knoten=len(g.nodes), wurzel=art, beim_aufbau_entschieden=erkannt_aufbau),
        E1=dict(status=('WIDERSPRUCH_AUS_AUFBAU' if erkannt_aufbau else st1), konflikt_erkannt=(erkannt_aufbau or st1 == 'WIDERSPRUCH'),
                noch_erlaubte_belegungen=len(e1_erlaubt), zeit_s=round(t_e1, 6)),
        E1_E4=dict(status=st4, konflikt_erkannt=(st4 == 'WIDERSPRUCH'), noch_erlaubte_belegungen=len(e4_erlaubt),
                   gespeicherte_paare=len(paare), davon_universell=paar_universell, tupelops=inf.get('tupelops'), zeit_s=round(t_e4, 6)),
        GF2=dict(loesbar=loesbar, konflikt_erkannt=(not loesbar), eliminationsschritte=schritte, zeit_s=round(t_gf, 8))))
a, b = ERG['faelle']
ERG['ergebnis'] = dict(
    trennt_der_fall_A=(a['GF2']['konflikt_erkannt'] and not a['E1']['konflikt_erkannt'] and not a['E1_E4']['konflikt_erkannt']),
    gegenprobe_B_von_paaren_erkannt=b['E1_E4']['konflikt_erkannt'],
    referenz_beide_unloesbar=(a['referenz_loesungen'] == 0 and b['referenz_loesungen'] == 0))
ERG['status'] = 'OK' if ERG['ergebnis']['referenz_beide_unloesbar'] else 'FEHLER'
ERG['gesamt_s'] = round(time.perf_counter() - T0, 3); ERG['peak_mib'] = peak()
(HERE / 'ERGEBNIS_XOR_BEISPIEL.json').write_text(json.dumps(ERG, indent=1))
for f in ERG['faelle']:
    print('%-14s Ref-Loesungen %d | Graph %d Knoten, Wurzel %s' % (f['fall'], f['referenz_loesungen'], f['graph']['knoten'], f['graph']['wurzel']))
    print('   E1     : Konflikt erkannt %-5s  noch erlaubt %2d  (%s)' % (f['E1']['konflikt_erkannt'], f['E1']['noch_erlaubte_belegungen'], f['E1']['status']))
    print('   E1+E4  : Konflikt erkannt %-5s  noch erlaubt %2d  Paare %d (davon universell %d)' % (f['E1_E4']['konflikt_erkannt'], f['E1_E4']['noch_erlaubte_belegungen'], f['E1_E4']['gespeicherte_paare'], f['E1_E4']['davon_universell']))
    print('   GF(2)  : Konflikt erkannt %-5s  Schritte %d, %.7f s' % (f['GF2']['konflikt_erkannt'], f['GF2']['eliminationsschritte'], f['GF2']['zeit_s']))
print(json.dumps(ERG['ergebnis']), ERG['status'], ERG['gesamt_s'], 's')
