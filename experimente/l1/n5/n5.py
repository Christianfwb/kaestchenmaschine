"""N5 MINI-ERWEITERUNG – M1: BAU UND SELBSTTEST (GO 2026-10-24 16:13). Keine Ableitung, kein M2/M3, kein R8g.
Varianten der Nachrichtenerweiterung bei sonst unveraenderter Mini-Rundenfunktion (8 Register x 4 Bit, IV4, K4, grosse Sigmas UNVERAENDERT wie N4):
  V0  W_i = W_(i-3)                                          (Kopie, Referenz)
  V1  W_i = W_(i-1) + W_(i-3) + W_(i-2)                      (nur Addition, mod 16)
  V2  W_i = s1(W_(i-1)) XOR W_(i-3) XOR s0(W_(i-2))          (nur linear)
  V3  W_i = s1(W_(i-1)) + W_(i-3) + s0(W_(i-2))              (Addition und Drehung, mod 16)
  rotr(x,n) = Rechtsrotation um n auf 4 Bit; shr(x,n) = logische Rechtsschiebung (Nullen von links).
  s0(x) = rotr(x,1) ^ rotr(x,3) ^ shr(x,1);  s1(x) = rotr(x,2) ^ rotr(x,3) ^ shr(x,2).
KONTROLLBELEGUNG (gemeinsam, vorab festgelegt): k = int.from_bytes(sha256(b'N5 Kontrollbelegung 2026-10-24').digest(), 'little') % 4096.
  Zeichenkette UTF-8 (reines ASCII), SHA-256 ueber die Bytes, 32-Byte-Digest als Little-Endian-Zahl, modulo 4096. Bit i von k = freies Bit x_i (i = 0..11).
BITZUORDNUNG: W0 = (x0, x1, x2, x3), W1 = (x4..x7), W2 = (x8..x11), jeweils Bit 0 = niedrigstwertig (LSB zuerst), Wortwert = sum x_(4w+b) * 2^b.
ZWEI VORWAERTSIMPLEMENTIERUNGEN: (A) einfache Wortrechnung auf Ganzzahlen (diese Datei, unabhaengig vom Graphen); (B) Kaestchennetz (pruefstand.Netz/_mini_runden
  mit eigener Erweiterung). Fuer jeden der acht Faelle (V0..V3 x 6/9 Runden) werden ALLE 4096 Eingaben in beiden gerechnet und verglichen; Abweichung -> FEHLER, Stopp.
Ziel je Netz: volles Endregister (32 Bit) der Kontrollbelegung aus (A); Pruefung, dass (B) es fuer k erreicht; Zahl echter Loesungen (A und B), Knotenzahl."""
import sys, os, json, hashlib, itertools, time, resource
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import pruefstand as P, gatter as G

KONTROLL_TEXT = b'N5 Kontrollbelegung 2026-10-24'
def kontrollbelegung():
    k = int.from_bytes(hashlib.sha256(KONTROLL_TEXT).digest(), 'little') % 4096
    return k, [(k >> i) & 1 for i in range(12)]
# ---------- (A) Wortrechnung auf Ganzzahlen ----------
def rotr(x, n): return ((x >> n) | (x << (4 - n))) & 15
def shr(x, n): return x >> n
def s0(x): return rotr(x, 1) ^ rotr(x, 3) ^ shr(x, 1)
def s1(x): return rotr(x, 2) ^ rotr(x, 3) ^ shr(x, 2)
def S1(e): return rotr(e, 1) ^ rotr(e, 3)       # grosse Sigmas UNVERAENDERT wie N4 (_mini_runden: rot(e,1)^rot(e,3) auf LSB-zuerst-Listen = Rechtsrotation)
def S0(a): return rotr(a, 1) ^ rotr(a, 2)
def ch(e, f, g): return (e & f) ^ ((~e & 15) & g)
def maj(a, b, c): return (a & b) | (a & c) | (b & c)
def erweiterung(W, i, variante):
    if variante == 9: return sum((((0xD5A3 >> ((i * 4 + b) % 16)) & 1) << b) for b in range(4))   # ohne Leine: feste Woerter wie N4r..o
    if variante == 0: return W[i - 3]
    if variante == 1: return (W[i - 1] + W[i - 3] + W[i - 2]) & 15
    if variante == 2: return s1(W[i - 1]) ^ W[i - 3] ^ s0(W[i - 2])
    if variante == 3: return (s1(W[i - 1]) + W[i - 3] + s0(W[i - 2])) & 15
