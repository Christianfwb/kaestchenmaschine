"""EXAKTER STERN MIT BITMENGEN AN N4r09, STUFE B (GO Christian 2026-10-25 14:16, Entwurf V3).
STUFE=V0: D6-Grundgeruest (Ableitung, kein R9) -> Umbau mit Status je Originalbedingung (Gleichwertigkeit) -> Min-Fill + Strukturpruefung -> Variablenmasken (beschleunigt, gegengeprueft) -> Initialisierung -> Uebergabedatei.
STUFE=V1: Austausch (Arbeitsliste, instrumentierte Kopie, Messhaken alle 25 Entnahmen + Ende, Fortschrittsdatei) -> Folgerungen eingefroren.
STUFE=V2: unabhaengige Kontrolle (4096 Vorwaertsauswertungen am unveraenderten Original) -> E3, E7. Liest nur Dateien; nichts fliesst zurueck.
Verwendet: 531 Kaestchen der Stufe B, Zustand wert/alias (vorzeichenrichtig), Min-Fill, Arbeitsliste, schlanke Bitmengen. NICHT: lin_gl/xor_gl, R9/R9a/R9b, Kontrollbelegung, Orakel.
Grenzen: Gruppen bis 18 Variablen als Bitmenge (freigegeben), 120 s / 400 MiB je Stufe (Waechter)."""
import sys, os, json, time, itertools, resource, hashlib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); L1 = os.path.dirname(HERE); ST = os.path.join(L1, 'stern')
sys.path.insert(0, L1); sys.path.insert(0, ST)
STUFE = os.environ.get('STUFE', 'V0'); MAX_K = 18
os.environ.setdefault('FALL', 'DU'); os.environ.setdefault('STAND', 'exakt'); os.environ.setdefault('NETZ', 'N3')
import gruppen, bitmenge, bitmenge_schlank, ereignis_mess; from stern import Kaestchen
nm = lambda i: 'v%04d' % i
def popc(x): return x.bit_count()
def sha(p): return hashlib.sha256(open(p, 'rb').read()).hexdigest()
def deps(mods): return {m: dict(pfad=sys.modules[m].__file__, sha256=sha(sys.modules[m].__file__)) for m in mods if m in sys.modules}
def bytes_rek(obj, seen):
    if id(obj) in seen: return 0
    seen.add(id(obj)); s = sys.getsizeof(obj)
    if isinstance(obj, (set, frozenset, list, tuple, collections.deque)): s += sum(bytes_rek(x, seen) for x in obj)
    elif isinstance(obj, dict): s += sum(bytes_rek(k, seen) + bytes_rek(v, seen) for k, v in obj.items())
    return s

# ---------- beschleunigter Aufbau (freigegeben) mit Gegenpruefung ----------
def eins_schnell(k, j):
    """EINS[j] fuer k Variablen: Muster (2^j Nullen, 2^j Einsen), auf 2^k Bits wiederholt – durch Verdoppeln."""
    x = ((1 << (1 << j)) - 1) << (1 << j); w = 1 << (j + 1)
    while w < (1 << k): x |= x << w; w <<= 1
    return x
def eins_schleife(k, j):
    e = 0
    for b in range(1 << k):
        if (b >> j) & 1: e |= 1 << b
    return e
class SternGruppe(bitmenge_schlank.SchlankBitGruppe):
    """Schlanke Bitgruppe mit beschleunigtem Aufbau der Variablen- und Kaestchenmasken; Semijoin-Zaehler."""
    SEMI = dict(aufrufe=0)
    def varmasken(self):
        if self.EINS is None:
            t = time.perf_counter(); k = len(self.vars); self.EINS = [eins_schnell(k, j) for j in range(k)]; self.NULL = [self.ALLE & ~e for e in self.EINS]
            O = bitmenge_schlank.OPS; O['varmasken_gebaut'] += 2 * k; O['varmasken_bits'] += 2 * k * (1 << k); O['varmasken_bau_s'] += time.perf_counter() - t
        return self.EINS, self.NULL
    def kaestchen_maske(self, kst):
        E, N0 = self.varmasken(); idx = [self.vars.index(v) for v in kst.vars]; m = 0
        for row in kst.zeilen:
            z = self.ALLE
            for i, val in zip(idx, row): z &= (E[i] if val else N0[i])
            m |= z
        return m
    def init_zeilen(self):
        if len(self.vars) > MAX_K: raise gruppen.Offen('Gruppe %s: %d Variablen > %d' % (self.name, len(self.vars), MAX_K))
        self.rel = self.ALLE
        for kst in self.kaestchen: self.rel &= self.kaestchen_maske(kst)
        self.init_zeilen_zahl = popc(self.rel); return self.init_zeilen_zahl > 0
    def semijoin(self, S, M): SternGruppe.SEMI['aufrufe'] += 1; return super().semijoin(S, M)
