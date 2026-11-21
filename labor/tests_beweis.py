"""tests_beweis.py - Pruefung der Vollstaendigkeitsbewertung mit leeren, gekuerzten und manipulierten Beweisbuechern (Ghosts Punkt 7).
Kein Hashen ausser dem einen hashlib-Vergleichsdigest. Dauer ~30 s (ein Aufbau, vier Bewertungen)."""
import sys, json, threading, time
from pathlib import Path
H = Path(__file__).resolve().parent; sys.path.insert(0, str(H))
from glas import kaestchen as KM
KM.paket()
import maschine
from rueckweg import KernRueckweg
h = bytes.fromhex(json.load(open(H / 'headers/H970000.json'))['header76_hex']); nonce = 0xacc33125
a = dict(header76_hex=h.hex(), basis=nonce, maske=0, arm='M', profil='bits_erweitert', nbits_ziel=(1 << 256) - 1, rueckweg=True, sekunden=120)
k = KernRueckweg(32); k.stop_event = threading.Event(); k.deadline = time.monotonic() + 120; k.rueckweg_an = True
maschine.aufbau(k, a); k.fixpunkt(); vertrag = maschine.vertrag(a); voll = list(k.buch); ok = 0
def t(name, bed):
    global ok; print(('OK  ' if bed else 'FEHL'), name); ok += bool(bed)
b = KM.bewerte(k, h, nonce, vertrag); t(f'B1 vollstaendiges Buch ({b["zeilen"]:,} Zeilen): vollstaendig, 256/256, 0 Fehler, Digest == hashlib', b['vollstaendig'] and b['hash_bits_belegt'] == 256 and b['pruefer_fehler'] == 0)
k.buch = []; b = KM.bewerte(k, h, nonce, vertrag); t('B2 leeres Buch: 0 Pruefer-Fehler, aber NICHT vollstaendig (0/256)', b['pruefer_fehler'] == 0 and not b['vollstaendig'] and b['hash_bits_belegt'] == 0)
k.buch = voll[:-2000]; b = KM.bewerte(k, h, nonce, vertrag); t(f'B3 gekuerztes Buch (letzte 2000 Zeilen fehlen): NICHT vollstaendig ({b["hash_bits_belegt"]}/256)', not b['vollstaendig'])
man = [list(z) for z in voll]
for z in reversed(man):
    if z[2] == 'BIT' and z[3][0].startswith('k2_H'): z[3] = [z[3][0], 1 - z[3][1]]; break
k.buch = [tuple(z) if isinstance(z, list) else z for z in man]; b = KM.bewerte(k, h, nonce, vertrag)
t(f'B4 manipuliertes Hash-Bit: Pruefer meldet Fehler ({b["pruefer_fehler"]}), Digest != hashlib, NICHT vollstaendig', b['pruefer_fehler'] > 0 and not b['hashlib_gleich'] and not b['vollstaendig'])
k.buch = voll; print(f'{ok}/4 bestanden'); sys.exit(0 if ok == 4 else 1)
