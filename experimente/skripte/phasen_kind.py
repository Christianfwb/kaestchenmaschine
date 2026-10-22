#!/usr/bin/env python3
"""PHASENVERGLEICH MIT NUMPY, EXAKT IN GANZEN ZAHLEN (Fable, 2026-10-22). python -I phasen_kind.py <ausgabe.json>

DARSTELLUNG – ausdrueckliche Definition (Ghosts Vorgabe):
  Grundfaelle: bei n freien Eingangsbits gibt es N = 2^n Faelle. Ein Fall ist eine vollstaendige Belegung der freien Bits.
  Zustand eines Bits = ein ganzzahliger Vektor der Laenge N: Eintrag k ist der Wert dieses Bits IM FALL k (0 oder 1).
    - EINZELWERT (sicher bekannt): alle N Eintraege gleich (konstant 0 oder konstant 1).
    - ALTERNATIVE MOEGLICHKEITEN: Eintraege verschieden – das Bit ist je nach Fall anders.
    - GEMEINSAME BINDUNG: entsteht dadurch, dass ALLE Bits ueber DENSELBEN Fallindex k indiziert sind. Die Bindung steckt
      nicht in den Werten, sondern in der gemeinsamen Nummerierung der Faelle. Sie geht genau dann verloren, wenn man je
      Variable nur noch die MENGE ihrer Werte behaelt (Domaene) oder nur Wertepaare (Paartabelle) statt des Fallindex.
  Gatter exakt in ganzen Zahlen, ohne Gleitkomma und ohne Rundung: UND = a*b, XOR = a+b-2*a*b, NICHT = 1-a (elementweise).
  Zielbedingung/Rueckwaerts: ein Ausgang wird nicht "gesetzt", sondern die Faelle, die ihn nicht erfuellen, werden gestrichen
    (Auswahl der Fallindizes). Das ist exakt und verliert die Bindung nicht, weil der Fallindex erhalten bleibt.
  WICHTIG: Der Vektor hat N Eintraege. Die Bindung wird also dadurch erhalten, dass alle Faelle EINZELN mitgefuehrt werden.
"""
import sys, json, time, struct, hashlib, resource, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
AUS = sys.argv[1]; T0 = time.perf_counter()
t = time.perf_counter(); import numpy as np; T_NUMPY_IMPORT = time.perf_counter() - t
import sha_ziffern as SZ, pruefung as P
from ziffern import Netz, TABELLEN
import ziffern_komp as ZK, ziffern_sha as ZS
def peak(): return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
ERG = dict(messung='Phasenvergleich (exakte Ganzzahl-Fallvektoren) gegen Paartabelle und Vier-Wege-Tabelle',
           python=platform.python_version(), numpy=np.__version__, numpy_import_s=round(T_NUMPY_IMPORT, 3),
           rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU', status='LAEUFT')

# ============ TEIL 1: PRUEFSTEIN "nur 00 oder 11" ============
# Aufgabe: z = x XOR y, rueckwaerts mit z = 0. Erlaubt muessen genau (0,0) und (1,1) sein; 01 und 10 duerfen NICHT hinzukommen.
WDH = 20000
def phasen_pruefstein():
    faelle = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=np.int64)   # alle Belegungen (x, y)
    x = faelle[:, 0].copy(); y = faelle[:, 1].copy(); ops = 0
    z = x + y - 2 * x * y; ops += 1                                        # XOR exakt in ganzen Zahlen
    behalten = (z == 0)                                                    # rueckwaerts: Faelle mit z != 0 streichen
    erlaubt = {(int(a), int(b)) for a, b in faelle[behalten]}
    paare = {(int(a), int(b)) for a, b in faelle[behalten]}
    speicher = x.nbytes + y.nbytes + z.nbytes + behalten.nbytes
    return erlaubt, paare, ops, speicher
def paartabelle_pruefstein():
    N = Netz(2); xs = N.wort('x'); ys = N.wort('y')          # w=2 -> eine Ziffer je Wort, Werte 0..3; wir nutzen Bit 0
    # exakte Modellierung mit unserer eigenen Maschinerie: XOR-Beziehung ueber Ziffern, Ergebnis auf 0 festgelegt
    z = N.xor(xs, ys, 'z'); N.fest(z[0], 0)
    for v in xs + ys: N.dom[v] &= 0b0011                      # nur Ziffernwerte 0 und 1 (= ein Bit)
    st, dom, paare, inf = ZK.e4(N, list(N.dom), max_paare=1000)
    erl = {(a, b) for a in range(2) for b in range(2) if (dom[xs[0]] >> a) & 1 and (dom[ys[0]] >> b) & 1}
    m = paare.get((xs[0], ys[0]) if xs[0] < ys[0] else (ys[0], xs[0]))
    paar_erl = None
    if m is not None:
        lo, hi = (xs[0], ys[0]) if xs[0] < ys[0] else (ys[0], xs[0])
        paar_erl = {((a, b) if lo == xs[0] else (b, a)) for a in range(2) for b in range(2) if (m >> (a * 4 + b)) & 1}
    return erl, paar_erl, len(paare), inf.get('tupelops')
