"""B2 – BEGRENZTE GRUPPEN AN N3/N3u AUF GATTEREBENE (GO Christian 2026-10-25 08:43; Entwurf B2).
Kaestchen = einzelne Gatter des Pruefstand-Netzes (XOR/UND, 3 Variablen, echte Wahrheitstabellen) + Zielbits (1 Variable). Staende: exakt | i5 (Vorprobe) | i4 | i3.
Aufspaltung/Strukturpruefung/Zaehler aus begrenzt.py, Arbeitsliste aus ereignis.py, Gruppierung aus gruppen.py – alle unveraendert importiert.
Drei getrennte Ausweise: SPEICHERUNG | ERKANNTE FOLGERUNGEN (vor der Kontrolle) | KONTROLLZAEHLUNG (1024 Eingabebelegungen vorwaerts, danach; nichts zurueck).
Aufruf: NETZ=N3|N3u STAND=exakt|i5|i4|i3 python3 -I begrenzt_n3.py"""
import sys, os, json, time, itertools, resource, hashlib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); L1 = os.path.dirname(HERE); sys.path.insert(0, HERE); sys.path.insert(0, L1)
os.environ.setdefault('FALL', 'DU'); os.environ.setdefault('STAND', 'exakt')
import gruppen, ereignis, begrenzt; from stern import Kaestchen; import pruefstand as P
NETZ = os.environ.get('NETZ', 'N3'); STAND = os.environ.get('STAND', 'i3'); I = {'exakt': None, 'i5': 5, 'i4': 4, 'i3': 3}[STAND]
nm = lambda i: 'v%03d' % i

def gatter_kaestchen(N):
    g = N.g; ks = []; typ = {}
    for i, nd in enumerate(g.nodes):
        if i < 2 or nd[0] == 'input': continue
        op, a, b = nd[0], nd[1], nd[2]; typ[nm(i)] = op
        vs = sorted({nm(i)} | {nm(abs(x)) for x in (a, b) if abs(x) >= 2})
        rows = set()
        for bel in itertools.product((0, 1), repeat=len(vs)):
            d = dict(zip(vs, bel)); d['v000'] = 0; d['v001'] = 1
            lit = lambda x: d[nm(abs(x))] ^ (1 if x < 0 else 0)
            out = (lit(a) & lit(b)) if op == 'and' else (lit(a) ^ lit(b))
            if d[nm(i)] == out: rows.add(bel)
        ks.append(Kaestchen('%s#%d' % (op, i), tuple(vs), rows))
    for z, val in N.ziel.items(): ks.append(Kaestchen('ziel#%d' % abs(z), (nm(abs(z)),), {(val ^ (1 if z < 0 else 0),)}))
    for f in N.frei: typ[nm(f)] = 'input'
    return ks, typ

