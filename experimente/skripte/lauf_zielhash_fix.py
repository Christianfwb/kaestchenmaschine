#!/usr/bin/env python3
"""Zielhash-Vergleich abschliessen (Fable, 2026-10-23): B/E1 allein ueber 12 Durchlaeufe hinaus bis Fixpunkt/Widerspruch/Limit.
Ein Lauf, 600 s / 400 MiB, RSS alle 0,1 s; Abbruch = OFFEN. Vergleich an den Messstellen mit dem vorhandenen ERGEBNIS_ZIELHASH_B_E4.json."""
import subprocess, sys, time, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from referenz import referenz_datei
HERE = pathlib.Path(__file__).resolve().parent; ZEIT_S, RAM_MIB = 600.0, 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024
    except FileNotFoundError: return 0.0
    return 0.0
aus = 'ERGEBNIS_ZIELHASH_B_E1_FIX.json'; p = HERE / aus
if p.exists(): p.unlink()
t = time.perf_counter(); kind = subprocess.Popen([sys.executable, '-I', str(HERE / 'zielhash_kind.py'), 'B', 'E1', aus, '2500000', '1000000'], cwd=str(HERE)); peak = 0.0; grund = None
while kind.poll() is None:
    time.sleep(0.1); r = rss(kind.pid); peak = max(peak, r)
    if r > RAM_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, RAM_MIB)
    elif time.perf_counter() - t > ZEIT_S: grund = 'Wall > %.0f s' % ZEIT_S
    if grund: kind.kill(); kind.wait(); break
wall = time.perf_counter() - t; k = json.loads(p.read_text()) if p.exists() else None
status = 'OFFEN' if grund else (k['status'] if k else 'FEHLER_OHNE_AUSGABE')
if grund and k: k['status'] = 'OFFEN'; k['abbruchgrund'] = grund; p.write_text(json.dumps(k, indent=1))
erg = dict(messung='Zielhash B/E1 bis Fixpunkt', grenze=dict(zeit_s=ZEIT_S, ram_mib=RAM_MIB), status=status, abbruchgrund=grund, wall_s=round(wall, 1),
           peak_rss_mib_extern=round(peak, 1), rueckgabe=kind.returncode)
if k and not grund:
    e4 = json.loads(referenz_datei('ERGEBNIS_ZIELHASH_B_E4.json').read_text(encoding='utf-8')); e1alt = json.loads(referenz_datei('ERGEBNIS_ZIELHASH_B_E1.json').read_text(encoding='utf-8'))
    K = {(z['phase'], z['runde'], z['reg']): z for z in k['karte']}; K4 = {(z['phase'], z['runde'], z['reg']): z for z in e4['karte']}; K1 = {(z['phase'], z['runde'], z['reg']): z for z in e1alt['karte']}
    diff = [dict(messstelle='%s r%d %s' % m, e1_12=K1[m]['bits_fest'], e1_fix=K[m]['bits_fest'], e1e4=K4[m]['bits_fest']) for m in K if K[m]['bits_fest'] != K4[m]['bits_fest'] or K[m]['bits_fest'] != K1[m]['bits_fest']]
    erg['vergleich'] = dict(e1_sweeps=[s for s in k['schritte'] if s['name'] == 'E1'][0], bitknoten_fest=dict(e1_12=e1alt['ergebnis']['bitknoten_fest'], e1_fix=k['ergebnis']['bitknoten_fest'], e1e4=e4['ergebnis']['bitknoten_fest']),
        noncebits=dict(e1_fix=k['ergebnis']['noncebits_abgeleitet'], e1e4=e4['ergebnis']['noncebits_abgeleitet']), messstellen_verschieden=diff, ausgang=k['ergebnis']['ausgang'])
(HERE / 'ERGEBNIS_ZIELHASH_FIX.json').write_text(json.dumps(erg, indent=1)); print(json.dumps(erg, indent=1))
