#!/usr/bin/env python3
"""KOMPAKTE PAAR-KOMPOSITION (Fable, 2026-10-22, Option c). Gleiche Beziehungen, gleiche Radius-1-Pfade, gleiche Reihenfolge wie
ziffern_sha.e4 – nur die Berechnung der Komposition, der Domaenenprojektion aus Paaren und der Paarpruefung je Tupel ist kompakter:
  Paar (x<y) bleibt eine Maske ueber (vx*gy + vy). Vorberechnete Tabellen je Groessenpaar (gx,gy): ROWS[maske] = Zeilenmasken (vx -> Menge vy),
  COLS[maske] = Spaltenmasken (vy -> Menge vx), TRANS[maske] = transponierte Maske. Komposition R(x,z) = R(x,y) o R(y,z) ueber dom[y]:
  res_zeile[vx] = OR ueber vy in zeile_xy[vx] & dom[y] von zeile_yz[vy] & dom[z]  (hoechstens gx*gy Ganzzahl-Operationen statt gx*gz*gy Aufrufe).
  Paargrenze VOR jeder Einfuegung; bei Erreichen sofort 'OPEN_PAARGRENZE' (U5, keine weiteren Kompositionen).
Soundness unveraendert: nur Schnitte/Projektionen. Gleichheit mit ziffern_sha.e4 wird in pruef_komposition.py gemessen (Status, Domaenen, alle Paare)."""
from ziffern import Netz, TABELLEN, GROESSEN
from ziffern_sha import e3, grundpaare, _vorbereiten, _kandidaten, _einwert

_TAB = {}
def tabellen(gx, gy):
    k = (gx, gy)
    if k in _TAB: return _TAB[k]
    n = 1 << (gx * gy); rows = [None] * n; cols = [None] * n; trans = [None] * n
    for m in range(n):
        r = [0] * gx; c = [0] * gy; t = 0
        for vx in range(gx):
            for vy in range(gy):
                if m >> (vx * gy + vy) & 1: r[vx] |= 1 << vy; c[vy] |= 1 << vx; t |= 1 << (vy * gx + vx)
        rows[m] = tuple(r); cols[m] = tuple(c); trans[m] = t
    _TAB[k] = (rows, cols, trans); return _TAB[k]

def komponiere(zx, zy, dx, dy, dz, gx, gy, gz):
    """Maske von R(x,z) = R(x,y) o R(y,z) ueber dom: zx/zy Zeilenmasken (None = universell), dx/dy/dz Domaenen."""
    m = 0
    for vx in range(gx):
        if not dx >> vx & 1: continue
        vys = dy if zx is None else (zx[vx] & dy)
        if zy is None: r = dz if vys else 0
        else:
            r = 0
            for vy in range(gy):
                if vys >> vy & 1: r |= zy[vy]
            r &= dz
        m |= r << (vx * gz)
    return m