def fall():
    N = P.NETZE[NETZ](); kaest, typ = gatter_kaestchen(N); frei = [nm(f) for f in N.frei]; alle_vars = sorted({v for k in kaest for v in k.vars})
    erw_loes = {'N3': 12, 'N3u': 0}[NETZ]; begrenzt.ZAEHL.update(semijoins=0, proj_zeilen=0)
    t0 = time.perf_counter(); status = None; prot = []; z = dict(bearbeitungen=0, nachrichten_geprueft=0, nachrichten_gesendet=0, gestrichen=0); aufsp = {}; strukt = None; gr = []; kanten = []; ordnung = None; ps = None; init_summe = None
    try:
        if I is None:
            gr0, kanten, ordnung, buckets = gruppen.baue(kaest); gruppen.strukturpruefung(gr0, kanten, kaest); byn = {}
            for g in gr0: h = begrenzt.GruppeZ(g.name, g.vars); h.kaestchen = g.kaestchen; byn[g.name] = (h, g)
            gr = [byn[g.name][0] for g in gr0]
            for h, g in byn.values(): h.eltern = byn[g.eltern.name][0] if g.eltern is not None else None
        else:
            gr, kanten, ordnung, aufsp, bauprot = begrenzt.baue_begrenzt(kaest, I); strukt = begrenzt.strukturpruefung_begrenzt(gr, kanten, kaest, aufsp, I)
        leer = [g.name for g in gr if not g.init_zeilen()]
        for g in gr:
            if len(g.vars) > 8 or len(g.zeilen) > 256: raise gruppen.Offen('%s ueber Grenze' % g.name)
        init = {g.name: set(g.zeilen) for g in gr}; ps = begrenzt.pruefsumme(gr, kanten); init_summe = sum(len(g.zeilen) for g in gr); t1 = time.perf_counter()
        if leer: status = 'WIDERSPRUCH'; prot.append(dict(ereignis='WIDERSPRUCH: Gruppe beim Initialisieren leer', gruppen=leer))
        else: w = ereignis.arbeitsliste(gr, kanten, prot, z); status = 'WIDERSPRUCH' if w else 'FIXPUNKT'
        t2 = time.perf_counter()
    except gruppen.Offen as o: status = 'OFFEN (%s)' % o; t1 = t2 = time.perf_counter(); init = {}
    except gruppen.Strukturfehler as f: status = 'FEHLER (Struktur: %s)' % f; t1 = t2 = time.perf_counter(); init = {}
    # ERKANNTE FOLGERUNGEN (vor der Kontrolle)
    fest = {}; paare_ausgeschlossen = 0
    for g in gr:
        if not g.zeilen: continue
        for k, v in enumerate(g.vars):
            w = {zl[k] for zl in g.zeilen}
            if len(w) == 1: fest[v] = w.pop()
        for k1, k2 in itertools.combinations(range(len(g.vars)), 2):
            if len({(zl[k1], zl[k2]) for zl in g.zeilen}) < 4: paare_ausgeschlossen += 1
    folg = dict(status=status, gestrichen=z['gestrichen'], fest_eingaenge={v: w for v, w in fest.items() if typ.get(v) == 'input'}, fest_innen={v: w for v, w in fest.items() if typ.get(v) != 'input'},
                paare_mit_ausschluss_in_gruppen=paare_ausgeschlossen, gruppen_veraendert=sum(1 for g in gr if g.zeilen is not None and set(g.zeilen) != init.get(g.name)),
                entnahmen=z['bearbeitungen'], semijoins=begrenzt.ZAEHL['semijoins'], projektionen=z['nachrichten_geprueft'], projektionszeilen_gesamt=begrenzt.ZAEHL['proj_zeilen'], nachrichten_gesendet=z['nachrichten_gesendet'], max_liste=z.get('max_schlange'), protokoll=prot)
    byn = {g.name: g for g in gr}; kanten_gleich = {('%s-%s' % (a, b)): (byn[a].proj(S) == byn[b].proj(S)) for a, b, S in kanten} if status == 'FIXPUNKT' else None; t3 = time.perf_counter()
    # KONTROLLE (danach, am Original): 1024 Belegungen vorwaerts, Zielbits pruefen -> volle Belegungen aller Variablen
    wahr = []
    for bel in itertools.product((0, 1), repeat=len(N.frei)):
        v = N.wert(list(bel))
        if all((v[abs(zk)] ^ (1 if zk < 0 else 0)) == val for zk, val in N.ziel.items()): wahr.append({nm(i): v[i] for i in range(2, len(v))})
    je = {}
    for g in gr:
        if g.zeilen is None: continue
        Pj = {tuple(w[x] for x in g.vars) for w in wahr}; je[g.name] = dict(zeilen=len(g.zeilen), projektion_echt=len(Pj), zu_viel=len(set(g.zeilen) - Pj), fehlend=len(Pj - set(g.zeilen)))
    fest_falsch = {v: w for v, w in fest.items() if any(s[v] != w for s in wahr)}
    fest_echt = {v for v in alle_vars if wahr and len({s[v] for s in wahr}) == 1}       # in der echten Loesungsmenge feste Variablen (Kontrolle)
    fehlt = sorted(v for v in fest_echt if v not in fest); t4 = time.perf_counter()
    speich = dict(echte_loesungen=len(wahr), fehlend_in_gruppen=sum(d['fehlend'] for d in je.values()), verbund_hinweis='Vollzaehlung ueber alle %d Variablen (2^%d) nicht durchfuehrbar; Erhalt wird je Gruppe (fehlend) geprueft' % (len(alle_vars), len(alle_vars)))
    kontr = dict(je_gruppe=je, zu_viel_gesamt=sum(d['zu_viel'] for d in je.values()), gruppen_mit_zu_viel=sum(1 for d in je.values() if d['zu_viel']), fest_widerspricht_kontrolle=fest_falsch,
                 fest_laut_kontrolle=len(fest_echt), fest_erkannt=len([v for v in fest if v in fest_echt]), fehlende_feste_variablen=[dict(variable=v, typ=typ.get(v), wert=next(iter({s[v] for s in wahr}))) for v in fehlt])
    pruef = dict(E2_konstruktion=(not status.startswith('FEHLER')), E3_speicherung=(speich['fehlend_in_gruppen'] == 0 and not fest_falsch), E5_keine_doppeleintraege=(not status.startswith('FEHLER')),
                 E6_kanten=(kanten_gleich is None or all(kanten_gleich.values())), kontrolle_erwartet=(len(wahr) == erw_loes))
    if I is None: pruef['E4_exakt'] = (status == ('FIXPUNKT' if erw_loes else 'WIDERSPRUCH')) and (status != 'FIXPUNKT' or kontr['zu_viel_gesamt'] == 0)
    sizes = [len(g.vars) for g in gr]
    erg = dict(netz=NETZ, name=N.name, stand=STAND, schranke_i=I, variablen=len(alle_vars), kaestchen=len(kaest), gatter=sum(1 for k in kaest if not k.name.startswith('ziel')), ordnung=ordnung, aufspaltungsstellen=aufsp, struktur=strukt, pruefsumme_struktur=ps,
               kosten=dict(gruppen=len(gr), aufspaltungsstellen=len(aufsp), groesste_gruppe_vars=(max(sizes) if sizes else None), histogramm=dict(sorted(collections.Counter(sizes).items())),
                           groesste_gruppe_zeilen_2k=(max(2 ** s for s in sizes) if sizes else None), groesste_gruppe_zeilen_init=(max((g.init_zeilen_zahl for g in gr if hasattr(g, 'init_zeilen_zahl')), default=None)), groesste_gruppe_zeilen_ende=(max((len(g.zeilen) for g in gr if g.zeilen is not None), default=None)),
                           summe_zeilen_init=init_summe, summe_zeilen_ende=sum(len(g.zeilen) for g in gr if g.zeilen is not None), summe_2k='%d' % sum(2 ** s for s in sizes), kanten=len(kanten)),
               gruppen=[dict(name=g.name, variablen=g.vars, kaestchen=[k.name for k in g.kaestchen], zeilen_init=getattr(g, 'init_zeilen_zahl', None), zeilen_ende=(len(g.zeilen) if g.zeilen is not None else None)) for g in gr],
               FOLGERUNGEN=folg, kanten_projektionen_gleich=kanten_gleich, SPEICHERUNG=speich, KONTROLLE=kontr, pruefung=pruef, bestanden=all(pruef.values()),
               zeiten_s=dict(T1_gruppierung_aufspaltung_init=round(t1 - t0, 5), T2_austausch=round(t2 - t1, 5), T3_kantenpruefung=round(t3 - t2, 5), T4_kontrolle=round(t4 - t3, 5)),
               maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), rlimit_as=resource.getrlimit(resource.RLIMIT_AS), python=sys.version.split()[0],
               abhaengigkeiten={m: dict(pfad=sys.modules[m].__file__, sha256=hashlib.sha256(open(sys.modules[m].__file__, 'rb').read()).hexdigest()) for m in ('gruppen', 'ereignis', 'begrenzt', 'stern', 'pruefstand', 'gatter', 'd6', 'e1_bit') if m in sys.modules})
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_B2_%s_%s.json' % (NETZ, STAND)), 'w'), indent=1, default=str)
    print('%-3s %-5s %-11s | Gruppen %d (max %s Var, Zeilen init %s) Aufsp %d | gestrichen %3d | fest Eing/Innen %d/%d (Kontrolle fest %d, fehlen %d) | Entn/Semij/Proj/Nachr %d/%d/%d/%d | zu_viel %d in %d Gruppen, fehlend %d | %s' % (
        NETZ, STAND, status[:11], len(gr), erg['kosten']['groesste_gruppe_vars'], erg['kosten']['groesste_gruppe_zeilen_init'], len(aufsp), z['gestrichen'], len(folg['fest_eingaenge']), len(folg['fest_innen']), kontr['fest_laut_kontrolle'], len(fehlt),
        z['bearbeitungen'], begrenzt.ZAEHL['semijoins'], z['nachrichten_geprueft'], z['nachrichten_gesendet'], kontr['zu_viel_gesamt'], kontr['gruppen_mit_zu_viel'], speich['fehlend_in_gruppen'], 'BESTANDEN' if erg['bestanden'] else 'FEHLER'))
    sys.exit(0 if erg['bestanden'] else 3)
if __name__ == '__main__': fall()
