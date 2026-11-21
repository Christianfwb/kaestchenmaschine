#!/usr/bin/env python3
"""glas_miner.py - Der glaeserne Miner, Stufe 1 (Kommandozeile). Ein Miner, der zeigt, was er tut.

  python glas_miner.py lebenslauf [--header DATEI] [--nonce HEX] [--runde k1:5]   Lebenslauf einer Nonce, Runde fuer Runde
  python glas_miner.py odds       [--header DATEI] [--hashrate H/s]                ehrliche Chancen aus nBits
  python glas_miner.py mine       [--header DATEI] [--start HEX] [--anzahl N] [--sekunden S]   echtes Hashen, sichtbar
  python glas_miner.py beweis     [--header DATEI] [--nonce HEX]                   Beweisbuch der Kaestchenmaschine fuer diese Nonce
  python glas_miner.py avalanche  [--header DATEI] [--nonce HEX] [--bit N] [--ausgabe X.json]  Avalanche-Labor: Kippen, Statistik, Abhaengigkeitskarte
  python glas_miner.py kante      [--header DATEI] [--nonce HEX] [--runden 16,17]  die Kante: herleiten bis 16, stehen bleiben ab 17
  python glas_miner.py test                                                        Selbsttest gegen hashlib

Header-Datei: JSON mit header76_hex (76 Byte) und optional nonce_hex (bekannter Treffer), quelle. Standard: headers/H970000.json.
Kein Versprechen auf Geschwindigkeit. Keine Nonce wird uebersprungen. Miner und Node des Projekts bleiben unveraendert."""
import sys, json, argparse
from pathlib import Path
H = Path(__file__).resolve().parent; sys.path.insert(0, str(H))
from glas import lebenslauf as LB, odds as OD, miner_cpu as MC

