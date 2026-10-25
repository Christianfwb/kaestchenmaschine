"""GRUPPENFINDUNG FUER DIE MITTE – Min-Fill-Eliminationsordnung, Bucket-Gruppen, Baum/Wald, Austausch (Entwurf Fassung 3; GO Christian 2026-10-24 20:27).
Eigenstaendig; importiert nur stern.py (Kaestchen) und die Netzdefinitionen aus stern_n3.py. Kein D6/Pruefstand/N4/N5.
S1 Primalgraph  S2 Min-Fill (Gleichstand: kleinster Grad, dann Name)  S3 ALLE Eliminationsgruppen behalten  S4 Baum/Wald (Eltern = Gruppe der fruehesten spaeter
eliminierten Nachbarvariablen)  S5 Kaestchen -> Gruppe seiner fruehesten eliminierten Variablen  S6 Gruppe startet mit allen 2^k Kombinationen, Kaestchen schraenken ein;
leer beim Initialisieren -> WIDERSPRUCH  S7 Strukturpruefungen (FEHLER) getrennt von Groessengrenze (OFFEN)  S8 Austausch entlang der Baumkanten bis Stillstand.
Drei Ergebnisse getrennt: SPEICHERUNG | ABLEITUNG | KONTROLLE. Grenzen: 8 Variablen (Baumweite 7) und 256 Zeilen je Gruppe."""
import sys, os, json, time, itertools, resource
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'stern_n3'))
from stern import Kaestchen
MAX_VARS, MAX_ZEILEN = 8, 256

class Offen(Exception): pass
class Strukturfehler(Exception): pass

def min_fill(kaestchen):
    """S1+S2: Primalgraph und Eliminationsordnung. Liefert Reihenfolge und je Schritt die Nachbarmenge (Bucket)."""
    nachbarn = {}
    for k in kaestchen:
        for v in k.vars:
            nachbarn.setdefault(v, set()).update(w for w in k.vars if w != v)
    rest = set(nachbarn); ordnung = []; buckets = {}
    while rest:
        def fill(v):
            N = [w for w in nachbarn[v] if w in rest]; return sum(1 for a, b in itertools.combinations(N, 2) if b not in nachbarn[a])
        v = min(rest, key=lambda v: (fill(v), len([w for w in nachbarn[v] if w in rest]), v))
        N = sorted(w for w in nachbarn[v] if w in rest)
        for a, b in itertools.combinations(N, 2): nachbarn[a].add(b); nachbarn[b].add(a)
        ordnung.append(v); buckets[v] = N; rest.remove(v)
    return ordnung, buckets

class Gruppe:
    def __init__(self, name, vars_): self.name = name; self.vars = tuple(vars_); self.kaestchen = []; self.zeilen = None; self.eltern = None; self.kinder = []
    def init_zeilen(self):
        """S6: alle 2^k Kombinationen, durch die zugeordneten Kaestchen eingeschraenkt."""
        if len(self.vars) > MAX_VARS: raise Offen('Gruppe %s: %d Variablen > %d (diese Eliminationsreihenfolge ueberschreitet die Grenze)' % (self.name, len(self.vars), MAX_VARS))
        rows = set(itertools.product((0, 1), repeat=len(self.vars)))
        for k in self.kaestchen:
            idx = [self.vars.index(v) for v in k.vars]; rows = {z for z in rows if tuple(z[i] for i in idx) in k.zeilen}
        if len(rows) > MAX_ZEILEN: raise Offen('Gruppe %s: %d Zeilen > %d' % (self.name, len(rows), MAX_ZEILEN))
        self.zeilen = rows; self.init_zeilen_zahl = len(rows); return rows
    def proj(self, S):
        idx = [self.vars.index(v) for v in S]; return {tuple(z[i] for i in idx) for z in self.zeilen}
    def semijoin(self, S, M):
        idx = [self.vars.index(v) for v in S]; vorher = len(self.zeilen); self.zeilen = {z for z in self.zeilen if tuple(z[i] for i in idx) in M}; return vorher - len(self.zeilen)

def baue(kaestchen):
    """S3–S5: Gruppen, Baum/Wald, Zuordnung. Liefert Gruppen (in Eliminationsreihenfolge), Kanten, Ordnung, Buckets."""
    ordnung, buckets = min_fill(kaestchen); pos = {v: i for i, v in enumerate(ordnung)}
    gruppen = {v: Gruppe('G_' + v, [v] + buckets[v]) for v in ordnung}
    kanten = []
    for v in ordnung:                                                      # S4: Eltern = Gruppe der fruehesten spaeter eliminierten Nachbarvariablen
        spaeter = [w for w in buckets[v] if pos[w] > pos[v]]
        if spaeter:
            e = min(spaeter, key=lambda w: pos[w]); gruppen[v].eltern = gruppen[e]; gruppen[e].kinder.append(gruppen[v])
            kanten.append((gruppen[v].name, gruppen[e].name, tuple(sorted(set(gruppen[v].vars) & set(gruppen[e].vars)))))
    for k in kaestchen:                                                    # S5
        v = min(k.vars, key=lambda x: pos[x]); gruppen[v].kaestchen.append(k)
    return [gruppen[v] for v in ordnung], kanten, ordnung, buckets

