"""Waechter S0/S1: Selbsttest, Dreieck DU/DL, N3/N3u (je 120 s / 400 MiB), danach N4r09 Stufe B (600 s / 400 MiB HART). Grenze -> OFFEN + Stopp, Fehler -> FEHLER + Stopp. Keine Labor-Importe."""
import sys, os, json, time, subprocess, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); GRENZE_MIB = 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024.0
    except Exception: pass
    return 0.0
def kind(args, env, erg, grenze_s):
    erg and os.path.exists(erg) and os.remove(erg); t = time.perf_counter(); peak = 0.0; grund = None; p = subprocess.Popen([sys.executable, '-I'] + args, cwd=HERE, env=env)
    while p.poll() is None:
        time.sleep(0.1); r = rss(p.pid); peak = max(peak, r)
        if r > GRENZE_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, GRENZE_MIB)
        elif time.perf_counter() - t > grenze_s: grund = 'Zeit > %.0f s' % grenze_s
        if grund: p.kill(); p.wait(); break
    e = json.load(open(erg)) if erg and os.path.exists(erg) else None
    return ('OFFEN (Grenze: %s)' % grund if grund else ('OK' if p.returncode == 0 and e else 'FEHLER (Rueckgabe %s)' % p.returncode)), round(time.perf_counter() - t, 2), round(peak, 1), e
if __name__ == '__main__':
    prot = dict(grenzen=dict(klein_s=120.0, n4r09_s=600.0, rss_mib=GRENZE_MIB), python=sys.version.split()[0], laeufe={}, dateien={f: hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest() for f in ('blockweise.py', 'blockweise_vergleich.py', 'blockweise_lauf.py', 'ereignis_mess.py')}); ok = True
    st, wall, peak, e = kind([os.path.join(HERE, 'blockweise.py')], dict(os.environ), os.path.join(HERE, 'ERGEBNIS_BLOCK_SELBSTTEST.json'), 120.0); prot['laeufe']['selbsttest'] = dict(status=st, wall_s=wall, faelle=(e or {}).get('faelle'), fehler=(e or {}).get('fehler_gesamt')); print('Selbsttest', st, (e or {}).get('faelle'), 'Faelle,', (e or {}).get('fehler_gesamt'), 'Fehler'); ok = ok and st == 'OK'
    for fall, gs in (('DU', 120.0), ('DL', 120.0), ('N3', 120.0), ('N3u', 120.0), ('N4R09', 600.0)):
        if not ok: break
        st, wall, peak, e = kind([os.path.join(HERE, 'blockweise_vergleich.py')], dict(os.environ, BFALL=fall), os.path.join(HERE, 'ERGEBNIS_BLOCK_%s.json' % fall), gs)
        prot['laeufe'][fall] = dict(status=st, wall_s=wall, peak_rss_abgetastet_mib=peak, maxrss_kind_mib=(e or {}).get('maxrss_mib'), bestanden=(e or {}).get('bestanden'), zeiten=(e or {}).get('zeiten_s'))
        print(fall, 'Status', st, '| Wand %.2f s | RSS abgetastet %.1f MiB | Kind ru_maxrss %s MiB' % (wall, peak, (e or {}).get('maxrss_mib')))
        if st != 'OK': ok = False; print('STOPP bei', fall)
    prot['alle_ok'] = ok; json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_BLOCK_BEGRENZT.json'), 'w'), indent=1, default=str); sys.exit(0 if ok else 3)
