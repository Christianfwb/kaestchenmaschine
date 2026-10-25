"""Waechter: vier Kinder (N3/N3u x R/A), je 120 s / 400 MiB (0,1 s Abtastung). Danach Vergleich E1 (gleiche Ausgangstabellen) und E2 (gleiche Endrelationen bei N3). Keine Labor-Importe."""
import sys, os, json, time, subprocess, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); GRENZE_S, GRENZE_MIB = 120.0, 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024.0
    except Exception: pass
    return 0.0
if __name__ == '__main__':
    prot = dict(grenzen=dict(zeit_s=GRENZE_S, rss_mib=GRENZE_MIB), python=sys.version.split()[0], laeufe={}, dateien={f: hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest() for f in ('ereignis.py', 'ereignis_lauf.py')})
    E = {}; ok = True
    for fall in ('N3', 'N3u'):
        for verf in ('R', 'A'):
            erg = os.path.join(HERE, 'ERGEBNIS_EREIGNIS_%s_%s.json' % (fall, verf)); os.path.exists(erg) and os.remove(erg)
            t = time.perf_counter(); peak = 0.0; grund = None; p = subprocess.Popen([sys.executable, '-I', os.path.join(HERE, 'ereignis.py')], cwd=HERE, env=dict(os.environ, FALL=fall, VERFAHREN=verf))
            while p.poll() is None:
                time.sleep(0.1); r = rss(p.pid); peak = max(peak, r)
                if r > GRENZE_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, GRENZE_MIB)
                elif time.perf_counter() - t > GRENZE_S: grund = 'Zeit > %.0f s' % GRENZE_S
                if grund: p.kill(); p.wait(); break
            e = json.load(open(erg)) if os.path.exists(erg) else None; E[(fall, verf)] = e
            status = 'OFFEN (Grenze: %s)' % grund if grund else ('OK' if p.returncode == 0 and e else 'FEHLER (Rueckgabe %s)' % p.returncode)
            prot['laeufe']['%s_%s' % (fall, verf)] = dict(status=status, wall_s=round(time.perf_counter() - t, 2), peak_rss_abgetastet_mib=round(peak, 1), maxrss_kind_mib=(e or {}).get('maxrss_mib'))
            if status != 'OK': ok = False; print('STOPP bei', fall, verf, status); break
        if not ok: break
    if ok:
        v = {}
        for fall in ('N3', 'N3u'):
            r, a = E[(fall, 'R')], E[(fall, 'A')]
            v[fall] = dict(E1_gleiche_ausgangstabellen=(r['ausgang_pruefsumme'] == a['ausgang_pruefsumme']), gleicher_status=(r['status'] == a['status']),
                           E2_gleiche_endrelationen=(r['endrelationen_pruefsumme'] == a['endrelationen_pruefsumme']) if fall == 'N3' else None,
                           gleiche_gestrichene_zeilen=(r['zaehler']['gestrichen'] == a['zaehler']['gestrichen']) if fall == 'N3' else None)
        prot['vergleich'] = v; ok = all(x for d in v.values() for x in d.values() if x is not None)
    prot['alle_ok'] = ok; json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_EREIGNIS_BEGRENZT.json'), 'w'), indent=1)
    print('Vergleich:', prot.get('vergleich'), '| Laeufe:', {k: (d['status'], d['wall_s'], d['maxrss_kind_mib']) for k, d in prot['laeufe'].items()}, '| alle_ok', ok); sys.exit(0 if ok else 3)
