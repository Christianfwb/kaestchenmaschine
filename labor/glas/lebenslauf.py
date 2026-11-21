"""lebenslauf.py - Der Lebenslauf einer Nonce: SHA256d eines 80-Byte-Headers, Runde fuer Runde, mit allem, was ein Miner sonst versteckt.
Reines Python, nur Standardbibliothek. Jede Zahl wird am Ende gegen hashlib geprueft.

Was der Lebenslauf zeigt:
  k0  erste Kompression (Header-Bytes 0..63): haengt NICHT von der Nonce ab -> "Midstate", wird in echten Minern einmal gerechnet.
  k1  zweite Kompression (Header-Bytes 64..79 + Padding): die Nonce ist Wort W3. Runden 0..2 sind nonce-frei (vorberechenbar),
      W16 und W17 des Fahrplans sind nonce-frei, ab Runde 3 haengt alles von der Nonce ab.
  k2  zweite SHA ueber den 32-Byte-Zwischenhash: Ergebnis = Hash. H2_7 = e61 + IV7 steht nach Runde 61 fest ("Early Exit"):
      Wer nur wissen will, ob die oberen 32 Bit des Hashs null sind, kann nach Runde 61 aufhoeren.
Konvention (wie im ganzen Projekt): Nonce little-endian an Byte 76..79; Hash als Zahl = int.from_bytes(digest, 'little'); Treffer: Zahl <= Target."""
import hashlib

M = 0xffffffff
K = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
     0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
     0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
     0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]
IV = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]
rotr = lambda x, n: ((x >> n) | (x << (32 - n))) & M
S0 = lambda x: rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22); S1 = lambda x: rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)
s0 = lambda x: rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3); s1 = lambda x: rotr(x, 17) ^ rotr(x, 19) ^ (x >> 10)
Ch = lambda e, f, g: (e & f) ^ (~e & g & M); Maj = lambda a, b, c: (a & b) ^ (a & c) ^ (b & c)

def woerter(b): return [int.from_bytes(b[i:i+4], 'big') for i in range(0, len(b), 4)]

def kompression(name, H, blk, nonce_frei_woerter, runden=64):
    """Eine Kompression mit Protokoll. nonce_frei_woerter: Menge der W-Indizes 0..15, die nicht von der Nonce abhaengen.
    Liefert (H_neu, protokoll). Protokoll je Runde: W_t, Zustand nach der Runde, Flag 'nonce_frei' (alle Eingaben bisher nonce-frei)."""
    W = woerter(blk)
    frei = [i in nonce_frei_woerter for i in range(16)]
    for t in range(16, runden):
        W.append((W[t-16] + s0(W[t-15]) + W[t-7] + s1(W[t-2])) & M)
        frei.append(frei[t-16] and frei[t-15] and frei[t-7] and frei[t-2])
    a, b, c, d, e, f, g, h = H; zustand_frei = True; prot = []
    for t in range(runden):
        T1 = (h + S1(e) + Ch(e, f, g) + K[t] + W[t]) & M; T2 = (S0(a) + Maj(a, b, c)) & M
        h, g, f, e, d, c, b, a = g, f, e, (d + T1) & M, c, b, a, (T1 + T2) & M
        zustand_frei = zustand_frei and frei[t]
        prot.append(dict(t=t, W=W[t], W_nonce_frei=frei[t], zustand=[a, b, c, d, e, f, g, h], zustand_nonce_frei=zustand_frei))
    Hn = [(x + y) & M for x, y in zip(H, [a, b, c, d, e, f, g, h])]
    return Hn, dict(name=name, W=W, W_nonce_frei=frei, runden=prot, H=Hn)

