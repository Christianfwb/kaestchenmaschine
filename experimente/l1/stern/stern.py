"""STERN-PRUEFSTAND (eigenstaendig, offline; GO 2026-10-24 18:56). Keine Einbindung in D6/N4/N5, keine Importe aus dem uebrigen Labor.
Kaestchen halten erlaubte Anschlusskombinationen (Relationen als Zeilenmengen). Die Mitte verbindet sie ueber gemeinsame Variablen (Schnittmengen):
  Austausch-Takt: Kaestchen -> Mitte: Projektion auf jede Schnittmenge S;  Mitte: M_S = Durchschnitt;  Mitte -> Kaestchen: Semijoin (Zeilen streichen).
  Join (nur VORAB festgelegt, keine automatische Kreissuche): mehrere Kaestchen zu EINER Relation ueber die Vereinigung ihrer Variablen (Join-Baum-Idee;
  bekannte relationale Logik, keine Neuheit). Grenzen: 8 Variablen und 256 Zeilen je Relation -> sonst OFFEN.
Drei getrennt ausgewiesene Ergebnisse je Fall:
  SPEICHERUNG: Loesungsmenge der (nach Austausch/Join) gespeicherten Kaestchen ueber den Originalvariablen == Loesungsmenge des unveraenderten Originals
               (weder verloren noch hinzugefuegt; Hilfsvariablen gibt es hier keine, Joins fuehren keine ein).
  ABLEITUNG:   was Austausch und Join tatsaechlich erkannt haben – Takte, gestrichene Zeilen, Mitte-Relationen, feste Variablen, Widerspruch – protokolliert VOR
               jeder Kontrollzaehlung. 'Zugelassen laut Mitte' = Belegungen der Originalvariablen, die mit allem vereinbar sind, was die MITTE haelt
               (Domaenen, Schnittmengen-Relationen, Join-Gruppen) – NICHT mit den Kaestchen selbst.
  KONTROLLE:   unabhaengige vollstaendige Zaehlung am unveraenderten Original; nichts davon geht an die Ableitung zurueck.
Erwartungen je Fall sind vorab festgelegt und werden automatisch geprueft: falsch -> FEHLER und Stopp (Exit 3)."""
import sys, os, json, time, itertools, copy, resource
HERE = os.path.dirname(os.path.abspath(__file__))
MAX_VARS, MAX_ZEILEN = 8, 256

class Kaestchen:
    def __init__(self, name, vars_, zeilen):
        self.name = name; self.vars = tuple(vars_); self.zeilen = set(tuple(z) for z in zeilen)
    def projektion(self, S):
        idx = [self.vars.index(v) for v in S]; return {tuple(z[i] for i in idx) for z in self.zeilen}
    def semijoin(self, S, M):
        idx = [self.vars.index(v) for v in S]; vorher = len(self.zeilen)
        self.zeilen = {z for z in self.zeilen if tuple(z[i] for i in idx) in M}; return vorher - len(self.zeilen)
    def kopie(self): return Kaestchen(self.name, self.vars, set(self.zeilen))

class Grenze(Exception): pass

def join(k1, k2, name):
    vars_ = list(k1.vars) + [v for v in k2.vars if v not in k1.vars]
    if len(vars_) > MAX_VARS: raise Grenze('Join %s: %d Variablen > %d' % (name, len(vars_), MAX_VARS))
    gem = [v for v in k2.vars if v in k1.vars]; i1 = [k1.vars.index(v) for v in gem]; i2 = [k2.vars.index(v) for v in gem]; rest2 = [i for i, v in enumerate(k2.vars) if v not in k1.vars]
    out = set(); kandidaten = 0
    for z1 in k1.zeilen:
        for z2 in k2.zeilen:
            kandidaten += 1
            if all(z1[a] == z2[b] for a, b in zip(i1, i2)): out.add(z1 + tuple(z2[i] for i in rest2))
            if len(out) > MAX_ZEILEN: raise Grenze('Join %s: > %d Zeilen' % (name, MAX_ZEILEN))
    return Kaestchen(name, vars_, out), kandidaten