def strukturpruefung(gruppen, kanten, kaestchen):
    """S7 (Scheitern -> Strukturfehler): (i) jedes Kaestchen genau einmal, (ii) Variablen enthalten, (iii) Running Intersection, (v) Kanten nur bei Schnittmenge, azyklisch."""
    zu = {}
    for g in gruppen:
        for k in g.kaestchen: zu[k.name] = zu.get(k.name, 0) + 1
    if any(zu.get(k.name, 0) != 1 for k in kaestchen): raise Strukturfehler('Kaestchen nicht genau einmal zugeordnet: %s' % zu)
    for g in gruppen:
        for k in g.kaestchen:
            if not set(k.vars) <= set(g.vars): raise Strukturfehler('Kaestchen %s nicht vollstaendig in %s' % (k.name, g.name))
    adj = {g.name: set() for g in gruppen}
    for a, b, S in kanten:
        if not S: raise Strukturfehler('Kante %s-%s ohne Schnittmenge' % (a, b))
        adj[a].add(b); adj[b].add(a)
    # echte Zykluserkennung: Tiefensuche ueber den ungerichteten Gruppengraphen; eine Kante zurueck zu einem schon besuchten Knoten (ausser dem Vorgaenger) = Kreis
    besucht = set()
    for start in adj:
        if start in besucht: continue
        stapel = [(start, None)]; besucht.add(start)
        while stapel:
            x, vor = stapel.pop()
            for y in adj[x]:
                if y == vor: continue
                if y in besucht: raise Strukturfehler('Kreis im Gruppengraphen bei %s-%s' % (x, y))
                besucht.add(y); stapel.append((y, x))
    komponenten = 0; gesehen2 = set()
    for start in adj:
        if start in gesehen2: continue
        komponenten += 1; stapel = [start]; gesehen2.add(start)
        while stapel:
            x = stapel.pop()
            for y in adj[x]:
                if y not in gesehen2: gesehen2.add(y); stapel.append(y)
    wurzeln = len([g for g in gruppen if g.eltern is None])
    if komponenten != wurzeln: raise Strukturfehler('Komponenten %d != Wurzeln %d' % (komponenten, wurzeln))
    if len(kanten) != len(gruppen) - wurzeln: raise Strukturfehler('Kantenzahl passt nicht zu Baum/Wald')
    alle_vars = sorted({v for g in gruppen for v in g.vars})
    for v in alle_vars:                                                    # (iii) Teilbaum je Variable zusammenhaengend
        mit = [g.name for g in gruppen if v in g.vars]; gesehen = {mit[0]}; stapel = [mit[0]]
        while stapel:
            x = stapel.pop()
            for y in adj[x]:
                if y in mit and y not in gesehen: gesehen.add(y); stapel.append(y)
        if gesehen != set(mit): raise Strukturfehler('Running Intersection verletzt fuer %s: %s' % (v, mit))

def austausch(gruppen, kanten, protokoll):
    """S8: Blaetter -> Wurzel -> Blaetter bis Stillstand; Kantenrelationen gehalten. Leer -> WIDERSPRUCH (True)."""
    byname = {g.name: g for g in gruppen}; kantenrel = {}; takte = 0; austausch.aufwand = 0; austausch.zwischen = []
    while True:
        takte += 1; gestrichen = 0
        for richtung in ('hoch', 'runter'):
            folge = kanten if richtung == 'hoch' else list(reversed(kanten))
            for a, b, S in folge:
                ga, gb = byname[a], byname[b]; austausch.aufwand += len(ga.zeilen) + len(gb.zeilen); M = ga.proj(S) & gb.proj(S); kantenrel[(a, b)] = M
                if not M: protokoll.append(dict(takt=takte, kante=(a, b), ereignis='WIDERSPRUCH: Kantenrelation leer')); return True, takte, kantenrel
                for g in (ga, gb):
                    s = g.semijoin(S, M)
                    if s: gestrichen += s; protokoll.append(dict(takt=takte, kante=(a, b), gruppe=g.name, gestrichen=s, verbleibend=len(g.zeilen)))
        austausch.zwischen.append(dict(takt=takte, summe_zeilen=sum(len(g.zeilen) for g in gruppen), max_zeilen=max(len(g.zeilen) for g in gruppen)))
        if gestrichen == 0: return False, takte, kantenrel

