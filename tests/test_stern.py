"""Schnelltests fuer das L1-Labor (Stern, Gruppenfindung, Arbeitsliste, begrenzte Gruppen, Bitmengen, blockweise, Ausduennen).
Linux-only (resource, /proc); unter Windows wird uebersprungen. Laufzeit ~20 s."""
import os, sys, subprocess, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]; L1 = ROOT / 'experimente' / 'l1'
try: import resource  # noqa
except ImportError: print('test_stern: uebersprungen (kein resource-Modul, Linux-only)'); sys.exit(0)
def lauf(rel, env=None, erwartet=0):
    p = subprocess.run([sys.executable, '-B', '-I', str(L1 / rel)], cwd=str((L1 / rel).parent), env=dict(os.environ, **(env or {})), capture_output=True, text=True, timeout=300)
    zeile = (p.stdout.strip().splitlines() or [''])[-1]; ok = (p.returncode == erwartet); print(('OK   ' if ok else 'FEHL ') + rel + ' | ' + zeile[:140])
    if not ok: print(p.stderr[-800:])
    return ok
ok = True
ok &= lauf('stern/gruppen_lauf.py')                                   # sieben Faelle Gruppenfindung + Austausch
ok &= lauf('stern/gruppen_sabotage.py')                               # Sabotage erkannt
ok &= lauf('stern/ereignis_lauf.py')                                  # Arbeitsliste == Rundenlauf (N3/N3u)
ok &= lauf('stern/begrenzt_lauf.py')                                  # Dreieck exakt/begrenzt
ok &= lauf('stern/bitmenge.py')                                       # Selbsttest Bitmengen
ok &= lauf('stern/bitmenge_schlank.py')                               # Selbsttest schlanke Masken
ok &= lauf('stern/blockweise.py')                                     # Selbsttest blockweise
ok &= lauf('stern_n3/stern_n3_lauf.py') if (L1 / 'stern_n3' / 'stern_n3_lauf.py').exists() else True
ok &= lauf('ausduennen/ausduennen.py', dict(KOPF='2', K='4', RUNDEN='6'))   # ein Ausduenn-Fall (Sicherheit, Bilanz)
e = json.load(open(L1 / 'ausduennen' / 'ERGEBNIS_AUSD2_r6_k4_F2.json')); ok &= e['pruefung']['E1_sicher'] and e['form1']['rang'] == 0
print('test_stern:', 'BESTANDEN' if ok else 'FEHLER'); sys.exit(0 if ok else 1)
