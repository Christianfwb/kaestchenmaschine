"""AUSDUENNEN – Mini-Test (GO Christian 2026-10-25 18:17; Entwurf V2 + Nachtraege 1/2 + Ghosts Zustimmung).
Frage: Spart sicheres Aussortieren von Nonce-Kandidaten mehr Arbeit, als es kostet?   Referenz K_0 = 256 x H_nonce;  Weg P (alle pruefen) K_P = C_pre + 256 x c_filter + (256 - A) x H_nonce;
Weg E (nur passende erzeugen) K_E = C_pre + E x (c_erzeugen + H_nonce);  Kombination K_EP. Alle Kosten in Gatter-Aequivalenten, C_pre getrennt (s, Regelaufrufe), Umrechnung nur gekennzeichnet.
Netz: pruefstand-Mini-Leine (4-Bit-Woerter, W_i = W_(i-3)), W0 = KOPF fest (aus sha256('AUSDUENNEN F i')), W1+W2 = NONCE (256), Ziel: Bits 0..k-1 von Register a (regs[0]) = 0.
Ableitung: D6-Grundgeruest (D6+R1b+R8c+R8m, kein R9) mit Kopf + Ziel; Zustand eingefroren. Form 1: affines System ueber den 8 Nonce-Bits (wert, alias, xor_gl nach Aufloesung), Gauss-Rang, Konsistenz, Erzeugungskosten aus der reduzierten Stufenform.
Form 2 (LAUF 2, korrigiert): Bedingungen = von D6 ABGELEITETE Tatsachen ueber nonceabhaengige Innenknoten – fester Wert eines Innenknotens (wert), Gleichheit/Gegengleichheit zweier Innenknoten (alias), neue Folgerungen aus der Faltung (rest_wert/rest_gleich). Auswahl VORAB nach nonceabhaengigen Kegelkosten c_rechnen <= s (s = 2, 8, 32), plus die drei billigsten (Kosten, Gatternummer) – eingefroren VOR der Kontrolle.
LAUF 1 (Ordner lauf1/, offengelegt): dort waren als Kandidaten die GATTERBEDINGUNGEN (out = f(in)) genommen worden; die sind bei Vorwaertsauswertung immer erfuellt (Tautologie) und koennen nichts ausschliessen – A = 0 in allen 48 Faellen. Das war ein Konstruktionsfehler meinerseits: Der Ausschluss kann nur aus den aus dem Ziel RUECKWAERTS abgeleiteten Tatsachen kommen (dieser Knoten MUSS 0 sein, diese zwei Knoten MUESSEN gleich sein), nicht aus der Gatterfunktion selbst. Lauf 1 bleibt als Datei erhalten; Form 1 und Sicherheit waren dort schon richtig.
AENDERUNG GEGENUEBER ENTWURF V2 (offengelegt): dort stand 'Knotentiefe <= d (1,2,3)' gemessen von den Eingaengen; im Mini-Netz liegen die Gatter, die Nonce-Bits lesen, bei Tiefe 5-14 (der Nonce kommt erst nach Sigma1/Ch in die Addierer), die Menge waere per Konstruktion leer (ein Testlauf F1/k2/r9 vor dieser Aenderung zeigte 0 Kandidaten, 62 Loesungen – er fliesst nicht in die Auswertung ein). Das Kriterium 'wenige Gatter vom Nonce entfernt' ist als Kegelkosten umgesetzt – weiterhin rein strukturell, vor der Kontrolle.
Kontrolle danach: alle 256 Nonces vorwaerts; Loesungen; Sicherheit (keine Loesung verletzt eine Einschraenkung -> sonst FEHLER); A je Filter; Bilanzen.
Aufruf: KOPF=1..8 K=2|3|4 RUNDEN=6|9 python3 -I ausduennen.py"""
import sys, os, json, time, itertools, resource, hashlib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); L1 = os.path.dirname(HERE); sys.path.insert(0, L1)
import pruefstand as P, d6
KOPF = int(os.environ.get('KOPF', '1')); K = int(os.environ.get('K', '2')); R = int(os.environ.get('RUNDEN', '9')); nm = lambda i: 'v%04d' % i
kopf_wert = int.from_bytes(hashlib.sha256(('AUSDUENNEN F %d' % KOPF).encode()).digest(), 'little') % 16
def sha(b): return hashlib.sha256(b).hexdigest()

