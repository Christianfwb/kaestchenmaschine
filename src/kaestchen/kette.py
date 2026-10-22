#!/usr/bin/env python3
"""AUFFRISCH-KAESTCHEN AM KETTENENDE (Christians Idee, Fable 2026-10-22).
Beobachtung: Paare verbinden nur Nachbarn. Laeuft eine duenne Kette von Kaestchen (jedes nur mit dem vorigen und dem naechsten
verbunden) ueber viele Glieder, verduennt sich die Herkunft Glied um Glied: am Ende weiss niemand mehr, dass Anfang und Ende
derselben Kette entstammen. Radius-1-Schliessung frischt nur EIN Glied weit auf.
Auffrischer: Am ENDE einer Kette ein Kaestchen anlegen, das direkt an den ANFANG der Kette zurueckbindet – die Beziehung
Anfang<->Ende, gewonnen durch Verkettung aller Zwischenglieder (Transfermatrix ueber den Paargraphen).
  Kette   = Pfad im Paargraphen, dessen INNERE Knoten Grad 2 haben (nur Vorgaenger und Nachfolger) und unbestimmt sind.
  Anfang/Ende = die beiden Endknoten des Pfades (Grad != 2, also Verzweigungs- oder Randkaestchen).
  Auffrischen = Komposition der Paarmasken entlang des Pfades (ueber die aktuellen Domaenen der inneren Knoten),
                Schnitt in das Paar (Anfang, Ende); fehlt es, wird es angelegt.
Das ist sound (nur Schnitte/Projektionen) und NICHT dasselbe wie Radius 1: Radius 1 komponiert nur ueber EINEN gemeinsamen
Nachbarn, der Auffrischer ueber die ganze Kette. Er ist auch nicht die volle Schliessung: nur duenne Pfade, Laenge begrenzt."""
from ziffern_komp import tabellen, komponiere

def paargraph(paare, gr):
    nb = {}
    for (x, y) in paare: nb.setdefault(x, set()).add(y); nb.setdefault(y, set()).add(x)
    return nb

def benannte_ketten(N, dom):
    """Die RECHENKETTEN des Netzes, nach Namen bestimmt (nicht nach Nachbarschaftsgrad – im Paargraphen hat kein Kaestchen Grad 2,
    weil jede Addition fuenf Kaestchen verbindet). Geliefert werden Pfade [Anfang, Glied, ..., Ende]:
      Uebertragskette je Addition:  x_0 -> c_1 -> c_2 -> ... -> c_D   (Glieder = Uebertraege, Anfang = niedrigste Eingangsziffer)
      Zielkette:                    le_0 -> le_1 -> ... -> le_128
    Innere Glieder duerfen weitere Nachbarn haben; entscheidend ist, dass die Kette LANG ist und Radius 1 nur ein Glied weit auffrischt."""
    import re
    ketten = []
    # Uebertragsketten: Variablen 'c<j>_<name>' gehoeren zur Addition <name>, Reihenfolge nach j
    add = {}
    for v, nm in enumerate(N.name):
        m = re.match(r'c(\d+)_(.+)$', nm)
        if m: add.setdefault(m.group(2), {})[int(m.group(1))] = v
    for nm, cs in add.items():
        idx = sorted(cs)
        if len(idx) < 3: continue
        ketten.append(('uebertrag_' + nm, [cs[i] for i in idx]))
    # Zielkette
    le = {}
    for v, nm in enumerate(N.name):
        m = re.match(r'le_(\d+)$', nm)
        if m: le[int(m.group(1))] = v
    if len(le) >= 3: ketten.append(('ziel', [le[i] for i in sorted(le)]))
    return ketten

def ketten(paare, dom, nb, max_laenge=12):
    """Maximale Pfade, deren innere Knoten im Paargraphen Grad 2 haben und noch unbestimmt sind.
    Liefert Liste von Pfaden [v0, v1, ..., vk] mit k >= 2 (mindestens ein inneres Glied) und v0 != vk."""
    innen = {v for v, ns in nb.items() if len(ns) == 2 and dom[v] & (dom[v] - 1)}
    gesehen = set(); out = []
    for v in innen:
        if v in gesehen: continue
        # von v aus in beide Richtungen laufen, solange innere Knoten
        kette = [v]; gesehen.add(v)
        for richtung in (0, 1):
            vor = kette[0] if richtung else kette[-1]
            prev = kette[1] if (richtung and len(kette) > 1) else (kette[-2] if (not richtung and len(kette) > 1) else None)
            while True:
                kand = [w for w in nb[vor] if w != prev]
                if not kand: break
                w = kand[0]
                if w in kette: break                       # Ring: abbrechen
                if richtung: kette.insert(0, w)
                else: kette.append(w)
                if w not in innen: break                   # Endknoten erreicht
                gesehen.add(w); prev, vor = vor, w
                if len(kette) > max_laenge + 2: break
        if len(kette) >= 3 and kette[0] != kette[-1]: out.append(kette)
    return out

