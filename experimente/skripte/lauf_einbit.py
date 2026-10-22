#!/usr/bin/env python3
"""EIN-BIT-GEGENPRUEFUNG, ELTERNPROZESS (Fable, 2026-10-22). Je Lauf ein Kindprozess (einbit_kind.py FALL VARIANTE), extern
ueberwacht (RSS alle 0,1 s ueber /proc, Wallzeit): 600 s / 400 MiB je Lauf, Paargrenze 2 500 000. Abbruch = OFFEN, keine
automatische Wiederholung, keine Ausweitung. Reihenfolge: F1 (echte Vorlage) E3, E3Z, E4, E4Z; dann F2 (Genesis, bekannter
Treffer in der Gruppe) ebenso. Ein FEHLER (falscher Ausschluss) stoppt alles sofort."""
import subprocess, sys, time, json, pathlib, platform
HERE = pathlib.Path(__file__).resolve().parent; ZEIT_S, RAM_MIB, MAXP = 600.0, 400.0, 2500000
def rss_mib(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024
    except FileNotFoundError: return 0.0
    return 0.0
erg = dict(messung='Ein-Bit-Gegenpruefung', beginn=time.strftime('%Y-%m-%d %H:%M:%S'), python=platform.python_version(),
           grenze=dict(zeit_s=ZEIT_S, ram_mib=RAM_MIB, paare=MAXP), laeufe=[])
def lauf(fall, var):
    aus = 'ERGEBNIS_EINBIT_%s_%s.json' % (fall, var); p = HERE / aus
    if p.exists(): p.unlink()
    t = time.perf_counter()
    kind = subprocess.Popen([sys.executable, '-I', str(HERE / 'einbit_kind.py'), fall, var, aus, str(MAXP)], cwd=str(HERE))
    peak = 0.0; grund = None
    while kind.poll() is None:
        time.sleep(0.1); r = rss_mib(kind.pid); peak = max(peak, r)
        if r > RAM_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, RAM_MIB)
        elif time.perf_counter() - t > ZEIT_S: grund = 'Wall > %.0f s' % ZEIT_S
        if grund: kind.kill(); kind.wait(); break
    wall = time.perf_counter() - t
    try: k = json.loads(p.read_text()) if p.exists() else None
    except Exception: k = None
    if grund:
        status = 'OFFEN'
        if k: k['status'] = 'OFFEN'; k['abbruchgrund'] = grund; p.write_text(json.dumps(k, indent=1))
    else: status = k['status'] if k else 'FEHLER_OHNE_AUSGABE'
    e = dict(fall=fall, variante=var, status=status, abbruchgrund=grund, wall_s=round(wall, 1), peak_rss_mib_extern=round(peak, 1),
             rueckgabe=kind.returncode, ausgabe=aus if k else None, fehler=(k or {}).get('fehler'),
             ergebnis=({x: (k['ergebnis'] or {}).get(x) for x in ('status', 'alle_gueltigen_referenzbelegungen_erhalten', 'massgebliche_zustaende', 'unloesbarer_referenzfall', 'paare_insgesamt')} if k and k.get('ergebnis') else None))
    erg['laeufe'].append(e)
    print('%-3s %-4s %-8s %6.1f s  Peak %6.1f MiB  %s' % (fall, var, status, wall, peak, grund or ''), flush=True)
    (HERE / 'ERGEBNIS_EINBIT.json').write_text(json.dumps(erg, indent=1))
    return status
for fall in ('F1', 'F2'):
    for var in ('E3', 'E3Z', 'E4', 'E4Z'):
        if lauf(fall, var) == 'FEHLER': print('STOPP: FEHLER in', fall, var); erg['abbruch'] = '%s %s FEHLER' % (fall, var); break
    else: continue
    break
erg['ende'] = time.strftime('%Y-%m-%d %H:%M:%S'); erg['gesamt_wall_s'] = round(sum(x['wall_s'] for x in erg['laeufe']), 1)
(HERE / 'ERGEBNIS_EINBIT.json').write_text(json.dumps(erg, indent=1))