def baue():
    N = P.Netz('AUSD r%d k%d F%d' % (R, K, KOPF), 12); x = N.frei; W = [x[0:4], x[4:8], x[8:12]]
    for i in range(3, R): W.append(W[i - 3])
    regs = P._mini_runden(N, W, P._K4, P._IV4, R)
    for b in range(4): N.setze_ziel(x[b], (kopf_wert >> b) & 1)
    for b in range(K): N.setze_ziel(regs[0][b], 0)
    return N, regs

def tiefen(g):
    T = [0] * len(g.nodes)
    for i, nd in enumerate(g.nodes):
        if i < 2 or nd[0] == 'input': T[i] = 0; continue
        T[i] = 1 + max(T[abs(nd[1])] if abs(nd[1]) >= 2 else 0, T[abs(nd[2])] if abs(nd[2]) >= 2 else 0)
    return T
def kegel(g, knoten, nur_nonce_abh, nonce_abh):
    """Gatter im Rueckwaertskegel der Knoten; optional nur die nonceabhaengigen."""
    seen = set(); stapel = list(knoten)
    while stapel:
        i = stapel.pop()
        if i < 2 or i in seen or g.nodes[i][0] == 'input': continue
        if nur_nonce_abh and not nonce_abh[i]: continue
        seen.add(i); stapel.extend(abs(x) for x in g.nodes[i][1:3])
    return seen

def gauss_gf2(rows, n):
    """rows: list of (maske ueber n Bits, konst). Liefert Rang, konsistent, reduzierte Zeilen, Pivots."""
    rows = [[m, c] for m, c in rows if m or c]; piv = []; red = []
    for col in range(n):
        p = next((r for r in rows if (r[0] >> col) & 1 and r not in red), None)
        if p is None: continue
        red.append(p); piv.append(col)
        for r in rows:
            if r is not p and (r[0] >> col) & 1: r[0] ^= p[0]; r[1] ^= p[1]
    konsistent = all(not (r[0] == 0 and r[1] == 1) for r in rows)
    return len(red), konsistent, [(r[0], r[1]) for r in red], piv

