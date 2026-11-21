"""tests_avalanche.py - Avalanche-Labor (Version 3). Hasht Lebenslaeufe, sucht keine Nonce, vergleicht nicht mit dem Ziel."""
import sys, json
from pathlib import Path
H = Path(__file__).resolve().parent; sys.path.insert(0, str(H))
from glas import avalanche as AV, lebenslauf as LB
h = bytes.fromhex(json.load(open(H / 'headers/H970000.json'))['header76_hex']); ok = 0
def t(name, bed):
    global ok; print(('OK  ' if bed else 'FEHL'), name); ok += bool(bed)
av = AV.kippen(h, 0xacc33125, 0)
t('A1 k0 ohne Unterschied; k1 erster Unterschied in Runde 3', av['komp']['k0']['erste_runde_mit_unterschied'] is None and av['komp']['k1']['erste_runde_mit_unterschied'] == 3)
t('A2 k1: W16/W17 unveraendert, W3 und W18 veraendert', 16 not in av['k1_W_unterschied'] and 17 not in av['k1_W_unterschied'] and 3 in av['k1_W_unterschied'] and 18 in av['k1_W_unterschied'])
t('A3 Hash-Abstand = Hamming der beiden Digests (unabhaengig nachgerechnet)', av['hash_abstand'] == sum(bin(a ^ b).count('1') for a, b in zip(bytes.fromhex(av['digest']), bytes.fromhex(av['digest2']))))
t('A4 XOR-Zustand stimmt mit zwei getrennten Lebenslaeufen ueberein (Runde 40, k2)', av['komp']['k2']['runden'][40]['xor'] == [a ^ b for a, b in zip(LB.lebenslauf(h, 0xacc33125, 0)['k2']['runden'][40]['zustand'], LB.lebenslauf(h, 0xacc33124, 0)['k2']['runden'][40]['zustand'])])
st = AV.statistik(h, 200, seed=7)
t(f'A5 Statistik 200 Paare: Mittel {st["hash_abstand"]["mittel"]:.1f} innerhalb 128 +- 3 Standardfehler', abs(st['hash_abstand']['abweichung_in_std']) < 3)
t('A6 Statistik: mittlere k1-Kurve ist 0 vor Runde 3 und > 100 ab Runde 10', all(v == 0 for v in st['mittel']['k1'][:3]) and all(v > 100 for v in st['mittel']['k1'][10:]))
ak = AV.abhaengigkeitskarte(h, 0xacc33125)
t('A7 Abhaengigkeitskarte: 64/128/192/256 erreichte Bits in Runden 3..6 (zwei neue Woerter je Runde)', ak['erreichte_zustandsbits']['k1'][3:7] == [64, 128, 192, 256])
t('A8 jedes der 32 Nonce-Bits wirkt zuerst in Runde 3', set(ak['erste_runde_je_noncebit_k1']) == {3})
t('A9 Matrix vorhanden: 32 Nonce-Bits x 64 Runden x 8 Woerter, und Zaehlung = Vereinigung der Matrix', len(ak['matrix']['k1']) == 32 and len(ak['matrix']['k1'][0]) == 64 and len(ak['matrix']['k1'][0][0]) == 8 and ak['erreichte_zustandsbits']['k1'][5] == sum(bin(x).count('1') for x in [__import__('functools').reduce(lambda a, b: a | b, (ak['matrix']['k1'][bit][5][w] for bit in range(32)), 0) for w in range(8)]))
mx = max(max(AV.kurve(av, 'k1')[8:]), max(AV.kurve(av, 'k2'))); t(f'A10 128 ist keine Obergrenze: Maximum in diesem Versuch {mx} > 128', mx > 128)
print(f'{ok}/10 bestanden'); sys.exit(0 if ok == 10 else 1)