def lebenslauf(header76: bytes, nonce: int, target: int):
    """Vollstaendiger Lebenslauf einer Nonce. Liefert dict mit k0, k1, k2, digest, zahl, treffer, early_exit, tricks."""
    assert len(header76) == 76
    hdr = header76 + nonce.to_bytes(4, 'little')
    # Block 1: Bytes 0..63 (kein Nonce-Bezug)
    H0, k0 = kompression('k0', IV, hdr[:64], set(range(16)))
    # Block 2: Bytes 64..79 + Padding (0x80, Nullen, Laenge 640 Bit)
    blk2 = hdr[64:80] + b'\x80' + b'\x00' * 39 + (640).to_bytes(8, 'big')
    H1, k1 = kompression('k1', H0, blk2, set(range(16)) - {3})
    # zweite SHA: 32 Byte Zwischenhash + Padding (Laenge 256 Bit)
    blk3 = b''.join(w.to_bytes(4, 'big') for w in H1) + b'\x80' + b'\x00' * 23 + (256).to_bytes(8, 'big')
    H2, k2 = kompression('k2', IV, blk3, set(range(8, 16)))   # W0..7 = H1 (nonce-abhaengig), W8..15 Padding (nonce-frei)
    digest = b''.join(w.to_bytes(4, 'big') for w in H2)
    assert digest == hashlib.sha256(hashlib.sha256(hdr).digest()).digest(), 'Lebenslauf stimmt nicht mit hashlib ueberein'
    zahl = int.from_bytes(digest, 'little'); treffer = zahl <= target
    # Early Exit: H2_7 = e61 + IV7; e61 = Zustand e nach Runde 60 (Index 60) -> nach Runde 61 (t=60 abgeschlossen) bekannt
    e61 = k2['runden'][60]['zustand'][4]; H2_7_frueh = (e61 + IV[7]) & M
    nullbits = 256 - target.bit_length()
    ganze_nullwoerter = nullbits // 32
    early = dict(runde=61, zaehlung='61 = die 61. ausgefuehrte Runde = Index t=60 (0-basiert); danach folgen t=61,62,63', H2_7_aus_e61=H2_7_frueh, stimmt=H2_7_frueh == H2[7],
                 noetig_null=ganze_nullwoerter >= 1, abbruch_moeglich=(ganze_nullwoerter >= 1 and H2_7_frueh != 0),
                 erklaerung='Hash <= Target verlangt bei diesem Target ' + str(ganze_nullwoerter) + ' ganze Nullwoerter oben; das oberste (H2_7) steht nach Runde 61 fest.')
    # Tricks, gezaehlt in Rundenaequivalenten je Doppel-SHA (naiv: 3 x 64 = 192 Runden)
    tricks = dict(
        naiv_runden=192,
        midstate=dict(gespart=64, erklaerung='k0 haengt nicht von der Nonce ab: einmal rechnen, fuer alle 2^32 Nonces gueltig.'),
        vorrunden_k1=dict(gespart=3, erklaerung='k1 Runden 0..2 benutzen nur W0..W2 (Header, nonce-frei): fuer alle Nonces gleich.'),
        fahrplan_konstanten=dict(gespart=0, erklaerung='k1_W16, k1_W17 nonce-frei; W4..W15 Padding-Konstanten; k2_W8..W15 Padding. Spart Additionen, keine ganzen Runden.',
                                 k1_W16_nonce_frei=k1['W_nonce_frei'][16], k1_W17_nonce_frei=k1['W_nonce_frei'][17], k1_W18_nonce_frei=k1['W_nonce_frei'][18]),
        early_exit=dict(gespart=3 if early['abbruch_moeglich'] else 0, erklaerung='Nach Runde 61 von k2 steht H2_7 fest; ist es nicht 0, kann man die Runden 61..63 und 7 der 8 Feedforward-Additionen weglassen.'),
    )
    tricks['gesamt_gespart'] = tricks['midstate']['gespart'] + tricks['vorrunden_k1']['gespart'] + tricks['early_exit']['gespart']
    tricks['verbleibend'] = tricks['naiv_runden'] - tricks['gesamt_gespart']
    return dict(nonce=nonce, header=hdr, digest=digest, zahl=zahl, target=target, treffer=treffer, k0=k0, k1=k1, k2=k2, early_exit=early, tricks=tricks,
                erste_nonceabhaengige_runde_k1=next(r['t'] for r in k1['runden'] if not r['zustand_nonce_frei']))

def kurz(lb, breite=8):
    """Kompakte Textansicht."""
    z = []
    z.append(f"Nonce {lb['nonce']:08x}  Hash {lb['digest'][::-1].hex()}  {'TREFFER' if lb['treffer'] else 'kein Treffer'}  (Zahl {lb['zahl'].bit_length()} Bit, Target {lb['target'].bit_length()} Bit)")
    z.append(f"k0: 64 Runden, nonce-frei (Midstate).  k1: nonce-frei bis Runde {lb['erste_nonceabhaengige_runde_k1']-1}, W16/W17 nonce-frei: {lb['tricks']['fahrplan_konstanten']['k1_W16_nonce_frei']}/{lb['tricks']['fahrplan_konstanten']['k1_W17_nonce_frei']}, W18: {lb['tricks']['fahrplan_konstanten']['k1_W18_nonce_frei']}")
    ee = lb['early_exit']; z.append(f"k2: Early Exit nach der {ee['runde']}. Runde (t={ee['runde']-1}): H2_7 = {ee['H2_7_aus_e61']:08x} -> {'Abbruch moeglich (kein Treffer)' if ee['abbruch_moeglich'] else 'weiterrechnen'}")
    tr = lb['tricks']; z.append(f"Tricks: naiv {tr['naiv_runden']} Runden, gespart {tr['gesamt_gespart']} (Midstate {tr['midstate']['gespart']}, Vorrunden {tr['vorrunden_k1']['gespart']}, Early Exit {tr['early_exit']['gespart']}) -> {tr['verbleibend']} Runden je Nonce. Keine Nonce uebersprungen.")
    return '\n'.join(z)

def runde_text(lb, komp, t):
    r = lb[komp]['runden'][t]; a, b, c, d, e, f, g, h = r['zustand']
    return f"{komp} Runde {t:2d}: W={r['W']:08x}{'*' if r['W_nonce_frei'] else ' '}  a={a:08x} b={b:08x} c={c:08x} d={d:08x} e={e:08x} f={f:08x} g={g:08x} h={h:08x}  {'nonce-frei' if r['zustand_nonce_frei'] else ''}"