def vorwaerts_wort(bel, runden, variante):
    """bel: 12 Bits (x0..x11). Liefert Endregister (a..h) als 8 Zahlen 0..15."""
    W = [sum(bel[4 * w + b] << b for b in range(4)) for w in range(3)]
    for i in range(3, runden): W.append(erweiterung(W, i, variante))
    a, b, c, d, e, f, g, h = P._IV4
    for i in range(runden):
        t1 = (h + S1(e) + ch(e, f, g) + P._K4[i] + W[i]) & 15; t2 = (S0(a) + maj(a, b, c)) & 15
        a, b, c, d, e, f, g, h = (t1 + t2) & 15, a, b, c, (d + t1) & 15, e, f, g
    return (a, b, c, d, e, f, g, h)
# ---------- (B) Kaestchennetz ----------
def _erweiterung_netz(N, W, i, variante):
    def rotw(x, n): return x[n:] + x[:n]                                  # Bitliste LSB zuerst: x[n:]+x[:n] = Rechtsrotation um n
    def shrw(x, n): return x[n:] + [0] * n                                 # logische Rechtsschiebung: hohe Bits werden 0
    def xorw(*ws): return [N.xor(*bits) for bits in zip(*ws)]
    def s0w(x): return xorw(rotw(x, 1), rotw(x, 3), shrw(x, 1))
    def s1w(x): return xorw(rotw(x, 2), rotw(x, 3), shrw(x, 2))
    def addw(a, b): s_, _, _ = N.add_bits(a, b); return s_
    if variante == 9: return [(0xD5A3 >> ((i * 4 + b) % 16)) & 1 for b in range(4)]
    if variante == 0: return W[i - 3]
    if variante == 1: return addw(addw(W[i - 1], W[i - 3]), W[i - 2])
    if variante == 2: return xorw(s1w(W[i - 1]), W[i - 3], s0w(W[i - 2]))
    if variante == 3: return addw(addw(s1w(W[i - 1]), W[i - 3]), s0w(W[i - 2]))
def netz(runden, variante, ziel_bel):
    N = P.Netz('N5 V%d r%02d (Erweiterung %s)' % (variante, runden, {0: 'Kopie', 1: 'nur Addition', 2: 'nur linear', 3: 'Addition+Drehung', 9: 'OHNE LEINE, Konstanten'}[variante]), 12); x = N.frei
    W = [x[0:4], x[4:8], x[8:12]]
    for i in range(3, runden): W.append(_erweiterung_netz(N, W, i, variante))
    regs = P._mini_runden(N, W, P._K4, P._IV4, runden)
    v = N.wert(ziel_bel)
    for r in regs:
        for node in r:
            val = (1 - v[-node]) if node < 0 else v[node]
            if node in (0, 1): continue
            N.setze_ziel(node, val)
    N.regs = regs; return N
def register_aus_netz(N, bel):
    v = N.wert(bel); out = []
    for r in N.regs: out.append(sum(((1 - v[-nd]) if nd < 0 else v[nd]) << b for b, nd in enumerate(r)))
    return tuple(out)
NETZE_N5 = {}
def _mach(runden, variante):
    def f():
        _, bel = kontrollbelegung(); return netz(runden, variante, bel)
    return f
for _r in (6, 9):
    for _v in (0, 1, 2, 3): NETZE_N5['N5v%dr%02d' % (_v, _r)] = _mach(_r, _v)
NETZE_N5['N5ohne_r09'] = _mach(9, 9)

