"""runden_modell.py: rundenreduziertes SHA256d (r Runden je Kompression, alle drei Kompressionen) fuer die Testreihe (GO 20:35).
Vollmodell (sha_verdrahtung32.kompression, 64 Runden) bleibt unveraendert; hier ein eigener Pfad mit Parameter r.
Referenz sha256d_r ist unabhaengig in reinem Python geschrieben (kein Engine-Code); bei r = 64 muss sie hashlib treffen (Test)."""
import sys as _s, pathlib as _p; _s.path.insert(0, str(_p.Path(__file__).resolve().parent))
from gemeinsam import *
import hashlib

# ---------- unabhaengige Referenz ----------
_K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
      0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
      0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
      0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
_IV = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]
M = 0xffffffff
def _rotr(x, n): return ((x >> n) | (x << (32 - n))) & M
def _komp(H, block, r):
    W = [int.from_bytes(block[i:i+4], 'big') for i in range(0, 64, 4)]
    for t in range(16, max(16, r)):
        s0 = _rotr(W[t-15], 7) ^ _rotr(W[t-15], 18) ^ (W[t-15] >> 3); s1 = _rotr(W[t-2], 17) ^ _rotr(W[t-2], 19) ^ (W[t-2] >> 10)
        W.append((W[t-16] + s0 + W[t-7] + s1) & M)
    a, b, c, d, e, f, g, h = H
    for t in range(r):
        S1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25); ch = (e & f) ^ (~e & g & M); T1 = (h + S1 + ch + _K[t] + W[t]) & M
        S0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22); maj = (a & b) ^ (a & c) ^ (b & c); T2 = (S0 + maj) & M
        a, b, c, d, e, f, g, h = (T1 + T2) & M, a, b, c, (d + T1) & M, e, f, g
    return [(x + y) & M for x, y in zip(H, (a, b, c, d, e, f, g, h))]
def sha256_r(msg, r):
    """SHA-256 mit r Runden je Kompression (Fahrplan W_t fuer t < r), Standard-Padding."""
    ml = len(msg) * 8; msg = msg + b'\x80' + b'\x00' * ((55 - len(msg)) % 64) + ml.to_bytes(8, 'big')
    H = list(_IV)
    for i in range(0, len(msg), 64): H = _komp(H, msg[i:i+64], r)
    return b''.join(x.to_bytes(4, 'big') for x in H)
def sha256d_r(msg, r): return sha256_r(sha256_r(msg, r), r)

# ---------- Verdrahtung mit r Runden ----------
def kompression_r(kern, p, start, W16, r, start_konst=None):
    import sha_verdrahtung32 as sv
    W = list(W16)
    for t in range(16, max(16, r)):
        n = lambda art: f"{p}_{art}{t}"
        kern.sigma(n('s0'), W[t-15], sv.ROT['s0'], (sv.SHR['s0'],), f"B-R4 sigma0 {p} {t}")
        kern.sigma(n('s1'), W[t-2], sv.ROT['s1'], (sv.SHR['s1'],), f"B-R4 sigma1 {p} {t}")
        kern.addition(n('y1'), W[t-16], n('s0')); kern.addition(n('y2'), n('y1'), W[t-7]); kern.addition(f"{p}_W{t}", n('y2'), n('s1')); W.append(f"{p}_W{t}")
    st = list(start)
    for t in range(r): st = sv.runde(kern, p, t, st, W[t], sv.K[t])
    H = []
    for j in range(8):
        h = f"{p}_H{j}"
        if start_konst is not None: kern.addition_konst(h, st[j], start_konst[j], 'IV')
        else: kern.addition(h, st[j], start[j])
        H.append(h)
    return H, st, W

def aufbau_r(kern, a, mit_ziel=True):
    """Wie a4_basis32.aufbau, aber r = a['runden'] je Kompression. arm 'W': exakter Zielhash (ziel_hash_hex, Digestbytes);
    arm 'M': Zahl-Vergleich gegen target_hex. Liefert (H2, verdeckt, zielbit)."""
    import sha_verdrahtung32 as sv, a4_basis32
    r = a['runden']; header76 = bytes.fromhex(a['header76_hex']); basis = a['basis']; maske = a['maske']
    iv = sv.konstanten_woerter(kern, 'k0', 'IV', sv.IV, 'IV')
    W0 = sv.konstanten_woerter(kern, 'k0', 'W', sv.woerter_aus_bytes(header76[:64]), 'HEADER')
    H0, _, _ = kompression_r(kern, 'k0', iv, W0, r, start_konst=sv.IV)
    W1 = sv.konstanten_woerter(kern, 'k1', 'W', sv.woerter_aus_bytes(header76[64:76]), 'HEADER')
    w3_basis = int.from_bytes((basis & ~maske & 0xffffffff).to_bytes(4, 'little'), 'big')
    nr = kern.buche('START AUFGABE', [], 'WORT', ('k1_W3', w3_basis, 32)); kern.worte['k1_W3'] = nr
    verdeckt = []
    for j in range(32):
        pos = a4_basis32.w3_bit(j)
        if (maske >> j) & 1: verdeckt.append(f"k1_W3.{pos}")
        else: kern.setze(f"k1_W3.{pos}", (w3_basis >> pos) & 1, f"B-R1 k1_W3 bit {pos}", [nr])
    kern.verdeckt = set(verdeckt); W1.append('k1_W3'); W1 += sv.konstanten_woerter(kern, 'k1', 'P', sv.PAD1, 'PAD')
    H1, _, _ = kompression_r(kern, 'k1', H0, W1, r)
    iv2 = sv.konstanten_woerter(kern, 'k2', 'IV', sv.IV, 'IV'); W2 = H1 + sv.konstanten_woerter(kern, 'k2', 'P', sv.PAD2, 'PAD')
    H2, _, _ = kompression_r(kern, 'k2', iv2, W2, r, start_konst=sv.IV)
    hb = sv.hash_zahl_bits(H2)
    if not mit_ziel: return H2, verdeckt, None
    if a['arm'] == 'W':
        Z = int.from_bytes(bytes.fromhex(a['ziel_hash_hex']), 'little')
        nrz = kern.buche('START ZIEL', [], 'WORT', ('ZIELHASH', Z, 256)); kern.worte['ZIELHASH'] = nrz
        for i in range(256): kern.xor_gl([hb[i]], (Z >> i) & 1, f"B-R4 Ziel W bit {i}", [nrz])
        zielbit = None
    else:
        zielbit = kern.vergleich(hb, int(a['target_hex'], 16), 256, praefix='V'); kern.xor_gl([zielbit], 1, 'B-R4 Ziel M treffer', [])
    return H2, verdeckt, zielbit

