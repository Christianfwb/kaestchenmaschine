"""STERN AN N3 (GO GHOST_AN_FABLE_GO_STERN_N3_20261024). Eigenstaendig; importiert nur stern.py (den kleinen Stern-Pruefstand), keine D6/Pruefstand/N5-Module.
STATISCHE NETZDEFINITION N3 (aus pruefstand.py abgelesen, unveraendert):
  A = (x0,x1,x2) + (x3,x4,x5)  Summe A = 5 (Bits LSB zuerst: sA0=1, sA1=0, sA2=1), Ausgangsuebertrag cA
  B = (x0,x1,x6) + (x7,x8,x9)  Summe B = 6 (sB0=0, sB1=1, sB2=1), Ausgangsuebertrag cB
  Kopplung: cA XOR cB = 0 (cA = cB). x0, x1 in beiden Additionen. 10 freie Bits x0..x9.
  Ripple-Addierer: Stufe i: x_i + y_i + cin_i = s_i + 2 cout_i, cin_0 = 0, cout_i = cin_(i+1).
KAESTCHEN (Relationen, Summenbits als feste Zielwerte eingesetzt; Hilfsvariablen = Uebertraege a1, a2, cA, b1, b2, cB):
  A0 (x0,x3,a1):        x0 + x3 = 1 + 2 a1          B0 (x0,x7,b1):        x0 + x7 = 0 + 2 b1
  A1 (x1,x4,a1,a2):     x1 + x4 + a1 = 0 + 2 a2     B1 (x1,x8,b1,b2):     x1 + x8 + b1 = 1 + 2 b2
  A2 (x2,x5,a2,cA):     x2 + x5 + a2 = 1 + 2 cA     B2 (x6,x9,b2,cB):     x6 + x9 + b2 = 1 + 2 cB
  KOP (cA,cB):          cA = cB
JOIN-GRUPPEN, VORAB nach Struktur festgelegt (gemeinsame Eingaenge bzw. gekoppelte Uebertraege), Reihenfolge fest, kein Blick auf Ergebnisse:
  G1 = {A0, B0}        (teilen x0)                  -> Variablen x0,x3,a1,x7,b1          (5)
  G2 = {A1, B1}        (teilen x1; a1,b1 aus G1)    -> x1,x4,a1,a2,x8,b1,b2             (7)
  G3 = {A2, B2, KOP}   (gekoppelte Uebertraege)     -> x2,x5,a2,cA,x6,x9,b2,cB          (8)  = Grenze 8 Variablen
  Nach den Joins: G1–G2 teilen (a1,b1), G2–G3 teilen (a2,b2): eine Kette -> Austausch ueber diese Schnittmengen.
ERWARTUNGEN (automatisch geprueft; FEHLER -> Stopp):
  E1 Speicherung exakt auf x0..x9 (Hilfsvariablen existenziell ausgeblendet): weder verloren noch hinzugefuegt – ohne und mit Join.
  E2 Soundness: 'zugelassen laut Mitte' enthaelt JEDE echte Loesung (ohne und mit Join).
  E3 Kein WIDERSPRUCH (das Netz ist laut frueherer Messung loesbar; die 12 sind eine zu pruefende Erwartung E4, kein Orakel fuer die Ableitung).
  E4 Kontrolle: Zahl der echten Loesungen auf x0..x9 = 12 (fruehere Messung; Abweichung -> FEHLER, da dann die Netzdefinition nicht uebereinstimmt).
  H  Hypothese (berichtet, kein FEHLER): mit Joins liegt eine Kette vor -> 'zugelassen laut Mitte' == echte Loesungen.
Grenzen: 8 Variablen / 256 Zeilen je Relation (auch Zwischenrelationen); 120 s / 400 MiB ueberwacht (stern_lauf-Muster)."""
import sys, os, json, time, itertools, resource
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'stern'))
import stern
from stern import Kaestchen, Mitte, Grenze

FREI = ['x%d' % i for i in range(10)]; HILF = ['a1', 'a2', 'cA', 'b1', 'b2', 'cB']
def stufe(name, x, y, cin, s_fest, cout):
    """Relation x + y + cin = s_fest + 2*cout ueber (x, y, [cin], cout); cin=None heisst Konstante 0."""
    vs = [x, y] + ([cin] if cin else []) + [cout]; rows = set()
    for w in itertools.product((0, 1), repeat=len(vs)):
        d = dict(zip(vs, w)); c = d[cin] if cin else 0
        if d[x] + d[y] + c == s_fest + 2 * d[cout]: rows.add(w)
    return Kaestchen(name, vs, rows)
