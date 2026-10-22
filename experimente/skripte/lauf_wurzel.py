#!/usr/bin/env python3
"""STUFE 1 – WURZELTEST, ELTERNPROZESS (Fable, 2026-10-22). Je Auswertung ein Kindprozess (python -I wurzel_kind.py ART FALL), extern ueberwacht
(RSS alle 0,1 s ueber /proc, Wall): 600 s / 400 MiB je Auswertung inkl. Aufbau -> Kind beendet, Auswertung OFFEN (Fortschritt aus Teil-JSON).
Reihenfolge: E1 F1, E1 F2 (Referenz), E4 F1, E4 F2 (Basis); E4D F1, E4D F2 (Dreier) NUR wenn beide Basislaeufe ohne FEHLER/Abbruch endeten,
sonst NOT_RUN. Keine Wiederholungen, keine Folgelaeufe. Ergebnis: ERGEBNIS_WURZEL.json + ERGEBNIS_<ART>_<FALL>.json."""
import subprocess, sys, time, json, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; ZEIT_S, RAM_MIB = 600.0, 400.0
def rss_mib(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024
    except FileNotFoundError: return 0.0
    return 0.0
erg = dict(stufe='1 Wurzeltest', beginn=time.strftime('%Y-%m-%d %H:%M:%S'), python=platform.python_version(), grenze=dict(zeit_s=ZEIT_S, ram_mib=RAM_MIB, paare=500000), auswertungen=[])
def lauf(art, fall):
    aus = 'ERGEBNIS_%s_%s.json' % (art, fall); p = HERE / aus
    if p.exists(): p.unlink()
    t = time.perf_counter(); kind = subprocess.Popen([sys.executable, '-I', str(HERE / 'wurzel_kind.py'), art, fall, aus], cwd=str(HERE)); peak = 0.0; grund = None
    while kind.poll() is None:
        time.sleep(0.1); r = rss_mib(kind.pid); peak = max(peak, r)
        if r > RAM_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, RAM_MIB)
        elif time.perf_counter() - t > ZEIT_S: grund = 'Wall > %.0f s' % ZEIT_S
        if grund: kind.kill(); kind.wait(); break
    wall = time.perf_counter() - t; k = json.loads(p.read_text()) if p.exists() else None
    if grund:
        status = 'OFFEN'
        if k: k['status'] = 'OFFEN'; k['abbruchgrund'] = grund; p.write_text(json.dumps(k, indent=1))
    else: status = k['status'] if k else 'FEHLER_OHNE_AUSGABE'
    e = dict(art=art, fall=fall, status=status, abbruchgrund=grund, wall_s=round(wall, 1), peak_rss_mib_extern=round(peak, 1), rueckgabe=kind.returncode, ausgabe=aus if k else None,
             ergebnis_status=(k or {}).get('ergebnis', {}).get('status') if k else None, letzter_schritt=(k['schritte'][-1]['name'] if k and k['schritte'] else None))
    erg['auswertungen'].append(e); print('%-4s %-3s %-8s %7.1f s  Peak %6.1f MiB  %s' % (art, fall, status, wall, peak, grund or ''), flush=True)
    (HERE / 'ERGEBNIS_WURZEL.json').write_text(json.dumps(erg, indent=1)); return status
basis = {}
for art in ('E1', 'E4'):
    for fall in ('F1', 'F2'): basis[(art, fall)] = lauf(art, fall)
if all(basis[('E4', f)] == 'OK' for f in ('F1', 'F2')):
    for fall in ('F1', 'F2'): lauf('E4D', fall)
else:
    for fall in ('F1', 'F2'): erg['auswertungen'].append(dict(art='E4D', fall=fall, status='NOT_RUN', grund='Basis nicht beide OK'))
erg['ende'] = time.strftime('%Y-%m-%d %H:%M:%S'); erg['gesamt_wall_s'] = round(sum(x.get('wall_s', 0) for x in erg['auswertungen']), 1)
(HERE / 'ERGEBNIS_WURZEL.json').write_text(json.dumps(erg, indent=1))