def viererteabelle_pruefstein():
    # Vier-Wege-Tabelle: jedes Bit als 4-Bit-Maske ueber die vier Faelle (x,y) = 00,01,10,11
    x = 0b1100; y = 0b1010; ops = 0                           # Bit k der Maske = Wert im Fall k  (Faelle: 00,01,10,11)
    z = x ^ y; ops += 1
    behalten = ~z & 0b1111                                    # Faelle mit z = 0
    faelle = [(0, 0), (0, 1), (1, 0), (1, 1)]
    erl = {faelle[k] for k in range(4) if (behalten >> k) & 1}
    return erl, erl, ops, 3 * sys.getsizeof(0)
pz, pz_paar, pz_ops, pz_mem = phasen_pruefstein()
tz, tz_paar, tz_ops, tz_mem = viererteabelle_pruefstein()
dz, dz_paar, dz_paare, dz_ops = paartabelle_pruefstein()
soll = {(0, 0), (1, 1)}
# Zeiten (ohne NumPy-Import), getrennt gemessen
t = time.perf_counter()
for _ in range(WDH): phasen_pruefstein()
t_ph = (time.perf_counter() - t) / WDH
t = time.perf_counter()
for _ in range(WDH): viererteabelle_pruefstein()
t_tab = (time.perf_counter() - t) / WDH
t = time.perf_counter()
for _ in range(50): paartabelle_pruefstein()
t_paar = (time.perf_counter() - t) / 50
pruefstein = dict(
    soll_erlaubt=sorted(soll),
    phasen=dict(erlaubt=sorted(pz), korrekt=(pz == soll), operationen=pz_ops, speicher_byte=pz_mem, zeit_s=round(t_ph, 9)),
    vier_wege_tabelle=dict(erlaubt=sorted(tz), korrekt=(tz == soll), operationen=tz_ops, speicher_byte=tz_mem, zeit_s=round(t_tab, 9)),
    paartabelle=dict(einzeldomaenen_erlaubt=sorted(dz), paarmaske_erlaubt=(sorted(dz_paar) if dz_paar else None),
                     korrekt_als_paar=(dz_paar == soll), einzeldomaenen_allein_korrekt=(dz == soll),
                     gespeicherte_paare=dz_paare, tupeloperationen=dz_ops, zeit_s=round(t_paar, 9)),
    bemerkung=('Bei NUR ZWEI Variablen ist die Bindung 00/11 eine reine Paarbeziehung – unsere Paartabelle haelt sie exakt. '
               'Die Einzeldomaenen allein (ohne Paar) lassen 01 und 10 faelschlich zu; deshalb sind beide Zeilen getrennt ausgewiesen. '
               'Phasenvektor und Vier-Wege-Tabelle halten sie ebenfalls exakt – sie fuehren die vier Faelle einzeln mit.'))
ERG['pruefstein'] = pruefstein
bestanden = pruefstein['phasen']['korrekt'] and pruefstein['vier_wege_tabelle']['korrekt'] and pruefstein['paartabelle']['korrekt_als_paar']
ERG['pruefstein_bestanden'] = bestanden
if not bestanden:
    ERG['status'] = 'FEHLER'; ERG['gesamt_s'] = round(time.perf_counter() - T0, 2); ERG['peak_mib'] = peak()
    (HERE / AUS).write_text(json.dumps(ERG, indent=1, default=str)); print('Pruefstein NICHT bestanden'); sys.exit(2)

# ============ TEIL 2: die beiden Zwei-Bit-SHA-Faelle in Phasendarstellung ============
class PhasenOps:
    """Jedes Bit = Ganzzahlvektor der Laenge 4 (ein Eintrag je Fall). UND = a*b, XOR = a+b-2ab, NICHT = 1-a. Exakt, kein Gleitkomma."""
    def __init__(self):
        self.n_und = 0; self.n_xor = 0
        
    def g(self, op, a, b):
        if op == 'and': self.n_und += 1; return a * b
        self.n_xor += 1; return a + b - 2 * a * b
    def const(self, x): return tuple(EINS if (x >> i) & 1 else NULL for i in range(32))
    rot = staticmethod(lambda x, n: x[n:] + x[:n])
    shr = staticmethod(lambda x, n: x[n:] + (NULL,) * n)
    def xor(self, a, b, c): return tuple(self.g('xor', self.g('xor', p, q), r) for p, q, r in zip(a, b, c))
    def ch(self, a, b, c): return tuple(self.g('xor', z, self.g('and', x, self.g('xor', y, z))) for x, y, z in zip(a, b, c))
    def maj(self, a, b, c): return tuple(self.g('xor', self.g('and', x, y), self.g('and', z, self.g('xor', x, y))) for x, y, z in zip(a, b, c))
    def add(self, *ws):
        r = ws[0]
        for w in ws[1:]:
            carry = NULL; out = []
            for a, b in zip(r, w):
                axb = self.g('xor', a, b); out.append(self.g('xor', axb, carry))
                carry = self.g('xor', self.g('and', a, b), self.g('and', axb, carry))
            r = tuple(out)
        return r