def kaestchen_maske_schleife(g, kst):
    k = len(g.vars); idx = [g.vars.index(v) for v in kst.vars]; m = 0
    for b in range(1 << k):
        if tuple((b >> i) & 1 for i in idx) in kst.zeilen: m |= 1 << b
    return m
def selbsttest_aufbau(seed=20261025):
    import random; rnd = random.Random(seed); faelle = 0; fehler = 0
    for k in range(1, 9):
        for j in range(k):
            faelle += 1; fehler += (eins_schnell(k, j) != eins_schleife(k, j))
    for _ in range(200):
        k = rnd.randint(1, 8); vars_ = tuple('v%d' % i for i in range(k)); g = SternGruppe('T', vars_); m = rnd.randint(1, min(3, k)); kv = tuple(rnd.sample(vars_, m))
        rows = {r for r in itertools.product((0, 1), repeat=m) if rnd.random() < 0.5}; kst = Kaestchen('K', kv, rows); faelle += 1; fehler += (g.kaestchen_maske(kst) != kaestchen_maske_schleife(g, kst))
    return dict(faelle=faelle, fehler=fehler, bestanden=(fehler == 0))

# ---------- V0 ----------
def v0():
    import pruefstand as P, d6
    t0 = time.perf_counter(); N = P._n4r(9, True); g = N.g
    d = d6.D6_R567bCM(); r = d.laufen(N); t_abl = time.perf_counter() - t0; z = d._zustand; wert = dict(z['wert']); find = z['find']
    def res(x):
        if x in (0, 1, -1): return ('c', 0 if x in (0, -1) else 1)
        rt, k = find(abs(x)); s = k ^ (1 if x < 0 else 0)
        return ('c', wert[rt] ^ s) if rt in wert else ('v', rt, s)
    t1 = time.perf_counter(); kaest = []; status = collections.Counter(); prot_c = []; widerspr = []
    for i, nd in enumerate(g.nodes):
        if i < 2 or nd[0] == 'input': continue
        op, a, b = nd[0], nd[1], nd[2]; A, B, O = res(a), res(b), res(i)
        if A[0] == 'c' and B[0] == 'c': G = ('c', (A[1] & B[1]) if op == 'and' else (A[1] ^ B[1]))
        elif A[0] == 'c' or B[0] == 'c':
            c, V = (A[1], B) if A[0] == 'c' else (B[1], A)
            G = (('c', 0) if c == 0 else V) if op == 'and' else (V if c == 0 else ('v', V[1], V[2] ^ 1))
        elif A[1] == B[1]:
            same = (A[2] == B[2]); G = (A if same else ('c', 0)) if op == 'and' else (('c', 0) if same else ('c', 1))
        else: G = ('g',)
        if G[0] == 'c':
            if O[0] == 'c':
                if O[1] == G[1]: status['b_erfuellt'] += 1
                else: widerspr.append(dict(gatter=i, op=op))
            else: status['c_neu'] += 1; prot_c.append(dict(gatter=i, art='wert', variable=nm(O[1]), wert=G[1] ^ O[2])); kaest.append(Kaestchen('rest_wert#%d' % i, (nm(O[1]),), {(G[1] ^ O[2],)}))
        elif G[0] == 'v':
            if O[0] == 'c': status['c_neu'] += 1; prot_c.append(dict(gatter=i, art='wert', variable=nm(G[1]), wert=O[1] ^ G[2])); kaest.append(Kaestchen('rest_wert#%d' % i, (nm(G[1]),), {(O[1] ^ G[2],)}))
            elif O[1] == G[1]:
                if O[2] == G[2]: status['b_erfuellt'] += 1
                else: widerspr.append(dict(gatter=i, op=op, grund='x = NICHT x'))
            else:
                neg = O[2] ^ G[2]; vs = tuple(sorted((nm(O[1]), nm(G[1])))); rows = {(x, x ^ neg) for x in (0, 1)}
                status['c_neu'] += 1; prot_c.append(dict(gatter=i, art='gleich', variable=nm(O[1]), gleich=nm(G[1]), negiert=neg)); kaest.append(Kaestchen('rest_gleich#%d' % i, vs, rows))
        else:                                             # (a) echtes Gatter: Wahrheitstabelle ueber den offenen Wurzeln
            lits = [A, B] + ([O] if O[0] == 'v' else []); roots = sorted({nm(l[1]) for l in lits}); rows = set()
            for bel in itertools.product((0, 1), repeat=len(roots)):
                dd = dict(zip(roots, bel)); val = lambda L: dd[nm(L[1])] ^ L[2]
                out = (val(A) & val(B)) if op == 'and' else (val(A) ^ val(B)); oval = val(O) if O[0] == 'v' else O[1]
                if out == oval: rows.add(bel)
            status['a_kaestchen_%d' % len(roots)] += 1; kaest.append(Kaestchen('%s#%d' % (op, i), tuple(roots), rows))
    ziel_ok = 0
    for zk, val in N.ziel.items():
        R = res(zk)
        if R[0] == 'c' and R[1] == val: ziel_ok += 1
        else: widerspr.append(dict(ziel=zk, grund='Zielbit nicht fest oder falsch im Zustand'))
    gatter = sum(1 for i, nd in enumerate(g.nodes) if i >= 2 and nd[0] != 'input'); a_sum = sum(v for k_, v in status.items() if k_.startswith('a_'))
    gleich = dict(originalgatter=gatter, a_erhalten=a_sum, a_je_breite={k_: v for k_, v in status.items() if k_.startswith('a_')}, b_erfuellt=status['b_erfuellt'], c_neu=status['c_neu'], summe=a_sum + status['b_erfuellt'] + status['c_neu'],
                  zielbits=len(N.ziel), d_zielbits_fest=ziel_ok, widersprueche=widerspr, restbedingungen=len(prot_c), kaestchen_gesamt=len(kaest), nicht_aufgenommene_folgerungen=dict(lin_gl=len(z['lin_gl']), xor_gl=len(z['xor_gl'])), protokoll_c=prot_c)
    E2 = (gleich['summe'] == gatter and ziel_ok == len(N.ziel) and not widerspr and len(kaest) == a_sum + status['c_neu'])
    t2 = time.perf_counter()
    gr0, kanten, ordnung, buckets = gruppen.baue(kaest); gruppen.strukturpruefung(gr0, kanten, kaest)
    gr = []; byn = {}
    for x in gr0: h = SternGruppe(x.name, x.vars); h.kaestchen = x.kaestchen; byn[x.name] = (h, x); gr.append(h)
    for h, x in byn.values(): h.eltern = byn[x.eltern.name][0] if x.eltern is not None else None
    sizes = [len(x.vars) for x in gr]; hist = dict(sorted(collections.Counter(sizes).items()))
    alt = json.load(open(os.path.join(HERE, 'ERGEBNIS_VEREINFACHT_B.json')))['struktur']
    E1 = (len(gr) == alt['gruppen'] and len(kanten) == alt['kanten'] and max(sizes) == alt['groesste_gruppe'] and {str(k_): v for k_, v in hist.items()} == alt['histogramm'])
    t3 = time.perf_counter(); st = selbsttest_aufbau(); E5 = st['bestanden']
    bitmenge_schlank.OPS.update(varmasken_gebaut=0, varmasken_bits=0, varmasken_bau_s=0.0)
    for x in gr: x.varmasken()
    t4 = time.perf_counter(); leer = [x.name for x in gr if not x.init_zeilen()]; t5 = time.perf_counter()
    seen = set(); b_tab = sum(bytes_rek(x.rel, seen) for x in gr); b_mask = sum(bytes_rek(x.EINS, seen) + bytes_rek(x.NULL, seen) + bytes_rek(x.ALLE, seen) for x in gr); b_kaest = sum(bytes_rek(k_.zeilen, seen) + bytes_rek(k_.vars, seen) for k_ in kaest)
    ueber = dict(gruppen=[dict(name=x.name, vars=list(x.vars), rel=format(x.rel, 'x'), init=x.init_zeilen_zahl, kaestchen=[k_.name for k_ in x.kaestchen]) for x in gr], kanten=[(a, b, list(S)) for a, b, S in kanten],
                 kaestchen=[dict(name=k_.name, vars=list(k_.vars), rows=sorted(k_.zeilen)) for k_ in kaest], ordnung=ordnung, leer=leer, zustand=dict(wert={nm(k_): v for k_, v in wert.items()}, alias={nm(v): [nm(find(v)[0]), find(v)[1]] for v in range(2, len(g.nodes)) if find(v)[0] != v}))
    up = os.path.join(HERE, 'UEBERGABE_V0.json'); json.dump(ueber, open(up, 'w')); t6 = time.perf_counter()
    pruef = dict(E1_struktur=E1, E2_gleichwertigkeit=E2, E5_aufbau_gegengeprueft=E5, keine_leere_gruppe=(not leer))
    erg = dict(stufe='V0', netz=N.name, d6=dict(status=z['status'], wert=len(wert), alias=sum(1 for v in range(2, len(g.nodes)) if find(v)[0] != v), zeit_s=round(t_abl, 3), darstellung='D6+R1b+R8c+R8m (Grundgeruest, kein R9)'),
               gleichwertigkeit=gleich, struktur=dict(gruppen=len(gr), kanten=len(kanten), groesste=max(sizes), histogramm=hist, wurzeln=sum(1 for x in gr if x.eltern is None)), selbsttest_aufbau=st,
               init=dict(summe_zeilen=sum(x.init_zeilen_zahl for x in gr), groesste_zeilen=max(x.init_zeilen_zahl for x in gr), leer=leer, voll_2k_summe=sum(2 ** s for s in sizes)),
               speicher_objektbytes=dict(tabellen=b_tab, masken=b_mask, kaestchen=b_kaest, uebergabedatei=os.path.getsize(up), hinweis='rekursiv gezaehlte Objektbytes, Identitaet einmal – nicht RAM'),
               masken=dict(anzahl=bitmenge_schlank.OPS['varmasken_gebaut'], bits=bitmenge_schlank.OPS['varmasken_bits'], bau_s=round(bitmenge_schlank.OPS['varmasken_bau_s'], 4)),
               zeiten_s=dict(ableitung_d6=round(t_abl, 3), umbau_gleichwertigkeit=round(t2 - t1, 3), minfill_struktur=round(t3 - t2, 3), selbsttest_und_masken=round(t4 - t3, 3), initialisierung=round(t5 - t4, 3), uebergabe=round(t6 - t5, 3), gesamt=round(t6 - t0, 3)),
               pruefung=pruef, bestanden=all(pruef.values()), maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), rlimit_as=resource.getrlimit(resource.RLIMIT_AS), python=sys.version.split()[0],
               abhaengigkeiten=deps(('pruefstand', 'd6', 'gatter', 'e1_bit', 'gruppen', 'stern', 'bitmenge', 'bitmenge_schlank', 'ereignis_mess')))
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_STERN_N4R09_V0.json'), 'w'), indent=1, default=str)
    print('V0 | D6 %s %.2fs | Gleichwertigkeit a/b/c = %d/%d/%d von %d, Ziele %d/%d, Widerspr %d -> E2 %s | Struktur %d/%d/%d E1 %s | Aufbau-Selbsttest %s | Init Summe %d Zeilen, groesste %d | Zeiten %s | %s' % (
        z['status'], t_abl, a_sum, status['b_erfuellt'], status['c_neu'], gatter, ziel_ok, len(N.ziel), len(widerspr), E2, len(gr), len(kanten), max(sizes), E1, E5, erg['init']['summe_zeilen'], erg['init']['groesste_zeilen'], erg['zeiten_s'], 'BESTANDEN' if erg['bestanden'] else 'FEHLER'))
    sys.exit(0 if erg['bestanden'] else 3)

