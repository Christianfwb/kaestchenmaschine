#!/usr/bin/env python3
"""ARRAY-GLEICHHEITSREIHE – ELTERNPROZESS (Fable, 2026-10-22). Startet je Phase einen Kindprozess (python -I array_kind.py), ueberwacht durchgehend
(alle 0,1 s) RSS/Peak ueber /proc und Wallzeit; Grenze gesamt 120 s / 400 MiB je Kind -> Kind wird beendet, Phase ABORTED, Stufe 0 stoppt.
Ergebnis: ERGEBNIS_ARRAY.json (Phasen mit Status, Wallzeit, Peak-RSS, Rueckgabecode) + je Phase ERGEBNIS_<PHASE>.json. Kein Suchlauf."""
import subprocess, sys, time, json, pathlib, os, platform
HERE = pathlib.Path(__file__).resolve().parent
ZEIT_S, RAM_MIB = 120.0, 400.0
PHASEN = sys.argv[1:] or ['A1']
def rss_mib(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024
    except FileNotFoundError: return 0.0
    return 0.0
erg = dict(stufe="Array-Gleichheit", beginn=time.strftime('%Y-%m-%d %H:%M:%S'), python=platform.python_version(), grenze=dict(zeit_s=ZEIT_S, ram_mib=RAM_MIB), phasen=[])
T_GESAMT = time.perf_counter()
for ph in PHASEN:
    aus = 'ERGEBNIS_%s.json' % ph; p = HERE / aus
    if p.exists(): p.unlink()
    t = time.perf_counter(); kind = subprocess.Popen([sys.executable, '-I', str(HERE / 'array_kind.py'), ph, aus], cwd=str(HERE))
    peak = 0.0; grund = None
    while kind.poll() is None:
        time.sleep(0.1); r = rss_mib(kind.pid); peak = max(peak, r)
        if r > RAM_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, RAM_MIB)
        elif time.perf_counter() - T_GESAMT > ZEIT_S: grund = 'Gesamtzeit > %.0f s' % ZEIT_S
        if grund: kind.kill(); kind.wait(); break
    wall = time.perf_counter() - t
    k = json.loads(p.read_text()) if p.exists() else None
    status = 'ABORTED' if grund else (k['status'] if k else 'FEHLER_OHNE_AUSGABE')
    erg['phasen'].append(dict(phase=ph, status=status, abbruchgrund=grund, wall_s=round(wall, 2), peak_rss_mib_extern=round(peak, 1), rueckgabe=kind.returncode, ausgabe=aus if k else None))
    print('%-5s %-10s %7.1f s  Peak %6.1f MiB  %s' % (ph, status, wall, peak, grund or ''), flush=True)
    (HERE / 'ERGEBNIS_ARRAY.json').write_text(json.dumps(erg, indent=1))
    if status != 'OK': print('Stufe 0 gestoppt bei', ph); break
erg['ende'] = time.strftime('%Y-%m-%d %H:%M:%S'); erg['gesamt_wall_s'] = round(sum(x['wall_s'] for x in erg['phasen']), 1)
(HERE / 'ERGEBNIS_ARRAY.json').write_text(json.dumps(erg, indent=1))
