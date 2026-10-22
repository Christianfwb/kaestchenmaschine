#!/usr/bin/env python3
"""XOR-GLEICHUNGEN AUS DEM ECHTEN SHA-GRAPHEN (Fable, 2026-10-22). python -I xor_sha_kind.py <F1|F2> <nbits> <ausgabe.json>
Ghosts praezisierte Messfragen: XOR-Gleichungen aus dem echten Bitgraphen sammeln, feste Werte (aus E1 mit Zielbedingung) und
die Zielbedingung einbeziehen, und pruefen, ob daraus ZUSAETZLICHE EINGANGSBEZIEHUNGEN oder WIDERSPRUECHE folgen.
Darstellung (exakt, aber gelockert): jeder Knoten erhaelt eine affine Form ueber GF(2) in einer Basis aus
  - den freien Eingangsbits,
  - der Konstanten 1,
  - je einem FREIEN Basisvektor fuer jeden UND-Ausgang (Lockerung: ueber UND wird nichts Lineares angenommen).
  XOR-Knoten: Form = Form(a) XOR Form(b); Negation = Form XOR 1. Dadurch sind ALLE XOR-Gatter als Gleichungen enthalten.
  Lockerung heisst: jede echte Loesung bleibt moeglich (sound), zusaetzliche falsche Loesungen koennen hinzukommen. Ein
  bewiesener Widerspruch oder eine abgeleitete Eingangsbeziehung ist trotzdem gueltig.
Gleichungen: fuer jeden Knoten, den E1 (mit Zielbedingung) auf einen festen Wert gebracht hat: Form(Knoten) = Wert.
  Dazu die Zielwurzel = 1. Gauss-Elimination ueber GF(2); danach: Widerspruch? Zeilen, die nur noch Eingangsbits enthalten
  (= abgeleitete Eingangsbeziehung)? Der Rang allein wird berichtet, aber nicht als Gewinn gewertet.
Speicherwaechter intern (Abbruch -> OFFEN mit Fortschritt), extern zusaetzlich durch lauf_xor_sha.py."""
import sys, json, time, resource, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ, gatter as G
from e1_bit import e1_lauf
FALL, NBITS, AUS = sys.argv[1], int(sys.argv[2]), sys.argv[3]; T0 = time.perf_counter(); RAM_MIB = 400
def peak(): return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
ERG = dict(fall=FALL, freie_bits=NBITS, python=platform.python_version(), rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU', status='LAEUFT', schritte=[])
def speichern(): (HERE / AUS).write_text(json.dumps(ERG, indent=1, default=str))
def schritt(n, **k): k.update(name=n, t_s=round(time.perf_counter() - T0, 2), peak_mib=peak()); ERG['schritte'].append(k); speichern()
def ende(st, **k): ERG.update(k); ERG['status'] = st; ERG['gesamt_s'] = round(time.perf_counter() - T0, 2); ERG['peak_mib'] = peak(); speichern(); sys.exit(0 if st == 'OK' else 2)
FD = next(F for F in json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle'] if F['name'].startswith(FALL))
h76 = bytes.fromhex(FD['header_hex_ohne_nonce']); T = int(FD['target_hex'], 16); maske = (1 << NBITS) - 1
basis_nonce = (FD['referenz_treffer'][0] & ~maske) if FD['referenz_treffer'] else 0
g, inputs, blog, bout, root = SZ.baue_bitgraph(h76, basis_nonce, list(range(NBITS)), T)
n_and = sum(1 for nd in g.nodes[2:] if nd[0] == 'and'); n_xor = sum(1 for nd in g.nodes[2:] if nd[0] == 'xor')
schritt('Aufbau', graphknoten=len(g.nodes), und_gatter=n_and, xor_gatter=n_xor, wurzel=('Gatterknoten' if root not in (0, 1) and root not in inputs else 'vorentschieden'))
if root in (0, 1): ende('OK', ergebnis=dict(hinweis='Wurzel beim Aufbau konstant – Fall ist vorentschieden, keine Gleichungsanalyse noetig'))
# ---- feste Werte: E1 mit Zielbedingung (sound) ----
d = [3] * len(g.nodes); d[0] = 1; d[1] = 2; SZ.dom_schneiden(d, root, 2)
t = time.perf_counter(); st1, sw = e1_lauf(g, d)
fest = {i: (d[i] >> 1) for i in range(2, len(g.nodes)) if d[i] in (1, 2)}
schritt('E1 mit Zielbedingung (liefert die festen Werte)', status=st1, sweeps=sw, feste_knoten=len(fest), s=round(time.perf_counter() - t, 2))
if st1 == 'WIDERSPRUCH': ende('OK', ergebnis=dict(hinweis='E1 allein widerspruechlich – Gleichungsanalyse nicht noetig'))
# ---- affine Formen ueber GF(2): Basis = Eingaenge | Konstante 1 | je UND-Ausgang ein freier Vektor ----
KONST = NBITS; basis_n = NBITS + 1
# LAUF 2 (nach Speicherabbruch in Lauf 1): Formen werden nur so lange gehalten, wie noch ein Verbraucher aussteht (Referenzzaehlung);
# Gleichungen fester Knoten werden sofort beim Erreichen des Knotens ausgegeben. Gleiche Regel, gleiche Lockerung, nur weniger Speicher.
verbraucher = [0] * len(g.nodes)
for i in range(2, len(g.nodes)):
    nd = g.nodes[i]
    if nd[0] != 'input':
        verbraucher[abs(nd[1])] += 1; verbraucher[abs(nd[2])] += 1
verbraucher[abs(root)] += 1
form = {0: 0, 1: 1 << KONST}; and_index = {}; zeilen = []; zielform = None
def f(x): return (form[-x] ^ (1 << KONST)) if x < 0 else form[x]
def freigeben(x):
    x = abs(x)
    if x < 2: return
    verbraucher[x] -= 1
    if verbraucher[x] <= 0: form.pop(x, None)
t = time.perf_counter(); pop_sum = 0; pop_n = 0; max_pop = 0; max_live = 0
for i in range(2, len(g.nodes)):
    nd = g.nodes[i]
    if nd[0] == 'input': form[i] = 1 << nd[1]
    elif nd[0] == 'and':
        and_index[i] = basis_n; form[i] = 1 << basis_n; basis_n += 1; freigeben(nd[1]); freigeben(nd[2])
    else:
        form[i] = f(nd[1]) ^ f(nd[2]); freigeben(nd[1]); freigeben(nd[2])
        p = bin(form[i]).count('1'); pop_sum += p; pop_n += 1
        if p > max_pop: max_pop = p
    if i in fest: zeilen.append(form[i] ^ (fest[i] << KONST))
    if i == abs(root): zielform = f(root)
    if verbraucher[i] <= 0: form.pop(i, None)
    if i % 10000 == 0:
        if len(form) > max_live: max_live = len(form)
        if peak() > RAM_MIB: ende('OFFEN', abbruch='RAM intern > %d MiB bei Knoten %d' % (RAM_MIB, i))
zeilen.append(zielform ^ (1 << KONST))                                     # Wurzel = 1
schritt('Affine Formen (Referenzzaehlung, nur lebende Formen gehalten)', basisvektoren=basis_n, davon_und_ausgaenge=len(and_index), xor_formen=pop_n,
        mittlere_termzahl_xor_formen=round(pop_sum / max(1, pop_n), 2), max_termzahl=max_pop, max_gleichzeitig_gehaltene_formen=max_live, s=round(time.perf_counter() - t, 2))
# ---- Gleichungen: feste Knoten + Zielwurzel ----
n_gl = len(zeilen)
# ---- Gauss ueber GF(2) (Zeilen als Python-Ints; Pivot = hoechstes gesetztes Nicht-Konstanten-Bit) ----
t = time.perf_counter(); pivots = {}; widerspruch = False; schritte = 0
KM = 1 << KONST
for z in zeilen:
    r = z
    while True:
        rest = r & ~KM
        if rest == 0: break
        p = rest.bit_length() - 1
        if p in pivots: r ^= pivots[p]; schritte += 1
        else: pivots[p] = r; break
    if (r & ~KM) == 0 and (r & KM): widerspruch = True
rang = len(pivots)
# Rueckwaertsreduktion, um reine Eingangsbeziehungen sichtbar zu machen
EING = (1 << NBITS) - 1
eingangs_beziehungen = []
for p in sorted(pivots):
    r = pivots[p]
    for q in sorted(pivots, reverse=True):
        if q != p and (r >> q) & 1: r ^= pivots[q]; schritte += 1
    pivots[p] = r
    if (r & ~KM & ~EING) == 0 and (r & EING):
        eingangs_beziehungen.append(dict(bits=[b for b in range(NBITS) if (r >> b) & 1], gleich=(r >> KONST) & 1))
and_in_gleichungen = len({b for r in pivots.values() for b in range(NBITS + 1, basis_n) if (r >> b) & 1})
schritt('Gauss-Elimination', gleichungen=n_gl, rang=rang, eliminationsschritte=schritte, widerspruch=widerspruch,
        abgeleitete_eingangsbeziehungen=eingangs_beziehungen, und_variablen_in_reduzierten_gleichungen=and_in_gleichungen, s=round(time.perf_counter() - t, 2))
# ---- Orakel nur zur Kontrolle: welche Kandidaten erfuellen das Ziel wirklich? ----
import hashlib
kand = []
for k in range(1 << NBITS):
    n = basis_nonce | k; hh = hashlib.sha256(hashlib.sha256(h76 + n.to_bytes(4, 'little')).digest()).digest()
    kand.append(dict(nonce=n, treffer=int.from_bytes(hh, 'little') <= T))
gueltige = [c['nonce'] for c in kand if c['treffer']]
# Soundness: jede abgeleitete Eingangsbeziehung muss fuer alle gueltigen Kandidaten gelten; ein Widerspruch ist nur erlaubt, wenn keiner gueltig ist
sound = True
if widerspruch and gueltige: sound = False
for eb in eingangs_beziehungen:
    for nz in gueltige:
        if sum((nz >> b) & 1 for b in eb['bits']) % 2 != eb['gleich']: sound = False
ERG['ergebnis'] = dict(widerspruch=widerspruch, abgeleitete_eingangsbeziehungen=eingangs_beziehungen, rang=rang, gleichungen=n_gl,
    orakel_gueltige_kandidaten=gueltige, orakel_unloesbar=(not gueltige), sound=sound,
    lesart=('Widerspruch bewiesen – gueltig trotz Lockerung' if widerspruch else
            ('Eingangsbeziehung(en) abgeleitet' if eingangs_beziehungen else 'keine Eingangsbeziehung und kein Widerspruch aus den XOR-Gleichungen (bei dieser Lockerung)')))
ende('OK' if sound else 'FEHLER')
