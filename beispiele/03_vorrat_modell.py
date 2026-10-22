#!/usr/bin/env python3
"""VORRATS-MODELL (Christians Idee, Fable 2026-10-22). python -I vorrat_modell.py
Mini-SHA im 2^16-Labor: 4 Register x 4 Bit = 16-Bit-Zustand, 4 Eingangswoerter x 4 Bit, Erweiterung auf 8 Rundenwoerter,
8 Runden mit SHA-Bauart (Ch, Maj, Sigma, Addition, Feed-forward), zweimal angewandt wie SHA256d. Ziel: erstes Wort des Endhashs = 0 (1 zu 16).
Frage: Rueckwaerts rechnen, beliebigen Startzustand speichern, spaeter nachschlagen – wie oft trifft das?
Messung A: zweite Anwendung rueckwaerts (Ende gewaehlt, Woerter gewaehlt) – wie oft landet der Startzustand auf den Konstanten (IV)?
Messung B: erste Anwendung rueckwaerts (Startzustand = Midstate gespeichert) – wie oft kann eine neue Vorlage nachgeschlagen werden?
Vergleich: direkte Suche (vorwaerts, Nonce probieren)."""
import random, time
M = 15
def rot(x, n): return ((x >> n) | (x << (4 - n))) & M
def S0(x): return rot(x, 1) ^ rot(x, 2) ^ (x >> 1)
def S1(x): return rot(x, 1) ^ rot(x, 3) ^ (x >> 2)
def ch(x, y, z): return (x & y) ^ (~x & z & M)
def maj(x, y, z): return (x & y) ^ (x & z) ^ (y & z)
K = [0x4, 0x7, 0xb, 0xe, 0x3, 0x5, 0x9, 0xc]
IV = (0x6, 0xb, 0x3, 0xa)
def expand(w):
    w = list(w)
    for i in range(4, 8): w.append((S1(w[i - 2]) + w[i - 3] + S0(w[i - 4]) + w[i - 4]) & M)
    return w
def runde(st, k, w):
    a, b, c, d = st
    t1 = (d + S1(c) + ch(c, b, a) + k + w) & M; t2 = (S0(a) + maj(a, b, c)) & M
    return ((t1 + t2) & M, a, b, c)
def runde_rueck(st, k, w):
    an, a, b, c = st
    t2 = (S0(a) + maj(a, b, c)) & M; t1 = (an - t2) & M
    d = (t1 - S1(c) - ch(c, b, a) - k - w) & M
    return (a, b, c, d)
def compress(start, words):
    st = start; W = expand(words)
    for i in range(8): st = runde(st, K[i], W[i])
    return tuple((s + x) & M for s, x in zip(st, start))
def rueckwaerts(ende, start_guess, words):
    """Von H = start + state8 zurueck. Da der Startzustand unbekannt ist, wird state8 = H - start gebraucht: wir setzen den
    Startzustand als Variable S und pruefen am Ende S == rueckgerechnet. Fuer die Messung: S frei gewaehlt (Christians 'beliebiger Zustand')."""
    st = tuple((h - s) & M for h, s in zip(ende, start_guess)); W = expand(words)
    for i in range(7, -1, -1): st = runde_rueck(st, K[i], W[i])
    return st
def ziel_ok(h): return h[0] == 0
rnd = random.Random(1); t0 = time.perf_counter()

# ---- Messung A: zweite Anwendung rueckwaerts ----
N = 200000; treffer_iv = 0
for _ in range(N):
    ende = (0, rnd.randrange(16), rnd.randrange(16), rnd.randrange(16))            # Endhash unter Ziel gewaehlt
    words = tuple(rnd.randrange(16) for _ in range(4))                             # H1 (Rundenwoerter) gewaehlt
    # Startzustand der zweiten Anwendung ist immer IV: Feed-forward mit IV abziehen, zurueckrechnen, muss wieder IV ergeben
    if rueckwaerts(ende, IV, words) == IV: treffer_iv += 1
# direkt: vorwaerts H1 raten bis Ziel
versuche = 0; gefunden = 0
while gefunden < 1000:
    versuche += 1
    if ziel_ok(compress(IV, tuple(rnd.randrange(16) for _ in range(4)))): gefunden += 1
print('A  zweite Anwendung: rueckwaerts %d Eintraege, Startzustand = Konstanten: %d  (erwartet %.1f = 1 zu 65536)' % (N, treffer_iv, N / 65536))
print('   direkt vorwaerts:  %.1f Versuche je gueltigem H1 (erwartet 16)' % (versuche / gefunden))

# ---- Messung B: erste Anwendung, Vorrat von Startzustaenden, Nachschlagen bei neuen Vorlagen ----
gute_h1 = []
while len(gute_h1) < 64:
    w = tuple(rnd.randrange(16) for _ in range(4))
    if ziel_ok(compress(IV, w)): gute_h1.append(w)
NB = 0x7                                                                           # nBits: fest
def vorlage(): return (tuple(rnd.randrange(16) for _ in range(4)), rnd.randrange(16), rnd.randrange(16))   # (Midstate, Merkle-Ende, Zeit)
def direkt(v):
    mid, w0, w1 = v; n = 0
    while True:
        for nonce in range(16):
            n += 2
            if ziel_ok(compress(IV, compress(mid, (w0, w1, NB, nonce)))): return n
        w0 = rnd.randrange(16)                                                      # Extranonce: neues Merkle-Ende
print('B  erste Anwendung, 2000 Vorlagen:')
vorl = [vorlage() for _ in range(2000)]
d = [direkt(v) for v in vorl]
print('   direkt: im Mittel %.1f Kompressionen je Block' % (sum(d) / len(d)))
for groesse in (2 ** 8, 2 ** 12, 2 ** 16, 2 ** 20):
    vorrat = {}
    for _ in range(groesse):
        h1 = gute_h1[rnd.randrange(64)]; w0, w1, nonce = rnd.randrange(16), rnd.randrange(16), rnd.randrange(16)
        S = tuple(rnd.randrange(16) for _ in range(4))                             # beliebiger Startzustand (Midstate)
        st = rueckwaerts(h1, S, (w0, w1, NB, nonce))
        # Eintrag ist nur in sich stimmig, wenn der rueckgerechnete Start der gewaehlte ist; sonst passt Feed-forward nicht.
        # Ehrlicher Weg: Start = rueckgerechneter Wert, Feed-forward dann H1' = st + state8 (nicht h1). Wir speichern, was wirklich gilt:
        h1_wirklich = compress(st, (w0, w1, NB, nonce))
        if ziel_ok(compress(IV, h1_wirklich)): vorrat[(st, w0, w1)] = nonce
    hits = sum(1 for (mid, w0, w1) in vorl if (mid, w0, w1) in vorrat)
    print('   Vorrat %8d Eintraege (%6d gueltig): %4d von 2000 Vorlagen nachschlagbar (%.2f%%), Vorarbeit %d Kompressionen'
          % (groesse, len(vorrat), hits, 100 * hits / 2000, 3 * groesse))
print('%.1f s' % (time.perf_counter() - t0))
