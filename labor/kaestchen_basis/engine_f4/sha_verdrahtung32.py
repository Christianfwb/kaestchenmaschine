#!/usr/bin/env python3
"""SHA-256-Verdrahtung auf bitkern32 (BLOCKTEST32). Nur Standardbibliothek. Keine Referenz, kein hashlib.

Namen: Woerter "<p>_<art><nr>", Bits "<wort>.<i>" (i = Stellenwert 2^i, SHA-Wort big-endian als Zahl).
Konstanten K und IV stehen hier als Zahlen (FIPS 180-4) und gehen mit Herkunft K bzw. IV als START in den Kern.
Eine Runde t (FIPS 180-4 6.2.2):
  S1 = Sigma1(e); ch = Ch(e,f,g); x1 = h + S1; x2 = x1 + ch; x3 = x2 + W_t; T1 = x3 + K_t
  S0 = Sigma0(a); maj = Maj(a,b,c); T2 = S0 + maj; e' = d + T1; a' = T1 + T2; (b',c',d',f',g',h') = (a,b,c,e,f,g)
Fahrplan: y1 = W_(t-16) + sigma0(W_(t-15)); y2 = y1 + W_(t-7); W_t = y2 + sigma1(W_(t-2)).
Feedforward: H_j = S64_j + Start_j (B-R6, oder B-R5 wenn der Start eine Konstante ist)."""
K = [0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
     0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
     0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
     0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
     0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
     0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
     0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
     0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]
IV = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
PAD1 = [0x80000000] + [0] * 10 + [640]
PAD2 = [0x80000000] + [0] * 6 + [256]
ROT = dict(S0=(2, 13, 22), S1=(6, 11, 25), s0=(7, 18), s1=(17, 19))
SHR = dict(s0=3, s1=10)
ZUSTAND = 'abcdefgh'


def runde(kern, p, t, st, W, K_t):
    """Eine Runde. st: 8 Wortnamen (a..h), W: Wortname W_t, K_t: Konstante. Liefert 8 neue Wortnamen."""
    a, b, c, d, e, f, g, h = st
    n = lambda art: f"{p}_{art}{t}"
    kern.sigma(n('S1'), e, ROT['S1'], (), f"B-R4 Sigma1 {p} {t}")
    kern.bitfunktion('Ch', n('ch'), [e, f, g], f"B-R3 Ch {p} {t}")
    kern.addition(n('x1'), h, n('S1'))
    kern.addition(n('x2'), n('x1'), n('ch'))
    kern.addition(n('x3'), n('x2'), W)
    kern.addition_konst(n('T1'), n('x3'), K_t, 'K')
    kern.sigma(n('S0'), a, ROT['S0'], (), f"B-R4 Sigma0 {p} {t}")
    kern.bitfunktion('Maj', n('maj'), [a, b, c], f"B-R3 Maj {p} {t}")
    kern.addition(n('T2'), n('S0'), n('maj'))
    kern.addition(f"{p}_e{t+1}", d, n('T1'))
    kern.addition(f"{p}_a{t+1}", n('T1'), n('T2'))
    return [f"{p}_a{t+1}", a, b, c, f"{p}_e{t+1}", e, f, g]


def fahrplan(kern, p, W16):
    """W16: 16 Wortnamen. Liefert 64 Wortnamen."""
    W = list(W16)
    for t in range(16, 64):
        n = lambda art: f"{p}_{art}{t}"
        kern.sigma(n('s0'), W[t-15], ROT['s0'], (SHR['s0'],), f"B-R4 sigma0 {p} {t}")
        kern.sigma(n('s1'), W[t-2], ROT['s1'], (SHR['s1'],), f"B-R4 sigma1 {p} {t}")
        kern.addition(n('y1'), W[t-16], n('s0'))
        kern.addition(n('y2'), n('y1'), W[t-7])
        kern.addition(f"{p}_W{t}", n('y2'), n('s1'))
        W.append(f"{p}_W{t}")
    return W


def kompression(kern, p, start, W16, start_konst=None):
    """start: 8 Wortnamen; W16: 16 Wortnamen; start_konst: 8 Zahlen, wenn der Start eine Konstante (IV) ist.
    Liefert (H-Wortnamen, Endzustand-Wortnamen, W-Wortnamen)."""
    W = fahrplan(kern, p, W16)
    st = list(start)
    for t in range(64):
        st = runde(kern, p, t, st, W[t], K[t])
    H = []
    for j in range(8):
        h = f"{p}_H{j}"
        if start_konst is not None:
            kern.addition_konst(h, st[j], start_konst[j], 'IV')
        else:
            kern.addition(h, st[j], start[j])
        H.append(h)
    return H, st, W


def konstanten_woerter(kern, p, art, werte, herkunft):
    namen = []
    for j, w in enumerate(werte):
        n = f"{p}_{art}{j}"; kern.wort_start(n, w, herkunft); namen.append(n)
    return namen


def woerter_aus_bytes(b):
    return [int.from_bytes(b[i:i+4], 'big') for i in range(0, len(b), 4)]


def sha256d_header(kern, header76, nonce, herkunft_nonce='AUFGABE'):
    """Vollstaendige Doppel-SHA256 eines 80-Byte-Headers im Kern: drei Kompressionen. Liefert die 8 Endhash-Wortnamen.
    header76: 76 feste Bytes (Herkunft HEADER); nonce: 32-Bit-Zahl (little-endian im Header) mit eigener Herkunft."""
    assert len(header76) == 76
    iv = konstanten_woerter(kern, 'k0', 'IV', IV, 'IV')
    W0 = konstanten_woerter(kern, 'k0', 'W', woerter_aus_bytes(header76[:64]), 'HEADER')
    H0, _, _ = kompression(kern, 'k0', iv, W0, start_konst=IV)
    W1 = konstanten_woerter(kern, 'k1', 'W', woerter_aus_bytes(header76[64:76]), 'HEADER')
    w3 = int.from_bytes(nonce.to_bytes(4, 'little'), 'big')
    kern.wort_start('k1_W3', w3, herkunft_nonce); W1.append('k1_W3')
    W1 += konstanten_woerter(kern, 'k1', 'P', PAD1, 'PAD')
    H1, _, _ = kompression(kern, 'k1', H0, W1)
    iv2 = konstanten_woerter(kern, 'k2', 'IV', IV, 'IV')
    W2 = H1 + konstanten_woerter(kern, 'k2', 'P', PAD2, 'PAD')
    H2, _, _ = kompression(kern, 'k2', iv2, W2, start_konst=IV)
    return H2


def durchgang2(kern, zwischenhash8):
    """A3a: Durchgang 2 allein. zwischenhash8: 8 Zahlen (Herkunft AUFGABE). Liefert 8 Endhash-Wortnamen."""
    iv2 = konstanten_woerter(kern, 'k2', 'IV', IV, 'IV')
    Z = konstanten_woerter(kern, 'k2', 'Z', zwischenhash8, 'AUFGABE')
    W2 = Z + konstanten_woerter(kern, 'k2', 'P', PAD2, 'PAD')
    H2, _, _ = kompression(kern, 'k2', iv2, W2, start_konst=IV)
    return H2


def hash_zahl_bits(H8):
    """Bitnamen der Zahl H (little-endian ueber die 32 Digestbytes), Index i = Stellenwert 2^i.
    Byte k = Bits 8*(3 - k%4) .. +7 von Wort H_(k//4)."""
    namen = []
    for i in range(256):
        k = i // 8
        namen.append(f"{H8[k // 4]}.{8 * (3 - k % 4) + i % 8}")
    return namen