def zeilen_von(paare, gr, x, y):
    """Zeilenmasken von R(x,y) (vx -> Menge vy) aus dem Paardict; None = universell."""
    if x < y:
        m = paare.get((x, y)); return None if m is None else tabellen(gr[x], gr[y])[0][m]
    m = paare.get((y, x)); return None if m is None else tabellen(gr[y], gr[x])[1][m]

def kompose_kette(kette, paare, dom, gr):
    """Verkettet die Paarmasken entlang des Pfades: liefert Maske ueber (Anfang, Ende) oder None (universell/leer nicht moeglich)."""
    S = kette[0]; gS = gr[S]
    # Zustand: fuer jeden Wert von S die Menge der an der aktuellen Position erreichbaren Werte
    akt = [dom[kette[1]] if zeilen_von(paare, gr, S, kette[1]) is None else (zeilen_von(paare, gr, S, kette[1])[vS] & dom[kette[1]]) for vS in range(gS)]
    for i in range(1, len(kette) - 1):
        a, b = kette[i], kette[i + 1]; za = zeilen_von(paare, gr, a, b); ga, gb = gr[a], gr[b]; db = dom[b]
        neu = []
        for vS in range(gS):
            m = akt[vS]; r = 0
            if za is None: r = db if m else 0
            else:
                for va in range(ga):
                    if m >> va & 1: r |= za[va]
                r &= db
            neu.append(r)
        akt = neu
    E = kette[-1]; gE = gr[E]
    maske = 0
    for vS in range(gS):
        if dom[S] >> vS & 1: maske |= (akt[vS] & dom[E]) << (vS * gE)
    return maske

def auffrischen_benannt(N, paare, dom, max_neu=400000, teilketten=True):
    """Auffrisch-Kaestchen am ENDE jeder Rechenkette: Beziehung (Anfang, Ende) durch Verkettung aller Glieder.
    teilketten=True: zusaetzlich jedes Teilstueck (Anfang, Glied k) ab Laenge 2 – damit die Herkunft unterwegs mehrfach aufgefrischt wird.
    Nur Schnitte -> sound. Liefert (anzahl_geaendert, statistik)."""
    gr = N.groesse; ks = benannte_ketten(N, dom); geaendert = 0; neu = 0; leer = None; betrachtet = 0
    for nm, kette in ks:
        for ende in (range(2, len(kette)) if teilketten else [len(kette) - 1]):
            teil = kette[:ende + 1]; S, E = teil[0], teil[-1]
            if S == E: continue
            betrachtet += 1
            m = kompose_kette(teil, paare, dom, gr)
            if S > E: m = tabellen(gr[S], gr[E])[2][m]; x, y = E, S
            else: x, y = S, E
            alt = paare.get((x, y)); voll = (1 << (gr[x] * gr[y])) - 1
            if alt is None:
                if m == voll or len(paare) >= max_neu: continue
                paare[(x, y)] = m; neu += 1; geaendert += 1
            else:
                n = alt & m
                if n != alt: paare[(x, y)] = n; geaendert += 1
            if paare[(x, y)] == 0: leer = (x, y)
    return geaendert, dict(rechenketten=len(ks), betrachtete_teilketten=betrachtet, geaenderte_paare=geaendert, neue_paare=neu, leeres_paar=leer,
                           laengen=sorted({len(k) for _, k in ks}))

def auffrischen(paare, dom, gr, max_laenge=12, max_neu=200000):
    """Legt/schneidet fuer jede Kette das Paar (Anfang, Ende). Liefert (geaendert, statistik). Nur Schnitte -> sound."""
    nb = paargraph(paare, gr); ks = ketten(paare, dom, nb, max_laenge)
    geaendert = 0; neu = 0; leer = None; laengen = {}
    for kette in ks:
        S, E = kette[0], kette[-1]
        if S == E: continue
        laengen[len(kette) - 2] = laengen.get(len(kette) - 2, 0) + 1
        m = kompose_kette(kette, paare, dom, gr)
        if S > E: m = tabellen(gr[S], gr[E])[2][m]; x, y = E, S
        else: x, y = S, E
        alt = paare.get((x, y))
        if alt is None:
            if len(paare) >= max_neu: continue
            voll = (1 << (gr[x] * gr[y])) - 1
            if m == voll: continue
            paare[(x, y)] = m; neu += 1; geaendert += 1
        else:
            n = alt & m
            if n != alt: paare[(x, y)] = n; geaendert += 1
        if paare[(x, y)] == 0: leer = (x, y)
    return geaendert, dict(ketten=len(ks), laengen=laengen, geaenderte_paare=geaendert, neue_paare=neu, leeres_paar=leer)