def n3_kaestchen():
    return [stufe('A0', 'x0', 'x3', None, 1, 'a1'), stufe('A1', 'x1', 'x4', 'a1', 0, 'a2'), stufe('A2', 'x2', 'x5', 'a2', 1, 'cA'),
            stufe('B0', 'x0', 'x7', None, 0, 'b1'), stufe('B1', 'x1', 'x8', 'b1', 1, 'b2'), stufe('B2', 'x6', 'x9', 'b2', 1, 'cB'),
            Kaestchen('KOP', ('cA', 'cB'), {(0, 0), (1, 1)})]
def n3u_kaestchen():
    """N3u (aus pruefstand.py abgelesen): wie N3 (Summen 5 und 6), aber cA = 1, cB = 1 (Zielwerte) und x2 XOR x6 = 1. Fruehere Messung: 0 Loesungen (Erwartung E4u)."""
    return [stufe('A0', 'x0', 'x3', None, 1, 'a1'), stufe('A1', 'x1', 'x4', 'a1', 0, 'a2'), stufe('A2', 'x2', 'x5', 'a2', 1, 'cA'),
            stufe('B0', 'x0', 'x7', None, 0, 'b1'), stufe('B1', 'x1', 'x8', 'b1', 1, 'b2'), stufe('B2', 'x6', 'x9', 'b2', 1, 'cB'),
            Kaestchen('KA', ('cA',), {(1,)}), Kaestchen('KB', ('cB',), {(1,)}), Kaestchen('UNG', ('x2', 'x6'), {(0, 1), (1, 0)})]
JOINS = [(['A0', 'B0'], 'JOIN_G1'), (['A1', 'B1'], 'JOIN_G2'), (['A2', 'B2', 'KOP'], 'JOIN_G3')]
# N3u: DIESELBE Strategie (Gruppen an geteilten Eingaengen x0, x1; dritte Gruppe = die beiden Endstufen samt allem, was ihre Uebertraege bzw. x2/x6 bindet):
JOINS_U = [(['A0', 'B0'], 'JOIN_G1'), (['A1', 'B1'], 'JOIN_G2'), (['A2', 'B2', 'KA', 'KB', 'UNG'], 'JOIN_G3')]
NETZE = {'N3': (n3_kaestchen, JOINS, 12, True), 'N3u': (n3u_kaestchen, JOINS_U, 0, False)}   # (Bau, Joins, erwartete echte Loesungen, loesbar?)

def loesungen_projiziert(kaestchen, frei, hilf):
    """Alle Belegungen (frei + hilf) gegen alle Kaestchen; Rueckgabe: Menge der Belegungen der FREIEN Variablen (Hilfsvariablen existenziell)."""
    alle = frei + hilf; out = set(); geprueft = 0
    for w in itertools.product((0, 1), repeat=len(alle)):
        b = dict(zip(alle, w)); geprueft += 1
        if all(tuple(b[v] for v in k.vars) in k.zeilen for k in kaestchen): out.add(w[:len(frei)])
    return out, geprueft
def zugelassen_laut_mitte(m, frei):
    """Belegungen der FREIEN Variablen, vereinbar mit dem, was die Mitte haelt: Domaenen, Schnittmengen-Relationen M_S (projiziert auf freie Variablen, existenziell ueber
    Hilfsvariablen), Join-Gruppen (ebenso projiziert). Nicht-Join-Kaestchen gehen nur ueber Projektionen/Domaenen ein."""
    if m.widerspruch: return set()
    dom = {v: set() for v in frei}
    for k in m.k:
        for i, v in enumerate(k.vars):
            if v in dom: dom[v] |= {z[i] for z in k.zeilen}
    rel = []   # (freie Variablen der Relation, Menge erlaubter Teilbelegungen)
    for S, M in m.M.items():
        fv = [v for v in S if v in frei]
        if fv: idx = [S.index(v) for v in fv]; rel.append((fv, {tuple(z[i] for i in idx) for z in M}))
    for g in m.k:
        if g.name.startswith('JOIN'):
            fv = [v for v in g.vars if v in frei]
            if fv: idx = [g.vars.index(v) for v in fv]; rel.append((fv, {tuple(z[i] for i in idx) for z in g.zeilen}))
    erl = set()
    for w in itertools.product((0, 1), repeat=len(frei)):
        b = dict(zip(frei, w))
        if any(b[v] not in dom[v] for v in frei): continue
        if any(tuple(b[v] for v in fv) not in R for fv, R in rel): continue
        erl.add(w)
    return erl