def main():
    t0 = time.perf_counter(); N, regs = baue(); g = N.g; x = N.frei; nonce = x[4:12]; nonce_set = set(nonce); kopf = x[0:4]
    T = tiefen(g); nonce_abh = [False] * len(g.nodes)
    for i in nonce: nonce_abh[i] = True
    for i, nd in enumerate(g.nodes):
        if i >= 2 and nd[0] != 'input': nonce_abh[i] = nonce_abh[abs(nd[1])] or nonce_abh[abs(nd[2])]
    gatter = [i for i, nd in enumerate(g.nodes) if i >= 2 and nd[0] != 'input']; H = len(gatter); H_nonce = sum(1 for i in gatter if nonce_abh[i]); H_kopf = H - H_nonce
    # ---------- A ABLEITUNG ----------
    t1 = time.perf_counter(); d = d6.D6_R567bCM(); r = d.laufen(N); t_abl = time.perf_counter() - t1; z = d._zustand; wert = dict(z['wert']); find = z['find']; status = z['status']
    regeln = r[2].get('regeln') if isinstance(r, tuple) and len(r) > 2 and isinstance(r[2], dict) else None
    def res(xn):
        if xn in (0, 1, -1): return ('c', 0 if xn in (0, -1) else 1)
        rt, k = find(abs(xn)); s = k ^ (1 if xn < 0 else 0)
        return ('c', wert[rt] ^ s) if rt in wert else ('v', rt, s)
    # Form 1: affines System ueber Nonce-Bits (Index j = Position in nonce)
    pos = {v: j for j, v in enumerate(nonce)}; rows = []; herk1 = []
    def zeile_aus(vs_signed, const):
        """vs_signed: Liste (knoten, vorzeichen) -> aufloesen; nur wenn alle Wurzeln Nonce-Bits (oder fest)."""
        m = 0; c = const
        for v, s in vs_signed:
            Rr = res(v if not s else -v)
            if Rr[0] == 'c': c ^= Rr[1]
            else:
                if Rr[1] not in pos: return None
                m ^= 1 << pos[Rr[1]]; c ^= Rr[2]
        return (m, c)
    for v in nonce:
        Rr = res(v)
        if Rr[0] == 'c': rows.append((1 << pos[v], Rr[1])); herk1.append(dict(art='fest', bit=nm(v), wert=Rr[1]))
        elif Rr[1] != v and Rr[1] in pos: rows.append(((1 << pos[v]) | (1 << pos[Rr[1]]), Rr[2])); herk1.append(dict(art='alias', bit=nm(v), gleich=nm(Rr[1]), negiert=Rr[2]))
    for vs, const in z['xor_gl']:
        zl = zeile_aus([(v, 0) for v in vs], const)
        if zl is not None and zl[0]: rows.append(zl); herk1.append(dict(art='xor_gl', knoten=sorted(vs), konst=const))
    rang, konsistent, red, piv = gauss_gf2(rows, 8)
    # Erzeugungskosten je Kandidat: tatsaechliche XOR beim Rueckeinsetzen (Nichtnull-Koeffizienten ausser Pivot je Zeile) + 1 Zaehlerfortschaltung
    c_erz = sum(bin(m).count('1') - 1 for m, c in red) + 1 if konsistent else None
    E = (1 << (8 - rang)) if konsistent else 0
    # Form 2: ABGELEITETE Tatsachen ueber nonceabhaengige Innenknoten (nicht die Gatterfunktion selbst)
    bedingungen = []; innen = [i for i in gatter if nonce_abh[i]]
    for i in innen:
        Rr = res(i)
        if Rr[0] == 'c': bedingungen.append(dict(art='d6_fest', gatter=i, vars=[i], pruef_konkret=1, test=('fest', i, Rr[1])))
        elif Rr[1] != i and Rr[1] >= 2 and g.nodes[Rr[1]][0] != 'input' and nonce_abh[Rr[1]]: bedingungen.append(dict(art='d6_alias', gatter=i, vars=[i, Rr[1]], pruef_konkret=2, test=('gleich', i, Rr[1], Rr[2])))
        elif Rr[1] != i and Rr[1] in nonce_set: bedingungen.append(dict(art='d6_alias_nonce', gatter=i, vars=[i, Rr[1]], pruef_konkret=2, test=('gleich', i, Rr[1], Rr[2])))
    for b_ in bedingungen:
        b_['tiefe'] = max(T[v] for v in b_['vars']); b_['nonce_bits'] = [v for v in b_['vars'] if v in nonce_set]; b_['pruef_tabelle'] = len(b_['vars']) + 1; b_['pruef'] = max(b_['pruef_konkret'], b_['pruef_tabelle'])
        b_['kegel'] = len(kegel(g, [v for v in b_['vars'] if v not in nonce_set and v not in set(kopf)], True, nonce_abh))
    kandidaten = [b_ for b_ in bedingungen if b_['kegel'] <= 32]
    def kosten_filter(bs):
        innen = [v for b_ in bs for v in b_['vars'] if v not in nonce_set and v not in set(kopf)]
        kg = kegel(g, innen, True, nonce_abh); kg_kopf = kegel(g, innen, False, nonce_abh) - kg
        return dict(q=len(bs), c_rechnen=len(kg), kopfgatter_wiederverwendbar=len(kg_kopf), c_pruefen=sum(b_['pruef'] for b_ in bs), c_verknuepfen=max(len(bs) - 1, 0), c_filter=len(kg) + sum(b_['pruef'] for b_ in bs) + max(len(bs) - 1, 0))
    filter_def = {}
    for smax in (2, 8, 32):
        bs = [b_ for b_ in kandidaten if b_['kegel'] <= smax]; filter_def['alle_kegel_le_%d' % smax] = dict(bedingungen=[b_['gatter'] for b_ in bs], kosten=kosten_filter(bs))
    einzel = sorted(kandidaten, key=lambda b_: (kosten_filter([b_])['c_filter'], b_['gatter']))[:3]; filter_def['drei_billigste'] = dict(bedingungen=[b_['gatter'] for b_ in einzel], kosten=kosten_filter(einzel))
    eingefroren = dict(fall=dict(kopf=KOPF, kopf_wert=kopf_wert, k=K, runden=R), status=status, form1=dict(rang=rang, konsistent=konsistent, zeilen=[(m, c) for m, c in red], herkunft=herk1, E=E, c_erzeugen=c_erz), filter=filter_def,
                       bedingungen={b_['gatter']: dict(art=b_['art'], vars=[nm(v) for v in b_['vars']], tiefe=b_['tiefe'], kegel=b_['kegel'], pruef=b_['pruef'], pruef_konkret=b_['pruef_konkret'], pruef_tabelle=b_['pruef_tabelle']) for b_ in kandidaten})
    fp = os.path.join(HERE, 'FILTER2_r%d_k%d_F%d.json' % (R, K, KOPF)); js = json.dumps(eingefroren, sort_keys=True, default=str); open(fp, 'w').write(js); filter_sha = sha(js.encode()); t2 = time.perf_counter()
    # ---------- C KONTROLLE (danach) ----------
    bedmap = {b_['gatter']: b_ for b_ in bedingungen}
    def pruefe_bed(b_, v):
        t = b_['test']
        if t[0] == 'fest': return v[t[1]] == t[2]
        if t[0] == 'gleich': return v[t[1]] == (v[t[2]] ^ t[3])
        i = t[1]; nd = g.nodes[i]; lit = lambda xn: (v[abs(xn)] ^ (1 if xn < 0 else 0)) if abs(xn) >= 2 else (0 if xn in (0, -1) else 1)
        return v[i] == ((lit(nd[1]) & lit(nd[2])) if nd[0] == 'and' else (lit(nd[1]) ^ lit(nd[2])))
    loes = []; verletzt = []; A_filter = {fname: 0 for fname in filter_def}; A_form1 = 0; raum_ok = True; A_einzel = {b_['gatter']: 0 for b_ in bedingungen}
    for nb in range(256):
        bel = [(kopf_wert >> b) & 1 for b in range(4)] + [(nb >> j) & 1 for j in range(8)]; v = N.wert(bel)
        treffer = all((v[abs(zk)] ^ (1 if zk < 0 else 0)) == val for zk, val in N.ziel.items() if abs(zk) not in set(kopf))
        im_raum = all(bin(m & nb).count('1') % 2 == c for m, c in red) if konsistent else False
        if not im_raum: A_form1 += 1
        for fname, fd in filter_def.items():
            if any(not pruefe_bed(bedmap[gi], v) for gi in fd['bedingungen']): A_filter[fname] += 1
        for b_ in bedingungen:
            if not pruefe_bed(b_, v): A_einzel[b_['gatter']] += 1
        if treffer:
            loes.append(nb)
            if not im_raum: raum_ok = False; verletzt.append(dict(nonce=nb, art='form1'))
            for b_ in kandidaten:
                if not pruefe_bed(b_, v): verletzt.append(dict(nonce=nb, art='bedingung', gatter=b_['gatter']))
            for b_ in bedingungen:                                   # alle Einschraenkungen, nicht nur Filter
                if not pruefe_bed(b_, v): verletzt.append(dict(nonce=nb, art='bedingung_alle', gatter=b_['gatter']))
    t3 = time.perf_counter()
    # Umrechnungsfaktor (gekennzeichnet): Zeit einer Gatterauswertung in dieser Umgebung
    tg = time.perf_counter(); [N.wert([0] * 12) for _ in range(20)]; t_gatter = (time.perf_counter() - tg) / 20 / H
    C_pre_gatter_est = t_abl / t_gatter
    K0 = 256 * H_nonce
    bilanz = dict(referenz_K0=K0, H=H, H_nonce=H_nonce, H_kopf_vorab=H_kopf, C_pre_s=round(t_abl, 4), C_pre_gatter_geschaetzt=int(C_pre_gatter_est), umrechnung_hinweis='C_pre in Gatter = Ableitungszeit / Zeit einer Gatterauswertung (%.2e s) in derselben Python-Umgebung – grobe Schaetzung' % t_gatter, wege={})
    for fname, fd in filter_def.items():
        A = A_filter[fname]; cf = fd['kosten']['c_filter']; KP = 256 * cf + (256 - A) * H_nonce
        bilanz['wege']['P_' + fname] = dict(A=A, r=A / 256, c_filter=cf, K_ohne_Cpre=KP, ersparnis_ohne_Cpre=K0 - KP, K_mit_Cpre=KP + int(C_pre_gatter_est), ersparnis_mit_Cpre=K0 - KP - int(C_pre_gatter_est))
    if status == 'WIDERSPRUCH': bilanz['widerspruch'] = dict(befund='kein Treffer moeglich laut Ableitung', kontrolle_loesungen=len(loes), sicher=(len(loes) == 0))
    elif konsistent:
        KE = E * ((c_erz or 0) + H_nonce); bilanz['wege']['E_form1'] = dict(E=E, A=256 - E, r=1 - E / 256, c_erzeugen=c_erz, K_ohne_Cpre=KE, ersparnis_ohne_Cpre=K0 - KE, K_mit_Cpre=KE + int(C_pre_gatter_est), ersparnis_mit_Cpre=K0 - KE - int(C_pre_gatter_est))
        for fname, fd in filter_def.items():
            cf = fd['kosten']['c_filter']; AE = 0
            for nb in range(256):
                if konsistent and all(bin(m & nb).count('1') % 2 == c for m, c in red):
                    bel = [(kopf_wert >> b) & 1 for b in range(4)] + [(nb >> j) & 1 for j in range(8)]; v = N.wert(bel)
                    if any(not pruefe_bed(bedmap[gi], v) for gi in fd['bedingungen']): AE += 1
            KEP = E * ((c_erz or 0) + cf) + (E - AE) * H_nonce
            bilanz['wege']['EP_' + fname] = dict(E=E, A_E=AE, K_ohne_Cpre=KEP, ersparnis_ohne_Cpre=K0 - KEP, ersparnis_mit_Cpre=K0 - KEP - int(C_pre_gatter_est))
    beob = sorted([dict(gatter=b_['gatter'], art=b_['art'], kegel=b_['kegel'], A=A_einzel[b_['gatter']], ersparnis_allein_ohne_Cpre=A_einzel[b_['gatter']] * H_nonce - 256 * (b_['kegel'] + b_['pruef'])) for b_ in bedingungen], key=lambda e_: (-e_['A'], e_['kegel']))
    mit_ausschluss = [e_ for e_ in beob if e_['A'] > 0]
    beobachtung = dict(hinweis='NACHTRAEGLICHE BEOBACHTUNG, nicht Teil der Bilanz (Filter waren vorab eingefroren): Ausschluss je einzelner abgeleiteter Bedingung ueber alle 256 Nonces gegen ihre Kegelkosten', bedingungen_gesamt=len(bedingungen), mit_ausschluss=len(mit_ausschluss), kleinster_kegel_mit_ausschluss=(min(e_['kegel'] for e_ in mit_ausschluss) if mit_ausschluss else None), groesster_kegel_ohne_ausschluss=max((e_['kegel'] for e_ in beob if e_['A'] == 0), default=None), beste_einzelbedingung=(max(mit_ausschluss, key=lambda e_: e_['ersparnis_allein_ohne_Cpre']) if mit_ausschluss else None), top10=beob[:10])
    pruef = dict(E1_sicher=(not verletzt), E2_raum=(raum_ok and (not konsistent or all(all(bin(m & nb).count('1') % 2 == c for m, c in red) for nb in loes))), E4_filter_vor_kontrolle=(sha(open(fp, 'rb').read()) == filter_sha), widerspruch_sicher=(status != 'WIDERSPRUCH' or len(loes) == 0))
    erg = dict(fall=dict(kopf=KOPF, kopf_wert=kopf_wert, k=K, runden=R, netz=N.name, knoten=len(g.nodes), gatter=H), ableitung=dict(status=status, wert=len(wert), alias=sum(1 for v in range(2, len(g.nodes)) if find(v)[0] != v), zeit_s=round(t_abl, 4), regeln=regeln, darstellung='D6+R1b+R8c+R8m'),
               form1=dict(rang=rang, konsistent=konsistent, zeilen=[(m, c) for m, c in red], herkunft_anzahl=len(herk1), E=E, c_erzeugen=c_erz, A_form1=A_form1), form2=dict(kandidaten=len(kandidaten), filter=filter_def, kandidaten_detail=eingefroren['bedingungen']),
               filter_eingefroren=dict(datei=os.path.basename(fp), sha256=filter_sha), kontrolle=dict(loesungen=len(loes), nonces=loes if len(loes) <= 64 else loes[:64], verletzt=verletzt[:20], verletzt_anzahl=len(verletzt), A_filter=A_filter, zeit_s=round(t3 - t2, 4)),
               bilanz=bilanz, beobachtung_nachtraeglich=beobachtung, pruefung=pruef, bestanden=all(pruef.values()), zeiten_s=dict(aufbau=round(t1 - t0, 4), ableitung=round(t_abl, 4), form1_form2_filter=round(t2 - t1 - t_abl, 4), kontrolle=round(t3 - t2, 4)), maxrss_mib=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1),
               abhaengigkeiten={m: dict(pfad=sys.modules[m].__file__, sha256=sha(open(sys.modules[m].__file__, 'rb').read())) for m in ('pruefstand', 'd6', 'gatter', 'e1_bit') if m in sys.modules})
    json.dump(erg, open(os.path.join(HERE, 'ERGEBNIS_AUSD2_r%d_k%d_F%d.json' % (R, K, KOPF)), 'w'), indent=1, default=str)
    w = bilanz['wege']; best = max(w.items(), key=lambda kv: kv[1]['ersparnis_mit_Cpre']) if w else None
    print('r%d k%d F%d(%2d) | %-11s | Loes %3d | Rang %d | Kand %d A_filter %s | H_nonce %d | beste Bilanz mit C_pre %s | Beob: %d/%d Bed. schliessen aus, kleinster Kegel mit Ausschluss %s, beste allein %s | sicher %s | %s' % (
        R, K, KOPF, kopf_wert, status[:11], len(loes), rang, len(kandidaten), max(A_filter.values()), H_nonce, best[1]['ersparnis_mit_Cpre'] if best else None, len(mit_ausschluss), len(bedingungen), beobachtung['kleinster_kegel_mit_ausschluss'], (beobachtung['beste_einzelbedingung'] or {}).get('ersparnis_allein_ohne_Cpre'), pruef['E1_sicher'], 'BESTANDEN' if erg['bestanden'] else 'FEHLER'))
    sys.exit(0 if erg['bestanden'] else 3)
if __name__ == '__main__': main()
