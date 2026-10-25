"""Waechter: fuenf Kinder (DU exakt, DU i3 Vorprobe, DU i2, DL exakt, DL i2), je 120 s / 400 MiB. Danach E1: Pruefsumme i3 == exakt (DU). Keine Labor-Importe."""
import sys, os, json, time, subprocess, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); GRENZE_S, GRENZE_MIB = 120.0, 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024.0
    except Exception: pass
    return 0.0
if __name__ == '__main__':
    prot = dict(grenzen=dict(zeit_s=GRENZE_S, rss_mib=GRENZE_MIB), python=sys.version.split()[0], laeufe={}, dateien={f: hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest() for f in ('begrenzt.py', 'begrenzt_lauf.py')}); E = {}; ok = True
    for fall, stand in (('DU', 'exakt'), ('DU', 'i3'), ('DU', 'i2'), ('DL', 'exakt'), ('DL', 'i2')):
        erg = os.path.join(HERE, 'ERGEBNIS_BEGRENZT_%s_%s.json' % (fall, stand)); os.path.exists(erg) and os.remove(erg)
        t = time.perf_counter(); peak = 0.0; grund = None; p = subprocess.Popen([sys.executable, '-I', os.path.join(HERE, 'begrenzt.py')], cwd=HERE, env=dict(os.environ, FALL=fall, STAND=stand))
        while p.poll() is None:
            time.sleep(0.1); r = rss(p.pid); peak = max(peak, r)
            if r > GRENZE_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, GRENZE_MIB)
            elif time.perf_counter() - t > GRENZE_S: grund = 'Zeit > %.0f s' % GRENZE_S
            if grund: p.kill(); p.wait(); break
        e = json.load(open(erg)) if os.path.exists(erg) else None; E[(fall, stand)] = e
        status = 'OFFEN (Grenze: %s)' % grund if grund else ('OK' if p.returncode == 0 and e else 'FEHLER (Rueckgabe %s)' % p.returncode)
        prot['laeufe']['%s_%s' % (fall, stand)] = dict(status=status, wall_s=round(time.perf_counter() - t, 2), peak_rss_abgetastet_mib=round(peak, 1), maxrss_kind_mib=(e or {}).get('maxrss_mib'))
        if status != 'OK': ok = False; print('STOPP bei', fall, stand, status); break
    if ok:
        prot['E1_i3_gleich_exakt_DU'] = (E[('DU', 'i3')]['pruefsumme_struktur'] == E[('DU', 'exakt')]['pruefsumme_struktur']); ok = prot['E1_i3_gleich_exakt_DU']
    prot['alle_ok'] = ok; json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_BEGRENZT_BEGRENZT.json'), 'w'), indent=1)
    print('E1 i3==exakt:', prot.get('E1_i3_gleich_exakt_DU'), '| Laeufe:', {k: (d['status'], d['maxrss_kind_mib']) for k, d in prot['laeufe'].items()}, '| alle_ok', ok); sys.exit(0 if ok else 3)
