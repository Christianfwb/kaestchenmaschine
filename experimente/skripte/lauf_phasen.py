#!/usr/bin/env python3
"""ELTERNPROZESS fuer den Phasenvergleich (Fable, 2026-10-22): Budget 120 s / 400 MiB, extern ueberwacht (RSS alle 0,1 s)."""
import subprocess, sys, time, json, pathlib
HERE = pathlib.Path(__file__).resolve().parent; ZEIT_S, RAM_MIB = 120.0, 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024
    except FileNotFoundError: return 0.0
    return 0.0
aus = 'ERGEBNIS_PHASEN.json'; p = HERE / aus
if p.exists(): p.unlink()
t = time.perf_counter(); kind = subprocess.Popen([sys.executable, '-I', str(HERE / 'phasen_kind.py'), aus], cwd=str(HERE))
peak = 0.0; grund = None
while kind.poll() is None:
    time.sleep(0.1); r = rss(kind.pid); peak = max(peak, r)
    if r > RAM_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, RAM_MIB)
    elif time.perf_counter() - t > ZEIT_S: grund = 'Wall > %.0f s' % ZEIT_S
    if grund: kind.kill(); kind.wait(); break
wall = time.perf_counter() - t
print('Wall %.1f s, Peak extern %.1f MiB, Rueckgabe %s, Abbruch: %s' % (wall, peak, kind.returncode, grund or 'keiner'))
if p.exists():
    d = json.loads(p.read_text()); d['wall_s_extern'] = round(wall, 1); d['peak_mib_extern'] = round(peak, 1); d['abbruchgrund'] = grund
    if grund: d['status'] = 'OFFEN'
    p.write_text(json.dumps(d, indent=1)); print('Status:', d['status'])
