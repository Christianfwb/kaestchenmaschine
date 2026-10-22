#!/usr/bin/env python3
"""ZIELHASH-VERSUCH, KINDPROZESS (Fable, 2026-10-22). python -I zielhash_kind.py <A|B> <E1|E4> <ausgabe.json> [maxpaare]
Vorlage F1 (echte gespeicherte Vorlage), Nonce 0..255 (8 freie Bits), Wurzel. Bedingung A: Hash <= Target (Vergleichskette, Wurzel=1).
Bedingung B: alle 256 Ausgangsbits auf den eingefrorenen Zielhash H* (ZIELHASH_V1.json) festgelegt – KEINE Vergleichskette,
Gleichheit je Bit im Bitgraphen und je Ziffer im Ziffernnetz. Derselbe Graph/dasselbe Netz fuer A und B (nur die Festlegung
unterscheidet sich), damit alle Messstellen (Register a..h je Runde beider Anwendungen, Nonce-Wort) eindeutig gemeinsam sind.
E1 = Bitregeln allein (Ziffern nur abgelesen); E4 = E1 + Ziffernnetz + Array-Paare (Radius 1) mit Austausch und Nachpruefung.
Orakel (hashlib) erst nach der Propagation: welche der 256 Nonces erfuellen A, welche B? Jeder Ausschluss wird dagegen geprueft.
Ausgaenge: TREFFER (unabhaengig bestaetigt) / BEWIESEN_UNLOESBAR_IM_BEREICH (Widerspruch, vom Orakel bestaetigt) / OFFEN."""
import sys, json, time, struct, hashlib, resource, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ, ziffern_sha as ZS, ziffern_array as ZA, pruefung as P
from e1_bit import e1_lauf
from austausch import austausch
BED, ART, AUS = sys.argv[1], sys.argv[2], sys.argv[3]; MAXP = int(sys.argv[4]) if len(sys.argv) > 4 else 2500000; SWEEPS = int(sys.argv[5]) if len(sys.argv) > 5 else 12; T0 = time.perf_counter()
FD = next(F for F in json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle'] if F['name'].startswith('F1'))
ZH = json.loads((HERE / 'ZIELHASH_V1.json').read_text()); HSTAR = int(ZH['zielzahl_hex'], 16)
h76 = bytes.fromhex(FD['header_hex_ohne_nonce']); T = int(FD['target_hex'], 16); BASIS = 0; BITS = list(range(8)); GRUPPE = list(range(256))
assert HSTAR <= T
ERG = dict(bedingung=BED, art=ART, vorlage=FD['name'], zielhash_bitcoin=ZH['zielhash_bitcoin'], noncebereich=[0, 255], python=platform.python_version(),
           rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU', status='LAEUFT', schritte=[], paargrenze=MAXP, e1_durchlaufgrenze=SWEEPS)
def peak(): return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
def speichern(): (HERE / AUS).write_text(json.dumps(ERG, indent=1, default=str))
def fort(t): sys.stderr.write('\r%s %s %s' % (BED, ART, t[:95].ljust(95))); sys.stderr.flush()
def schritt(n, **k): k.update(name=n, t_s=round(time.perf_counter() - T0, 2), peak_mib=peak()); ERG['schritte'].append(k); speichern()
def ende(st, **k):
    ERG.update(k); ERG['status'] = st; ERG['gesamt_s'] = round(time.perf_counter() - T0, 2); ERG['peak_mib_kind'] = peak(); speichern()
    fort('fertig ' + st); sys.stderr.write('\n'); sys.exit(0 if st == 'OK' else 2)
def fehler(n, **k): schritt('FEHLER ' + n, **k); ende('FEHLER', fehler=dict(name=n, **k))

# ---- Aufbau (identisch fuer A und B) ----
g, inputs, blog, bout, root = SZ.baue_bitgraph(h76, BASIS, BITS, T)
N, zops, zout, eing, le = SZ.baue_ziffernnetz(h76, BASIS, BITS, T, 'voll')
zu = SZ.wortzuordnung(blog, zops); zu.append(('H1_nonce', tuple(bout['H1_words'][3]), list(zout['H1_words'][3])))
schritt('Aufbau', graphknoten=len(g.nodes), wurzel_art=('Gatterknoten' if root not in (0, 1) else 'konstant'), ziffernvariablen=len(N.dom), beziehungen=len(N.bez))
# ---- Festlegung ----
d = [3] * len(g.nodes); d[0] = 1; d[1] = 2; zd = list(N.dom)
if BED == 'A':
    SZ.dom_schneiden(d, root, 2); zd[le] &= 2; fest_beschr = 'Hash <= Target: Vergleichskette, Wurzel = 1 (Bitgraph), le_128 = 1 (Ziffernnetz)'
else:
    digest = bout['digest2']; n_fest = 0
    for i in range(256):
        node = digest[(i // 8) // 4][8 * (3 - (i // 8) % 4) + i % 8]
        if SZ.dom_schneiden(d, node, 1 << ((HSTAR >> i) & 1)) == 0: fehler('Zielhash-Bit widerspricht Konstante', bit=i)
        n_fest += 1
    zb = HSTAR.to_bytes(32, 'little'); woerter = struct.unpack('>8I', zb)
    for k, w in enumerate(zout['digest2']):
        for j, v in enumerate(w):
            zd[v] &= 1 << ((woerter[k] >> (2 * j)) & 3)
            if zd[v] == 0: fehler('Zielhash-Ziffer widerspricht Konstante', wort=k, ziffer=j)
    fest_beschr = 'Hash = H*: alle 256 Digestbits fest (Bitgraph) und alle 128 Digestziffern fest (Ziffernnetz); keine Vergleichskette gesetzt'
schritt('Festlegung', beschreibung=fest_beschr)
# ---- Messstellen (gemeinsam fuer A und B): Register a..h je Runde beider Anwendungen, Nonce-Wort ----
MESS = [('H1', i + 1, nm, bout['H1_trace'][i][k], zout['H1_trace'][i][k]) for i in range(64) for k, nm in enumerate('abcdefgh')]
MESS += [('H2', i + 1, nm, bout['H2_trace'][i][k], zout['H2_trace'][i][k]) for i in range(64) for k, nm in enumerate('abcdefgh')]
def bits_fest(bw): return sum(1 for b in bw if SZ.dom_von(d, b) in (1, 2))
def ziff_fest(zw): return sum(1 for v in zw if zd[v] and zd[v] & (zd[v] - 1) == 0)
def noncebits(): return [(i, SZ.dom_von(d, nd) >> 1) for i, nd in enumerate(inputs) if SZ.dom_von(d, nd) in (1, 2)]
def ausgeschlossen():
    f = dict(noncebits()); return [n for n in GRUPPE if any(((n >> BITS[i]) & 1) != v for i, v in f.items())]
# ---- Propagation ----
t = time.perf_counter(); st1, sw = e1_lauf(g, d, max_sweeps=SWEEPS); t1 = time.perf_counter() - t
schritt('E1', status=st1, sweeps=sw, s=round(t1, 2), bitknoten_fest=sum(1 for x in d[2:] if x in (1, 2)), noncebits=noncebits())
status = st1; paare = None; info = {}
if st1 != 'WIDERSPRUCH':
    if ART == 'E1':
        for nm, bw, zw in zu:
            for j in range(16): zd[zw[j]] &= SZ.bits_zu_ziffern(SZ.dom_von(d, bw[2 * j]), SZ.dom_von(d, bw[2 * j + 1]))
        schritt('Ziffern aus Bitdomaenen abgelesen (kein Ziffernnetz-Lauf)')
    else:
        R = austausch(g, inputs, root, d, N, zu, zd, ZA.e4, MAXP, True, schritt=schritt, fort=fort, fehler=fehler,
                      zaehler=lambda d_, zd_: dict(noncebits=noncebits(), knoten_fest=sum(1 for x in d_[2:] if x in (1, 2))))
        status, d, zd, paare, info = R['status'], R['d'], R['zd'], R['paare'], R['info4']
        if R['open_grund'] is not None: ERG['open_grund'] = R['open_grund']
        np_ = info.get('nachpruefung_e3')
        if np_ is not None and (np_['geaendert'] or np_['status'] != 'FIXPUNKT'): fehler('Nachpruefung E3', nachpruefung=np_)
fort('Auswertung')
# ---- Orakel, erst jetzt ----
hits_A = []; hits_B = []
for n in GRUPPE:
    hh = hashlib.sha256(hashlib.sha256(h76 + n.to_bytes(4, 'little')).digest()).digest(); v = int.from_bytes(hh, 'little')
    if v <= T: hits_A.append(n)
    if v == HSTAR: hits_B.append(n)
erfuellend = hits_B if BED == 'B' else hits_A
aus = ausgeschlossen() if status != 'WIDERSPRUCH' else list(GRUPPE)
if any(n in erfuellend for n in aus): fehler('Falscher Ausschluss', ausgeschlossen=aus[:10], erfuellend=erfuellend)
# ---- Karte: feste Bits/Ziffern je Messstelle ----
karte = [dict(phase=p, runde=r, reg=nm, bits_fest=bits_fest(bw), ziffern_fest=ziff_fest(zw)) for p, r, nm, bw, zw in MESS]
h2_voll = [z['runde'] for z in karte if z['phase'] == 'H2' and z['bits_fest'] == 32]
h2_teil = [z['runde'] for z in karte if z['phase'] == 'H2' and 0 < z['bits_fest'] < 32]
h1_offen = next((z['runde'] for z in karte if z['phase'] == 'H1' and z['reg'] == 'a' and z['bits_fest'] == 0), None)
if status == 'WIDERSPRUCH': ausgang = 'BEWIESEN_UNLOESBAR_IM_BEREICH' if not erfuellend else 'FEHLER'
elif erfuellend and all(n not in aus for n in erfuellend) and len(aus) == 255: ausgang = 'TREFFER_ABGELEITET'
else: ausgang = 'OFFEN'
ERG['karte'] = karte
ERG['ergebnis'] = dict(status=status, ausgang=ausgang, noncebits_abgeleitet=noncebits(), ausgeschlossene_nonces=len(aus),
    orakel=dict(erfuellen_A_target=hits_A, erfuellen_B_zielhash=hits_B, bedingung_hat_loesung_im_bereich=bool(erfuellend)),
    bitknoten_fest=sum(1 for x in d[2:] if x in (1, 2)), bitknoten_gesamt=len(g.nodes) - 2,
    ziffern_fest=sum(1 for m in zd if m and m & (m - 1) == 0), ziffern_fest_start=sum(1 for m in N.dom if m & (m - 1) == 0), ziffern_gesamt=len(zd),
    paare=(len(paare) if paare is not None else 0), paare_eingeschraenkt=(paare.eingeschraenkt() if paare is not None else None),
    rueckwaerts_H2=dict(register_vollstaendig_fest_in_runden=sorted(set(h2_voll)), register_teilweise_fest_in_runden=sorted(set(h2_teil)),
                        frueheste_beruehrte_runde=(min(h2_voll + h2_teil) if (h2_voll or h2_teil) else None)),
    vorwaerts_H1=dict(erste_runde_mit_register_a_voellig_offen=h1_offen),
    e4_letzte_info={k: v for k, v in info.items() if k != 'nachpruefung_e3'} if info else None, nachpruefung=info.get('nachpruefung_e3') if info else None)
ende('OK')
