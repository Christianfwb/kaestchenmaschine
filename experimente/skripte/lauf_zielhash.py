#!/usr/bin/env python3
"""Elternprozess Zielhash-Versuch (Fable, 2026-10-22): vier Wurzelauswertungen A/E1, A/E4, B/E1, B/E4; je 600 s / 400 MiB / 2,5 Mio. Paare,
RSS alle 0,1 s; Abbruch = OFFEN; FEHLER stoppt; kein Folgelauf."""
import subprocess, sys, time, json, pathlib
HERE = pathlib.Path(__file__).resolve().parent; ZEIT_S, RAM_MIB, MAXP = 600.0, 400.0, 2500000
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024
    except FileNotFoundError: return 0.0
    return 0.0
erg = dict(messung='Zielhash-Versuch: Bedingung A (<= Target) gegen B (= H*)', grenze=dict(zeit_s=ZEIT_S, ram_mib=RAM_MIB, paare=MAXP), laeufe=[])
for bed, art in (('A', 'E1'), ('A', 'E4'), ('B', 'E1'), ('B', 'E4')):
    aus = 'ERGEBNIS_ZIELHASH_%s_%s.json' % (bed, art); p = HERE / aus
    if p.exists(): p.unlink()
    t = time.perf_counter(); kind = subprocess.Popen([sys.executable, '-I', str(HERE / 'zielhash_kind.py'), bed, art, aus, str(MAXP)], cwd=str(HERE)); peak = 0.0; grund = None
    while kind.poll() is None:
        time.sleep(0.1); r = rss(kind.pid); peak = max(peak, r)
        if r > RAM_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, RAM_MIB)
        elif time.perf_counter() - t > ZEIT_S: grund = 'Wall > %.0f s' % ZEIT_S
        if grund: kind.kill(); kind.wait(); break
    wall = time.perf_counter() - t; k = json.loads(p.read_text()) if p.exists() else None
    status = 'OFFEN' if grund else (k['status'] if k else 'FEHLER_OHNE_AUSGABE')
    if grund and k: k['status'] = 'OFFEN'; k['abbruchgrund'] = grund; p.write_text(json.dumps(k, indent=1))
    e = dict(bedingung=bed, art=art, status=status, abbruchgrund=grund, wall_s=round(wall, 1), peak_rss_mib_extern=round(peak, 1), rueckgabe=kind.returncode,
             ausgang=((k or {}).get('ergebnis') or {}).get('ausgang'), fehler=(k or {}).get('fehler'))
    erg['laeufe'].append(e); print('%s %-3s %-7s %6.1f s  Peak %6.1f MiB  %s %s' % (bed, art, status, wall, peak, e['ausgang'] or '', grund or ''), flush=True)
    (HERE / 'ERGEBNIS_ZIELHASH.json').write_text(json.dumps(erg, indent=1))
    if status == 'FEHLER': print('STOPP'); break
erg['gesamt_wall_s'] = round(sum(x['wall_s'] for x in erg['laeufe']), 1); (HERE / 'ERGEBNIS_ZIELHASH.json').write_text(json.dumps(erg, indent=1))
