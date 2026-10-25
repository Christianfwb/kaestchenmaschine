"""BEGRENZTE GRUPPEN – Dreiecks-Pruefstand (GO Christian 2026-10-25 08:25; Entwurf B1 V2 + Ghosts Deutungspraezisierung 08:16).
Mini-Bucket-Aufspaltung (Dechter & Rish 2003) entlang der Min-Fill-Ordnung; Kaestchen bleiben ganz (Posten > i -> OFFEN). Austausch = Arbeitsliste (ereignis.py, unveraendert importiert).
Drei getrennte Ausweise: SPEICHERUNG | ERKANNTE FOLGERUNGEN (vor der Kontrolle festgehalten) | KONTROLLZAEHLUNG (danach, nichts zurueck).
Aufruf: FALL=DU|DL STAND=exakt|i3|i2 python3 -I begrenzt.py"""
import sys, os, json, time, itertools, resource, hashlib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gruppen, ereignis; from stern import Kaestchen
FALL = os.environ.get('FALL', 'DU'); STAND = os.environ.get('STAND', 'i2')
ZAEHL = dict(semijoins=0, proj_zeilen=0)
class GruppeZ(gruppen.Gruppe):
    """Gruppe mit eigenem Semijoin-Zaehler (Ghosts Hinweis: Semijoins separat messen) und Projektionszeilen-Zaehler."""
    def semijoin(self, S, M): ZAEHL['semijoins'] += 1; return super().semijoin(S, M)
    def proj(self, S): p = super().proj(S); ZAEHL['proj_zeilen'] += len(p); return p

def faelle():
    U = lambda a, b: {(0, 1), (1, 0)}; G = lambda a, b: {(0, 0), (1, 1)}
    if FALL == 'DU': return [Kaestchen('K_ab', ('a', 'b'), U('a', 'b')), Kaestchen('K_ac', ('a', 'c'), U('a', 'c')), Kaestchen('K_bc', ('b', 'c'), U('b', 'c'))], 0, 'Dreieck unloesbar: a!=b, b!=c, a!=c'
    return [Kaestchen('K_ab', ('a', 'b'), U('a', 'b')), Kaestchen('K_ac', ('a', 'c'), G('a', 'c')), Kaestchen('K_bc', ('b', 'c'), U('b', 'c'))], 2, 'Dreieck loesbar: a!=b, b!=c, a=c'

def baue_begrenzt(kaest, i):
    """Mini-Bucket: je Bucket v Posten = zugeordnete Kaestchen (Name) + eingehende Nachrichten (Absender); First-Fit in Teilgruppen mit <= i Variablen."""
    ordnung, buckets = gruppen.min_fill(kaest); pos = {v: k for k, v in enumerate(ordnung)}
    zu = collections.defaultdict(list)
    for k in kaest: zu[min(k.vars, key=lambda x: pos[x])].append(k)
    nachrichten = collections.defaultdict(list)      # v -> [(absender_gruppe, vars)]
    alle = []; kanten = []; aufspaltung = {}; protokoll = []
    for v in ordnung:
        posten = [('K', k.name, set(k.vars), k) for k in sorted(zu[v], key=lambda k: k.name)] + [('N', g.name, set(S), g) for g, S in sorted(nachrichten[v], key=lambda t: t[0].name)]
        teil = []
        for art, name, vs, obj in posten:
            if len(vs) > i: raise gruppen.Offen('Posten %s (%s, %d Variablen) passt nicht in Schranke i=%d' % (name, art, len(vs), i))
            for T in teil:
                if len(T['vars'] | vs) <= i: T['vars'] |= vs; T['posten'].append((art, name, obj)); break
            else: teil.append(dict(vars=set(vs), posten=[(art, name, obj)]))
        if len(teil) > 1: aufspaltung[v] = len(teil)
        for j, T in enumerate(teil):
            g = GruppeZ(('G_%s' % v) if len(teil) == 1 else ('G_%s_%d' % (v, j + 1)), [v] + sorted(T['vars'] - {v}, key=lambda x: pos[x]))
            for art, name, obj in T['posten']:
                if art == 'K': g.kaestchen.append(obj)
                else: obj.eltern = g; g.kinder.append(obj); kanten.append((obj.name, g.name, tuple(sorted(set(obj.vars) & set(g.vars), key=lambda x: pos[x]))))
            rest = T['vars'] - {v}
            if rest: nachrichten[min(rest, key=lambda x: pos[x])].append((g, rest))
            alle.append(g); protokoll.append(dict(bucket=v, teilgruppe=g.name, variablen=g.vars, posten=[(a, n) for a, n, _ in T['posten']]))
    return alle, kanten, ordnung, aufspaltung, protokoll

