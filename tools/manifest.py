"""Verify released bytes; update from tracked files after git add."""
import argparse
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--update', action='store_true')
    args = parser.parse_args()
    if args.check == args.update:
        parser.error('Choose --check or --update')
    manifest = ROOT / 'SHA256SUMS.txt'
    if args.update:
        names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
        names = sorted(n for n in names if n and n not in ('SHA256SUMS.txt', 'DATEILISTE.txt'))
        (ROOT / 'DATEILISTE.txt').write_text('\n'.join(names + ['DATEILISTE.txt', 'SHA256SUMS.txt']) + '\n', encoding='utf-8', newline='\n')
        names = sorted(names + ['DATEILISTE.txt'])
        # Repository policy is LF. Normalize checkout bytes for reproducible release hashes.
        lines = [hashlib.sha256((ROOT/n).read_bytes().replace(b'\r\n', b'\n')).hexdigest() + '  ' + n for n in names]
        manifest.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        print('Updated', len(lines), 'file hashes')
    else:
        bad = []; count = 0
        for line in manifest.read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            expected, name = line.split(maxsplit=1); path = ROOT / name
            count += 1
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                bad.append(name)
        if bad:
            raise SystemExit('Checksum mismatch (check LF line endings): ' + ', '.join(bad))
        print('All', count, 'file hashes match')

if __name__ == '__main__':
    main()