class Mitte:
    def __init__(self, kaestchen):
        self.k = [k.kopie() for k in kaestchen]; self.M = {}; self.protokoll = []; self.joins = []; self.takte = 0; self.widerspruch = False
        self._schnittmengen()
    def _schnittmengen(self):
        S = set()
        for a, b in itertools.combinations(range(len(self.k)), 2):
            s = tuple(v for v in self.k[a].vars if v in self.k[b].vars)
            if s: S.add(s)
        self.schnitt = sorted(S)
    def takt(self):
        self.takte += 1; gestrichen = 0
        for S in self.schnitt:
            beteiligt = [k for k in self.k if all(v in k.vars for v in S)]
            M = None
            for k in beteiligt:
                p = k.projektion(S); M = p if M is None else (M & p)
            self.M[S] = M
            if not M: self.widerspruch = True; self.protokoll.append(dict(takt=self.takte, schnittmenge=S, ereignis='WIDERSPRUCH: Durchschnitt leer')); return 0
            for k in beteiligt:
                g = k.semijoin(S, M)
                if g: gestrichen += g; self.protokoll.append(dict(takt=self.takte, schnittmenge=S, kaestchen=k.name, gestrichen=g, verbleibend=len(k.zeilen)))
        return gestrichen
    def austausch(self):
        while True:
            g = self.takt()
            if self.widerspruch or g == 0: break
        return self
    def join_gruppe(self, namen, name):
        teile = [k for k in self.k if k.name in namen]; rest = [k for k in self.k if k.name not in namen]
        g = teile[0]; kand = 0; zwischen = []
        for t in teile[1:]:
            g, c = join(g, t, name); kand += c; zwischen.append(dict(variablen=len(g.vars), zeilen=len(g.zeilen), kandidaten=c))
        self.k = rest + [g]; self._schnittmengen(); self.joins.append(dict(name=name, aus=namen, variablen=g.vars, zeilen=len(g.zeilen), zwischen=zwischen, kandidaten_gesamt=kand))
        self.protokoll.append(dict(ereignis='JOIN', name=name, aus=namen, variablen=list(g.vars), zeilen=len(g.zeilen), zwischenrelationen=zwischen))
        if not g.zeilen: self.widerspruch = True; self.protokoll.append(dict(ereignis='WIDERSPRUCH: Join-Relation leer', name=name))
        return self
    def feste(self):
        f = {}
        for k in self.k:
            for i, v in enumerate(k.vars):
                w = {z[i] for z in k.zeilen}
                if len(w) == 1: f[v] = w.pop()
        return f
    def zugelassen_laut_mitte(self, vars_):
        """Belegungen der Originalvariablen, vereinbar mit allem, was die MITTE haelt: Domaenen (aus Projektionen), Schnittmengen-Relationen M_S, Join-Gruppen.
        Kaestchen, die NICHT aus einem Join stammen, gehen NUR ueber ihre Projektionen auf Schnittmengen/Domaenen ein."""
        if self.widerspruch: return set()
        dom = {v: set() for v in vars_}
        for k in self.k:
            for i, v in enumerate(k.vars): dom[v] |= {z[i] for z in k.zeilen}
        gruppen = [k for k in self.k if k.name.startswith('JOIN')]
        erl = set()
        for w in itertools.product((0, 1), repeat=len(vars_)):
            b = dict(zip(vars_, w))
            if any(b[v] not in dom[v] for v in vars_): continue
            if any(tuple(b[v] for v in S) not in M for S, M in self.M.items() if all(v in b for v in S)): continue
            if any(tuple(b[v] for v in g.vars) not in g.zeilen for g in gruppen if all(v in b for v in g.vars)): continue
            erl.add(w)
        return erl

def loesungen(kaestchen, vars_):
    """Vollstaendige Zaehlung: alle Belegungen der Variablen gegen ALLE Kaestchen (Orakel bzw. Speicherungs-Vergleich)."""
    out = set()
    for w in itertools.product((0, 1), repeat=len(vars_)):
        b = dict(zip(vars_, w))
        if all(tuple(b[v] for v in k.vars) in k.zeilen for k in kaestchen): out.add(w)
    return out