def strukturpruefung_begrenzt(gr, kanten, kaest, aufspaltung, i):
    zu = collections.Counter(k.name for g in gr for k in g.kaestchen)
    if any(zu.get(k.name, 0) != 1 for k in kaest): raise gruppen.Strukturfehler('Kaestchen nicht genau einmal: %s' % dict(zu))
    for g in gr:
        if len(g.vars) > i: raise gruppen.Strukturfehler('%s > i' % g.name)
        for k in g.kaestchen:
            if not set(k.vars) <= set(g.vars): raise gruppen.Strukturfehler('%s nicht in %s' % (k.name, g.name))
    adj = {g.name: set() for g in gr}
    for a, b, S in kanten:
        if not S: raise gruppen.Strukturfehler('Kante %s-%s ohne Schnittmenge' % (a, b))
        adj[a].add(b); adj[b].add(a)
    besucht = set(); komp = 0
    for s in adj:
        if s in besucht: continue
        komp += 1; stapel = [(s, None)]; besucht.add(s)
        while stapel:
            x, vor = stapel.pop()
            for y in adj[x]:
                if y == vor: continue
                if y in besucht: raise gruppen.Strukturfehler('Kreis bei %s-%s' % (x, y))
                besucht.add(y); stapel.append((y, x))
    wurzeln = sum(1 for g in gr if g.eltern is None)
    if komp != wurzeln: raise gruppen.Strukturfehler('Komponenten %d != Wurzeln %d' % (komp, wurzeln))
    ri = {}
    for v in sorted({x for g in gr for x in g.vars}):
        mit = [g.name for g in gr if v in g.vars]; gesehen = set(); teile = 0
        for m in mit:
            if m in gesehen: continue
            teile += 1; stapel = [m]; gesehen.add(m)
            while stapel:
                x = stapel.pop()
                for y in adj[x]:
                    if y in mit and y not in gesehen: gesehen.add(y); stapel.append(y)
        ri[v] = teile
        if teile > 1 and v not in aufspaltung: raise gruppen.Strukturfehler('Running Intersection fuer %s verletzt (%d Teile) ausserhalb einer Aufspaltungsstelle' % (v, teile))
    return dict(komponenten=komp, wurzeln=wurzeln, ri_teile_je_variable=ri)

def pruefsumme(gr, kanten):
    return hashlib.sha256(json.dumps(sorted([sorted(g.vars), sorted(sorted(zip(g.vars, z)) for z in g.zeilen)] for g in gr) + sorted(sorted([a, b]) + [sorted(S)] for a, b, S in kanten), default=list).encode()).hexdigest()