def zugelassen_laut_mitte_existenziell(m, frei, hilf):
    """Wie zugelassen_laut_mitte, aber ALLE von der Mitte gehaltenen Relationen (Domaenen, M_S, Join-Gruppen) werden ueber frei + hilf gemeinsam geprueft und erst
    danach auf die freien Variablen projiziert (Hilfsvariablen existenziell). Misst, was die Mitte als GANZES ueber die Eingaenge weiss, einschliesslich der
    Kopplung der Gruppen ueber Hilfsvariablen. Weiterhin ohne die Nicht-Join-Kaestchen selbst."""
    if m.widerspruch: return set()
    alle = frei + hilf; dom = {v: set() for v in alle}
    for k in m.k:
        for i, v in enumerate(k.vars): dom[v] |= {z[i] for z in k.zeilen}
    rel = [(list(S), set(M)) for S, M in m.M.items()] + [(list(g.vars), set(g.zeilen)) for g in m.k if g.name.startswith('JOIN')]
    out = set()
    for w in itertools.product((0, 1), repeat=len(alle)):
        b = dict(zip(alle, w))
        if any(b[v] not in dom[v] for v in alle): continue
        if any(tuple(b[v] for v in vs) not in R for vs, R in rel): continue
        out.add(w[:len(frei)])
    return out