def loesungen(kaestchen, frei, hilf):
    alle = frei + hilf; out = set()
    for w in itertools.product((0, 1), repeat=len(alle)):
        b = dict(zip(alle, w))
        if all(tuple(b[v] for v in k.vars) in k.zeilen for k in kaestchen): out.add(w[:len(frei)])
    return out
def loesungen_gruppen(gruppen, frei, hilf):
    alle = frei + hilf; out = set()
    for w in itertools.product((0, 1), repeat=len(alle)):
        b = dict(zip(alle, w))
        if all(tuple(b[v] for v in g.vars) in g.zeilen for g in gruppen): out.add(w[:len(frei)])
    return out

def fall(name, kaestchen, frei, hilf, erw, ausgabe='ERGEBNIS_GRUPPEN.json'):
    """erw: dict(loesungen=int|None, status in {'FIXPUNKT','WIDERSPRUCH', None})"""
    t0 = time.perf_counter(); original = [k.kopie() for k in kaestchen]; protokoll = []; status = None; kantenrel = {}; takte = 0; gruppen = []; kanten = []; austausch.aufwand = 0; austausch.zwischen = []
    try:
        gruppen, kanten, ordnung, buckets = baue(kaestchen); strukturpruefung(gruppen, kanten, kaestchen)
        leer = []
        for g in gruppen:
            if not g.init_zeilen(): leer.append(g.name)
        if leer: status = 'WIDERSPRUCH'; protokoll.append(dict(ereignis='WIDERSPRUCH: Gruppe beim Initialisieren leer', gruppen=leer))
        else:
            w, takte, kantenrel = austausch(gruppen, kanten, protokoll); status = 'WIDERSPRUCH' if w else 'FIXPUNKT'
    except Offen as o: status = 'OFFEN (%s)' % o
    except Strukturfehler as f: status = 'FEHLER (Struktur: %s)' % f
    t_abl = time.perf_counter() - t0
    abl = dict(status=status, ordnung=ordnung if gruppen else None, gruppen=[dict(name=g.name, variablen=g.vars, kaestchen=[k.name for k in g.kaestchen], zeilen_initial=getattr(g, 'init_zeilen_zahl', None), zeilen=(len(g.zeilen) if g.zeilen is not None else None)) for g in gruppen],
               kanten=[(a, b, list(S)) for a, b, S in kanten], takte=takte, kantenrelationen={'%s-%s' % k: sorted(v) for k, v in kantenrel.items()}, protokoll=protokoll,
               groesste_gruppe_vars=(max(len(g.vars) for g in gruppen) if gruppen else None), groesste_gruppe_zeilen=(max((len(g.zeilen) for g in gruppen if g.zeilen is not None), default=None)),
               groesste_gruppe_zeilen_initial=(max((g.init_zeilen_zahl for g in gruppen if hasattr(g, 'init_zeilen_zahl')), default=None)), summe_zeilen_initial=sum(getattr(g, 'init_zeilen_zahl', 0) for g in gruppen), summe_zeilen_ende=sum(len(g.zeilen) for g in gruppen if g.zeilen is not None),
               zwischenstand_je_takt=austausch.zwischen, aufwand_betrachtete_zeilen=austausch.aufwand, zeit_s=round(t_abl, 5))
    # Kontrolle (Original) und Speicherung (Gruppen), beide nach der Ableitung
    t1 = time.perf_counter(); wahr = loesungen(original, frei, hilf); t_kon = time.perf_counter() - t1
    gesp = set() if status == 'WIDERSPRUCH' else (loesungen_gruppen(gruppen, frei, hilf) if status == 'FIXPUNKT' else None)
    sp = dict(original=len(wahr), gespeichert=(len(gesp) if gesp is not None else None), verloren=(len(wahr - gesp) if gesp is not None else None), hinzugefuegt=(len(gesp - wahr) if gesp is not None else None))
    # globale Konsistenz (nachtraeglich): jede gespeicherte Zeile Teil einer Loesung?
    gk = None; gk_je_gruppe = None
    if status == 'FIXPUNKT':
        alle = frei + hilf; voll = [w for w in itertools.product((0, 1), repeat=len(alle)) if all(tuple(dict(zip(alle, w))[v] for v in k.vars) in k.zeilen for k in original)]
        gk_je_gruppe = {}
        for g in gruppen:
            proj = {tuple(dict(zip(alle, w))[v] for v in g.vars) for w in voll}
            gk_je_gruppe[g.name] = dict(gleich=(set(g.zeilen) == proj), zeilen=len(g.zeilen), projektion=len(proj), zu_viel=len(set(g.zeilen) - proj), fehlend=len(proj - set(g.zeilen)))
        gk = all(d['gleich'] for d in gk_je_gruppe.values())
    pruef = dict(status=(erw.get('status') is None or status == erw['status']), kontrolle=(erw.get('loesungen') is None or len(wahr) == erw['loesungen']),
                 speicherung=(gesp is None or (sp['verloren'] == 0 and sp['hinzugefuegt'] == 0)), kein_strukturfehler=(not status.startswith('FEHLER')),
                 keine_scheinentscheidung=(not (len(wahr) == 0 and status == 'FIXPUNKT' and gesp is not None and len(gesp) == 1)),
                 global_konsistent=(gk is None or gk is True))   # verbindlich: bei FIXPUNKT muss jede gespeicherte Zeile Teil einer echten Loesung sein
    ok = all(pruef.values())
    print('%-30s %-11s | Gruppen %d (max %s Var, Zeilen initial %s -> Ende %s) | Kanten %d | Takte %d | Original %d | Speicherung verloren/hinzu %s/%s | global konsistent %s | %s' % (
        name, status[:11], len(gruppen), abl['groesste_gruppe_vars'], abl['groesste_gruppe_zeilen_initial'], abl['groesste_gruppe_zeilen'], len(kanten), takte, len(wahr), sp['verloren'], sp['hinzugefuegt'], gk, 'BESTANDEN' if ok else 'FEHLER'))
    erg = dict(fall=name, erwartung=erw, ableitung=abl, global_konsistent=gk, global_konsistent_je_gruppe=gk_je_gruppe, kontrolle=dict(loesungen=len(wahr), zeit_s=round(t_kon, 5)), speicherung=sp, pruefung=pruef, bestanden=ok)
    if not ok:
        json.dump(dict(alle_bestanden=False, abgebrochen_bei=name, fall=erg), open(os.path.join(HERE, ausgabe), 'w'), indent=1, default=str)
        print('FEHLER in %s – SOFORTIGER STOPP' % name); sys.exit(3)
    return erg

