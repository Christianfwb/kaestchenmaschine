"""Waechter fuer strukt_n4.py: Kindprozess, Zeit 120 s und RSS 400 MiB ueberwacht (0,1 s); Grenze -> OFFEN, Fehler -> FEHLER (Exit 3). Eigenstaendig, keine Labor-Importe."""
import sys, os, json, time, subprocess, hashlib
MAXV = os.environ.get('STRUKT_MAX_VARS', '8'); SUF = '' if MAXV == '8' else '_MAX%s' % MAXV
HERE = os.path.dirname(os.path.abspath(__file__)); GRENZE_S, GRENZE_MIB = 120.0, 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024.0
    except Exception: pass
    return 0.0
if __name__ == '__main__':
    erg = os.path.join(HERE, 'ERGEBNIS_STRUKTUR_N4R09%s.json' % SUF); os.path.exists(erg) and os.remove(erg)
    t = time.perf_counter(); peak = 0.0; grund = None; p = subprocess.Popen([sys.executable, '-I', os.path.join(HERE, 'strukt_n4.py')], cwd=HERE)
    while p.poll() is None:
        time.sleep(0.1); r = rss(p.pid); peak = max(peak, r)
        if r > GRENZE_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, GRENZE_MIB)
        elif time.perf_counter() - t > GRENZE_S: grund = 'Zeit > %.0f s' % GRENZE_S
        if grund: p.kill(); p.wait(); break
    wall = round(time.perf_counter() - t, 2); status = 'OFFEN (Grenze: %s)' % grund if grund else ('OK' if p.returncode == 0 and os.path.exists(erg) else 'FEHLER (Rueckgabe %s)' % p.returncode)
    prot = dict(status=status, wall_s=wall, peak_rss_mib=round(peak, 1), grenzen=dict(zeit_s=GRENZE_S, rss_mib=GRENZE_MIB), rueckgabe=p.returncode, python=sys.version.split()[0],
                dateien={f: hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest() for f in ('strukt_n4.py', 'strukt_n4_lauf.py')}, ergebnis=(json.load(open(erg)) if os.path.exists(erg) else None))
    json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_STRUKTUR_N4R09%s_BEGRENZT.json' % SUF), 'w'), indent=1, default=str)
    prot['peak_rss_mib_abgetastet'] = prot.pop('peak_rss_mib'); prot['abtastung_hinweis'] = 'Abtastung alle 0,1 s; bei Laeufen unter 0,1 s wird keine Spitze erfasst (0.0 = nicht gemessen, NICHT = klein)'
    prot['maxrss_mib_kern'] = prot['ergebnis'].get('maxrss_mib') if prot['ergebnis'] else None
    print('Status %s | Wand %.2f s | Spitze RSS abgetastet %.1f MiB (0.0 = nicht erfasst) | Spitze RSS laut Kern (ru_maxrss im Kind) %s MiB | Grenzen %.0f MiB / %.0f s' % (status, wall, peak, prot['maxrss_mib_kern'], GRENZE_MIB, GRENZE_S)); sys.exit(0 if status == 'OK' else 3)
