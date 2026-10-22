#!/usr/bin/env python3
"""TESTKOPIE der Ableitungsregeln E3/E4 fuer das grosse SHA256d-Ziffernnetz (Fable, 2026-10-22, Stufe 0).
ziffern.py bleibt UNVERAENDERT (Netz, Tabellen, Groessen werden importiert). Unterschiede zu ziffern.e3/ziffern.e4, alle benannt:
  U1  e3: Richtungswechsel je Runde (vorwaerts, rueckwaerts ueber die Beziehungsliste) wie e1_lauf – gleiche Regel (GAC), nur Reihenfolge;
      Tupelpruefung ohne wiederholte all()-Generatoren (Laufzeit); Wiederholungs-Pruefung nur fuer Beziehungen mit doppelter Variable.
  U2  Fortschritt/Abbruch: optionaler Rueckruf pruef(runden, ops) nach jeder Beziehungsgruppe (Elternprozess ueberwacht zusaetzlich extern).
  U3  Grundpaare: Paare werden NUR zwischen Variablen angelegt, die nach der E3-Vorpropagation unbestimmt sind (Domaene > 1 Wert); nie
      Konstanten-/Selbstpaare; Beziehungen mit < 2 unbestimmten Variablen bekommen keine Paare. Paargrenze wird VOR jeder Einfuegung
      geprueft (auch beim Anlegen der Grundpaare) -> 'OPEN_PAARGRENZE'.
  U5  Paargrenze in der Komposition erreicht -> sofort 'OPEN_PAARGRENZE' zurueck (keine weiteren Kompositionen; Ghost-Review 2026-10-22).
  U4  e4: Komposition (Radius 1) nur ueber gemeinsame Nachbarn im Grundpaar-Graphen; abgeleitete Paare werden geschnitten, nicht komponiert.
      Fehlende Paare universell; Originalbeziehungen (Tupeltabellen) und E3 bleiben vollstaendig aktiv. Alles bleibt sound (nur Schnitte).
Korrektheit: jede Operation entfernt nur Werte/Paare, die in keiner Gesamtloesung vorkommen (Projektion/Schnitt) – wie ziffern.py."""
from ziffern import Netz, TABELLEN, GROESSEN, ALLE

def _vorbereiten(N):
    """Je Beziehung: (vs, tabelle, doppel) – doppel = Liste gleicher Positionen (meist leer)."""
    out = []
    for typ, vs in N.bez:
        dup = [(i, j) for i in range(len(vs)) for j in range(i + 1, len(vs)) if vs[i] == vs[j]]
        out.append((vs, TABELLEN[typ], dup))
    return out

_INDEX = {}
def _kandidaten(typ, tab, d):
    """U1: Tupel der Tabelle, deren Werte an den EINWERTIGEN Positionen passen (Index je (typ, Positionsmaske)); Rest wird gefiltert.
    Ergebnis identisch mit der vollen Tabellenpruefung, nur schneller."""
    maske = 0; schl = []
    for i, m in enumerate(d):
        if m & (m - 1) == 0: maske |= 1 << i; schl.append(m.bit_length() - 1)
    if not maske: return tab
    ix = _INDEX.get((typ, maske))
    if ix is None:
        ix = {}
        pos = [i for i in range(len(d)) if maske >> i & 1]
        for tup in tab: ix.setdefault(tuple(tup[i] for i in pos), []).append(tup)
        _INDEX[(typ, maske)] = ix
    return ix.get(tuple(schl), ())

def _vorbereiten(N):
    out = []
    for typ, vs in N.bez:
        dup = [(i, j) for i in range(len(vs)) for j in range(i + 1, len(vs)) if vs[i] == vs[j]]
        out.append((vs, typ, TABELLEN[typ], dup))
    return out

