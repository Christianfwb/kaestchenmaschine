"""STRUKTURPRUEFUNG N4r09 (GO 2026-10-24 21:15): nur Variablen und Verbindungen. Keine Loesungstabellen, keine Rueckwaertsableitung, keine Kontrollbelegung.
Kaestchen = jedes Gatter des bestehenden Netzes (Variablen: Ausgang + 1..2 Eingaenge, Vorzeichen ignoriert, Konstanten 0/1 ausgelassen). Zielbits sind einstellige
Kaestchen (eine Variable) und erzeugen keine Kanten. Min-Fill wie gruppen.min_fill (Gleichstand: Grad, dann Name), aber mit SOFORTSTOPP, sobald eine Gruppe
(eliminierte Variable + Bucket) mehr als MAX_VARS Variablen haette. Passt alles: baue + strukturpruefung aus gruppen.py (Baum/Wald, Abdeckung, Running Intersection)."""
import sys, os, json, time, itertools, resource, hashlib
HERE = os.path.dirname(os.path.abspath(__file__)); L1 = os.path.dirname(HERE)
sys.path.insert(0, L1); sys.path.insert(0, os.path.join(L1, 'stern'))
MAX_VARS = int(os.environ.get('STRUKT_MAX_VARS', '8')); AUSGABE = 'ERGEBNIS_STRUKTUR_N4R09%s.json' % ('' if MAX_VARS == 8 else '_MAX%d' % MAX_VARS)
import pruefstand as P                      # nur fuer die Netzdefinition _n4r(9, True); nichts wird abgeleitet
import gruppen; from stern import Kaestchen

def netz_struktur():
    N = P._n4r(9, True); g = N.g; kaest = []; name = lambda i: 'v%04d' % i
    for i, nd in enumerate(g.nodes):
        if i < 2 or nd[0] == 'input': continue
        vs = {name(i)} | {name(abs(a)) for a in nd[1:3] if abs(a) >= 2}
        kaest.append(Kaestchen('%s#%d' % (nd[0], i), tuple(sorted(vs)), set()))        # Tabelle leer: nur Struktur
    for z in N.ziel: kaest.append(Kaestchen('ziel#%d' % abs(z), (name(abs(z)),), set()))
    return N.name, len(g.nodes), kaest

def min_fill_mit_stopp(kaestchen):
    nachbarn = {}
    for k in kaestchen:
        for v in k.vars: nachbarn.setdefault(v, set()).update(w for w in k.vars if w != v)
    rest = set(nachbarn); ordnung = []; buckets = {}; schritt = 0; groesste = 0
    while rest:
        def fill(v):
            Nn = [w for w in nachbarn[v] if w in rest]; return sum(1 for a, b in itertools.combinations(Nn, 2) if b not in nachbarn[a])
        v = min(rest, key=lambda v: (fill(v), len([w for w in nachbarn[v] if w in rest]), v))
        Nn = sorted(w for w in nachbarn[v] if w in rest); schritt += 1; groesste = max(groesste, len(Nn) + 1)
        if len(Nn) + 1 > MAX_VARS:
            return dict(passt=False, schritt=schritt, variable=v, gruppe=[v] + Nn, gruppen_vars=len(Nn) + 1, bisher_groesste=max(len(b) + 1 for b in buckets.values()) if buckets else 0,
                        eliminiert_bisher=len(ordnung), rest=len(rest)), ordnung, buckets
        for a, b in itertools.combinations(Nn, 2): nachbarn[a].add(b); nachbarn[b].add(a)
        ordnung.append(v); buckets[v] = Nn; rest.remove(v)
    return dict(passt=True, schritt=schritt, groesste_gruppe=groesste), ordnung, buckets

if __name__ == '__main__':
    t0 = time.perf_counter(); name, n_knoten, kaest = netz_struktur()
    vars_ = sorted({v for k in kaest for v in k.vars})
    info = dict(netz=name, knoten_im_graph=n_knoten, variablen=len(vars_), kaestchen=len(kaest), gatter=sum(1 for k in kaest if not k.name.startswith('ziel')), zielbits=sum(1 for k in kaest if k.name.startswith('ziel')), max_vars=MAX_VARS)
    befund, ordnung, buckets = min_fill_mit_stopp(kaest); t_mf = time.perf_counter() - t0; struktur = None
    if befund['passt']:
        gr, kanten, ordnung2, buckets2 = gruppen.baue(kaest)           # dieselbe Regel ohne Stopp; Gleichheit der Ordnung wird geprueft
        assert ordnung2 == ordnung, 'Ordnung weicht ab'
        try: gruppen.strukturpruefung(gr, kanten, kaest); struktur = dict(bestanden=True, gruppen=len(gr), kanten=len(kanten), wurzeln=sum(1 for g in gr if g.eltern is None), groesste_gruppe=max(len(g.vars) for g in gr))
        except gruppen.Strukturfehler as f: struktur = dict(bestanden=False, fehler=str(f))
    deps = {m: dict(pfad=sys.modules[m].__file__, sha256=hashlib.sha256(open(sys.modules[m].__file__, 'rb').read()).hexdigest()) for m in ('pruefstand', 'gatter', 'gruppen', 'stern', 'e1_bit', 'd6') if m in sys.modules}
    erg = dict(info=info, befund=befund, struktur=struktur, zeit_min_fill_s=round(t_mf, 3), zeit_gesamt_s=round(time.perf_counter() - t0, 3), maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1),
               rlimit_as=resource.getrlimit(resource.RLIMIT_AS), python=sys.version.split()[0], abhaengigkeiten=deps, ordnung_anfang=ordnung[:40], eliminiert=len(ordnung))
    json.dump(erg, open(os.path.join(HERE, AUSGABE), 'w'), indent=1, default=str)
    print(json.dumps(dict(info=info, befund=befund, struktur=struktur, zeit_s=erg['zeit_gesamt_s'], maxrss_mib=erg['maxrss_mib']), indent=1, default=str))
