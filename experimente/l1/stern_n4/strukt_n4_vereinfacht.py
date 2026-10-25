"""VEREINFACHEN, DANN GRUPPIEREN (GO 2026-10-24 22:00, Entwurf V2 + Ergaenzung): N4r09, Stufen 0 / A / B / C1 / C2.
Gemessen wird die STRUKTUR DER VERBLEIBENDEN GATTER nach Einsetzen von Werten und Aliasen. Nicht aufgenommene D6-Beziehungen (lin_gl/xor_gl) sind
NICHT im Gruppenbaum; sie werden nur gezaehlt. Keine Loesungstabellen, kein Austausch, kein Orakel, keine Kontrollbelegung.
Variablen sind die Knoten fuer Min-Fill; Kaestchen mit gleicher Variablenmenge erzeugen dieselben Verbindungen (werden einzeln mit Herkunft erhalten).
Neue Folgerungen beim Umbau werden NICHT eingesetzt: sie bleiben als Restbedingung (Kaestchen mit 1 bzw. 2 Variablen) im Restnetz und werden gesondert protokolliert.
Aufruf: STUFE=0|A|B|C1|C2 python3 -I strukt_n4_vereinfacht.py"""
import sys, os, json, time, resource, hashlib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); L1 = os.path.dirname(HERE)
sys.path.insert(0, L1); sys.path.insert(0, os.path.join(L1, 'stern'))
import pruefstand as P, d6, gruppen; from stern import Kaestchen
STUFE = os.environ.get('STUFE', '0'); AUSGABE = os.path.join(HERE, 'ERGEBNIS_VEREINFACHT_%s.json' % STUFE)
nm = lambda i: 'v%04d' % i

def zustand(N):
    """Werte/Aliase je Stufe. Liefert wert{knoten:0/1}, find(v)->(wurzel,k), zeit_ableitung, zusatz."""
    if STUFE == '0': return {}, (lambda v: (v, 0)), 0.0, dict(quelle='keine')
    if STUFE == 'A':
        wert = {}
        for node, val in N.ziel.items(): wert[abs(node)] = val ^ (1 if node < 0 else 0)
        return wert, (lambda v: (v, 0)), 0.0, dict(quelle='nur Zielwerte (32), keine Weitergabe', zielbits=len(wert))
    t = time.perf_counter(); d = (d6.D6_R567bCM() if STUFE == 'B' else d6.D6_R9()); r = d.laufen(N); t_abl = time.perf_counter() - t
    z = d._zustand; wert = dict(z['wert']); find = z['find']
    lin = z['lin_gl']; xg = z['xor_gl']
    zusatz = dict(quelle=('D6+R1b+R8c+R8m (Grundgeruest)' if STUFE == 'B' else 'Grundgeruest + R9 (D6_R9)'), d6_status=z['status'], d6_ergebnis=str(r[0]) if isinstance(r, tuple) else str(r),
                  d6_wert=len(wert), d6_alias=len(z['alias']), nicht_aufgenommen=dict(lin_gl=len(lin), xor_gl=len(xg),
                  xor_gl_variablen_verteilung=dict(collections.Counter(len(e[0]) if isinstance(e, (tuple, list)) and e else 0 for e in xg)),
                  lin_gl_variablen_verteilung=dict(collections.Counter(len(e[0]) if isinstance(e, (tuple, list)) and e else 0 for e in lin))))
    return wert, find, t_abl, zusatz

def vorwaerts(N, wert, find):
    """C2: Vorwaertsvereinfachung – Gatter mit zwei festen Eingaengen legen den Ausgang fest; bis Stillstand. Eigenes dict (nicht D6)."""
    g = N.g; neu = {}; runden = 0
    def val(x):
        if x in (0, 1, -1): return 0 if x in (0, -1) else 1
        r, k = find(abs(x)); s = 1 if x < 0 else 0
        if r in wert: return wert[r] ^ k ^ s
        if r in neu: return neu[r] ^ k ^ s
        return None
    while True:
        runden += 1; ch = 0
        for i, nd in enumerate(g.nodes):
            if i < 2 or nd[0] == 'input': continue
            r, k = find(i)
            if r in wert or r in neu: continue
            a, b = val(nd[1]), val(nd[2])
            if a is None or b is None: continue
            o = (a & b) if nd[0] == 'and' else (a ^ b); neu[r] = o ^ k; ch += 1
        if ch == 0: break
    return neu, runden