def vertrag_r(a):
    import bitkern32 as bk
    k = bk.Kern(32); aufbau_r(k, a); return bk.vertrag_aus(k)

def pruefen_r(t):
    """Vertragspruefung fuer reduzierte Aufgaben."""
    for k in ('header76_hex', 'basis', 'maske', 'runden', 'arm'):
        if k not in t: raise ValueError('Vertrag (runden): Feld fehlt ' + k)
    if not 1 <= t['runden'] <= 64: raise ValueError('runden 1..64')
    if t.get('test_w22') is not None: raise ValueError('test_w22 nicht erlaubt')
    if t['basis'] & t['maske']: raise ValueError('freie Bits muessen in basis 0 sein')
    if t['arm'] == 'W':
        if len(bytes.fromhex(t['ziel_hash_hex'])) != 32: raise ValueError('ziel_hash_hex 32 Bytes')
        if 'referenz_nonce' in t: raise ValueError('referenz_nonce darf NICHT im Vertrag stehen (Leck)')
    elif t['arm'] == 'M':
        if t.get('target_kind') != 'DIAGNOSE': raise ValueError('reduzierte M-Aufgaben nur als DIAGNOSE')
    else: raise ValueError('arm W|M')
    return True

def referenz_digest(t, nonce):
    return sha256d_r(bytes.fromhex(t['header76_hex']) + nonce_bytes(nonce), t['runden'])

def herleiten_r(t, sekunden=60, meldung=lambda s: None):
    """Propagation + anwendbare erweiterte Regeln (Z-R1 nur bei arm M; RB/RT; RT-R3) auf frischem Kern des reduzierten Vertrags.
    Z-R2/Z-R3 (an k2_e63 gebunden) werden bewusst nicht benutzt. Liefert (kern, protokoll, zeiten)."""
    import bitkern32 as bk, threading
    from rueckweg import KernRueckweg
    from anschluss import saettigen
    from rt3_adapter import anwenden as rt3
    import regelprofil
    z = {}; k = KernRueckweg(32); k.stop_event = threading.Event(); k.deadline = time.monotonic() + sekunden; k.rueckweg_an = True
    t0 = time.perf_counter(); aufbau_r(k, t); z['aufbau'] = time.perf_counter() - t0
    prot = dict(schritte=[], stop=None, regeln='fixpunkt, Z-R1 (arm M), RB/RT-R1/RT-R2 (anschluss), RT-R3; ohne Z-R2/Z-R3')
    t0 = time.perf_counter()
    def schritt(name, fn):
        e = dict(name=name, bits_vorher=len(k.wert), zeilen_vorher=len(k.buch))
        try: fn(); k.fixpunkt(); e['status'] = 'BEENDET'
        except (bk.Budget, bk.Widerspruch) as ex: e['status'] = type(ex).__name__ + ': ' + str(ex); prot['stop'] = e['status']
        e.update(bits_nachher=len(k.wert), zeilen_nachher=len(k.buch)); prot['schritte'].append(e); meldung(f"{name}: {e['status']} bits {len(k.wert)}")
        return e['status'] == 'BEENDET'
    if schritt('fixpunkt', lambda: None):
        if t['arm'] == 'M':
            from zielbits import anwenden as zielbits
            schritt('Z-R1', lambda: zielbits(k))
        k.tabellen_rueckgabe = True; k.relationstabellen_an = True
        if schritt('RB/RT-R1/RT-R2', lambda: saettigen(k, runden=regelprofil.GRENZEN['anschluss_runden'])):
            k.rt3_einsetzen = True; k.rt3_maxgl = regelprofil.GRENZEN['rt3_gleichung_freie_namen']
            schritt('RT-R3', lambda: rt3(k))
    z['herleitung'] = time.perf_counter() - t0
    return k, prot, z

if __name__ == '__main__':
    import random
    rnd = random.Random(0); ok = True
    for _ in range(20):
        m = rnd.randbytes(80)
        if sha256d_r(m, 64) != hashlib.sha256(hashlib.sha256(m).digest()).digest(): ok = False
    print('Referenz r=64 == hashlib:', ok)