if __name__ == '__main__':
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)                                   # TATSAECHLICH aktive harte Speichergrenze dieses Prozesses
    rlimit = dict(rlimit_as_soft_mib=(soft >> 20) if soft != resource.RLIM_INFINITY else None, rlimit_as_hard_mib=(hard >> 20) if hard != resource.RLIM_INFINITY else None)
    erwartet = os.environ.get('N5_ERWARTE_RLIMIT_MIB')
    if erwartet is not None:
        if rlimit['rlimit_as_soft_mib'] != int(erwartet):
            print('FEHLER: harte Speichergrenze nicht aktiv (erwartet %s MiB, aktiv %s) – Test nicht gestartet' % (erwartet, rlimit)); sys.exit(3)
    print('Aktive RLIMIT_AS im Testprozess:', rlimit)
    k, bel = kontrollbelegung(); alle = list(itertools.product((0, 1), repeat=12))
    prot = dict(rlimit_im_testprozess=rlimit, kontrolltext=KONTROLL_TEXT.decode('utf-8'), k=k, k_hex=hex(k), bits_x0_bis_x11=bel, W0=sum(bel[b] << b for b in range(4)), W1=sum(bel[4 + b] << b for b in range(4)), W2=sum(bel[8 + b] << b for b in range(4)),
                sigmas=dict(s0=[s0(x) for x in range(16)], s1=[s1(x) for x in range(16)], S1_gross=[S1(x) for x in range(16)], S0_gross=[S0(x) for x in range(16)]), faelle=[])
    print('Kontrollbelegung: k = %d (0x%03x), W0=%d W1=%d W2=%d, Bits x0..x11 = %s' % (k, k, prot['W0'], prot['W1'], prot['W2'], bel))
    ok_alle = True
    for runden in (6, 9):
        for variante in (0, 1, 2, 3):
            t = time.perf_counter(); N = netz(runden, variante, bel); t_bau = time.perf_counter() - t
            ziel_A = vorwaerts_wort(bel, runden, variante); ziel_B = register_aus_netz(N, bel)
            t = time.perf_counter(); abweichungen = 0; loes_A = 0; loes_B = 0
            for b in alle:
                b = list(b); ra = vorwaerts_wort(b, runden, variante); rb = register_aus_netz(N, b)
                if ra != rb: abweichungen += 1
                if ra == ziel_A: loes_A += 1
                if N.erfuellt(b): loes_B += 1
            t_vgl = time.perf_counter() - t
            fall = dict(variante=variante, runden=runden, name=N.name, knoten=len(N.g.nodes), ch_kaestchen=len(N.ch_kaestchen), maj_kaestchen=len(N.maj_kaestchen), stufen=len(N.stufen),
                        ziel_wortrechnung=list(ziel_A), ziel_netz=list(ziel_B), ziel_gleich=(ziel_A == ziel_B), kontrolle_erreicht_netz=N.erfuellt(bel),
                        abweichungen_A_B_ueber_4096=abweichungen, echte_loesungen_A=loes_A, echte_loesungen_B=loes_B, zeit_bau_s=round(t_bau, 3), zeit_vergleich_4096_s=round(t_vgl, 2))
            ok = fall['ziel_gleich'] and fall['kontrolle_erreicht_netz'] and abweichungen == 0 and loes_A == loes_B and loes_A >= 1
            fall['status'] = 'OK' if ok else 'FEHLER'; ok_alle &= ok; prot['faelle'].append(fall)
            print('%-40s Knoten %5d (Ch %d, Maj %d, Stufen %d) | Ziel A=B %s | Kontrolle erreicht %s | Abweichungen A/B %d | echte Loesungen A %d B %d | Bau %.2fs Vergleich %.1fs | %s' % (
                N.name, fall['knoten'], fall['ch_kaestchen'], fall['maj_kaestchen'], fall['stufen'], fall['ziel_gleich'], fall['kontrolle_erreicht_netz'], abweichungen, loes_A, loes_B, t_bau, t_vgl, fall['status']))
            if not ok: print('FEHLER – STOPP'); json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_N5_M1.json'), 'w'), indent=1); sys.exit(3)
    prot['alle_ok'] = ok_alle; json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_N5_M1.json'), 'w'), indent=1); print('M1: alle acht Faelle OK' if ok_alle else 'M1: FEHLER')
# Zusaetzliche Darstellungen fuer den Pruefstand-Haken (nur wenn r10b.py vorhanden ist)
try:
    sys.path.insert(0, HERE); import r10b as _r10b; DARSTELLUNGEN_ZUSATZ = {'Vollscan+R10b': _r10b.D6_R10b}
except Exception as _e: DARSTELLUNGEN_ZUSATZ = {}
