#!/usr/bin/env python3
"""VIER-WEGE-WAHRHEITSTABELLEN, KINDPROZESS (Fable, 2026-10-22). python -I tabellen4_kind.py <ausgabe.json>
Zwei freie Noncebits -> vier Kandidaten. JEDES Zwischenbit wird als Wahrheitstabelle mit vier Eintraegen gefuehrt (ein Eintrag je
Kandidat), gespeichert als 4-Bit-Maske 0..15. UND = bitweises Und der Masken, XOR = bitweises Xor, Negation = 15 - Maske;
Konstanten 0 und 1 sind die Masken 0 und 15. Das ist EXAKT (kein Verlust), weil eine Tabelle ueber vier Eingaben die Funktion
vollstaendig beschreibt. Identische Tabellen sind automatisch derselbe Wert (Maskenzahl) – gemeinsames Speichern ist damit
eingebaut; es gibt hoechstens 16 verschiedene Tabellen ueberhaupt.
Gerechnet wird derselbe Weg wie im Bitgraphen (pruefung.compress ueber beide Hashanwendungen, gatter-Ops-Schnittstelle), danach
die Zielvergleichskette wie in gatter.build. Referenz (hashlib) wird NUR nachher zum Pruefen gelesen, nie eingespeist.
Ausdruecklich: das ist eine gemeinsame Auswertung aller vier Moeglichkeiten, KEIN nachgewiesener Suchvorteil."""
import sys, json, time, struct, hashlib, resource, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent.parent / 'src' / 'kaestchen'))
import sha_ziffern as SZ, pruefung as P, gatter as G
AUS = sys.argv[1]; T0 = time.perf_counter()
def peak(): return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
ERG = dict(messung='Vier-Wege-Wahrheitstabellen bei zwei freien Noncebits', python=platform.python_version(),
           rechner='Fable-Container Linux, Intel Xeon 2.10 GHz (2 Kerne), CPU, reines Python', faelle=[], status='LAEUFT')

class TabellenOps:
    """Wie gatter.Ops, aber die Knoten sind 4-Bit-Masken (Wahrheitstabellen ueber die vier Kandidaten)."""
    def __init__(self): self.n_und = 0; self.n_xor = 0; self.gesehen = set()
    def _m(self, v): self.gesehen.add(v); return v
    def g(self, op, a, b):
        if op == 'and': self.n_und += 1; return self._m(a & b)
        self.n_xor += 1; return self._m(a ^ b)
    const = staticmethod(lambda x: tuple(15 if (x >> i) & 1 else 0 for i in range(32)))
    rot = staticmethod(lambda x, n: x[n:] + x[:n])
    shr = staticmethod(lambda x, n: x[n:] + (0,) * n)
    def xor3(self, a, b, c): return tuple(self.g('xor', self.g('xor', x, y), z) for x, y, z in zip(a, b, c))
    def ch(self, a, b, c): return tuple(self.g('xor', z, self.g('and', x, self.g('xor', y, z))) for x, y, z in zip(a, b, c))
    def maj(self, a, b, c): return tuple(self.g('xor', self.g('and', x, y), self.g('and', z, self.g('xor', x, y))) for x, y, z in zip(a, b, c))
    def add(self, *ws):
        r = ws[0]
        for w in ws[1:]:
            carry = 0; out = []
            for a, b in zip(r, w):
                axb = self.g('xor', a, b); out.append(self.g('xor', axb, carry))
                carry = self.g('xor', self.g('and', a, b), self.g('and', axb, carry))
            r = tuple(out)
        return r
class Adapter(TabellenOps):
    """Signatur wie sha_ziffern.rechenweg erwartet (xor dreistellig)."""
    def xor(self, a, b, c): return self.xor3(a, b, c)