def e3(N, dom=None, max_runden=200, pruef=None, nur_eine_runde=False):
    """GAC ueber Tupeltabellen. dom: Startdomaenen (Kopie von N.dom, wenn None). Liefert (status, dom, {}, info)."""
    dom = list(N.dom) if dom is None else list(dom)
    if any(m == 0 for m in dom): return 'WIDERSPRUCH', dom, {}, dict(runden=0, tupelops=0)
    bez = _vorbereiten(N); runden = 0; ops = 0
    while True:
        runden += 1; geaendert = False
        folge = bez if runden % 2 == 1 else bez[::-1]
        for vs, typ, tab, dup in folge:
            n = len(vs); neu = [0] * n; d = [dom[v] for v in vs]
            for tup in _kandidaten(typ, tab, d):
                ops += 1
                ok = True
                for i in range(n):
                    if not (d[i] >> tup[i]) & 1: ok = False; break
                if not ok: continue
                if dup and any(tup[i] != tup[j] for i, j in dup): continue
                for i in range(n): neu[i] |= 1 << tup[i]
            for i in range(n):
                v = vs[i]; m = dom[v] & neu[i]
                if m != dom[v]:
                    dom[v] = m; geaendert = True
                    if m == 0: return 'WIDERSPRUCH', dom, {}, dict(runden=runden, tupelops=ops, leer=N.name[v])
            if pruef is not None and ops % 100000 < len(tab): pruef(runden, ops)
        if nur_eine_runde: return 'EINE_RUNDE', dom, {}, dict(runden=runden, tupelops=ops)
        if not geaendert: return 'FIXPUNKT', dom, {}, dict(runden=runden, tupelops=ops)
        if runden >= max_runden: return 'OFFEN', dom, {}, dict(runden=runden, tupelops=ops)

def _paarmaske(gx, gy): return (1 << (gx * gy)) - 1
def _einwert(m): return m & (m - 1) == 0

def grundpaare(N, dom, max_paare):
    """U3: ungeordnete Paare (x<y) unbestimmter Variablen innerhalb je einer Beziehung. Liefert (paare, anzahl_bez_mit_paaren, status)."""
    gr = N.groesse; paare = {}; bez_mit = 0
    for typ, vs in N.bez:
        frei = [v for v in dict.fromkeys(vs) if not _einwert(dom[v])]
        if len(frei) < 2: continue
        bez_mit += 1
        for i in range(len(frei)):
            for j in range(i + 1, len(frei)):
                x, y = (frei[i], frei[j]) if frei[i] < frei[j] else (frei[j], frei[i])
                if (x, y) not in paare:
                    if len(paare) >= max_paare: return paare, bez_mit, 'OPEN_PAARGRENZE'
                    paare[(x, y)] = _paarmaske(gr[x], gr[y])
    return paare, bez_mit, 'OK'