def faelle():
    import stern_n3 as S3
    GL = lambda a, b, n: Kaestchen(n, (a, b), {(0, 0), (1, 1)}); UG = lambda a, b, n: Kaestchen(n, (a, b), {(0, 1), (1, 0)})
    F = []
    F.append(fall('F1 gleich vs ungleich', [GL('a', 'b', 'K1'), UG('a', 'b', 'K2')], ['a', 'b'], [], dict(loesungen=0, status='WIDERSPRUCH')))
    F.append(fall('F2 gleich + a=0', [GL('a', 'b', 'K1'), Kaestchen('K2', ('a',), {(0,)})], ['a', 'b'], [], dict(loesungen=1, status='FIXPUNKT')))
    F.append(fall('F3 Kette', [GL('a', 'b', 'K1'), GL('b', 'c', 'K2'), UG('c', 'd', 'K3')], ['a', 'b', 'c', 'd'], [], dict(loesungen=2, status='FIXPUNKT')))
    F.append(fall('F4 Dreieck', [UG('a', 'b', 'K1'), UG('b', 'c', 'K2'), UG('a', 'c', 'K3')], ['a', 'b', 'c'], [], dict(loesungen=0, status='WIDERSPRUCH')))
    P_ = Kaestchen('Kp', ('a', 'b', 'p'), {(a, b, a & (1 - b)) for a in (0, 1) for b in (0, 1)}); Q_ = Kaestchen('Kq', ('a', 'b', 'q'), {(a, b, (1 - a) & b) for a in (0, 1) for b in (0, 1)})
    F.append(fall('F5 Spiegelpaar', [P_, Q_], ['a', 'b', 'p', 'q'], [], dict(loesungen=4, status='FIXPUNKT')))
    F.append(fall('N3', S3.n3_kaestchen(), S3.FREI, S3.HILF, dict(loesungen=12, status='FIXPUNKT')))
    F.append(fall('N3u', S3.n3u_kaestchen(), S3.FREI, S3.HILF, dict(loesungen=0, status='WIDERSPRUCH')))
    return F

if __name__ == '__main__':
    t = time.perf_counter(); F = faelle(); ok = all(f['bestanden'] for f in F); maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    json.dump(dict(alle_bestanden=ok, grenzen=dict(max_vars=MAX_VARS, max_zeilen=MAX_ZEILEN), zeit_gesamt_s=round(time.perf_counter() - t, 3), maxrss_mib_kind=round(maxrss, 1), faelle=F), open(os.path.join(HERE, 'ERGEBNIS_GRUPPEN.json'), 'w'), indent=1, default=str)
    print('GRUPPENFINDUNG:', 'alle sieben Faelle BESTANDEN' if ok else 'FEHLER', '| Spitze RSS %.1f MiB' % maxrss); sys.exit(0 if ok else 3)
