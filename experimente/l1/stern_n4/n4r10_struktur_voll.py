"""N4r10 VOLLSTAENDIGE STRUKTURZAEHLUNG (GO Christian 2026-10-25 14:36): wie n4r10_struktur.py, aber OHNE 18er-Stopp (MAX_K ueber Umgebung N4R10_MAX_K, hier 100000) – nur fuer die Zaehlung. Keine Tabellen, Masken, Ableitung.
URSPRUNG: N4r10 VORBEREITUNG (GO Christian 2026-10-25 14:28): D6-Grundgeruest (kein R9/R9a/R9b) -> Werte/Aliase vorzeichenrichtig einsetzen, Status je Originalbedingung ->
Min-Fill mit Stopp bei > 18 Variablen (OFFEN mit Stoppstelle) -> Strukturpruefung -> Groessen und Speicherbedarf GERECHNET. Kein Stern-Austausch, keine Tabellen, keine Masken.
Ausgangsstaende nicht vermischen: Grundgeruest allein liess bei N4r10 512 Eingaben offen; 384 stammten vom erweiterten Regelsatz (R9a/R9b/R7)."""
import sys, os, json, time, itertools, resource, hashlib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); L1 = os.path.dirname(HERE); ST = os.path.join(L1, 'stern'); sys.path.insert(0, L1); sys.path.insert(0, ST)
os.environ.setdefault('FALL', 'DU'); os.environ.setdefault('STAND', 'exakt'); os.environ.setdefault('NETZ', 'N3')
import gruppen; from stern import Kaestchen; import pruefstand as P, d6
MAX_K = int(os.environ.get('N4R10_MAX_K', '18')); nm = lambda i: 'v%04d' % i
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def gs(bits): return sys.getsizeof((1 << bits) - 1) if bits > 0 else sys.getsizeof(0)

def umbau(N, wert, find):
    g = N.g
    def res(x):
        if x in (0, 1, -1): return ('c', 0 if x in (0, -1) else 1)
        rt, k = find(abs(x)); s = k ^ (1 if x < 0 else 0)
        return ('c', wert[rt] ^ s) if rt in wert else ('v', rt, s)
    kaest = []; status = collections.Counter(); prot_c = []; widerspr = []
    for i, nd in enumerate(g.nodes):
        if i < 2 or nd[0] == 'input': continue
        op, a, b = nd[0], nd[1], nd[2]; A, B, O = res(a), res(b), res(i)
        if A[0] == 'c' and B[0] == 'c': G = ('c', (A[1] & B[1]) if op == 'and' else (A[1] ^ B[1]))
        elif A[0] == 'c' or B[0] == 'c':
            c, V = (A[1], B) if A[0] == 'c' else (B[1], A); G = (('c', 0) if c == 0 else V) if op == 'and' else (V if c == 0 else ('v', V[1], V[2] ^ 1))
        elif A[1] == B[1]:
            same = (A[2] == B[2]); G = (A if same else ('c', 0)) if op == 'and' else (('c', 0) if same else ('c', 1))
        else: G = ('g',)
        if G[0] == 'c':
            if O[0] == 'c':
                if O[1] == G[1]: status['b_erfuellt'] += 1
                else: widerspr.append(dict(gatter=i))
            else: status['c_neu'] += 1; prot_c.append(dict(gatter=i, art='wert', variable=nm(O[1]), wert=G[1] ^ O[2])); kaest.append(Kaestchen('rest_wert#%d' % i, (nm(O[1]),), {(G[1] ^ O[2],)}))
        elif G[0] == 'v':
            if O[0] == 'c': status['c_neu'] += 1; prot_c.append(dict(gatter=i, art='wert', variable=nm(G[1]), wert=O[1] ^ G[2])); kaest.append(Kaestchen('rest_wert#%d' % i, (nm(G[1]),), {(O[1] ^ G[2],)}))
            elif O[1] == G[1]:
                if O[2] == G[2]: status['b_erfuellt'] += 1
                else: widerspr.append(dict(gatter=i, grund='x = NICHT x'))
            else:
                neg = O[2] ^ G[2]; vs = tuple(sorted((nm(O[1]), nm(G[1])))); status['c_neu'] += 1; prot_c.append(dict(gatter=i, art='gleich', variable=nm(O[1]), gleich=nm(G[1]), negiert=neg)); kaest.append(Kaestchen('rest_gleich#%d' % i, vs, {(x, x ^ neg) for x in (0, 1)}))
        else:
            lits = [A, B] + ([O] if O[0] == 'v' else []); roots = sorted({nm(l[1]) for l in lits}); rows = set()
            for bel in itertools.product((0, 1), repeat=len(roots)):
                dd = dict(zip(roots, bel)); val = lambda L: dd[nm(L[1])] ^ L[2]; out = (val(A) & val(B)) if op == 'and' else (val(A) ^ val(B)); oval = val(O) if O[0] == 'v' else O[1]
                if out == oval: rows.add(bel)
            status['a_kaestchen_%d' % len(roots)] += 1; kaest.append(Kaestchen('%s#%d' % (op, i), tuple(roots), rows))
    ziel_ok = 0
    for zk, val in N.ziel.items():
        R = res(zk)
        if R[0] == 'c' and R[1] == val: ziel_ok += 1
        else: widerspr.append(dict(ziel=zk, grund='Zielbit nicht fest/falsch'))
    gatter = sum(1 for i, nd in enumerate(g.nodes) if i >= 2 and nd[0] != 'input'); a_sum = sum(v for k, v in status.items() if k.startswith('a_'))
    return kaest, dict(originalgatter=gatter, a_erhalten=a_sum, a_je_breite={k: v for k, v in status.items() if k.startswith('a_')}, b_erfuellt=status['b_erfuellt'], c_neu=status['c_neu'], summe=a_sum + status['b_erfuellt'] + status['c_neu'],
                       zielbits=len(N.ziel), d_zielbits_fest=ziel_ok, widersprueche=widerspr, restbedingungen=len(prot_c), kaestchen_gesamt=len(kaest), protokoll_c=prot_c,
                       E2=(a_sum + status['b_erfuellt'] + status['c_neu'] == gatter and ziel_ok == len(N.ziel) and not widerspr))

