"""Waechter: je Stufe (0, A, B, C1, C2) ein Kindprozess, 120 s / 400 MiB ueberwacht (0,1 s). Grenze -> OFFEN, Fehler -> FEHLER + Stopp (Exit 3). Keine Labor-Importe."""
import sys, os, json, time, subprocess, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); GRENZE_S, GRENZE_MIB = 120.0, 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024.0
    except Exception: pass
    return 0.0
if __name__ == '__main__':
    prot = dict(grenzen=dict(zeit_s=GRENZE_S, rss_mib=GRENZE_MIB), python=sys.version.split()[0], stufen={}, dateien={f: hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest() for f in ('strukt_n4_vereinfacht.py', 'strukt_n4_vereinfacht_lauf.py')})
    gesamt_ok = True
    for st in ('0', 'A', 'B', 'C1', 'C2'):
        erg = os.path.join(HERE, 'ERGEBNIS_VEREINFACHT_%s.json' % st); os.path.exists(erg) and os.remove(erg)
        env = dict(os.environ, STUFE=st); t = time.perf_counter(); peak = 0.0; grund = None
        p = subprocess.Popen([sys.executable, '-I', os.path.join(HERE, 'strukt_n4_vereinfacht.py')], cwd=HERE, env=env)
        while p.poll() is None:
            time.sleep(0.1); r = rss(p.pid); peak = max(peak, r)
            if r > GRENZE_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, GRENZE_MIB)
            elif time.perf_counter() - t > GRENZE_S: grund = 'Zeit > %.0f s' % GRENZE_S
            if grund: p.kill(); p.wait(); break
        wall = round(time.perf_counter() - t, 2); e = json.load(open(erg)) if os.path.exists(erg) else None
        status = 'OFFEN (Grenze: %s)' % grund if grund else ('OK' if p.returncode == 0 and e else 'FEHLER (Rueckgabe %s)' % p.returncode)
        prot['stufen'][st] = dict(status=status, wall_s=wall, peak_rss_abgetastet_mib=round(peak, 1), maxrss_kind_mib=(e or {}).get('maxrss_mib'), rueckgabe=p.returncode)
        print('Stufe %-2s Status %s | Wand %.2f s | RSS abgetastet %.1f MiB | ru_maxrss Kind %s MiB' % (st, status, wall, peak, (e or {}).get('maxrss_mib')))
        if status != 'OK': gesamt_ok = False; print('STOPP nach Stufe', st); break
    prot['alle_ok'] = gesamt_ok; json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_VEREINFACHT_BEGRENZT.json'), 'w'), indent=1); sys.exit(0 if gesamt_ok else 3)