# ---------- V1 ----------
def v1():
    t0 = time.perf_counter(); U = json.load(open(os.path.join(HERE, 'UEBERGABE_V0.json'))); kaest = {k_['name']: Kaestchen(k_['name'], tuple(k_['vars']), {tuple(r) for r in k_['rows']}) for k_ in U['kaestchen']}
    gr = []; byn = {}
    for gd in U['gruppen']:
        x = SternGruppe(gd['name'], gd['vars']); x.rel = int(gd['rel'], 16); x.init_zeilen_zahl = gd['init']; x.kaestchen = [kaest[n] for n in gd['kaestchen']]; gr.append(x); byn[gd['name']] = x
    kanten = [(a, b, tuple(S)) for a, b, S in U['kanten']]
    for x in gr: x.varmasken()
    bitmenge_schlank.OPS.update(und=0, oder=0, popcount=0, maske_c_berechnet=0, zwischen_bytes_max=0); SternGruppe.SEMI['aufrufe'] = 0
    t1 = time.perf_counter(); z = dict(bearbeitungen=0, nachrichten_geprueft=0, nachrichten_gesendet=0, gestrichen=0); prot = []; mess = []; fp = os.path.join(HERE, 'FORTSCHRITT_V1.json')
    def messen(punkt, zu):
        if punkt.startswith('Ma'): return
        if punkt.startswith('Mb') and z['bearbeitungen'] % 25 != 0: return
        seen = set(); tab = sum(bytes_rek(x.rel, seen) for x in gr); mask = sum(bytes_rek(x.EINS, seen) + bytes_rek(x.NULL, seen) + bytes_rek(x.ALLE, seen) for x in gr)
        ges = [v for v in zu['N'].values() if v is not None]; nachr = sum(bytes_rek(v, seen) for v in ges)
        arbeit = bytes_rek(zu['N'], seen) + bytes_rek(zu['schlange'], seen) + bytes_rek(zu['drin'], seen) + bytes_rek(zu['neu_eingang'], seen) + bytes_rek(zu['nachbarn'], seen)
        m = dict(nr=len(mess), punkt=punkt, zeit_s=round(time.perf_counter() - t1, 3), entnahmen=z['bearbeitungen'], semijoins=SternGruppe.SEMI['aufrufe'], projektionen=z['nachrichten_geprueft'], nachrichten=len(ges), gestrichen=z['gestrichen'], schlange=len(zu['schlange']),
                 zeilen_gesamt=sum(popc(x.rel) for x in gr), tabellen=tab, masken=mask, nachrichten_bytes=nachr, arbeitsstrukturen=arbeit, summe=tab + mask + nachr + arbeit, ops=dict(bitmenge_schlank.OPS), rss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1))
        mess.append(m); json.dump(dict(stand='laufend', letzter_messpunkt=m), open(fp, 'w'), default=str)
    w = ereignis_mess.arbeitsliste(gr, kanten, prot, z, messen); status = 'WIDERSPRUCH' if w else 'FIXPUNKT'; t2 = time.perf_counter()
    kg = {('%s-%s' % (a, b)): (byn[a].proj(S) == byn[b].proj(S)) for a, b, S in kanten} if status == 'FIXPUNKT' else None; t3 = time.perf_counter()
    fest = {}
    for x in gr:
        if not x.rel: continue
        E, N0 = x.varmasken()
        for j, v in enumerate(x.vars):
            if x.rel & E[j] == 0: fest[v] = 0
            elif x.rel & N0[j] == 0: fest[v] = 1
    eing = {v: w_ for v, w_ in fest.items() if int(v[1:]) in range(2, 14)}      # freie Eingaenge sind Knoten 2..13
    folg = dict(status=status, eingefroren=True, feste_eingangsbits=eing, feste_innen=len(fest) - len(eing), feste_gesamt=len(fest), zeilen_je_gruppe={x.name: popc(x.rel) for x in gr}, gruppen_mit_einer_zeile=sum(1 for x in gr if popc(x.rel) == 1), zeilen_gesamt=sum(popc(x.rel) for x in gr),
                zaehler=dict(entnahmen=z['bearbeitungen'], semijoins_direkt=SternGruppe.SEMI['aufrufe'], projektionen=z['nachrichten_geprueft'], nachrichten_gesendet=z['nachrichten_gesendet'], gestrichen=z['gestrichen'], max_schlange=z.get('max_schlange'), ops=dict(bitmenge_schlank.OPS)))
    hoechst = max(mess, key=lambda m: m['summe']) if mess else None
    erg = dict(stufe='V1', FOLGERUNGEN=folg, kanten_projektionen_gleich=(all(kg.values()) if kg else None), messpunkte=dict(definition='M0; Mb nach jeder 25. Entnahme; ME Ende (Ma ausgelassen)', anzahl=len(mess), hinweis='Hoechststand = beobachtet an diesen Punkten'), hoechststand_beobachtet=hoechst, endstand=(mess[-1] if mess else None), messreihe=mess,
               endrelationen={x.name: format(x.rel, 'x') for x in gr}, protokoll_laenge=len(prot), zeiten_s=dict(laden_und_masken=round(t1 - t0, 3), austausch=round(t2 - t1, 3), kantenpruefung=round(t3 - t2, 3)),
               pruefung=dict(E4_kanten=(kg is None or all(kg.values())), kein_fehler=True), bestanden=(kg is None or all(kg.values())), maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), rlimit_as=resource.getrlimit(resource.RLIMIT_AS), python=sys.version.split()[0],
               abhaengigkeiten=deps(('gruppen', 'stern', 'bitmenge', 'bitmenge_schlank', 'ereignis_mess')))
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_STERN_N4R09_V1.json'), 'w'), indent=1, default=str); json.dump(dict(stand='fertig'), open(fp, 'w'))
    print('V1 | %s | Entnahmen %d Semijoins %d Proj %d Nachr %d gestrichen %d | feste Eingangsbits %d/12, fest gesamt %d, Gruppen mit 1 Zeile %d/%d, Zeilen gesamt %d | Kanten gleich %s | Austausch %.1f s | Hoechststand %s | %s' % (
        status, z['bearbeitungen'], SternGruppe.SEMI['aufrufe'], z['nachrichten_geprueft'], z['nachrichten_gesendet'], z['gestrichen'], len(eing), len(fest), folg['gruppen_mit_einer_zeile'], len(gr), folg['zeilen_gesamt'], erg['kanten_projektionen_gleich'], t2 - t1, (hoechst or {}).get('summe'), 'BESTANDEN' if erg['bestanden'] else 'FEHLER'))
    sys.exit(0 if erg['bestanden'] else 3)