def min_fill_mit_stopp(kaestchen, maxk):
    nachbarn = {}
    for k in kaestchen:
        for v in k.vars: nachbarn.setdefault(v, set()).update(w for w in k.vars if w != v)
    rest = set(nachbarn); ordnung = []; buckets = {}; schritt = 0; groesste = 0
    while rest:
        def fill(v):
            Nn = [w for w in nachbarn[v] if w in rest]; return sum(1 for a, b in itertools.combinations(Nn, 2) if b not in nachbarn[a])
        v = min(rest, key=lambda v: (fill(v), len([w for w in nachbarn[v] if w in rest]), v)); Nn = sorted(w for w in nachbarn[v] if w in rest); schritt += 1; groesste = max(groesste, len(Nn) + 1)
        if len(Nn) + 1 > maxk: return dict(passt=False, schritt=schritt, variable=v, gruppe=[v] + Nn, gruppen_vars=len(Nn) + 1, bisher_groesste=max((len(b) + 1 for b in buckets.values()), default=0), eliminiert=len(ordnung), rest=len(rest)), ordnung, buckets
        for a, b in itertools.combinations(Nn, 2): nachbarn[a].add(b); nachbarn[b].add(a)
        ordnung.append(v); buckets[v] = Nn; rest.remove(v)
    return dict(passt=True, schritt=schritt, groesste_gruppe=groesste), ordnung, buckets

