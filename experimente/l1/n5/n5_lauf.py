"""Begrenzter M1-Lauf: startet n5.py als Kindprozess unter denselben Grenzen wie der Pruefstand (Zeit 120 s, RSS 400 MiB extern ueberwacht, harte RLIMIT_AS 1024 MiB
im Kind) und dokumentiert die tatsaechlich importierten Abhaengigkeiten mit Pfad und SHA-256. Ueberschreitung -> OFFEN (Abbruch), Absturz/Fehler -> FEHLER, Exit 3."""
import sys, os, json, time, hashlib, subprocess, resource
HERE = os.path.dirname(os.path.abspath(__file__)); L1 = os.path.dirname(HERE); sys.path.insert(0, L1)
import pruefstand as P
GRENZE_S, GRENZE_MIB, HART_MIB = P.GRENZE_S, P.GRENZE_MIB, P.HART_MIB

def sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()
WURZEL = os.path.abspath(os.path.join(L1, '..'))      # /home/claude/kastenmaschine – alles darunter gilt als lokale Abhaengigkeit
def abhaengigkeiten():
    """SAEMTLICHE lokalen Module, die der Import von n5.py tatsaechlich laedt: im Kind aus sys.modules gelesen, gefiltert auf Dateien unter WURZEL."""
    code = ("import sys, os, json; sys.path.insert(0, %r); import n5; print(json.dumps({m: os.path.abspath(getattr(mod, '__file__', '') or '') for m, mod in list(sys.modules.items()) if getattr(mod, '__file__', None) and os.path.abspath(mod.__file__).startswith(%r)}))" % (HERE, WURZEL))
    out = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True, cwd=HERE, check=True); mods = json.loads(out.stdout.strip().splitlines()[-1])
    return {m: dict(pfad=f, relativ=os.path.relpath(f, WURZEL), sha256=sha(f)) for m, f in sorted(mods.items())}

def kind_limits():
    resource.setrlimit(resource.RLIMIT_AS, (HART_MIB << 20, HART_MIB << 20))      # Fehlschlag -> Ausnahme -> Popen scheitert -> FEHLER, kein Test

if __name__ == '__main__':
    deps = abhaengigkeiten(); print('Abhaengigkeiten:'); [print('  %-10s %s  %s' % (m, d['sha256'][:16], d['pfad'])) for m, d in deps.items()]
    ergebnis = os.path.join(HERE, 'ERGEBNIS_N5_M1.json'); os.path.exists(ergebnis) and os.remove(ergebnis)
    t = time.perf_counter(); peak = 0.0; grund = None
    env = dict(os.environ, N5_ERWARTE_RLIMIT_MIB=str(HART_MIB))
    try: p = subprocess.Popen([sys.executable, '-I', os.path.join(HERE, 'n5.py')], cwd=HERE, preexec_fn=kind_limits, env=env)
    except Exception as e:
        print('FEHLER: harte Speichergrenze konnte nicht gesetzt werden (%s) – Test nicht gestartet' % e); json.dump(dict(status='FEHLER', grund=str(e), abhaengigkeiten=deps), open(os.path.join(HERE, 'ERGEBNIS_N5_M1_BEGRENZT.json'), 'w'), indent=1); sys.exit(3)
    while p.poll() is None:
        time.sleep(0.1); r = P.rss(p.pid); peak = max(peak, r)
        if r > GRENZE_MIB: grund = 'RAM %.0f MiB > %.0f' % (r, GRENZE_MIB)
        elif time.perf_counter() - t > GRENZE_S: grund = 'Zeit > %.0f s' % GRENZE_S
        if grund: p.kill(); p.wait(); break
    wall = round(time.perf_counter() - t, 2)
    status = 'OFFEN (Grenze: %s)' % grund if grund else ('OK' if p.returncode == 0 and os.path.exists(ergebnis) else 'FEHLER (Rueckgabe %s)' % p.returncode)
    prot = dict(status=status, wall_s=wall, peak_rss_mib_extern=round(peak, 1), grenzen=dict(zeit_s=GRENZE_S, rss_mib_extern=GRENZE_MIB, rlimit_as_mib_kind=HART_MIB), rueckgabe=p.returncode,
                python=sys.version.split()[0], abhaengigkeiten=deps, n5_lauf_py=dict(pfad=os.path.abspath(__file__), sha256=sha(__file__)),
                m1_ergebnis=(json.load(open(ergebnis)) if os.path.exists(ergebnis) else None))
    prot['rlimit_im_testprozess'] = prot['m1_ergebnis'].get('rlimit_im_testprozess') if prot['m1_ergebnis'] else None
    json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_N5_M1_BEGRENZT.json'), 'w'), indent=1)
    print('Status %s | Wand %.2f s | Spitze RSS %.1f MiB (Grenze %d) | harte Grenze Kind %d MiB | Zeitgrenze %d s' % (status, wall, peak, GRENZE_MIB, HART_MIB, GRENZE_S))
    if status != 'OK': sys.exit(3)