def e4(N, dom=None, max_runden=200, max_paare=20000, pruef=None):
    """E3 + Paarbeziehungen (Radius 1, U3/U4). Liefert (status, dom, paare, info)."""
    st, dom, _, info0 = e3(N, dom, max_runden=max_runden, pruef=pruef)
    if st != 'FIXPUNKT': return st, dom, {}, dict(runden=info0['runden'], tupelops=info0['tupelops'], paare=0, phase='E3-Vorpropagation')
    gr = N.groesse
    paare, bez_mit, pst = grundpaare(N, dom, max_paare)
    if pst != 'OK': return pst, dom, paare, dict(runden=0, tupelops=info0['tupelops'], paare=len(paare), phase='Grundpaare')
    basis_nb = {}
    for (x, y) in paare: basis_nb.setdefault(x, set()).add(y); basis_nb.setdefault(y, set()).add(x)
    bez = [(vs, typ, tab, dup) for vs, typ, tab, dup in _vorbereiten(N) if sum(1 for v in dict.fromkeys(vs) if not _einwert(dom[v])) >= 2]
    def key(x, y): return (x, y) if x < y else (y, x)
    def setze(x, y, maske_xy):
        if x == y: return False
        if x > y:
            m = 0
            for vx in range(gr[x]):
                for vy in range(gr[y]):
                    if maske_xy >> (vx * gr[y] + vy) & 1: m |= 1 << (vy * gr[x] + vx)
            maske_xy = m; x, y = y, x
        alt = paare.get((x, y))
        if alt is None and len(paare) >= max_paare: return None            # Grenze VOR Einfuegung
        neu = maske_xy if alt is None else (alt & maske_xy)
        if neu != alt: paare[(x, y)] = neu; return True
        return False
    def erlaubt(x, y, vx, vy):
        if x == y: return vx == vy
        if x < y:
            m = paare.get((x, y)); return True if m is None else (m >> (vx * gr[y] + vy)) & 1
        m = paare.get((y, x)); return True if m is None else (m >> (vy * gr[x] + vx)) & 1
    runden = 0; ops = info0['tupelops']; status = None
    while True:
        runden += 1; geaendert = False
        folge = bez if runden % 2 == 1 else bez[::-1]
        for vs, typ, tab, dup in folge:
            n = len(vs); neu_dom = [0] * n; neu_paar = {}; d = [dom[v] for v in vs]
            for tup in _kandidaten(typ, tab, d):
                ops += 1
                ok = True
                for i in range(n):
                    if not (d[i] >> tup[i]) & 1: ok = False; break
                if not ok: continue
                if dup and any(tup[i] != tup[j] for i, j in dup): continue
                if not all(erlaubt(vs[i], vs[j], tup[i], tup[j]) for i in range(n) for j in range(i + 1, n)): continue
                for i in range(n): neu_dom[i] |= 1 << tup[i]
                for i in range(n):
                    for j in range(i + 1, n):
                        if vs[i] != vs[j]: neu_paar[(i, j)] = neu_paar.get((i, j), 0) | (1 << (tup[i] * gr[vs[j]] + tup[j]))
            for i in range(n):
                v = vs[i]; m = dom[v] & neu_dom[i]
                if m != dom[v]:
                    dom[v] = m; geaendert = True
                    if m == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare), leer=N.name[v])
            for (i, j), m in neu_paar.items():
                if key(vs[i], vs[j]) not in paare: continue                  # nur Grundpaare/abgeleitete Paare pflegen, keine neuen aus Tupeln
                r = setze(vs[i], vs[j], m)
                if r: geaendert = True
                if paare.get(key(vs[i], vs[j])) == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
            if pruef is not None and ops % 100000 < len(tab): pruef(runden, ops)
        for y, ns in basis_nb.items():
            ns = sorted(ns)
            for ia in range(len(ns)):
                for ib in range(ia + 1, len(ns)):
                    x, z = ns[ia], ns[ib]
                    m = 0
                    for vx in range(gr[x]):
                        if not dom[x] >> vx & 1: continue
                        for vz in range(gr[z]):
                            if not dom[z] >> vz & 1: continue
                            ops += 1
                            if any(dom[y] >> vy & 1 and erlaubt(x, y, vx, vy) and erlaubt(y, z, vy, vz) for vy in range(gr[y])): m |= 1 << (vx * gr[z] + vz)
                    r = setze(x, z, m)
                    if r is None: return 'OPEN_PAARGRENZE', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare), phase='Komposition')   # U5
                    if r: geaendert = True
                    if paare.get(key(x, z)) == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
            if pruef is not None: pruef(runden, ops)
        for (x, y), m in paare.items():
            mx = 0; my = 0
            for vx in range(gr[x]):
                if not dom[x] >> vx & 1: continue
                for vy in range(gr[y]):
                    if m >> (vx * gr[y] + vy) & 1 and dom[y] >> vy & 1: mx |= 1 << vx; my |= 1 << vy
            if (dom[x] & mx) != dom[x]: dom[x] &= mx; geaendert = True
            if (dom[y] & my) != dom[y]: dom[y] &= my; geaendert = True
            if dom[x] == 0 or dom[y] == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
        if not geaendert: return (status or 'FIXPUNKT'), dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare), bez_mit_paaren=len(bez))
        if runden >= max_runden: return 'OFFEN', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