def fall(name, kaestchen, joins, erwartung):
    """erwartung: dict(status_ohne_join, status_mit_join (oder None), feste_mit (dict) optional, zugelassen_mitte_ohne, zugelassen_mitte_mit (oder None))"""
    vars_ = sorted({v for k in kaestchen for v in k.vars}); t0 = time.perf_counter()
    original = [k.kopie() for k in kaestchen]
    # ---- ABLEITUNG (vor jeder Kontrollzaehlung) ----
    m = Mitte(kaestchen).austausch(); t_abl_ohne = time.perf_counter() - t0                     # ZEIT 1: Ableitung ohne Join (nur Austausch)
    abl = dict(takte=m.takte, widerspruch_ohne_join=m.widerspruch, protokoll_ohne_join=list(m.protokoll), mitte_relationen={str(S): sorted(M) for S, M in m.M.items()},
               feste_ohne_join=m.feste(), kaestchen_zeilen_ohne_join={k.name: len(k.zeilen) for k in m.k})
    status_ohne = 'WIDERSPRUCH' if m.widerspruch else 'FIXPUNKT'
    m2 = None; status_mit = None; zug_mit = None; t_abl_mit = None
    if joins:
        t2 = time.perf_counter(); m2 = Mitte([k.kopie() for k in m.k]); m2.protokoll = []; m2.takte = 0
        try:
            for namen, jname in joins: m2.join_gruppe(namen, jname)
            if not m2.widerspruch: m2.austausch()
            status_mit = 'WIDERSPRUCH' if m2.widerspruch else 'FIXPUNKT'
        except Grenze as g: status_mit = 'OFFEN (%s)' % g
        t_abl_mit = time.perf_counter() - t2                                                       # ZEIT 2: Ableitung mit Join (Join + Austausch)
        abl.update(joins=m2.joins, protokoll_mit_join=list(m2.protokoll), feste_mit_join=m2.feste(), kaestchen_zeilen_mit_join={k.name: dict(variablen=k.vars, zeilen=len(k.zeilen)) for k in m2.k})
    # Ableitung ist hier ABGESCHLOSSEN und protokolliert. Erst jetzt Zaehlungen (eigene Zeit), die nichts zurueckgeben.
    t3 = time.perf_counter(); zug_ohne = m.zugelassen_laut_mitte(vars_); abl['zugelassen_laut_mitte_ohne_join'] = len(zug_ohne)
    if m2 is not None:
        zug_mit = m2.zugelassen_laut_mitte(vars_) if not status_mit.startswith('OFFEN') else None; abl['zugelassen_laut_mitte_mit_join'] = (len(zug_mit) if zug_mit is not None else None)
    t_zaehl = time.perf_counter() - t3                                                             # ZEIT 3: Zaehlung 'zugelassen laut Mitte' (kein Teil der Ableitung)
    t_abl = t_abl_ohne
    # ---- KONTROLLE (unabhaengig, am unveraenderten Original; nichts geht zurueck) ----
    t1 = time.perf_counter(); wahr = loesungen(original, vars_); t_kon = time.perf_counter() - t1   # ZEIT 4: Kontrolle am Original
    # ---- SPEICHERUNG: gespeicherte Kaestchen beschreiben dieselbe Loesungsmenge? ----
    t4 = time.perf_counter(); gesp_ohne = loesungen(m.k, vars_) if not m.widerspruch else set()
    gesp_mit = (loesungen(m2.k, vars_) if (m2 is not None and not m2.widerspruch and not status_mit.startswith('OFFEN')) else (set() if (m2 is not None and m2.widerspruch) else None))
    sp = dict(original_loesungen=len(wahr), gespeichert_ohne_join=len(gesp_ohne), verloren_ohne_join=len(wahr - gesp_ohne), hinzugefuegt_ohne_join=len(gesp_ohne - wahr),
              gespeichert_mit_join=(len(gesp_mit) if gesp_mit is not None else None), verloren_mit_join=(len(wahr - gesp_mit) if gesp_mit is not None else None),
              hinzugefuegt_mit_join=(len(gesp_mit - wahr) if gesp_mit is not None else None))
    t_speich = time.perf_counter() - t4                                                            # ZEIT 5: Speicherungsvergleich
    # ---- Erwartungen pruefen ----
    pruef = dict(status_ohne=(status_ohne == erwartung['status_ohne']), status_mit=(status_mit == erwartung.get('status_mit')),
                 zugelassen_ohne=(len(zug_ohne) == erwartung['zugelassen_mitte_ohne']), zugelassen_mit=((len(zug_mit) if zug_mit is not None else None) == erwartung.get('zugelassen_mitte_mit')),
                 speicherung_ohne=(sp['verloren_ohne_join'] == 0 and sp['hinzugefuegt_ohne_join'] == 0), speicherung_mit=(gesp_mit is None or (sp['verloren_mit_join'] == 0 and sp['hinzugefuegt_mit_join'] == 0)),
                 feste=(all(abl.get('feste_mit_join', abl['feste_ohne_join']).get(v) == w for v, w in erwartung.get('feste', {}).items())),
                 kontrolle_unberuehrt=True)
    ok = all(pruef.values())
    groesse = dict(variablen=len(vars_), kaestchen=len(kaestchen), zeilen_gesamt=sum(len(k.zeilen) for k in kaestchen), schnittmengen=len(m.schnitt), mitte_zeilen=sum(len(M) for M in m.M.values()),
                   groesste_relation_vars=max([len(k.vars) for k in (m2.k if m2 else m.k)]), groesste_relation_zeilen=max([len(k.zeilen) for k in (m2.k if m2 else m.k)] + [0]), joins=(abl.get('joins') or []))
    print('%-34s ohne Join: %-11s zugelassen(Mitte) %2d | mit Join: %-11s zugelassen %s | Original %d | Speicherung verloren/hinzu %d/%d%s | groesste Relation %d Var %d Zeilen | %s' % (
        name, status_ohne, len(zug_ohne), status_mit, (len(zug_mit) if zug_mit is not None else '-'), len(wahr), sp['verloren_ohne_join'], sp['hinzugefuegt_ohne_join'],
        ('' if gesp_mit is None else ' (mit %d/%d)' % (sp['verloren_mit_join'], sp['hinzugefuegt_mit_join'])), groesse['groesste_relation_vars'], groesse['groesste_relation_zeilen'], 'BESTANDEN' if ok else 'FEHLER'))
    ergebnis = dict(fall=name, erwartung=erwartung, ableitung=abl, kontrolle=dict(original_loesungen=len(wahr), zeit_s=round(t_kon, 4)), speicherung=sp, groesse=groesse,
                zeiten_s=dict(ableitung_ohne_join=round(t_abl_ohne, 5), ableitung_mit_join=(round(t_abl_mit, 5) if t_abl_mit is not None else None), zaehlung_zugelassen_laut_mitte=round(t_zaehl, 5), kontrolle=round(t_kon, 5), speicherungsvergleich=round(t_speich, 5)),
                pruefung=pruef, bestanden=ok)
    if not ok:
        json.dump(dict(alle_bestanden=False, abgebrochen_bei=name, fall=ergebnis), open(os.path.join(HERE, 'ERGEBNIS_STERN.json'), 'w'), indent=1, default=str)
        print('FEHLER in %s – SOFORTIGER STOPP (keine weiteren Faelle)' % name); sys.exit(3)
    return ergebnis

