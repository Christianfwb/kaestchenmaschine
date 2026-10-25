"""Waechter: drei Kinder (minfill Referenz, mindegree, minfill_rev), je 120 s / 400 MiB. Grenze -> OFFEN, Fehler -> FEHLER. Keine Labor-Importe."""
import sys, os, json, time, subprocess, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); GRENZE_S, GRENZE_MIB = 120.0, 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024.0
    except Exception: pass
    return 0.0
if __name__ == '__main__':
    prot = dict(grenzen=dict(zeit_s=GRENZE_S, rss_mib=GRENZE_MIB), python=sys.version.split()[0], laeufe={}, dateien={f: hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest() for f in ('n4r10_heuristik.py', 'n4r10_heuristik_lauf.py')}); ok = True
    for h in ('minfill', 'mindegree', 'minfill_rev'):
        erg = os.path.join(HERE, 'ERGEBNIS_N4R10_HEUR_%s.json' % h); os.path.exists(erg) and os.remove(erg)
        t = time.perf_counter(); peak = 0.0; grund = None; p = subprocess.Popen([sys.executable, '-I', os.path.join(HERE, 'n4r10_heuristik.py')], cwd=HERE, env=dict(os.environ, HEUR=h))
        while p.poll() is None:
            time.sleep(0.1); r = rss(p.pid); peak = max(peak, r)
            if r > GRENZE_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, GRENZE_MIB)
            elif time.perf_counter() - t > GRENZE_S: grund = 'Zeit > %.0f s' % GRENZE_S
            if grund: p.kill(); p.wait(); break
        e = json.load(open(erg)) if os.path.exists(erg) else None; status = 'OFFEN (Grenze: %s)' % grund if grund else ('OK' if p.returncode == 0 and e else 'FEHLER (Rueckgabe %s)' % p.returncode)
        prot['laeufe'][h] = dict(status=status, wall_s=round(time.perf_counter() - t, 2), peak_rss_abgetastet_mib=round(peak, 1), maxrss_kind_mib=(e or {}).get('maxrss_mib'), groesste_gruppe=(e or {}).get('struktur', {}).get('groesste_gruppe'), groesste_schnittstelle=(e or {}).get('struktur', {}).get('groesste_schnittstelle'), summe_MiB=(e or {}).get('summe_MiB'), aufwand=(e or {}).get('austausch_aufwand_summe_2s_mal_s_minus_1'))
        if status != 'OK': ok = False
    prot['alle_ok'] = ok; json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_N4R10_HEUR_BEGRENZT.json'), 'w'), indent=1, default=str); print(json.dumps(prot['laeufe'], indent=0)); sys.exit(0 if ok else 3)
