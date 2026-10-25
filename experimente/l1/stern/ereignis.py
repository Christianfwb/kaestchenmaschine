"""EREIGNISGESTEUERTER ARBEITSTAKT (GO Christian 2026-10-25 06:59; Entwurf + Ghosts Ergaenzungen 06:58).
Nur N3 und N3u. Gleiche Gruppierung und Ausgangstabellen wie gruppen.py (baue/strukturpruefung/init_zeilen unveraendert importiert).
Verglichen: (R) voller Rundenlauf = zaehlende KOPIE von gruppen.austausch (gleiche Logik, nur Zaehler) gegen (A) Arbeitsliste.
Aufruf: VERFAHREN=R|A FALL=N3|N3u python3 -I ereignis.py  -> ERGEBNIS_EREIGNIS_<FALL>_<VERFAHREN>.json
Speicherung / Ableitung / Kontrolle getrennt; Kontrolle (Vollzaehlung am Original) erst nach der Ableitung, nichts fliesst zurueck.
Bekanntes Schema (AC-3 auf dem Join-Baum), keine Neuheit; gemessen wird nur Aufwand."""
import sys, os, json, time, itertools, resource, hashlib, collections, copy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'stern_n3'))
import gruppen, stern_n3 as S3
VERF = os.environ.get('VERFAHREN', 'A'); FALL = os.environ.get('FALL', 'N3')
MAX_VARS, MAX_ZEILEN = gruppen.MAX_VARS, gruppen.MAX_ZEILEN
class Widerspruch(Exception): pass

def rundenlauf_zaehlend(gruppen_, kanten, prot, z):
    """Identisch zu gruppen.austausch, plus Zaehler z (Bearbeitungen = Semijoin-Aufrufe je Gruppe, Nachrichten geprueft = Projektionen, gesendet = Kantenrelationen gesetzt)."""
    byname = {g.name: g for g in gruppen_}; kantenrel = {}; takte = 0
    while True:
        takte += 1; gestrichen = 0
        for richtung in ('hoch', 'runter'):
            folge = kanten if richtung == 'hoch' else list(reversed(kanten))
            for a, b, S in folge:
                ga, gb = byname[a], byname[b]; z['nachrichten_geprueft'] += 2; M = ga.proj(S) & gb.proj(S); z['nachrichten_gesendet'] += 1; kantenrel[(a, b)] = M
                if not M: prot.append(dict(takt=takte, kante=(a, b), ereignis='WIDERSPRUCH: Kantenrelation leer')); z['takte'] = takte; return True, takte, kantenrel
                for g in (ga, gb):
                    z['bearbeitungen'] += 1; s = g.semijoin(S, M); z['gestrichen'] += s
                    if len(g.zeilen) > MAX_ZEILEN: raise gruppen.Offen('%s > %d Zeilen' % (g.name, MAX_ZEILEN))
                    if s: gestrichen += s; prot.append(dict(takt=takte, kante=(a, b), gruppe=g.name, gestrichen=s, verbleibend=len(g.zeilen)))
        if gestrichen == 0: z['takte'] = takte; return False, takte, kantenrel

NIE = None   # "noch nie gesendet" – unterscheidbar von einer gesendeten (auch leeren) Projektion
def arbeitsliste(gruppen_, kanten, prot, z):
    """(A): FIFO + Mengen-Markierung; Nachrichten je gerichteter Kante als frozenset; Empfang = Schnitt (Semijoin) mit der vorhandenen Tabelle, nie Ersatz."""
    t_aufbau = time.perf_counter()
    byname = {g.name: g for g in gruppen_}; nachbarn = collections.defaultdict(list)          # name -> [(nachbar, S)]
    for a, b, S in kanten: nachbarn[a].append((b, S)); nachbarn[b].append((a, S))
    N = {(a, b): NIE for a, b, S in kanten}; N.update({(b, a): NIE for a, b, S in kanten})    # gesendeter Stand je Richtung
    neu_eingang = {g.name: set() for g in gruppen_}                                             # Absender mit neuer Nachricht seit letzter Bearbeitung
    schlange = collections.deque(g.name for g in gruppen_); drin = set(schlange)                # alle einmal, Eliminationsreihenfolge
    for g in gruppen_: neu_eingang[g.name] = set()                                              # erste Bearbeitung: es gibt noch keine Nachrichten
    z['aufbau_s'] = round(time.perf_counter() - t_aufbau, 6); z['max_schlange'] = len(schlange)
    while schlange:
        if len(drin) != len(schlange): raise gruppen.Strukturfehler('Arbeitsliste: Doppeleintrag')   # E4 waehrend des Laufs
        name = schlange.popleft(); drin.discard(name); g = byname[name]; z['bearbeitungen'] += 1
        for h in sorted(neu_eingang[name]):                                                     # a) Empfang: Schnitt mit vorhandener Tabelle
            S = dict(nachbarn[name])[h]; M = N[(h, name)]; assert M is not NIE
            s = g.semijoin(S, M); z['gestrichen'] += s
            if s: prot.append(dict(bearbeitung=z['bearbeitungen'], gruppe=name, von=h, gestrichen=s, verbleibend=len(g.zeilen)))
            if not g.zeilen: prot.append(dict(bearbeitung=z['bearbeitungen'], gruppe=name, ereignis='WIDERSPRUCH: Gruppe leer')); return True
        neu_eingang[name] = set()
        for h, S in nachbarn[name]:                                                             # b) Senden: nur bei tatsaechlicher Aenderung
            P = frozenset(g.proj(S)); z['nachrichten_geprueft'] += 1
            if N[(name, h)] is NIE or N[(name, h)] != P:
                N[(name, h)] = P; z['nachrichten_gesendet'] += 1; neu_eingang[h].add(name)
                if h not in drin: schlange.append(h); drin.add(h); z['max_schlange'] = max(z['max_schlange'], len(schlange))
    return False

