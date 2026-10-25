"""Waechter: Selbsttest, dann vier Kinder (N3/N3u x TUPEL/BIT), je 120 s / 400 MiB. Danach: E1 Struktur gleich (Pruefsumme TUPEL == BIT == B2 exakt), E2 Endrelationen je Gruppe gleich, E3 Zaehler (Abweichung = UNTERSUCHUNGSFALL, kein FEHLER). Keine Labor-Importe."""
import sys, os, json, time, subprocess, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); GRENZE_S, GRENZE_MIB = 120.0, 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024.0
    except Exception: pass
    return 0.0
def kind(args, env, erg):
    os.path.exists(erg) and os.remove(erg); t = time.perf_counter(); peak = 0.0; grund = None; p = subprocess.Popen([sys.executable, '-I'] + args, cwd=HERE, env=env)
    while p.poll() is None:
        time.sleep(0.1); r = rss(p.pid); peak = max(peak, r)
        if r > GRENZE_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, GRENZE_MIB)
        elif time.perf_counter() - t > GRENZE_S: grund = 'Zeit > %.0f s' % GRENZE_S
        if grund: p.kill(); p.wait(); break
    e = json.load(open(erg)) if os.path.exists(erg) else None
    return ('OFFEN (Grenze: %s)' % grund if grund else ('OK' if p.returncode == 0 and e else 'FEHLER (Rueckgabe %s)' % p.returncode)), round(time.perf_counter() - t, 2), round(peak, 1), e
if __name__ == '__main__':
    prot = dict(grenzen=dict(zeit_s=GRENZE_S, rss_mib=GRENZE_MIB), python=sys.version.split()[0], laeufe={}, dateien={f: hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest() for f in ('bitmenge_schlank.py', 'bitmenge_schlank_mess.py', 'bitmenge_schlank_lauf.py')}); ok = True; E = {}
    st, wall, peak, e = kind([os.path.join(HERE, 'bitmenge_schlank.py')], dict(os.environ), os.path.join(HERE, 'ERGEBNIS_SCHLANK_SELBSTTEST.json')); prot['selbsttest'] = dict(status=st, wall_s=wall, faelle=(e or {}).get('faelle'), fehler=(e or {}).get('fehler_gesamt')); print('Selbsttest', st, (e or {}).get('faelle'), 'Faelle')
    if st != 'OK': ok = False
    for netz in (('N3', 'N3u') if ok else ()):
        for form in ('BIT', 'SCHLANK'):
            st, wall, peak, e = kind([os.path.join(HERE, 'bitmenge_schlank_mess.py')], dict(os.environ, NETZ=netz, FORM=form), os.path.join(HERE, 'ERGEBNIS_SCHLANK_%s_%s.json' % (netz, form))); E[(netz, form)] = e
            prot['laeufe']['%s_%s' % (netz, form)] = dict(status=st, wall_s=wall, peak_rss_abgetastet_mib=peak, maxrss_kind_mib=(e or {}).get('maxrss_mib'))
            if st != 'OK': ok = False; print('STOPP bei', netz, form, st); break
        if not ok: break
    if ok:
        v = {}
        for netz in ('N3', 'N3u'):
            T, B = E[(netz, 'BIT')], E[(netz, 'SCHLANK')]; b2 = os.path.join(HERE, 'ERGEBNIS_B2_%s_exakt.json' % netz); b2ps = json.load(open(b2))['pruefsumme_struktur'] if os.path.exists(b2) else None
            zt = {k: T['zaehler'][k] for k in ('entnahmen', 'semijoin_aufrufe_direkt', 'projektionen', 'nachrichten_gesendet', 'gestrichen')}; zb = {k: B['zaehler'][k] for k in zt}
            v[netz] = dict(E1_struktur_gleich=(T['pruefsumme_struktur'] == B['pruefsumme_struktur']), E1_gleich_B2_exakt=(b2ps == T['pruefsumme_struktur']), E2_status_gleich=(T['status'] == B['status']),
                           E2_endrelationen_gleich=(T['endrelationen'] == B['endrelationen']), E2_fest_gleich=(T['fest'] == B['fest']), E3_zaehler_gleich=(zt == zb), zaehler_bisher=zt, zaehler_schlank=zb,
                           untersuchungsfall=(zt != zb), hoechststand_bisher=T['hoechststand_beobachtet']['summe'], hoechststand_schlank=B['hoechststand_beobachtet']['summe'], E0_bisher=T['pruefung']['E0_instrumentierte_kopie_gleich_original'], E0_schlank=B['pruefung']['E0_instrumentierte_kopie_gleich_original'])
        prot['vergleich'] = v; ok = all(d[k] for d in v.values() for k in ('E1_struktur_gleich', 'E2_status_gleich', 'E2_endrelationen_gleich', 'E2_fest_gleich', 'E0_bisher', 'E0_schlank'))
        prot['untersuchungsfaelle'] = [n for n, d in v.items() if d['untersuchungsfall']]
    prot['alle_ok'] = ok; json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_SCHLANK_BEGRENZT.json'), 'w'), indent=1)
    print('Vergleich:', json.dumps(prot.get('vergleich'), indent=0)[:1500], '| alle_ok', ok); sys.exit(0 if ok else 3)
