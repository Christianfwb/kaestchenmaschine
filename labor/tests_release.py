"""Release checks: complete exported matrix, invalid inputs, no candidate search."""
import functools
import json
import sys
from pathlib import Path
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P))
from glas import avalanche as AV
h = bytes.fromhex(json.loads((P / 'headers/H970000.json').read_text())['header76_hex'])
a = AV.abhaengigkeitskarte(h, 0xacc33125)
a = json.loads(json.dumps(a))
for comp in ('k1', 'k2'):
    matrix = a['matrix'][comp]
    assert len(matrix) == 32
    for row in matrix:
        assert len(row) == 64
        for words in row:
            assert len(words) == 8 and all(type(x) is int and 0 <= x < 2**32 for x in words)
    for t in range(64):
        count = sum(functools.reduce(int.__or__, (matrix[b][t][w] for b in range(32)), 0).bit_count() for w in range(8))
        assert count == a['erreichte_zustandsbits'][comp][t]
for call in (
    lambda: AV.kippen(h, 0, -1), lambda: AV.kippen(h, 0, 32),
    lambda: AV.kippen(h, -1, 0), lambda: AV.kippen(h, 2**32, 0),
    lambda: AV.statistik(h, 0), lambda: AV.statistik(h, 1, bits=[]),
    lambda: AV.statistik(h, 1, bits=[32]),
):
    try:
        call()
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid input accepted')
print('PASS: JSON roundtrip, 32768 matrix words, 128 union counts, 7 invalid inputs')
