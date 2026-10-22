#!/usr/bin/env python3
"""Elternprozess XOR-Gleichungsanalyse (Fable, 2026-10-22): je Lauf 600 s / 400 MiB, RSS alle 0,1 s. Laeufe: F1 und F2 mit 2 freien Bits, dann mit 8."""
import subprocess, sys, time, json, pathlib
HERE = pathlib.Path(__file__).resolve().parent; ZEIT_S, RAM_MIB = 600.0, 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024
    except FileNotFoundError: return 0.0
    return 0.0
erg = dict(messung='XOR-Gleichungen aus dem echten SHA-Graphen', laeufe=[])
for fall, nb in (('F1', 2), ('F2', 2), ('F1', 8), ('F2', 8)):
    aus = 'ERGEBNIS_XORSHA_%s_%dbit.json' % (fall, nb); p = HERE / aus
    if p.exists(): p.unlink()
    t = time.perf_counter(); kind = subprocess.Popen([sys.executable, '-I', str(HERE / 'xor_sha_kind.py'), fall, str(nb), aus], cwd=str(HERE)); peak = 0.0; grund = None
    while kind.poll() is None:
        time.sleep(0.1); r = rss(kind.pid); peak = max(peak, r)
        if r > RAM_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, RAM_MIB)
        elif time.perf_counter() - t > ZEIT_S: grund = 'Wall > %.0f s' % ZEIT_S
        if grund: kind.kill(); kind.wait(); break
    wall = time.perf_counter() - t; k = json.loads(p.read_text()) if p.exists() else None
    status = 'OFFEN' if grund else (k['status'] if k else 'FEHLER_OHNE_AUSGABE')
    if grund and k: k['status'] = 'OFFEN'; k['abbruchgrund'] = grund; p.write_text(json.dumps(k, indent=1))
    e = dict(fall=fall, freie_bits=nb, status=status, abbruchgrund=grund, wall_s=round(wall, 1), peak_rss_mib_extern=round(peak, 1), ergebnis=(k or {}).get('ergebnis'))
    erg['laeufe'].append(e); print('%s %d Bit: %-6s %6.1f s  Peak %6.1f MiB  %s' % (fall, nb, status, wall, peak, json.dumps(e['ergebnis'])[:160] if e['ergebnis'] else grund), flush=True)
    (HERE / 'ERGEBNIS_XORSHA.json').write_text(json.dumps(erg, indent=1))
    if status == 'FEHLER': print('STOPP'); break
