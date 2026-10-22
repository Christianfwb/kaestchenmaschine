#!/usr/bin/env python3
"""Rundenkurve, Elternprozess (Fable, 2026-10-23): R = 4, 6, 8, 12, 16 nacheinander, je 600 s / 400 MiB / 2,5 Mio. Paare, RSS alle 0,1 s;
Abbruch = OFFEN; FEHLER stoppt die Reihe; keine Wiederholung."""
import subprocess, sys, time, json, pathlib
HERE = pathlib.Path(__file__).resolve().parent; ZEIT_S, RAM_MIB, MAXP = 600.0, 400.0, 2500000
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024
    except FileNotFoundError: return 0.0
    return 0.0
erg = dict(messung='Rundenkurve reduziertes SHA256d, F1, 8 freie Noncebits, Zielhash aus Kontrollnonce', grenze=dict(zeit_s=ZEIT_S, ram_mib=RAM_MIB, paare=MAXP), laeufe=[])
for R in (4, 6, 8, 12, 16):
    aus = 'ERGEBNIS_RUNDEN_R%02d.json' % R; p = HERE / aus
    if p.exists(): p.unlink()
    t = time.perf_counter(); kind = subprocess.Popen([sys.executable, '-I', str(HERE / 'runden_kind.py'), str(R), aus, str(MAXP)], cwd=str(HERE)); peak = 0.0; grund = None
    while kind.poll() is None:
        time.sleep(0.1); r = rss(kind.pid); peak = max(peak, r)
        if r > RAM_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, RAM_MIB)
        elif time.perf_counter() - t > ZEIT_S: grund = 'Wall > %.0f s' % ZEIT_S
        if grund: kind.kill(); kind.wait(); break
    wall = time.perf_counter() - t; k = json.loads(p.read_text()) if p.exists() else None
    status = 'OFFEN' if grund else (k['status'] if k else 'FEHLER_OHNE_AUSGABE')
    if grund and k: k['status'] = 'OFFEN'; k['abbruchgrund'] = grund; p.write_text(json.dumps(k, indent=1))
    e = (k or {}).get('ergebnis') or {}; e1 = next((s for s in (k or {}).get('schritte', []) if s['name'] == 'E1'), {})
    z = dict(runden=R, status=status, abbruchgrund=grund, wall_s=round(wall, 1), peak_rss_mib_extern=round(peak, 1), rueckgabe=kind.returncode, ausgang=e.get('ausgang'),
             stufe=e.get('stufe'), e1_status=e1.get('status'), e1_sweeps=e1.get('sweeps'), e1_s=e1.get('s'), noncebits_e1=len(e1.get('noncebits', [])), noncebits=len(e.get('noncebits_abgeleitet', [])),
             verbleibende_kandidaten=e.get('verbleibende_kandidaten'), treffer=e.get('orakel', {}).get('treffer'), paare=e.get('paare'), fehler=(k or {}).get('fehler'))
    erg['laeufe'].append(z); print(json.dumps(z), flush=True)
    (HERE / 'ERGEBNIS_RUNDEN.json').write_text(json.dumps(erg, indent=1))
    if status == 'FEHLER': print('STOPP'); break
erg['gesamt_wall_s'] = round(sum(x['wall_s'] for x in erg['laeufe']), 1); (HERE / 'ERGEBNIS_RUNDEN.json').write_text(json.dumps(erg, indent=1)); print('fertig')