def fall():
    bau, _, erw_loes, loesbar = S3.NETZE[FALL]; kaest = bau(); frei, hilf = S3.FREI, S3.HILF
    original = [k.kopie() for k in kaest]; prot = []; z = dict(bearbeitungen=0, nachrichten_geprueft=0, nachrichten_gesendet=0, gestrichen=0)
    t0 = time.perf_counter(); gr, kanten, ordnung, buckets = gruppen.baue(kaest); gruppen.strukturpruefung(gr, kanten, kaest)
    leer = [g.name for g in gr if not g.init_zeilen()]
    ausgang = hashlib.sha256(json.dumps([(g.name, g.vars, sorted(g.zeilen)) for g in gr] + [list(k) for k in kanten], default=list).encode()).hexdigest()   # E1
    t_init = time.perf_counter() - t0; status = None; t1 = time.perf_counter()
    try:
        if leer: status = 'WIDERSPRUCH'; prot.append(dict(ereignis='WIDERSPRUCH: Gruppe beim Initialisieren leer', gruppen=leer))
        else:
            w = rundenlauf_zaehlend(gr, kanten, prot, z)[0] if VERF == 'R' else arbeitsliste(gr, kanten, prot, z); status = 'WIDERSPRUCH' if w else 'FIXPUNKT'
    except gruppen.Offen as o: status = 'OFFEN (%s)' % o
    except gruppen.Strukturfehler as f: status = 'FEHLER (%s)' % f
    t_abl = time.perf_counter() - t1
    # E6 unabhaengig: auf jeder Baumkante stimmen die Projektionen beider Gruppen ueberein (nur sinnvoll bei FIXPUNKT)
    byname = {g.name: g for g in gr}; kanten_gleich = None
    if status == 'FIXPUNKT': kanten_gleich = {('%s-%s' % (a, b)): (byname[a].proj(S) == byname[b].proj(S)) for a, b, S in kanten}
    # Kontrolle danach, am Original; nichts zurueck
    t2 = time.perf_counter(); wahr = gruppen.loesungen(original, frei, hilf)
    gesp = set() if status == 'WIDERSPRUCH' else (gruppen.loesungen_gruppen(gr, frei, hilf) if status == 'FIXPUNKT' else None)
    gk = None
    if status == 'FIXPUNKT':
        alle = frei + hilf; voll = [w for w in itertools.product((0, 1), repeat=len(alle)) if all(tuple(dict(zip(alle, w))[v] for v in k.vars) in k.zeilen for k in original)]
        gk = {g.name: (set(g.zeilen) == {tuple(dict(zip(alle, w))[v] for v in g.vars) for w in voll}) for g in gr}
    t_kon = time.perf_counter() - t2
    end = {g.name: sorted(g.zeilen) for g in gr}
    pruef = dict(status=(status == ('FIXPUNKT' if loesbar else 'WIDERSPRUCH')), kontrolle=(len(wahr) == erw_loes), speicherung=(gesp is None or (gesp == wahr)),
                 global_konsistent=(gk is None or all(gk.values())), E6_kanten_projektionen_gleich=(kanten_gleich is None or all(kanten_gleich.values())), kein_fehler=(not status.startswith('FEHLER')))
    erg = dict(fall=FALL, verfahren=('Rundenlauf (zaehlende Kopie von gruppen.austausch)' if VERF == 'R' else 'Arbeitsliste'), status=status, ausgang_pruefsumme=ausgang,
               gruppen=len(gr), kanten=len(kanten), ordnung=ordnung, zaehler=z, protokoll=prot, endrelationen=end, endrelationen_pruefsumme=hashlib.sha256(json.dumps(end, sort_keys=True).encode()).hexdigest(),
               kanten_projektionen_gleich=kanten_gleich, speicherung=dict(original=len(wahr), gespeichert=(len(gesp) if gesp is not None else None)), global_konsistent_je_gruppe=gk,
               zeiten_s=dict(gruppierung_und_init=round(t_init, 5), ableitung=round(t_abl, 5), kontrolle=round(t_kon, 5)), pruefung=pruef, bestanden=all(pruef.values()),
               maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1), rlimit_as=resource.getrlimit(resource.RLIMIT_AS), python=sys.version.split()[0],
               abhaengigkeiten={m: dict(pfad=sys.modules[m].__file__, sha256=hashlib.sha256(open(sys.modules[m].__file__, 'rb').read()).hexdigest()) for m in ('gruppen', 'stern', 'stern_n3')})
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_EREIGNIS_%s_%s.json' % (FALL, VERF)), 'w'), indent=1, default=str)
    print('%-4s %-12s %-11s | Bearb %3d | Nachr gepr/ges %3d/%3d | gestrichen %3d | Takte/maxSchlange %s | Zeiten init/abl/kon %s | E6 %s | %s' % (
        FALL, erg['verfahren'][:12], status[:11], z['bearbeitungen'], z['nachrichten_geprueft'], z['nachrichten_gesendet'], z['gestrichen'], z.get('takte', z.get('max_schlange')), erg['zeiten_s'],
        pruef['E6_kanten_projektionen_gleich'], 'BESTANDEN' if erg['bestanden'] else 'FEHLER'))
    sys.exit(0 if erg['bestanden'] else 3)
if __name__ == '__main__': fall()