def faelle():
    GL = lambda a, b, n: Kaestchen(n, (a, b), {(0, 0), (1, 1)}); UG = lambda a, b, n: Kaestchen(n, (a, b), {(0, 1), (1, 0)})
    F = []
    F.append(fall('F1 gleich(a,b) vs ungleich(a,b)', [GL('a', 'b', 'K1'), UG('a', 'b', 'K2')], [], dict(status_ohne='WIDERSPRUCH', zugelassen_mitte_ohne=0)))
    F.append(fall('F2 gleich(a,b) + a=0', [GL('a', 'b', 'K1'), Kaestchen('K2', ('a',), {(0,)})], [], dict(status_ohne='FIXPUNKT', zugelassen_mitte_ohne=1, feste={'a': 0, 'b': 0})))
    F.append(fall('F3 Kette gleich,gleich,ungleich', [GL('a', 'b', 'K1'), GL('b', 'c', 'K2'), UG('c', 'd', 'K3')], [], dict(status_ohne='FIXPUNKT', zugelassen_mitte_ohne=16)))
    F.append(fall('F4 Dreieck ungleich x3', [UG('a', 'b', 'K1'), UG('b', 'c', 'K2'), UG('a', 'c', 'K3')], [(['K1', 'K2', 'K3'], 'JOIN_Dreieck')], dict(status_ohne='FIXPUNKT', zugelassen_mitte_ohne=8, status_mit='WIDERSPRUCH', zugelassen_mitte_mit=0)))
    P_ = Kaestchen('Kp', ('a', 'b', 'p'), {(a, b, a & (1 - b)) for a in (0, 1) for b in (0, 1)}); Q_ = Kaestchen('Kq', ('a', 'b', 'q'), {(a, b, (1 - a) & b) for a in (0, 1) for b in (0, 1)})
    F.append(fall('F5 Spiegelpaar p=a&~b, q=~a&b', [P_, Q_], [(['Kp', 'Kq'], 'JOIN_Spiegel')], dict(status_ohne='FIXPUNKT', zugelassen_mitte_ohne=16, status_mit='FIXPUNKT', zugelassen_mitte_mit=4)))
    return F

if __name__ == '__main__':
    t = time.perf_counter(); F = faelle(); ok = all(f['bestanden'] for f in F)
    maxrss_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0   # Spitze dieses Prozesses, vom Kern gezaehlt (nicht abgetastet)
    json.dump(dict(alle_bestanden=ok, grenzen=dict(max_vars=MAX_VARS, max_zeilen=MAX_ZEILEN), zeit_gesamt_s=round(time.perf_counter() - t, 3), maxrss_mib_kind=round(maxrss_mib, 1), faelle=F), open(os.path.join(HERE, 'ERGEBNIS_STERN.json'), 'w'), indent=1, default=str)
    print('STERN-PRUEFSTAND:', 'alle fuenf Faelle BESTANDEN' if ok else 'FEHLER – STOPP', '| Spitze RSS (ru_maxrss) %.1f MiB' % maxrss_mib); sys.exit(0 if ok else 3)