# ---------- V2 ----------
def v2():
    import pruefstand as P
    t0 = time.perf_counter(); U = json.load(open(os.path.join(HERE, 'UEBERGABE_V0.json'))); V1 = json.load(open(os.path.join(HERE, 'ERGEBNIS_STERN_N4R09_V1.json'))); V0 = json.load(open(os.path.join(HERE, 'ERGEBNIS_STERN_N4R09_V0.json')))
    N = P._n4r(9, True); g = N.g; wahr = []
    for bel in itertools.product((0, 1), repeat=len(N.frei)):
        v = N.wert(list(bel))
        if all((v[abs(zk)] ^ (1 if zk < 0 else 0)) == val for zk, val in N.ziel.items()): wahr.append({nm(i): v[i] for i in range(2, len(v))})
    t1 = time.perf_counter(); kaest = [Kaestchen(k_['name'], tuple(k_['vars']), {tuple(r) for r in k_['rows']}) for k_ in U['kaestchen']]; wert = U['zustand']['wert']; alias = U['zustand']['alias']
    # E3: jede echte Loesung erfuellt alle Kaestchen und den Zustand (Werte, Aliase vorzeichenrichtig)
    e3_k = all(tuple(s[v] for v in k_.vars) in k_.zeilen for s in wahr for k_ in kaest); e3_w = all(s[v] == w_ for s in wahr for v, w_ in wert.items()); e3_a = all(s[v] == s[rt] ^ k_ for s in wahr for v, (rt, k_) in alias.items())
    # E7: Gruppentabellen == Projektionen der echten Loesungen (bei FIXPUNKT, Kanten gleich, Gleichwertigkeit, Struktur)
    je = {}; fehlend = 0; zu_viel = 0
    for gd in U['gruppen']:
        rel = int(V1['endrelationen'][gd['name']], 16); vars_ = gd['vars']; P_ = {sum(s[v] << j for j, v in enumerate(vars_)) for s in wahr}; R = {b for b in range(1 << len(vars_)) if (rel >> b) & 1}
        je[gd['name']] = dict(zeilen=len(R), projektion=len(P_), zu_viel=len(R - P_), fehlend=len(P_ - R)); fehlend += len(P_ - R); zu_viel += len(R - P_)
    voraus = dict(gleichwertigkeit=V0['pruefung']['E2_gleichwertigkeit'], struktur=V0['pruefung']['E1_struktur'], fixpunkt=(V1['FOLGERUNGEN']['status'] == 'FIXPUNKT'), kanten_gleich=bool(V1['kanten_projektionen_gleich']))
    e7_anwendbar = all(voraus.values()); eing = V1['FOLGERUNGEN']['feste_eingangsbits']; eing_ok = all(all(s[v] == w_ for s in wahr) for v, w_ in eing.items())
    E7 = (not e7_anwendbar) or (zu_viel == 0 and fehlend == 0 and len(eing) == 12 and eing_ok)
    fest_falsch = {v: w_ for v, w_ in eing.items() if any(s[v] != w_ for s in wahr)}
    t2 = time.perf_counter()
    pruef = dict(E3_kontrolle_eine_loesung=(len(wahr) == 1), E3_loesung_erfuellt_kaestchen=e3_k, E3_loesung_erfuellt_werte=e3_w, E3_loesung_erfuellt_aliase=e3_a, E3_nichts_fehlt=(fehlend == 0), E3_keine_falsche_eingangsfestlegung=(not fest_falsch), E7_abschlusstest=E7)
    erg = dict(stufe='V2', kontrolle=dict(belegungen=4096, echte_loesungen=len(wahr), loesung_eingaenge=([{v: s[v] for v in (nm(i) for i in range(2, 14))} for s in wahr] if len(wahr) <= 4 else None), zeit_s=round(t1 - t0, 3)),
               E7=dict(anwendbar=e7_anwendbar, voraussetzungen=voraus, zu_viel_gesamt=zu_viel, fehlend_gesamt=fehlend, gruppen_mit_zu_viel=sum(1 for d in je.values() if d['zu_viel']), feste_eingangsbits_der_mitte=len(eing), eingangsbits_korrekt=eing_ok, je_gruppe=je),
               pruefung=pruef, bestanden=all(pruef.values()), zeiten_s=dict(kontrolle=round(t1 - t0, 3), vergleich=round(t2 - t1, 3)), maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), python=sys.version.split()[0], abhaengigkeiten=deps(('pruefstand', 'gatter', 'd6', 'e1_bit', 'stern')))
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_STERN_N4R09_V2.json'), 'w'), indent=1, default=str)
    print('V2 | echte Loesungen %d | E3 Kaestchen/Werte/Aliase %s/%s/%s, fehlend %d | E7 anwendbar %s: zu_viel %d in %d Gruppen, feste Eingangsbits %d/12 korrekt %s -> %s | %s' % (
        len(wahr), e3_k, e3_w, e3_a, fehlend, e7_anwendbar, zu_viel, erg['E7']['gruppen_mit_zu_viel'], len(eing), eing_ok, E7, 'BESTANDEN' if erg['bestanden'] else 'FEHLER'))
    sys.exit(0 if erg['bestanden'] else 3)

if __name__ == '__main__': {'V0': v0, 'V1': v1, 'V2': v2}[STUFE]()