FAELLE = json.loads((HERE / 'FAELLE_SHA256D.json').read_text())['faelle']
alle_ok = True
for FD in FAELLE:
    h76 = bytes.fromhex(FD['header_hex_ohne_nonce']); T = int(FD['target_hex'], 16)
    maske = 3; basis = (FD['referenz_treffer'][0] & ~maske) if FD['referenz_treffer'] else 0
    noncen = [basis | i for i in range(4)]
    t = time.perf_counter(); ops = Adapter()
    padded = P.padded(h76 + basis.to_bytes(4, 'little')); w3 = struct.unpack('>16I', padded[64:])[3]
    wort3 = list(TabellenOps.const(w3))
    for i, b in enumerate([0, 1]):                       # Eingangsbit b -> Tabelle ueber die vier Kandidaten
        pos = SZ.nonce_wortbit(b); wort3[pos] = sum(1 << k for k in range(4) if (noncen[k] >> b) & 1)
    out = SZ.rechenweg(ops, h76, basis, [0, 1], 'voll', nonce_wort=tuple(wort3))
    t_rechnung = time.perf_counter() - t
    # Zielvergleichskette wie gatter.build, auf Tabellen
    t = time.perf_counter(); digest = out['digest2']
    numeric = [digest[byte // 4][8 * (3 - byte % 4) + bit] for byte in range(32) for bit in range(8)]
    le = 15
    for i, x in enumerate(numeric):
        if T >> i & 1: le = 15 ^ ops.g('and', x, 15 ^ le)
        else: le = ops.g('and', 15 ^ x, le)
    t_ziel = time.perf_counter() - t
    # ---- unabhaengige Pruefung gegen hashlib, erst jetzt ----
    pruef = []
    for k, n in enumerate(noncen):
        dig_tab = struct.pack('>8I', *[sum(((w[i] >> k) & 1) << i for i in range(32)) for w in digest])
        echt = hashlib.sha256(hashlib.sha256(h76 + n.to_bytes(4, 'little')).digest()).digest()
        treffer = int.from_bytes(echt, 'little') <= T
        pruef.append(dict(nonce=n, digest_gleich_hashlib=(dig_tab == echt), hash_bitcoin=echt[::-1].hex(),
                          fuehrende_nullbits=256 - int.from_bytes(echt, 'little').bit_length(),
                          zielentscheidung_tabelle=bool((le >> k) & 1), zielentscheidung_hashlib=treffer,
                          stimmt=((le >> k) & 1) == int(treffer)))
    t = time.perf_counter()
    for wdh in range(100):
        for n in noncen:
            hh = hashlib.sha256(hashlib.sha256(h76 + n.to_bytes(4, 'little')).digest()).digest()
            int.from_bytes(hh, 'little') <= T
    t_hashlib = (time.perf_counter() - t) / 100
    ok = all(p['digest_gleich_hashlib'] and p['stimmt'] for p in pruef)
    treffer_erhalten = None
    if FD['referenz_treffer']:
        z = FD['referenz_treffer'][0]; k = noncen.index(z)
        treffer_erhalten = bool((le >> k) & 1)
        ok = ok and treffer_erhalten
    alle_ok = alle_ok and ok
    ERG['faelle'].append(dict(fall=FD['name'], noncen=noncen, zielnullbits=FD['target_nullbits'],
        aufbauzeit_rechnung_s=round(t_rechnung, 2), aufbauzeit_zielkette_s=round(t_ziel, 2),
        und_gatter=ops.n_und, xor_gatter=ops.n_xor, gatter_gesamt=ops.n_und + ops.n_xor,
        unterschiedliche_tabellen=len(ops.gesehen), tabellen_moeglich=16, tabellen_liste=sorted(ops.gesehen),
        zielmaske_le=le, kandidaten_die_das_ziel_erfuellen=[noncen[k] for k in range(4) if (le >> k) & 1],
        vergleich_direkt_hashlib=dict(vier_kandidaten_s=round(t_hashlib, 8), mittel_aus_wiederholungen=100,
            faktor_tabellen_langsamer=round((t_rechnung + t_ziel) / t_hashlib)),
        pruefung_gegen_hashlib=pruef, bekannter_treffer_erhalten=treffer_erhalten, alles_korrekt=ok, peak_mib=peak()))
ERG['status'] = 'OK' if alle_ok else 'FEHLER'
ERG['gesamt_s'] = round(time.perf_counter() - T0, 2); ERG['peak_mib'] = peak()
ERG['einordnung'] = ('Gemeinsame exakte Auswertung aller vier Kandidaten in einem Durchgang. KEIN nachgewiesener Suchvorteil: '
    'die Kosten je Gatter sind dieselben wie bei einer Einzelrechnung, nur werden vier Kandidaten gleichzeitig gefuehrt. '
    'Hoechstens 16 verschiedene Tabellen existieren ueberhaupt; die Rechnung ist damit exakt, aber nicht kleiner als vier Einzelrechnungen.')
(HERE / AUS).write_text(json.dumps(ERG, indent=1))
print(json.dumps({k: v for k, v in ERG.items() if k != 'faelle'}, indent=1))
for f in ERG['faelle']: print({k: f[k] for k in ('fall','noncen','aufbauzeit_rechnung_s','gatter_gesamt','unterschiedliche_tabellen','zielmaske_le','kandidaten_die_das_ziel_erfuellen','bekannter_treffer_erhalten','alles_korrekt','peak_mib')})
