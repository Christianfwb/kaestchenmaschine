"""avalanche.py - Das Avalanche-Labor (Version 3, Idee Ghost 21.11.). Nur Standardbibliothek, baut auf lebenslauf.py.

kippen(header76, nonce, bit)        Ein Nonce-Bit kippen (bit = Stellenwert 0..31 der Nonce-Zahl). Zwei Lebenslaeufe, Runde fuer Runde
                                    XOR der acht Zustandswoerter: wie viele Bits unterscheiden sich, in welchen Woertern, ab welcher Runde.
statistik(header76, n, seed)        n zufaellige (Nonce, Bit)-Paare: mittlere Unterschiedskurve je Runde, Verteilung des Hash-Abstands
                                    (Hamming) gegen den Erwartungswert einer idealen Zufallsfunktion: 128 +- 8 (Binomial 256, 1/2).
abhaengigkeitskarte(header76, nonce) Alle 32 Nonce-Bits einzeln kippen: welches Nonce-Bit erreicht in welcher Runde welche Zustandsbits.
                                    EMPIRISCH (eine konkrete Nonce, ein Flip), nicht die strukturelle Abhaengigkeit der Kaestchenmaschine.
Alles rechnet Hashes, aber sucht keine Nonce und verwendet keinen Zielvergleich zur Auswahl - Laborrechnung, kein Mining."""
import random
from . import lebenslauf as LB

M = 0xffffffff
def popcount(x): return bin(x).count('1')

def _zustaende(lb, komp): return [r['zustand'] for r in lb[komp]['runden']]

def kippen(header76: bytes, nonce: int, bit: int):
    if type(nonce) is not int or not 0 <= nonce < 2**32:
        raise ValueError('Nonce muss eine ganze Zahl von 0 bis 2^32-1 sein')
    if type(bit) is not int or not 0 <= bit < 32:
        raise ValueError('Nonce-Bit muss eine ganze Zahl von 0 bis 31 sein')
    nonce2 = nonce ^ (1 << bit)
    a = LB.lebenslauf(header76, nonce, 0); b = LB.lebenslauf(header76, nonce2, 0)
    aus = dict(nonce=nonce, nonce2=nonce2, bit=bit, komp={})
    for komp in ('k0', 'k1', 'k2'):
        za, zb = _zustaende(a, komp), _zustaende(b, komp); runden = []
        for t in range(64):
            x = [u ^ v for u, v in zip(za[t], zb[t])]
            runden.append(dict(t=t, xor=x, bits=sum(popcount(w) for w in x), woerter=[popcount(w) for w in x],
                               W_bits=popcount(a[komp]['runden'][t]['W'] ^ b[komp]['runden'][t]['W'])))
        erste = next((r['t'] for r in runden if r['bits']), None)
        aus['komp'][komp] = dict(runden=runden, erste_runde_mit_unterschied=erste, H_xor=[u ^ v for u, v in zip(a[komp]['H'], b[komp]['H'])])
    da, db = a['digest'], b['digest']
    aus['hash_abstand'] = sum(popcount(u ^ v) for u, v in zip(da, db)); aus['digest'] = da.hex(); aus['digest2'] = db.hex()
    aus['k1_W_unterschied'] = [t for t in range(64) if aus['komp']['k1']['runden'][t]['W_bits']]
    return aus

def kurve(av, komp):
    return [r['bits'] for r in av['komp'][komp]['runden']]

def statistik(header76: bytes, n: int = 300, seed: int = 20261121, bits=None):
    if type(n) is not int or n < 1:
        raise ValueError('Anzahl muss eine positive ganze Zahl sein')
    if bits is not None and (not bits or any(type(b) is not int or not 0 <= b < 32 for b in bits)):
        raise ValueError('bits muss mindestens einen Bitindex von 0 bis 31 enthalten')
    rnd = random.Random(seed); summe = {'k1': [0] * 64, 'k2': [0] * 64}; abst = []; erste = []
    for i in range(n):
        nonce = rnd.getrandbits(32); bit = rnd.randrange(32) if bits is None else bits[i % len(bits)]
        av = kippen(header76, nonce, bit); abst.append(av['hash_abstand']); erste.append(av['komp']['k1']['erste_runde_mit_unterschied'])
        for komp in ('k1', 'k2'):
            for t in range(64): summe[komp][t] += av['komp'][komp]['runden'][t]['bits']
    mw = sum(abst) / n; var = sum((x - mw) ** 2 for x in abst) / max(n - 1, 1)
    return dict(n=n, seed=seed, mittel={k: [v / n for v in s] for k, s in summe.items()}, hash_abstand=dict(mittel=mw, std=var ** 0.5, min=min(abst), max=max(abst),
                erwartet_mittel=128.0, erwartet_std=8.0, abweichung_in_std=(mw - 128) / (8 / n ** 0.5)),
                erste_runde_k1=dict(min=min(erste), max=max(erste)),
                hinweis='128 ist der ERWARTUNGSWERT fuer eine ideale Zufallsfunktion (Binomial 256, 1/2: Streuung 8), keine Obergrenze - einzelne Runden oder Paare liegen regelmaessig bei 150 oder 105. Abweichung in Standardfehlern des Mittels (|z| < 3 = unauffaellig). Kein Beweis fuer oder gegen irgendetwas - eine Messung.')

def abhaengigkeitskarte(header76: bytes, nonce: int):
    """Je Nonce-Bit und Runde: welche der 256 Zustandsbits (k1) bzw. (k2) sich aendern. Liefert kompakte Zaehlungen plus Matrix."""
    karte = {'k1': [], 'k2': []}; erreicht = {'k1': [0] * 64, 'k2': [0] * 64}
    for bit in range(32):
        av = kippen(header76, nonce, bit)
        for komp in ('k1', 'k2'):
            karte[komp].append([r['xor'] for r in av['komp'][komp]['runden']])
    for komp in ('k1', 'k2'):
        for t in range(64):
            vereinigung = [0] * 8
            for bit in range(32):
                for w in range(8): vereinigung[w] |= karte[komp][bit][t][w]
            erreicht[komp][t] = sum(popcount(w) for w in vereinigung)
    voll = {k: next((t for t, v in enumerate(e) if v == 256), None) for k, e in erreicht.items()}
    je_bit_erste = [next((t for t in range(64) if any(karte['k1'][b][t])), None) for b in range(32)]
    # Bit-Matrix: matrix[komp][noncebit][runde] = 8 Woerter (int), Bit gesetzt = dieses Zustandsbit aendert sich beim Kippen dieses Nonce-Bits
    return dict(nonce=nonce, erreichte_zustandsbits=erreicht, erste_runde_alle_256={k: v for k, v in voll.items()}, erste_runde_je_noncebit_k1=je_bit_erste,
                matrix=karte, matrix_format='matrix[komp][noncebit 0..31][runde 0..63] = Liste von 8 Woertern (a..h nach der Runde) als 32-Bit-Zahlen; Bit i gesetzt = Zustandsbit i aendert sich',
                hinweis='Empirische Sensitivitaet (ein Flip je Nonce-Bit an dieser Nonce), nicht strukturelle Abhaengigkeit: ein Bit, das sich bei diesem Flip nicht aendert, kann trotzdem abhaengen. Die Zaehlungen sind Vereinigungen ueber alle 32 Nonce-Bits.')
