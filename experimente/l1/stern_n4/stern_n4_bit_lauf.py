"""Waechter: V0 -> V1 -> V2 nacheinander, je eigenes Kind, 120 s / 400 MiB (0,1 s Abtastung). Grenze -> OFFEN + Stopp (Fortschrittsdatei bleibt), Fehler -> FEHLER + Stopp. Keine Wiederholung."""
import sys, os, json, time, subprocess, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); GRENZE_S, GRENZE_MIB = 120.0, 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024.0
    except Exception: pass
    return 0.0
if __name__ == '__main__':
    prot = dict(grenzen=dict(zeit_s=GRENZE_S, rss_mib=GRENZE_MIB), python=sys.version.split()[0], stufen={}, dateien={f: hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest() for f in ('stern_n4_bit.py', 'stern_n4_bit_lauf.py')}); ok = True
    for st in ('V0', 'V1', 'V2'):
        erg = os.path.join(HERE, 'ERGEBNIS_STERN_N4R09_%s.json' % st); os.path.exists(erg) and os.remove(erg)
        t = time.perf_counter(); peak = 0.0; grund = None; p = subprocess.Popen([sys.executable, '-I', os.path.join(HERE, 'stern_n4_bit.py')], cwd=HERE, env=dict(os.environ, STUFE=st))
        while p.poll() is None:
            time.sleep(0.1); r = rss(p.pid); peak = max(peak, r)
            if r > GRENZE_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, GRENZE_MIB)
            elif time.perf_counter() - t > GRENZE_S: grund = 'Zeit > %.0f s' % GRENZE_S
            if grund: p.kill(); p.wait(); break
        e = json.load(open(erg)) if os.path.exists(erg) else None
        status = 'OFFEN (Grenze: %s)' % grund if grund else ('OK' if p.returncode == 0 and e else 'FEHLER (Rueckgabe %s)' % p.returncode)
        fp = os.path.join(HERE, 'FORTSCHRITT_V1.json'); fort = json.load(open(fp)) if (st == 'V1' and os.path.exists(fp)) else None
        prot['stufen'][st] = dict(status=status, wall_s=round(time.perf_counter() - t, 2), peak_rss_abgetastet_mib=round(peak, 1), maxrss_kind_mib=(e or {}).get('maxrss_mib'), rueckgabe=p.returncode, fortschritt_bei_abbruch=(fort if status != 'OK' else None))
        print('%s Status %s | Wand %.2f s | RSS abgetastet %.1f MiB | ru_maxrss Kind %s MiB' % (st, status, time.perf_counter() - t, peak, (e or {}).get('maxrss_mib')))
        if status != 'OK': ok = False; print('STOPP nach', st); break
    prot['alle_ok'] = ok; json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_STERN_N4R09_BEGRENZT.json'), 'w'), indent=1, default=str); sys.exit(0 if ok else 3)