if __name__ == '__main__':
    t0 = time.perf_counter(); N = P._n4r(10, True); g = N.g
    d = d6.D6_R567bCM(); r = d.laufen(N); t_abl = time.perf_counter() - t0; z = d._zustand; wert = dict(z['wert']); find = z['find']
    frei_offen = [nm(f) for f in N.frei if find(f)[0] not in wert]; frei_alias = {nm(f): [nm(find(f)[0]), find(f)[1]] for f in N.frei if find(f)[0] != f}
    t1 = time.perf_counter(); kaest, gl = umbau(N, wert, find); t2 = time.perf_counter()
    offen = sorted({v for k in kaest for v in k.vars}); befund, ordnung, buckets = min_fill_mit_stopp(kaest, MAX_K); t3 = time.perf_counter(); struktur = None; groessen = None; speicher = None
    if befund['passt']:
        gr, kanten, ordnung2, b2 = gruppen.baue(kaest); assert ordnung2 == ordnung
        try: gruppen.strukturpruefung(gr, kanten, kaest); struktur = dict(bestanden=True)
        except gruppen.Strukturfehler as f: struktur = dict(bestanden=False, fehler=str(f))
        sizes = [len(x.vars) for x in gr]; ss = [len(S) for a, b, S in kanten]; byn = {x.name: x for x in gr}
        struktur.update(gruppen=len(gr), kanten=len(kanten), wurzeln=sum(1 for x in gr if x.eltern is None), groesste_gruppe=max(sizes), histogramm_k=dict(sorted(collections.Counter(sizes).items())), histogramm_s=dict(sorted(collections.Counter(ss).items())),
                        groesste_kanten=sorted(((len(S), len(byn[a].vars), len(byn[b].vars), a, b) for a, b, S in kanten), reverse=True)[:8], gruppen_ohne_kaestchen=sum(1 for x in gr if not x.kaestchen))
        # Speicherbedarf GERECHNET (Objektbytes dieses Pythons), nichts aufgebaut
        speicher = dict(einheit='gerechnet aus der Struktur (sys.getsizeof-Formel), nichts aufgebaut – Schaetzung',
                        tabellen_bits=sum(2 ** k for k in sizes), tabellen_objektbytes=sum(gs(2 ** k) for k in sizes), groesste_tabelle_bits=2 ** max(sizes), groesste_tabelle_objektbytes=gs(2 ** max(sizes)),
                        nachrichten_anzahl=2 * len(kanten), nachrichten_bits=sum(2 * 2 ** s for s in ss), nachrichten_objektbytes_mit_huelle=sum(2 * (gs(2 ** s) + sys.getsizeof((0,)) + sys.getsizeof(frozenset({(0,)}))) for s in ss),
                        masken_schlank_anzahl=sum(2 * k for k in sizes), masken_schlank_bits=sum(2 * k * 2 ** k for k in sizes), masken_schlank_objektbytes=sum(2 * k * gs(2 ** k) + 2 * sys.getsizeof([0] * k) for k in sizes),
                        masken_bisher_bits=sum((2 ** len(S)) * (2 ** len(byn[a].vars) + 2 ** len(byn[b].vars)) for a, b, S in kanten),
                        zwischenobjekt_je_aufruf_gerechnet=2 * gs(2 ** max(sizes)) + gs(2 ** max(ss)), arbeitsstrukturen_hinweis='bei N4r09 (492 Gruppen) 578 KB gemessen; hier proportional zur Gruppenzahl geschaetzt', arbeitsstrukturen_schaetzung=int(578272 * len(gr) / 492),
                        austausch_aufwand_summe_2s_mal_s_minus_1=sum(2 ** s * max(s - 1, 0) for s in ss), vergleich_n4r09=dict(summe_2s_mal_s_minus_1=None))
        try:
            A = json.load(open(os.path.join(HERE, 'UEBERGABE_V0.json'))); ss9 = [len(S) for a, b, S in A['kanten']]; speicher['vergleich_n4r09'] = dict(summe_2s_mal_s_minus_1=sum(2 ** s * max(s - 1, 0) for s in ss9), gruppen=len(A['gruppen']), austausch_s_gemessen=62.2)
        except Exception: pass
    erg = dict(netz=N.name, knoten=len(g.nodes), frei=len(N.frei), zielbits=len(N.ziel), d6=dict(darstellung='D6+R1b+R8c+R8m (Grundgeruest, kein R9/R9a/R9b)', status=z['status'], wert=len(wert), alias=sum(1 for v in range(2, len(g.nodes)) if find(v)[0] != v), zeit_s=round(t_abl, 3),
               hinweis_ausgangsstand='Grundgeruest allein: 512 zugelassene Eingaben (frueherer Bericht); 384 stammten vom erweiterten Regelsatz – hier NICHT verwendet'),
               freie_eingaenge=dict(offen=frei_offen, offen_anzahl=len(frei_offen), aliasiert=frei_alias, fest={nm(f): wert[find(f)[0]] ^ find(f)[1] for f in N.frei if find(f)[0] in wert}),
               gleichwertigkeit={k: v for k, v in gl.items() if k != 'protokoll_c'}, restbedingungen=gl['protokoll_c'], offene_variablen=len(offen), kaestchen=len(kaest),
               min_fill=befund, ordnung_anfang=ordnung[:30], struktur=struktur, speicher_gerechnet=speicher, nicht_aufgenommen=dict(lin_gl=len(z['lin_gl']), xor_gl=len(z['xor_gl'])),
               zeiten_s=dict(ableitung_d6=round(t_abl, 3), umbau=round(t2 - t1, 3), min_fill=round(t3 - t2, 3), gesamt=round(time.perf_counter() - t0, 3)), maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), rlimit_as=resource.getrlimit(resource.RLIMIT_AS), python=sys.version.split()[0],
               status=('OK' if befund['passt'] and struktur and struktur['bestanden'] and gl['E2'] else ('OFFEN (Gruppe > %d bei Schritt %d, Variable %s)' % (MAX_K, befund['schritt'], befund['variable']) if not befund['passt'] else 'FEHLER')),
               abhaengigkeiten={m: dict(pfad=sys.modules[m].__file__, sha256=sha(sys.modules[m].__file__)) for m in ('pruefstand', 'd6', 'gatter', 'e1_bit', 'gruppen', 'stern') if m in sys.modules})
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_N4R10_STRUKTUR_VOLL.json'), 'w'), indent=1, default=str)
    print('N4r10 | D6 %s %.2fs wert %d alias %d | Gleichwertigkeit a/b/c %d/%d/%d von %d, Ziele %d/%d, Widerspr %d -> E2 %s | offen %d Var, %d Kaestchen | Min-Fill %s | Struktur %s | Status %s' % (
        z['status'], t_abl, len(wert), erg['d6']['alias'], gl['a_erhalten'], gl['b_erfuellt'], gl['c_neu'], gl['originalgatter'], gl['d_zielbits_fest'], gl['zielbits'], len(gl['widersprueche']), gl['E2'], len(offen), len(kaest), befund, (struktur or {}).get('bestanden'), erg['status']))
    if speicher: print('Groessen:', {k: struktur[k] for k in ('gruppen', 'kanten', 'groesste_gruppe', 'histogramm_k', 'histogramm_s')}); print('Speicher gerechnet:', {k: v for k, v in speicher.items() if 'bits' in k or 'bytes' in k or 'aufwand' in k or k == 'vergleich_n4r09'})
    sys.exit(0 if erg['status'] == 'OK' else (2 if erg['status'].startswith('OFFEN') else 3))