def e4(N, dom=None, max_runden=200, max_paare=20000, pruef=None, nachpruefung=False, start_paare=None):
    """start_paare (optional, 2026-10-22): zusaetzlich vorgegebene Paarmasken (z. B. Auffrischer vom Kettenende, kette.py).
    Sie werden nach dem Anlegen der Grundpaare hineingeschnitten bzw. angelegt; alles Weitere unveraendert. Nur Schnitte -> sound.
    start_paare=None ergibt exakt das bisherige Verhalten."""
    st, dom, _, info0 = e3(N, dom, max_runden=max_runden, pruef=pruef)
    if st != 'FIXPUNKT': return st, dom, {}, dict(runden=info0['runden'], tupelops=info0['tupelops'], paare=0, phase='E3-Vorpropagation')
    gr = N.groesse
    paare, bez_mit, pst = grundpaare(N, dom, max_paare)
    if pst != 'OK': return pst, dom, paare, dict(runden=0, tupelops=info0['tupelops'], paare=len(paare), phase='Grundpaare')
    if start_paare:
        for (x, y), m in start_paare.items():
            alt = paare.get((x, y))
            if alt is None:
                if len(paare) >= max_paare: return 'OPEN_PAARGRENZE', dom, paare, dict(runden=0, tupelops=info0['tupelops'], paare=len(paare), phase='Auffrischer anlegen')
                paare[(x, y)] = m
            else: paare[(x, y)] = alt & m
            if paare[(x, y)] == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=0, tupelops=info0['tupelops'], paare=len(paare), phase='Auffrischer')
    basis_nb = {}
    for (x, y) in paare: basis_nb.setdefault(x, set()).add(y); basis_nb.setdefault(y, set()).add(x)
    bez = []
    for vs, typ, tab, dup in _vorbereiten(N):
        if sum(1 for v in dict.fromkeys(vs) if not _einwert(dom[v])) < 2: continue
        pp = []   # (i, j, key, flip): Bitindex im Paar = tup[i]*g_j+tup[j] (flip=False) bzw. tup[j]*g_i+tup[i] (flip=True)
        for i in range(len(vs)):
            for j in range(i + 1, len(vs)):
                a, b = vs[i], vs[j]
                if a == b: continue
                key = (a, b) if a < b else (b, a)
                if key in paare: pp.append((i, j, key, a > b, gr[a], gr[b]))
        bez.append((vs, typ, tab, dup, pp))
    def zeilen(x, y):
        """Zeilenmasken von R(x,y) (vx -> Menge vy), None wenn universell."""
        if x < y:
            m = paare.get((x, y)); return None if m is None else tabellen(gr[x], gr[y])[0][m]
        m = paare.get((y, x)); return None if m is None else tabellen(gr[y], gr[x])[1][m]
    def setze(x, y, maske_xy):
        if x > y: maske_xy = tabellen(gr[x], gr[y])[2][maske_xy]; x, y = y, x
        alt = paare.get((x, y))
        if alt is None and len(paare) >= max_paare: return None
        neu = maske_xy if alt is None else (alt & maske_xy)
        if neu != alt: paare[(x, y)] = neu; return True
        return False
    runden = 0; ops = info0['tupelops']; status = None
    while True:
        runden += 1; geaendert = False
        folge = bez if runden % 2 == 1 else bez[::-1]
        for vs, typ, tab, dup, pp in folge:
            n = len(vs); neu_dom = [0] * n; neu_paar = {}; d = [dom[v] for v in vs]
            for tup in _kandidaten(typ, tab, d):
                ops += 1
                ok = True
                for i in range(n):
                    if not (d[i] >> tup[i]) & 1: ok = False; break
                if not ok: continue
                if dup and any(tup[i] != tup[j] for i, j in dup): continue
                for i, j, key, flip, gi, gj in pp:
                    m = paare.get(key)
                    if m is None: continue
                    idx = (tup[j] * gi + tup[i]) if flip else (tup[i] * gj + tup[j])
                    if not (m >> idx) & 1: ok = False; break
                if not ok: continue
                for i in range(n): neu_dom[i] |= 1 << tup[i]
                for i, j, key, flip, gi, gj in pp:
                    idx = (tup[j] * gi + tup[i]) if flip else (tup[i] * gj + tup[j])
                    neu_paar[key] = neu_paar.get(key, 0) | (1 << idx)
            for i in range(n):
                v = vs[i]; m = dom[v] & neu_dom[i]
                if m != dom[v]:
                    dom[v] = m; geaendert = True
                    if m == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare), leer=N.name[v])
            for key, m in neu_paar.items():
                alt = paare.get(key)
                if alt is None: continue
                neu = alt & m
                if neu != alt:
                    paare[key] = neu; geaendert = True
                    if neu == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
            if pruef is not None and ops % 100000 < len(tab): pruef(runden, ops)
        for y, ns in basis_nb.items():
            ns = sorted(ns); dy = dom[y]; gy = gr[y]
            for ia in range(len(ns)):
                x = ns[ia]; zx = zeilen(x, y); gx = gr[x]; dx = dom[x]
                for ib in range(ia + 1, len(ns)):
                    z = ns[ib]; gz = gr[z]; dz = dom[z]; zy = zeilen(y, z)
                    ops += gx; m = komponiere(zx, zy, dx, dy, dz, gx, gy, gz)
                    s = setze(x, z, m)
                    if s is None: return 'OPEN_PAARGRENZE', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare), phase='Komposition')
                    if s: geaendert = True
                    if paare.get((x, z) if x < z else (z, x)) == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
            if pruef is not None: pruef(runden, ops)
        for (x, y), m in paare.items():
            rows, cols, _ = tabellen(gr[x], gr[y]); dx = dom[x]; dy = dom[y]; mx = 0; my = 0
            for vx in range(gr[x]):
                if dx >> vx & 1 and rows[m][vx] & dy: mx |= 1 << vx
            for vy in range(gr[y]):
                if dy >> vy & 1 and cols[m][vy] & dx: my |= 1 << vy
            if mx != dx: dom[x] = mx; geaendert = True
            if my != dy: dom[y] = my; geaendert = True
            if mx == 0 or my == 0: return 'WIDERSPRUCH', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
        if not geaendert:
            info = dict(runden=runden, tupelops=ops, paare=len(paare), bez_mit_paaren=len(bez))
            if nachpruefung:   # abschliessender voller E3-Durchlauf ueber ALLE Beziehungen (auch die nach E3 ausgefilterten): darf nichts aendern
                st2, dom2, _, inf2 = e3(N, dom); info['nachpruefung_e3'] = dict(status=st2, geaendert=(dom2 != dom), runden=inf2['runden'])
            return (status or 'FIXPUNKT'), dom, paare, info
        if runden >= max_runden: return 'OFFEN', dom, paare, dict(runden=runden, tupelops=ops, paare=len(paare))
