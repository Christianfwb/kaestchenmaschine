"""tests_glas.py - Selbsttest des glaesernen Miners gegen hashlib und bekannte Werte."""
import sys, json, hashlib, random
from pathlib import Path
H = Path(__file__).resolve().parent; sys.path.insert(0, str(H))
from glas import lebenslauf as LB, odds as OD, miner_cpu as MC
h = bytes.fromhex(json.load(open(H / 'headers/H970000.json'))['header76_hex']); target = OD.nbits_zu_target(OD.nbits_aus_header(h)); ok = 0
def t(name, bed):
    global ok; print(('OK  ' if bed else 'FEHL'), name); ok += bool(bed)
# G1 Lebenslauf == hashlib fuer 50 zufaellige Nonces (Assertion im Lebenslauf selbst)
rnd = random.Random(1); [LB.lebenslauf(h, rnd.getrandbits(32), target) for _ in range(50)]; t('G1 Lebenslauf == hashlib (50 Nonces)', True)
lb = LB.lebenslauf(h, 0xacc33125, target)
t('G2 echter Blocktreffer acc33125 ist Treffer', lb['treffer'])
t('G3 k0 komplett nonce-frei, k1 nonce-frei bis Runde 2, ab Runde 3 nicht', lb['k0']['runden'][63]['zustand_nonce_frei'] and lb['erste_nonceabhaengige_runde_k1'] == 3)
t('G4 k1_W16/W17 nonce-frei, W18 nicht', lb['k1']['W_nonce_frei'][16] and lb['k1']['W_nonce_frei'][17] and not lb['k1']['W_nonce_frei'][18])
t('G5 Early Exit: H2_7 aus e61 == H2_7', lb['early_exit']['stimmt'] and lb['early_exit']['H2_7_aus_e61'] == 0)
lb2 = LB.lebenslauf(h, 0xacc33126, target); t('G6 Nachbar-Nonce: kein Treffer, Early Exit bricht ab', (not lb2['treffer']) and lb2['early_exit']['abbruch_moeglich'])
t('G7 nBits -> Target: Block 970000 Target hat 78 Nullbits', 256 - target.bit_length() == 78)
t('G8 Difficulty-1-Target aus nBits 0x1d00ffff', OD.nbits_zu_target(0x1d00ffff) == OD.MAX_TARGET)
z = OD.zahlen(target, 1e6); t('G9 Odds: Chance je Hash = (T+1)/2^256, Erwartung = 1/p', abs(z['p_je_hash'] * z['erwartete_hashes'] - 1) < 1e-9 and 0 < z['chance_jahr'] < 1)
if '--ohne-suche' not in sys.argv:
    m = MC.mine(h, target, start=0xacc33125 - 5, anzahl=20); t('G10 mine findet den echten Treffer im Bereich', m['status'] == 'TREFFER' and m['treffer_nonce'] == 0xacc33125)
if '--ohne-suche' not in sys.argv:
    m2 = MC.mine(h, target, start=0, anzahl=5000); t('G11 mine ohne Treffer: BEREICH_ENDE, 5000 geprueft', m2['status'] == 'BEREICH_ENDE' and m2['geprueft'] == 5000)
# Nachtraege nach Ghosts Pruefung 21.11.
z1 = OD.zahlen(target, 1.0); t('G12 Odds: auch bei 1 H/s ist die Stundenchance > 0 (numerisch stabil)', z1['chance_stunde'] > 0 and z1['eins_zu_stunde'] < float('inf'))
z2 = OD.zahlen(target, 1e6); t('G13 Odds: Gegenprobe Anteil am Netz x 144 Bloecke/Tag == Tageschance (auf 1 % genau)', abs(z2['anteil_am_netz'] * 144 / z2['chance_tag'] - 1) < 0.01)
t('G14 k2: Padding W8..W15 je Runde als nonce-frei beschriftet, W0..W7 nicht', all(lb['k2']['runden'][i]['W_nonce_frei'] for i in range(8, 16)) and not any(lb['k2']['runden'][i]['W_nonce_frei'] for i in range(8)))
z0 = OD.zahlen(target, 0.0); t('G15 Odds: Hashrate 0 -> Chance 0, kein Absturz', z0['chance_tag'] == 0 and z0['eins_zu_tag'] == float('inf'))
zz = OD.zahlen(2**192 - 1, 1e9); t('G16 Odds: Ghosts Gegenfall Target 2^192-1, 1e9 H/s, ein Tag ~ 4.68e-6', abs(zz['chance_tag'] / 4.683742416381618e-6 - 1) < 1e-6)
anzahl = 14 if '--ohne-suche' in sys.argv else 16
if anzahl == 14: print('G10/G11 AUSGELASSEN: keine Nonce-Suche')
print(f'{ok}/{anzahl} bestanden'); sys.exit(0 if ok == anzahl else 1)
