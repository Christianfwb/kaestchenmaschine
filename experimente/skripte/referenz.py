"""Read archived baselines explicitly; never substitute a previous local run."""
from pathlib import Path

def referenz_datei(name):
    if Path(name).name != name or name in ('', '.', '..'):
        raise ValueError('Expected a reference filename without directory components')
    path = Path(__file__).resolve().parent.parent / 'ergebnisse' / name
    if not path.is_file():
        raise FileNotFoundError('Archived reference missing: ' + str(path))
    return path