def umbau(N, wert, find):
    g = g_ = N.g; kaest = []; prot = dict(enthalten=0, neu_wert=[], neu_alias=[], widerspruch=None); rest_neu = 0
    def res(x):                              # Literal -> ('c', wert) oder ('v', wurzel, vorzeichen)
        if x in (0, 1, -1): return ('c', 0 if x in (0, -1) else 1)
        r, k = find(abs(x)); s = k ^ (1 if x < 0 else 0)
        return ('c', wert[r] ^ s) if r in wert else ('v', r, s)
    for i, nd in enumerate(g.nodes):
        if i < 2 or nd[0] == 'input': continue
        op = nd[0]; A, B, O = res(nd[1]), res(nd[2]), res(i)
        # Gatter ueber aufgeloesten Eingaengen falten
        if A[0] == 'c' and B[0] == 'c': G = ('c', (A[1] & B[1]) if op == 'and' else (A[1] ^ B[1]))
        elif A[0] == 'c' or B[0] == 'c':
            c, V = (A[1], B) if A[0] == 'c' else (B[1], A)
            G = (('c', 0) if c == 0 else V) if op == 'and' else (V if c == 0 else ('v', V[1], V[2] ^ 1))
        elif A[1] == B[1]:
            same = (A[2] == B[2])
            G = (A if same else ('c', 0)) if op == 'and' else (('c', 0) if same else ('c', 1))
        else: G = ('g',)                     # echtes Gatter ueber zwei verschiedenen offenen Variablen
        herk = dict(gatter=i, op=op, eingaenge=[nd[1], nd[2]])
        if G[0] == 'c':
            if O[0] == 'c':
                if O[1] == G[1]: prot['enthalten'] += 1
                else: prot['widerspruch'] = dict(herk, ausgang_zustand=O[1], gefaltet=G[1]); return kaest, prot
            else:                            # neue Folgerung: Ausgang = Konstante -> Restbedingung (1 Variable), NICHT eingesetzt
                prot['neu_wert'].append(dict(herk, variable=O[1], wert=G[1] ^ O[2])); kaest.append(Kaestchen('rest_wert#%d' % i, (nm(O[1]),), set(), ))
        elif G[0] == 'v':
            if O[0] == 'c':                  # neue Folgerung: Eingangsvariable = Konstante -> Restbedingung (1 Variable)
                prot['neu_wert'].append(dict(herk, variable=G[1], wert=O[1] ^ G[2])); kaest.append(Kaestchen('rest_wert#%d' % i, (nm(G[1]),), set()))
            elif O[1] == G[1]:
                if O[2] == G[2]: prot['enthalten'] += 1
                else: prot['widerspruch'] = dict(herk, grund='Ausgang = NICHT Ausgang'); return kaest, prot
            else:                            # neue Folgerung: Ausgang = +/- Eingang -> Restbedingung (2 Variablen, Gleichheit)
                prot['neu_alias'].append(dict(herk, variable=O[1], gleich=G[1], negiert=O[2] ^ G[2])); kaest.append(Kaestchen('rest_gleich#%d' % i, tuple(sorted({nm(O[1]), nm(G[1])})), set()))
        else:
            vs = {nm(A[1]), nm(B[1])} | ({nm(O[1])} if O[0] == 'v' else set())
            kaest.append(Kaestchen('%s#%d%s' % (op, i, '' if O[0] == 'v' else '=%d' % O[1]), tuple(sorted(vs)), set()))
    if STUFE == '0':
        for z in N.ziel: kaest.append(Kaestchen('ziel#%d' % abs(z), (nm(abs(z)),), set()))
    return kaest, prot

