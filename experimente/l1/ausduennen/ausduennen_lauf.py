"""Waechter: 48 Kinder (Koepfe 1..8 x k 2,3,4 x Runden 6,9), je 120 s / 400 MiB; Grenze -> OFFEN, Fehler -> FEHLER + Stopp. Danach Zusammenfassung ueber alle Faelle. Keine Labor-Importe."""
import sys, os, json, time, subprocess, hashlib, statistics
HERE = os.path.dirname(os.path.abspath(__file__)); GRENZE_S, GRENZE_MIB = 120.0, 400.0
def rss(pid):
    try:
        for z in open('/proc/%d/status' % pid):
            if z.startswith('VmRSS:'): return int(z.split()[1]) / 1024.0
    except Exception: pass
    return 0.0
if __name__ == '__main__':
    prot = dict(grenzen=dict(zeit_s=GRENZE_S, rss_mib=GRENZE_MIB), python=sys.version.split()[0], laeufe=[], dateien={f: hashlib.sha256(open(os.path.join(HERE, f), 'rb').read()).hexdigest() for f in ('ausduennen.py', 'ausduennen_lauf.py')}); ok = True; E = []
    t0 = time.perf_counter()
    for R in (6, 9):
        for K in (2, 3, 4):
            for F in range(1, 9):
                erg = os.path.join(HERE, 'ERGEBNIS_AUSD2_r%d_k%d_F%d.json' % (R, K, F)); os.path.exists(erg) and os.remove(erg)
                t = time.perf_counter(); peak = 0.0; grund = None; p = subprocess.Popen([sys.executable, '-I', os.path.join(HERE, 'ausduennen.py')], cwd=HERE, env=dict(os.environ, KOPF=str(F), K=str(K), RUNDEN=str(R)), stdout=subprocess.PIPE, text=True)
                while p.poll() is None:
                    time.sleep(0.05); r = rss(p.pid); peak = max(peak, r)
                    if r > GRENZE_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, GRENZE_MIB)
                    elif time.perf_counter() - t > GRENZE_S: grund = 'Zeit > %.0f s' % GRENZE_S
                    if grund: p.kill(); p.wait(); break
                out = p.stdout.read().strip().splitlines(); e = json.load(open(erg)) if os.path.exists(erg) else None
                status = 'OFFEN (Grenze: %s)' % grund if grund else ('OK' if p.returncode == 0 and e else 'FEHLER (Rueckgabe %s)' % p.returncode)
                prot['laeufe'].append(dict(r=R, k=K, F=F, status=status, wall_s=round(time.perf_counter() - t, 2), peak_rss_mib=round(peak, 1), zeile=(out[-1] if out else None))); E.append(e)
                print(out[-1] if out else '', '|', status)
                if status != 'OK': ok = False; print('STOPP'); break
            if not ok: break
        if not ok: break
    if ok:
        Z = {}
        for e in E:
            key = 'r%d_k%d' % (e['fall']['runden'], e['fall']['k']); Z.setdefault(key, dict(faelle=0, widerspruch=0, loesungen=[], rang=[], kandidaten=[], beste_ersparnis_mit=[], beste_ersparnis_ohne=[], sicher=True, nulloesung_ohne_widerspruch=0))
            z = Z[key]; z['faelle'] += 1; z['loesungen'].append(e['kontrolle']['loesungen']); z['rang'].append(e['form1']['rang']); z['kandidaten'].append(e['form2']['kandidaten']); z['sicher'] &= e['pruefung']['E1_sicher']
            if e['ableitung']['status'] == 'WIDERSPRUCH': z['widerspruch'] += 1
            elif e['kontrolle']['loesungen'] == 0: z['nulloesung_ohne_widerspruch'] += 1
            w = e['bilanz']['wege']
            if w and e['ableitung']['status'] != 'WIDERSPRUCH': z['beste_ersparnis_mit'].append(max(v['ersparnis_mit_Cpre'] for v in w.values())); z['beste_ersparnis_ohne'].append(max(v['ersparnis_ohne_Cpre'] for v in w.values()))
        for z in Z.values():
            for kk in ('loesungen', 'rang', 'kandidaten', 'beste_ersparnis_mit', 'beste_ersparnis_ohne'): z[kk] = dict(min=min(z[kk]), max=max(z[kk]), mittel=round(statistics.mean(z[kk]), 2)) if z[kk] else None
        prot['zusammenfassung'] = Z
    prot['alle_ok'] = ok; prot['wall_gesamt_s'] = round(time.perf_counter() - t0, 1); json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_AUSD2_BEGRENZT.json'), 'w'), indent=1, default=str)
    print(json.dumps(prot.get('zusammenfassung'), indent=0)[:3000]); sys.exit(0 if ok else 3)
