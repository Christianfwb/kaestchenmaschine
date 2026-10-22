#!/usr/bin/env python3
"""RUNDENKURVE, KINDPROZESS (Fable, 2026-10-23). python -I runden_kind.py <R> <ausgabe.json> [maxpaare]
MODELL "reduziertes SHA256d mit R Runden" – AUSDRUECKLICH NICHT das Bitcoin-Verfahren (das hat 64 Runden):
  Kompression: genau R Runden (Runde 1..R, Konstanten K[0..R-1]), Zustand 8 x 32 Bit, Rundenfunktion unveraendert (Ch, Maj, Sigma0/1, Additionen).
  Nachrichtenerweiterung: W[0..15] aus dem Block, W[16..R-1] nach der SHA-256-Regel (fuer R <= 16 keine Erweiterung noetig).
  Padding: unveraendert (80-Byte-Header -> 2 Bloecke; 32-Byte-Digest -> 1 Block), Feed-forward unveraendert (Zustand + Startzustand).
  Alle drei Kompressionen (Block 1 -> Midstate, Block 2 -> H1, H1 -> H2) mit R Runden. R = 64 ist textgleich zu SHA256d (gegen hashlib geprueft).
Vorlage F1, Nonce 0..255 (8 freie Bits). Kontrollkandidat vorab aus Samen (sha256('KONTROLLE_RUNDENKURVE_2026-10-23_R<R>') mod 256);
Zielhash = reduziertes SHA256d(Vorlage, Kontrollnonce) – dem Loeser werden NUR Vorlage, freie Bits und Zielhash gegeben.
Loeser: E1 bis Fixpunkt (keine Durchlaufgrenze, nur Zeit/RAM extern); falls nicht entschieden, E1+E4 (Ziffernnetz, Paare Radius 1, Austausch, Nachpruefung).
Orakel (Integer-Referenz pruefung.IntegerOps, getrennter Code) erst danach ueber ALLE 256 Kandidaten; alle Treffer muessen erhalten bleiben."""
import sys, json, time, struct, hashlib, resource, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ, ziffern_array as ZA, pruefung as P
from e1_bit import e1_lauf
from austausch import austausch
R, AUS = int(sys.argv[1]), sys.argv[2]; MAXP = int(sys.argv[3]) if len(sys.argv) > 3 else 2500000; T0 = time.perf_counter()
FD = next(F for F in json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle'] if F['name'].startswith('F1'))
h76 = bytes.fromhex(FD['header_hex_ohne_nonce']); BASIS = 0; BITS = list(range(8)); GRUPPE = list(range(256))
def sha256d_r(nonce):
    p = P.padded(h76 + nonce.to_bytes(4, 'little'))
    mid = SZ.compress_r(P.IV, struct.unpack('>16I', p[:64]), P.IntegerOps, runden=R)
    d1 = SZ.compress_r(mid, struct.unpack('>16I', p[64:]), P.IntegerOps, runden=R)
    d2 = SZ.compress_r(P.IV, list(d1) + [0x80000000] + [0] * 6 + [256], P.IntegerOps, runden=R)
    return d2   # 8 Woerter big-endian
SAMEN = 'KONTROLLE_RUNDENKURVE_2026-10-23_R%d' % R
KONTROLLE = int.from_bytes(hashlib.sha256(SAMEN.encode()).digest(), 'little') % 256
ZIEL = sha256d_r(KONTROLLE); HSTAR = int.from_bytes(struct.pack('>8I', *ZIEL), 'little')
ERG = dict(runden=R, modell='reduziertes SHA256d (siehe Docstring), NICHT Bitcoin', vorlage=FD['name'], noncebereich=[0, 255], samen=SAMEN,
           zielhash_bitcoin=struct.pack('>8I', *ZIEL)[::-1].hex(), python=platform.python_version(),
           rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU', status='LAEUFT', schritte=[], paargrenze=MAXP)
def peak(): return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
def speichern(): (HERE / AUS).write_text(json.dumps(ERG, indent=1, default=str))
def fort(t): sys.stderr.write('\rR%d %s' % (R, t[:95].ljust(95))); sys.stderr.flush()
def schritt(n, **k): k.update(name=n, t_s=round(time.perf_counter() - T0, 2), peak_mib=peak()); ERG['schritte'].append(k); speichern()
def ende(st, **k):
    ERG.update(k); ERG['status'] = st; ERG['gesamt_s'] = round(time.perf_counter() - T0, 2); ERG['peak_mib_kind'] = peak(); speichern()
    fort('fertig ' + st); sys.stderr.write('\n'); sys.exit(0 if st == 'OK' else 2)
def fehler(n, **k): schritt('FEHLER ' + n, **k); ende('FEHLER', fehler=dict(name=n, **k))

# ---- Aufbau (ohne Vergleichskette; Zielhash wird als Gleichheit festgelegt) ----
g, inputs, blog, bout, _ = SZ.baue_bitgraph(h76, BASIS, BITS, 0, runden=R, mit_ziel=False)
N, zops, zout, eing, _ = SZ.baue_ziffernnetz(h76, BASIS, BITS, 0, 'voll', mit_ziel=False, runden=R)
zu = SZ.wortzuordnung(blog, zops); zu.append(('H1_nonce', tuple(bout['H1_words'][3]), list(zout['H1_words'][3])))
schritt('Aufbau', graphknoten=len(g.nodes), ziffernvariablen=len(N.dom), beziehungen=len(N.bez))
d = [3] * len(g.nodes); d[0] = 1; d[1] = 2; zd = list(N.dom)
digest = bout['digest2']
for i in range(256):
    node = digest[(i // 8) // 4][8 * (3 - (i // 8) % 4) + i % 8]
    if SZ.dom_schneiden(d, node, 1 << ((HSTAR >> i) & 1)) == 0: fehler('Zielhash-Bit widerspricht Konstante', bit=i)
for k, w in enumerate(zout['digest2']):
    for j, v in enumerate(w):
        zd[v] &= 1 << ((ZIEL[k] >> (2 * j)) & 3)
        if zd[v] == 0: fehler('Zielhash-Ziffer widerspricht Konstante', wort=k, ziffer=j)
schritt('Festlegung', beschreibung='Hash = Zielhash: 256 Digestbits und 128 Digestziffern fest; Kontrollnonce NICHT uebergeben')
MESS = [('H1', i + 1, nm, bout['H1_trace'][i][k], zout['H1_trace'][i][k]) for i in range(R) for k, nm in enumerate('abcdefgh')]
MESS += [('H2', i + 1, nm, bout['H2_trace'][i][k], zout['H2_trace'][i][k]) for i in range(R) for k, nm in enumerate('abcdefgh')]
def bits_fest(bw): return sum(1 for b in bw if SZ.dom_von(d, b) in (1, 2))
def ziff_fest(zw): return sum(1 for v in zw if zd[v] and zd[v] & (zd[v] - 1) == 0)
def noncebits(): return [(i, SZ.dom_von(d, nd) >> 1) for i, nd in enumerate(inputs) if SZ.dom_von(d, nd) in (1, 2)]
def ausgeschlossen():
    f = dict(noncebits()); return [n for n in GRUPPE if any(((n >> BITS[i]) & 1) != v for i, v in f.items())]
def knoten_fest(dd): return sum(1 for x in dd[2:] if x in (1, 2))
# ---- Stufe 1: E1 bis Fixpunkt ----
t = time.perf_counter(); st1, sw = e1_lauf(g, d, max_sweeps=10 ** 9); t1 = time.perf_counter() - t
nb1 = noncebits()
schritt('E1', status=st1, sweeps=sw, s=round(t1, 2), bitknoten_fest=knoten_fest(d), noncebits=nb1, verbleibende_kandidaten=256 - len(ausgeschlossen()) if st1 != 'WIDERSPRUCH' else 0)
karte_e1 = [dict(phase=p, runde=r, reg=nm, bits_fest=bits_fest(bw)) for p, r, nm, bw, zw in MESS]
status = st1; paare = None; info = {}; stufe = 'E1'
entschieden = st1 == 'WIDERSPRUCH' or len(nb1) == 8
# ---- Stufe 2: E1+E4, nur wenn E1 nicht entscheidet ----
if not entschieden:
    stufe = 'E1+E4'
    R_ = austausch(g, inputs, None, d, N, zu, zd, ZA.e4, MAXP, True, schritt=schritt, fort=fort, fehler=fehler,
                   zaehler=lambda d_, zd_: dict(noncebits=noncebits(), knoten_fest=knoten_fest(d_)))
    status, d, zd, paare, info = R_['status'], R_['d'], R_['zd'], R_['paare'], R_['info4']
    if R_['open_grund'] is not None: ERG['open_grund'] = R_['open_grund']
    np_ = info.get('nachpruefung_e3')
    if np_ is not None and (np_['geaendert'] or np_['status'] != 'FIXPUNKT'): fehler('Nachpruefung E3', nachpruefung=np_)
else:
    for nm, bw, zw in zu:
        for j in range(16): zd[zw[j]] &= SZ.bits_zu_ziffern(SZ.dom_von(d, bw[2 * j]), SZ.dom_von(d, bw[2 * j + 1]))
fort('Auswertung')
# ---- Orakel: alle 256 Kandidaten, Integer-Referenz ----
treffer = [n for n in GRUPPE if sha256d_r(n) == ZIEL]
assert KONTROLLE in treffer
aus = ausgeschlossen() if status != 'WIDERSPRUCH' else list(GRUPPE)
if any(n in aus for n in treffer): fehler('Falscher Ausschluss', ausgeschlossen=aus[:10], treffer=treffer, kontrolle=KONTROLLE)
if status == 'WIDERSPRUCH': fehler('Widerspruch trotz erreichbarem Zielhash', treffer=treffer)
verbleibend = [n for n in GRUPPE if n not in aus]
if len(verbleibend) == len(treffer) and set(verbleibend) == set(treffer): ausgang = 'TREFFER_ABGELEITET'
else: ausgang = 'OFFEN'
karte = [dict(phase=p, runde=r, reg=nm, bits_fest=bits_fest(bw), ziffern_fest=ziff_fest(zw), bits_fest_nach_e1=karte_e1[i]['bits_fest']) for i, (p, r, nm, bw, zw) in enumerate(MESS)]
ERG['karte'] = karte
ERG['ergebnis'] = dict(status=status, stufe=stufe, ausgang=ausgang, noncebits_nach_e1=nb1, noncebits_abgeleitet=noncebits(), ausgeschlossene_nonces=len(aus),
    verbleibende_kandidaten=len(verbleibend), orakel=dict(treffer=treffer, kontrollnonce=KONTROLLE, anzahl_treffer=len(treffer)),
    bitknoten_fest=knoten_fest(d), bitknoten_gesamt=len(g.nodes) - 2, ziffern_fest=sum(1 for m in zd if m and m & (m - 1) == 0),
    ziffern_fest_start=sum(1 for m in N.dom if m & (m - 1) == 0), ziffern_gesamt=len(zd),
    paare=(len(paare) if paare is not None else 0), paare_eingeschraenkt=(paare.eingeschraenkt() if paare is not None else None),
    e4_letzte_info={k: v for k, v in info.items() if k != 'nachpruefung_e3'} if info else None, nachpruefung=info.get('nachpruefung_e3') if info else None)
ende('OK')