def header_laden(pfad):
    d = json.load(open(pfad)); h = bytes.fromhex(d['header76_hex']); assert len(h) == 76, 'header76_hex muss 76 Byte haben'
    return h, d

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('befehl', choices=['lebenslauf', 'odds', 'mine', 'beweis', 'kante', 'avalanche', 'test'])
    ap.add_argument('--bit', type=int, default=0); ap.add_argument('--ausgabe', help='JSON-Datei fuer avalanche (Kurven, Statistik, Abhaengigkeits-Matrix)')
    ap.add_argument('--header', default=str(H / 'headers' / 'H970000.json')); ap.add_argument('--nonce'); ap.add_argument('--runde', help='z.B. k1:5 oder k2:61 oder alle')
    ap.add_argument('--hashrate', type=float); ap.add_argument('--start'); ap.add_argument('--anzahl', type=int, default=1 << 20); ap.add_argument('--sekunden', type=float)
    ap.add_argument('--runden', default='16,17'); a = ap.parse_args()
    if a.befehl == 'test':
        import subprocess; sys.exit(subprocess.call([sys.executable, '-I', str(H / 'tests_glas.py')]))
    h, d = header_laden(a.header); target = OD.nbits_zu_target(OD.nbits_aus_header(h))
    nonce = int(a.nonce, 16) if a.nonce else int(d.get('nonce_hex', '0'), 16)
    print(f"Header: {d.get('quelle', a.header)}  nBits {OD.nbits_aus_header(h):08x}  Target {target.bit_length()} Bit ({256 - target.bit_length()} Nullbits)")
    if a.befehl == 'lebenslauf':
        lb = LB.lebenslauf(h, nonce, target); print(LB.kurz(lb))
        if a.runde:
            if a.runde == 'alle':
                for komp in ('k0', 'k1', 'k2'):
                    for t in range(64): print(LB.runde_text(lb, komp, t))
            else:
                komp, t = a.runde.split(':'); print(LB.runde_text(lb, komp, int(t)))
        print('  (* = Fahrplanwort nonce-frei)')
    elif a.befehl == 'odds':
        hr = a.hashrate
        if hr is None:
            m = MC.mine(h, 0, start=0, anzahl=200000); hr = m['hashrate']; print(f"Eigene Hashrate gemessen (200.000 Nonces, eine CPU, Python+hashlib): {OD.si(hr)}")
        print(OD.text(OD.zahlen(target, hr)))
    elif a.befehl == 'mine':
        start = int(a.start, 16) if a.start else 0
        m = MC.mine(h, target, start=start, anzahl=a.anzahl, sekunden=a.sekunden, melden=lambda s: print(MC.zeile(s), end='', flush=True)); print()
        print(f"{m['status']}: {m['geprueft']:,} Nonces in {m['sekunden']:.1f} s = {OD.si(m['hashrate'])}; bestes Ergebnis {m['bester_hash_zahl'].bit_length()} Bit bei Nonce {m['bester_nonce']:08x}" +
              (f"; TREFFER Nonce {m['treffer_nonce']:08x} Hash {bytes.fromhex(m['treffer_digest'])[::-1].hex()}" if m['treffer_nonce'] is not None else ''))
        z = OD.zahlen(target, m['hashrate']); print(f"Zum Vergleich: Chance auf einen Block bei dieser Hashrate je Tag 1 zu {z['eins_zu_tag']:.3e}. Keine Nonce wurde uebersprungen.")
    elif a.befehl == 'beweis':
        from glas import kaestchen as KM
        print(f"Baue Kaestchenmaschine fuer Nonce {nonce:08x} (volle 64 Runden, drei Kompressionen) ...", flush=True)
        b = KM.beweis(h, nonce)
        print(f"Beweisbuch: {b['zeilen']:,} Zeilen ({', '.join(f'{k} {v}' for k, v in sorted(b['zeilenarten'].items()))}), {b['bits_fest']:,} feste Bits")
        print(f"Digest aus den geprueften Buchzeilen: {bytes.fromhex(b['digest_aus_buch'])[::-1].hex() if b['digest_aus_buch'] else '-'}  == hashlib: {b['pruefung_vollstaendig']}")
        print(f"Unabhaengiger Pruefer: {b['pruefer_fehler']} Fehler; Hash-Bits mit Buchzeile: {b['hash_bits_belegt']}/256; Beweis vollstaendig: {b['pruefung_vollstaendig']} (Vertrag ohne Zielvorgabe: bewiesen ist die Hashberechnung).  Aufbau+Herleitung {b['zeit_aufbau_herleitung']} s, Pruefung {b['zeit_pruefung']} s")
    elif a.befehl == 'avalanche':
        from glas import avalanche as AV
        av = AV.kippen(h, nonce, a.bit); st = AV.statistik(h, 300); ak = AV.abhaengigkeitskarte(h, nonce)
        print(f"Bit {a.bit} gekippt: {nonce:08x} -> {av['nonce2']:08x}; k1 erster Unterschied Runde {av['komp']['k1']['erste_runde_mit_unterschied']}; Hash-Abstand {av['hash_abstand']}/256")
        print('k1 je Runde:', ' '.join(str(v) for v in AV.kurve(av, 'k1'))); print('k2 je Runde:', ' '.join(str(v) for v in AV.kurve(av, 'k2')))
        ha = st['hash_abstand']; print(f"Statistik 300 Paare: Mittel {ha['mittel']:.2f}, Streuung {ha['std']:.2f}, min {ha['min']}, max {ha['max']} (Erwartungswert 128, Streuung 8 - kein Maximum); z = {ha['abweichung_in_std']:+.2f}")
        print('Abhaengigkeitskarte k1 erreichte Bits je Runde:', ' '.join(str(v) for v in ak['erreichte_zustandsbits']['k1'][:12]), '... alle 256 ab Runde', ak['erste_runde_alle_256'])
        if a.ausgabe:
            json.dump(dict(kippen={k: v for k, v in av.items() if k != 'komp'}, kurven={k: AV.kurve(av, k) for k in ('k1', 'k2')}, statistik=st, abhaengigkeitskarte=ak), open(a.ausgabe, 'w'), indent=1)
            print('geschrieben:', a.ausgabe, '(mit Bit-Matrix)')
    elif a.befehl == 'kante':
        from glas import kaestchen as KM
        for r in [int(x) for x in a.runden.split(',')]:
            print(f"r = {r:2d} Runden je Kompression, untere 16 Noncebits frei, Ziel = reduzierter Hash der Nonce {nonce:08x} ...", flush=True)
            e = KM.kante(h, nonce, r)
            if e['nonce_hergeleitet']: print(f"   -> Maschine leitet die Nonce HER: {e['nonce_hergeleitet']} (stimmt: {e['stimmt']}), {e['zeilen']:,} Beweiszeilen, Pruefer {e['pruefer_fehler']} Fehler, {e['sekunden']} s")
            else: print(f"   -> Maschine bleibt stehen (dieser Versuch, kein Unmoeglichkeitsbeweis): {e['noncebits_fest']}/16 Noncebits, k2_W16 feste Bits: {e['k2_W16_feste_bits']}, {e['zeilen']:,} Zeilen, {e['sekunden']} s, Stop: {e['stop']}")

if __name__ == '__main__': main()
