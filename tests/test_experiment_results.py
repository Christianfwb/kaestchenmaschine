"""Validate newly produced Linux CI results; process exit zero alone is insufficient."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'experimente' / 'skripte'

def load(name):
    return json.loads((root / name).read_text(encoding='utf-8'))

fixed = load('ERGEBNIS_ZIELHASH_FIX.json')
assert fixed['status'] == 'OK' and fixed['rueckgabe'] == 0 and not fixed['abbruchgrund']
child = load('ERGEBNIS_ZIELHASH_B_E1_FIX.json')
assert child['status'] == 'OK' and child['ergebnis']['status'] == 'FIXPUNKT'
assert child['ergebnis']['noncebits_abgeleitet'] == []
rounds = load('ERGEBNIS_RUNDEN.json')['laeufe']
assert [row['runden'] for row in rounds] == [4, 6, 8, 12, 16]
for row in rounds:
    assert row['status'] == 'OK' and row['rueckgabe'] == 0 and not row['abbruchgrund'], row
    assert row['ausgang'] == 'TREFFER_ABGELEITET' and row['noncebits'] == 8, row
    result = load('ERGEBNIS_RUNDEN_R%02d.json' % row['runden'])['ergebnis']
    assert result['orakel']['treffer'] == [result['orakel']['kontrollnonce']]
print('New target-hash and reduced-round experiment results verified')