NULL = np.zeros(4, dtype=np.int64); EINS = np.ones(4, dtype=np.int64)
FAELLE = json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle']
ERG['sha_faelle'] = []; alle_ok = True
for FD in FAELLE:
    h76 = bytes.fromhex(FD['header_hex_ohne_nonce']); T = int(FD['target_hex'], 16)
    maske = 3; basis = (FD['referenz_treffer'][0] & ~maske) if FD['referenz_treffer'] else 0
    noncen = [basis | i for i in range(4)]
    t = time.perf_counter(); ops = PhasenOps()
    w3 = struct.unpack('>16I', P.padded(h76 + basis.to_bytes(4, 'little'))[64:])[3]
    wort3 = list(ops.const(w3))
    for b in (0, 1): wort3[SZ.nonce_wortbit(b)] = np.array([(n >> b) & 1 for n in noncen], dtype=np.int64)
    out = SZ.rechenweg(ops, h76, basis, [0, 1], 'voll', nonce_wort=tuple(wort3))
    digest = out['digest2']
    numeric = [digest[byte // 4][8 * (3 - byte % 4) + bit] for byte in range(32) for bit in range(8)]
    le = EINS
    for i, x in enumerate(numeric):
        if T >> i & 1: le = 1 - ops.g('and', x, 1 - le)
        else: le = ops.g('and', 1 - x, le)
    t_lauf = time.perf_counter() - t
    pruef = []
    for k, n in enumerate(noncen):
        dig = struct.pack('>8I', *[sum(int(w[i][k]) << i for i in range(32)) for w in digest])
        echt = hashlib.sha256(hashlib.sha256(h76 + n.to_bytes(4, 'little')).digest()).digest()
        tr = int.from_bytes(echt, 'little') <= T
        pruef.append(dict(nonce=n, digest_gleich_hashlib=(dig == echt), zielentscheidung_phasen=bool(le[k]),
                          zielentscheidung_hashlib=tr, stimmt=(bool(le[k]) == tr),
                          fuehrende_nullbits=256 - int.from_bytes(echt, 'little').bit_length()))
    treffer_erhalten = (bool(le[noncen.index(FD['referenz_treffer'][0])]) if FD['referenz_treffer'] else None)
    ok = all(p['digest_gleich_hashlib'] and p['stimmt'] for p in pruef) and (treffer_erhalten is not False)
    alle_ok = alle_ok and ok
    speicher_je_bit = NULL.nbytes
    ERG['sha_faelle'].append(dict(fall=FD['name'], noncen=noncen, laufzeit_s=round(t_lauf, 2),
        und_gatter=ops.n_und, xor_gatter=ops.n_xor, gatter_gesamt=ops.n_und + ops.n_xor,
        speicher_je_bit_byte=speicher_je_bit, speicher_je_bit_vier_wege_tabelle_byte='1 kleine Ganzzahl (4-Bit-Maske)',
        erfuellende_kandidaten=[noncen[k] for k in range(4) if le[k]], bekannter_treffer_erhalten=treffer_erhalten,
        pruefung_gegen_hashlib=pruef, alles_korrekt=ok, peak_mib=peak()))
ERG['status'] = 'OK' if alle_ok else 'FEHLER'
ERG['gesamt_s'] = round(time.perf_counter() - T0, 2); ERG['peak_mib'] = peak()
(HERE / AUS).write_text(json.dumps(ERG, indent=1, default=str))
print(json.dumps(ERG['pruefstein'], indent=1, default=str))
for f in ERG['sha_faelle']: print({k: f[k] for k in ('fall','laufzeit_s','gatter_gesamt','speicher_je_bit_byte','erfuellende_kandidaten','bekannter_treffer_erhalten','alles_korrekt')})
print('Status', ERG['status'], ERG['gesamt_s'], 's, Peak', ERG['peak_mib'], 'MiB, NumPy-Import', ERG['numpy_import_s'], 's')