if __name__ == '__main__':
    t0 = time.perf_counter(); N = P._n4r(9, True); n_knoten = len(N.g.nodes); alle_vars = [i for i, nd in enumerate(N.g.nodes) if i >= 2]
    wert, find, t_abl, zusatz = zustand(N); vorw = None
    if STUFE == 'C2':
        t = time.perf_counter(); neu, runden = vorwaerts(N, wert, find); vorw = dict(neu_fest=len(neu), runden=runden, zeit_s=round(time.perf_counter() - t, 4)); wert = dict(wert); wert.update(neu)
    t1 = time.perf_counter(); kaest, prot = umbau(N, wert, find); t_umbau = time.perf_counter() - t1
    wurzeln = {find(v)[0] for v in alle_vars}; fest = {r for r in wurzeln if r in wert}; offen_roots = wurzeln - fest
    alias_n = sum(1 for v in alle_vars if find(v)[0] != v)
    in_k = {v for k in kaest for v in k.vars}; offen = sorted(nm(r) for r in offen_roots)
    mengen = collections.Counter(k.vars for k in kaest)
    zaehl = dict(variablen_gesamt=len(alle_vars), wurzeln=len(wurzeln), fest=len(fest), aliasiert=alias_n, offen=len(offen), offen_in_keinem_kaestchen=len([v for v in offen if v not in in_k]),
                 kaestchen=len(kaest), kaestchen_1=sum(1 for k in kaest if len(k.vars) == 1), kaestchen_2=sum(1 for k in kaest if len(k.vars) == 2), kaestchen_3=sum(1 for k in kaest if len(k.vars) == 3),
                 rest_wert=len(prot['neu_wert']), rest_gleich=len(prot['neu_alias']), enthalten=prot['enthalten'], variablenmengen_verschieden=len(mengen), mengen_mehrfach=sum(1 for c in mengen.values() if c > 1))
    erg = dict(stufe=STUFE, netz=N.name, knoten=n_knoten, zustand=zusatz, vorwaerts=vorw, zaehlung=zaehl, widerspruch=prot['widerspruch'],
               restbedingungen=dict(neu_wert=prot['neu_wert'][:200], neu_alias=prot['neu_alias'][:200], hinweis='erste 200 je Liste; Zahlen in zaehlung'),
               kaestchen_herkunft=[dict(name=k.name, variablen=list(k.vars)) for k in kaest] if len(kaest) <= 3000 else 'siehe Zaehlung',
               zeiten_s=dict(ableitung=round(t_abl, 4), umbau=round(t_umbau, 4)))
    pr = dict(E4_kein_widerspruch=(prot['widerspruch'] is None))
    if prot['widerspruch'] is None and kaest:
        t2 = time.perf_counter(); gr, kanten, ordnung, buckets = gruppen.baue(kaest)
        try: gruppen.strukturpruefung(gr, kanten, kaest); st = dict(bestanden=True)
        except gruppen.Strukturfehler as f: st = dict(bestanden=False, fehler=str(f))
        sizes = [len(g.vars) for g in gr]; erst = []; seen = 0
        for i, s in enumerate(sizes, 1):
            if s > seen: seen = s; erst.append((i, s))
        st.update(gruppen=len(gr), kanten=len(kanten), wurzeln=sum(1 for g in gr if g.eltern is None), groesste_gruppe=max(sizes), histogramm=dict(sorted(collections.Counter(sizes).items())),
                  erstmals=erst, gruppen_ueber_8=sum(1 for s in sizes if s > 8), gruppen_ueber_16=sum(1 for s in sizes if s > 16), summe_2_hoch_k_obergrenze_volltabellen='%.3e' % sum(2 ** s for s in sizes))
        erg['struktur'] = st; erg['zeiten_s']['min_fill_und_strukturpruefung'] = round(time.perf_counter() - t2, 4); pr['E3_struktur'] = st['bestanden']
    else: erg['struktur'] = None if kaest else dict(bestanden=True, gruppen=0, groesste_gruppe=0, hinweis='keine Kaestchen uebrig'); pr['E3_struktur'] = (prot['widerspruch'] is None)
    if STUFE == '0': pr['E1_reproduktion'] = (len(alle_vars) == 1326 and zaehl['kaestchen_3'] + zaehl['kaestchen_2'] == 1314 and erg['struktur']['groesste_gruppe'] == 64)
    if STUFE == 'C2': pr['E5_null_offen'] = (zaehl['offen'] == 0)
    erg['pruefung'] = pr; erg['bestanden'] = all(pr.values()); erg['maxrss_mib'] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1); erg['rlimit_as'] = resource.getrlimit(resource.RLIMIT_AS)
    erg['abhaengigkeiten'] = {m: dict(pfad=sys.modules[m].__file__, sha256=hashlib.sha256(open(sys.modules[m].__file__, 'rb').read()).hexdigest()) for m in ('pruefstand', 'gatter', 'd6', 'gruppen', 'stern', 'e1_bit') if m in sys.modules}
    json.dump(erg, open(AUSGABE, 'w'), indent=1, default=str)
    s = erg['struktur'] or {}
    print('Stufe %-2s | offen %4d fest %4d alias %4d | Kaestchen %4d (1:%d 2:%d 3:%d) Rest wert/gleich %d/%d | groesste Gruppe %s | >8: %s | Zeiten abl/umbau/minfill %s | %s' % (
        STUFE, zaehl['offen'], zaehl['fest'], zaehl['aliasiert'], zaehl['kaestchen'], zaehl['kaestchen_1'], zaehl['kaestchen_2'], zaehl['kaestchen_3'], zaehl['rest_wert'], zaehl['rest_gleich'],
        s.get('groesste_gruppe'), s.get('gruppen_ueber_8'), erg['zeiten_s'], 'BESTANDEN' if erg['bestanden'] else 'FEHLER'))
    sys.exit(0 if erg['bestanden'] else 3)