def fall():
    kaest, erw_loes, beschr = faelle(); frei = ['a', 'b', 'c']; original = [k.kopie() for k in kaest]
    i = {'exakt': None, 'i3': 3, 'i2': 2}[STAND]; t0 = time.perf_counter(); status = None; prot = []; z = dict(bearbeitungen=0, nachrichten_geprueft=0, nachrichten_gesendet=0, gestrichen=0); aufsp = {}; bauprot = None; strukt = None
    try:
        if i is None:
            gr, kanten, ordnung, buckets = gruppen.baue(kaest); gruppen.strukturpruefung(gr, kanten, kaest)
            gr2 = []
            for g in gr: h = GruppeZ(g.name, g.vars); h.kaestchen = g.kaestchen; h.eltern = g.eltern; gr2.append(h)
            byn = {h.name: h for h in gr2}
            for h in gr2: h.eltern = byn[h.eltern.name] if h.eltern is not None else None
            gr = gr2
        else:
            gr, kanten, ordnung, aufsp, bauprot = baue_begrenzt(kaest, i); strukt = strukturpruefung_begrenzt(gr, kanten, kaest, aufsp, i)
        leer = [g.name for g in gr if not g.init_zeilen()]
        for g in gr:
            if i is not None and len(g.zeilen) > 2 ** i: raise gruppen.Offen('%s > 2^i Zeilen' % g.name)
        ps = pruefsumme(gr, kanten); init_summe = sum(len(g.zeilen) for g in gr); t1 = time.perf_counter()
        if leer: status = 'WIDERSPRUCH'; prot.append(dict(ereignis='WIDERSPRUCH: Gruppe beim Initialisieren leer', gruppen=leer))
        else: w = ereignis.arbeitsliste(gr, kanten, prot, z); status = 'WIDERSPRUCH' if w else 'FIXPUNKT'
        t2 = time.perf_counter()
    except gruppen.Offen as o: status = 'OFFEN (%s)' % o; gr = []; kanten = []; ordnung = None; ps = None; init_summe = None; t1 = t2 = time.perf_counter()
    except gruppen.Strukturfehler as f: status = 'FEHLER (Struktur: %s)' % f; gr = []; kanten = []; ordnung = None; ps = None; init_summe = None; t1 = t2 = time.perf_counter()
    # ERKANNTE FOLGERUNGEN – festgehalten VOR der Kontrolle
    fest = {}
    for g in gr:
        if g.zeilen:
            for k, v in enumerate(g.vars):
                w = {zl[k] for zl in g.zeilen}
                if len(w) == 1: fest[v] = w.pop()
    folgerungen = dict(status=status, gestrichen=z['gestrichen'], fest=fest, zeilen_je_gruppe={g.name: (len(g.zeilen) if g.zeilen is not None else None) for g in gr}, protokoll=prot,
                       entnahmen=z['bearbeitungen'], semijoins=ZAEHL['semijoins'], projektionen=z['nachrichten_geprueft'], projektionszeilen_gesamt=ZAEHL['proj_zeilen'], nachrichten_gesendet=z['nachrichten_gesendet'], max_liste=z.get('max_schlange'))
    byn = {g.name: g for g in gr}; kanten_gleich = {('%s-%s' % (a, b)): (byn[a].proj(S) == byn[b].proj(S)) for a, b, S in kanten} if status == 'FIXPUNKT' else None; t3 = time.perf_counter()
    # KONTROLLZAEHLUNG – danach, am Original; nichts zurueck
    wahr = gruppen.loesungen(original, frei, []); verbund = (gruppen.loesungen_gruppen(gr, frei, []) if status == 'FIXPUNKT' else (set() if status == 'WIDERSPRUCH' else None))
    je = {}
    for g in gr:
        if g.zeilen is None: continue
        idx = [frei.index(v) for v in g.vars]; P = {tuple(w[k] for k in idx) for w in wahr}
        je[g.name] = dict(zeilen=len(g.zeilen), projektion_echt=len(P), zu_viel=len(set(g.zeilen) - P), fehlend=len(P - set(g.zeilen)))
    fest_falsch = {v: w for v, w in fest.items() if any(s[frei.index(v)] != w for s in wahr)}
    t4 = time.perf_counter()
    speicherung = dict(echte_loesungen=len(wahr), verbund_zaehlung=(len(verbund) if verbund is not None else None), fehlend_gesamt=(len(wahr - verbund) if verbund is not None else None), hinweis='Verbundzaehlung ist Kontrolle, keine Leistung der Mitte')
    kontrolle = dict(je_gruppe=je, fest_widerspricht_kontrolle=fest_falsch, zu_viel_gesamt=sum(d['zu_viel'] for d in je.values()), fehlend_in_gruppen=sum(d['fehlend'] for d in je.values()))
    pruef = dict(E2_konstruktion=(not status.startswith('FEHLER')), E3_speicherung=(speicherung['fehlend_gesamt'] in (0, None) and kontrolle['fehlend_in_gruppen'] == 0 and not fest_falsch),
                 E5_keine_doppeleintraege=(not status.startswith('FEHLER')), E6_kanten=(kanten_gleich is None or all(kanten_gleich.values())), kontrolle_erwartet=(len(wahr) == erw_loes))
    if i is None: pruef['E4_exakt'] = (status == ('FIXPUNKT' if erw_loes else 'WIDERSPRUCH')) and (status != 'FIXPUNKT' or all(d['zu_viel'] == 0 for d in je.values()))
    erg = dict(fall=FALL, beschreibung=beschr, stand=STAND, schranke_i=i, ordnung=ordnung, aufspaltungsstellen=aufsp, aufbau_protokoll=bauprot, struktur=strukt, pruefsumme_struktur=ps,
               gruppen=[dict(name=g.name, variablen=g.vars, kaestchen=[k.name for k in g.kaestchen], zeilen_2k=2 ** len(g.vars), zeilen_init=getattr(g, 'init_zeilen_zahl', None), zeilen_ende=(len(g.zeilen) if g.zeilen is not None else None)) for g in gr],
               kanten=[(a, b, list(S)) for a, b, S in kanten], kosten=dict(gruppen=len(gr), summe_zeilen_init=init_summe, summe_zeilen_ende=sum(len(g.zeilen) for g in gr if g.zeilen is not None), groesste_gruppe_vars=(max(len(g.vars) for g in gr) if gr else None)),
               FOLGERUNGEN=folgerungen, kanten_projektionen_gleich=kanten_gleich, SPEICHERUNG=speicherung, KONTROLLE=kontrolle, pruefung=pruef, bestanden=all(pruef.values()),
               zeiten_s=dict(T1_gruppierung_aufspaltung_init=round(t1 - t0, 6), T2_austausch=round(t2 - t1, 6), T3_kantenpruefung=round(t3 - t2, 6), T4_kontrolle=round(t4 - t3, 6)),
               maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), rlimit_as=resource.getrlimit(resource.RLIMIT_AS), python=sys.version.split()[0],
               abhaengigkeiten={m: dict(pfad=sys.modules[m].__file__, sha256=hashlib.sha256(open(sys.modules[m].__file__, 'rb').read()).hexdigest()) for m in ('gruppen', 'ereignis', 'stern')})
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_BEGRENZT_%s_%s.json' % (FALL, STAND)), 'w'), indent=1, default=str)
    print('%s %-5s %-11s | Gruppen %d (max %s Var) Aufspaltung %s | gestrichen %d fest %s | Entn/Semij/Proj/Nachr %d/%d/%d/%d | echt %d Verbund %s zu_viel %d fehlend %d | %s' % (
        FALL, STAND, status[:11], len(gr), erg['kosten']['groesste_gruppe_vars'], aufsp, z['gestrichen'], fest, z['bearbeitungen'], ZAEHL['semijoins'], z['nachrichten_geprueft'], z['nachrichten_gesendet'],
        len(wahr), speicherung['verbund_zaehlung'], kontrolle['zu_viel_gesamt'], kontrolle['fehlend_in_gruppen'], 'BESTANDEN' if erg['bestanden'] else 'FEHLER'))
    sys.exit(0 if erg['bestanden'] else 3)
if __name__ == '__main__': fall()