if __name__ == '__main__':
    NETZ = sys.argv[1] if len(sys.argv) > 1 else 'N3'; bau, JOINS, ERW_LOES, LOESBAR = NETZE[NETZ]
    t_start = time.perf_counter(); K = bau(); original = [k.kopie() for k in K]
    doku = {k.name: dict(variablen=k.vars, zeilen=sorted(k.zeilen)) for k in K}
    prot = dict(netz='%s (statisch nachgebildet)' % NETZ, kaestchen=doku, joins_vorab=JOINS, grenzen=dict(max_vars=stern.MAX_VARS, max_zeilen=stern.MAX_ZEILEN))
    # ---------- ABLEITUNG A: nur Austausch ----------
    t = time.perf_counter(); mA = Mitte(K).austausch(); tA = time.perf_counter() - t
    ablA = dict(takte=mA.takte, widerspruch=mA.widerspruch, protokoll=mA.protokoll, schnittmengen=[list(S) for S in mA.schnitt], mitte_relationen={str(S): sorted(M) for S, M in mA.M.items()},
                feste=mA.feste(), kaestchen_zeilen={k.name: len(k.zeilen) for k in mA.k}, zeit_s=round(tA, 5))
    # ---------- ABLEITUNG B: vorab festgelegte Joins + Austausch ----------
    t = time.perf_counter(); mB = Mitte(K); statusB = None
    try:
        for namen, jn in JOINS: mB.join_gruppe(namen, jn)
        if not mB.widerspruch: mB.austausch()
        statusB = 'WIDERSPRUCH' if mB.widerspruch else 'FIXPUNKT'
    except Grenze as g: statusB = 'OFFEN (%s)' % g
    tB = time.perf_counter() - t
    ablB = dict(status=statusB, takte=mB.takte, protokoll=mB.protokoll, joins=mB.joins, schnittmengen_nach_join=[list(S) for S in mB.schnitt], mitte_relationen={str(S): sorted(M) for S, M in mB.M.items()},
                feste=mB.feste(), gruppen={k.name: dict(variablen=k.vars, zeilen=len(k.zeilen)) for k in mB.k}, zeit_s=round(tB, 5),
                groesste_relation=dict(variablen=max(len(k.vars) for k in mB.k), zeilen=max(len(k.zeilen) for k in mB.k)), kandidaten_gesamt=sum(j['kandidaten_gesamt'] for j in mB.joins))
    # Folgerungen festgehalten. Erst jetzt Zaehlungen.
    t = time.perf_counter(); zugA = zugelassen_laut_mitte(mA, FREI); zugB = zugelassen_laut_mitte(mB, FREI) if not statusB.startswith('OFFEN') else None
    zugA_ex = zugelassen_laut_mitte_existenziell(mA, FREI, HILF); zugB_ex = zugelassen_laut_mitte_existenziell(mB, FREI, HILF) if zugB is not None else None; t_zaehl = time.perf_counter() - t
    # ---------- KONTROLLE am unveraenderten Original ----------
    t = time.perf_counter(); wahr, gepr = loesungen_projiziert(original, FREI, HILF); t_kon = time.perf_counter() - t
    # ---------- SPEICHERUNG ----------
    t = time.perf_counter(); gespA, _ = loesungen_projiziert(mA.k, FREI, HILF); gespB = loesungen_projiziert(mB.k, FREI, HILF)[0] if zugB is not None else None; t_sp = time.perf_counter() - t
    sp = dict(original=len(wahr), ohne_join=dict(gespeichert=len(gespA), verloren=len(wahr - gespA), hinzugefuegt=len(gespA - wahr)),
              mit_join=(dict(gespeichert=len(gespB), verloren=len(wahr - gespB), hinzugefuegt=len(gespB - wahr)) if gespB is not None else None))
    # ---------- Erwartungen ----------
    E = dict(E1_speicherung_ohne=(sp['ohne_join']['verloren'] == 0 and sp['ohne_join']['hinzugefuegt'] == 0), E1_speicherung_mit=(gespB is None or (sp['mit_join']['verloren'] == 0 and sp['mit_join']['hinzugefuegt'] == 0)),
             E2_sound_ohne=wahr <= zugA, E2_sound_mit=(zugB is None or wahr <= zugB), E3_status_plausibel=((not mA.widerspruch and statusB != 'WIDERSPRUCH') if LOESBAR else True), E4_kontrolle_erwartet=(len(wahr) == ERW_LOES),
             E5_keine_scheinentscheidung=(True if LOESBAR else not (statusB == 'FIXPUNKT' and zugB_ex is not None and len(zugB_ex) == 1)))   # unloesbar: nie 'genau eine Loesung' behaupten
    H = dict(H_kette_exakt_gruppenweise=(zugB is not None and zugB == wahr), H_kette_exakt_existenziell=(zugB_ex is not None and zugB_ex == wahr))
    E['E2_sound_ohne_ex'] = wahr <= zugA_ex; E['E2_sound_mit_ex'] = (zugB_ex is None or wahr <= zugB_ex)
    ok = all(E.values()); maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    prot.update(ableitung_ohne_join=ablA, ableitung_mit_join=ablB, zugelassen_laut_mitte=dict(gruppenweise_projiziert=dict(ohne_join=len(zugA), mit_join=(len(zugB) if zugB is not None else None)), existenziell_ueber_hilfsvariablen=dict(ohne_join=len(zugA_ex), mit_join=(len(zugB_ex) if zugB_ex is not None else None)), zeit_s=round(t_zaehl, 5)),
                kontrolle=dict(echte_loesungen_x0_bis_x9=len(wahr), belegungen_geprueft=gepr, zeit_s=round(t_kon, 4)), speicherung=dict(sp, zeit_s=round(t_sp, 4)),
                erwartungen=E, hypothese=H, alle_erwartungen_bestanden=ok, maxrss_mib_kind=round(maxrss, 1), zeit_gesamt_s=round(time.perf_counter() - t_start, 3))
    json.dump(prot, open(os.path.join(HERE, 'ERGEBNIS_STERN_%s.json' % NETZ), 'w'), indent=1, default=str)
    print('%s statisch | Kontrolle:' % NETZ + ' %d echte Loesungen auf x0..x9 (65536 Belegungen geprueft, %.3f s)' % (len(wahr), t_kon))
    print('OHNE Join : %s, %d Takte, Schnittmengen %s | feste %s | Kaestchen-Zeilen %s | zugelassen laut Mitte %d | Speicherung verloren/hinzu %d/%d | %.5f s' % (
        'WIDERSPRUCH' if mA.widerspruch else 'FIXPUNKT', mA.takte, ablA['schnittmengen'], ablA['feste'], ablA['kaestchen_zeilen'], len(zugA), sp['ohne_join']['verloren'], sp['ohne_join']['hinzugefuegt'], tA))
    print('MIT Joins : %s, %d Takte nach Join | Gruppen %s | Schnittmengen %s | feste %s | zugelassen laut Mitte %s | Speicherung %s | groesste Relation %s | Kandidaten %d | %.5f s' % (
        statusB, mB.takte, {k: v['zeilen'] for k, v in ablB['gruppen'].items()}, ablB['schnittmengen_nach_join'], ablB['feste'], (len(zugB) if zugB is not None else '-'), sp['mit_join'], ablB['groesste_relation'], ablB['kandidaten_gesamt'], tB))
    print('zugelassen laut Mitte, EXISTENZIELL ueber Hilfsvariablen: ohne Join %d | mit Joins %s' % (len(zugA_ex), (len(zugB_ex) if zugB_ex is not None else '-')))
    print('Erwartungen:', E, '| Hypothese:', H, '| Spitze RSS (ru_maxrss) %.1f MiB' % maxrss)
    print('ALLE ERWARTUNGEN BESTANDEN' if ok else 'FEHLER – STOPP'); sys.exit(0 if ok else 3)
