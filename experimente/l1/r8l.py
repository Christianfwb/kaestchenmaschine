"""R8l – lokales Rueckwaertskaestchen: Ch-Bit + GENAU EINE binaere Additionsstufe (z + b + cin = s + 2*cout, z = Ch(e,f,g)).
Gemeinsame Tabelle aller Anschlussbelegungen (e,f,g,b,cin -> z,s,cout), geschnitten NUR mit bereits von D6 hergeleiteten Werten/Beziehungen,
die auf diese Anschluesse anwendbar sind. Keine Orakelwerte, keine Kandidatenpruefung, keine Weitergabe in R1-R7 (eigener spaeterer Schritt).
Gemessen: lokaler Informationsgewinn (Zeilen vorher/nachher, neue feste Anschluesse, neue Paar-/XOR-Beziehungen, die D6 noch nicht hatte).
Nachtraegliche Kontrolle: Zeile der echten Loesung muss erhalten bleiben (Orakel liest nur, speist nichts ein).
Messung: A = Kombinationen der 8 Anschluesse, die D6s lokale Bedingungen allein erlauben; B = davon die, die Ch UND Stufe erfuellen.
Gewinn = A - B. 'Neu' nur, was in B gilt und in A verletzt wird. Verlorene echte Loesung -> FEHLER (SystemExit 3).
Aufruf: python3 r8l.py N4r09 [runde] [Darstellung]   (Tabellen: A = D6 lokal, C = A+Ch allein, B = A+Ch+Stufe gemeinsam)   (GO 2026-10-24 12:25: 'R8l an den vier letzten Ch-Bits, R8g noch nicht')"""
import sys, os, json, time, itertools
import pruefstand as P, d6

def anschluss_wert(Z, node):
    """Hergeleiteter Wert eines Knotens (Literal) oder None; Wurzel+Versatz fuer Alias-Vergleiche."""
    v, c = Z['lit'](node)
    if v is None: return c, (None, c)
    r, k = Z['find'](v); k ^= c
    if r in Z['wert']: return Z['wert'][r] ^ k, (r, k)
    return None, (r, k)

def r8l(N, D, ch_indices):
    status, F, gr = D.laufen(N); Z = D._zustand
    assert status != 'WIDERSPRUCH'
    bericht = dict(netz=N.name, darstellung=D.name, status_d6=status, erlaubt_vorher=None, kaestchen=[])
    # Kontrolle: echte Loesung (nur lesen, nachtraeglich)
    import hashlib
    k = int.from_bytes(hashlib.sha256(N.name.encode()).digest(), 'little') % (1 << len(N.frei)); bel = [(k >> i) & 1 for i in range(len(N.frei))]; vw = N.wert(bel)
    def echt(node): return (1 - vw[-node]) if node < 0 else vw[node]
    for ci in ch_indices:
        e, f, g, z = N.ch_kaestchen[ci]
        st = [s for s in N.stufen if s[1] == z or s[0] == z]
        assert len(st) == 1, 'Ch-Ausgang muss in genau einer Stufe stecken'
        x, y, cin, s_, cout = st[0]; b = x if y == z else y
        namen = ['e', 'f', 'g', 'b', 'cin', 'z', 's', 'cout']; knoten = [e, f, g, b, cin, z, s_, cout]
        # Tabelle A: alle 2^8 Kombinationen der 8 Anschluesse als UNABHAENGIGE Variablen, gefiltert nur durch D6-eigene lokale Bedingungen
        fest = {}; wurzel = {}
        for nm, nd in zip(namen, knoten):
            w, (r, kk) = anschluss_wert(Z, nd); wurzel[nm] = (r, kk)
            if w is not None: fest[nm] = w
        aliasse = []
        for i in range(len(namen)):
            for j in range(i + 1, len(namen)):
                ri, ki = wurzel[namen[i]]; rj, kj = wurzel[namen[j]]
                if ri is not None and ri == rj and namen[i] not in fest: aliasse.append((namen[i], namen[j], ki ^ kj))
        wurzel_zu_namen = {}
        for nm in namen:
            r, kk = wurzel[nm]
            if r is not None and nm not in fest: wurzel_zu_namen.setdefault(r, nm)
        xor_bez = []
        for pv, (res, cc) in Z['pivots'].items():
            if res and all(r in wurzel_zu_namen for r in res):
                c = cc
                for r in res: c ^= wurzel[wurzel_zu_namen[r]][1]
                xor_bez.append(([wurzel_zu_namen[r] for r in res], c))
        lin_bez = []
        for paare_, const0 in Z['lin_gl']:
            terms = {}; const = const0; ok = True
            for node, coef in paare_:
                v, c = Z['lit'](node)
                if v is None: const -= coef * c; continue
                r, kk = Z['find'](v); kk ^= c
                if r in Z['wert']: const -= coef * (Z['wert'][r] ^ kk); continue
                if r not in wurzel_zu_namen: ok = False; break
                nm = wurzel_zu_namen[r]; ka = wurzel[nm][1]; kk ^= ka; const -= coef * kk; terms[nm] = terms.get(nm, 0) + coef * (1 - 2 * kk)
            if not ok: continue
            terms = {a: c for a, c in terms.items() if c != 0}
            if len(terms) >= 2: lin_bez.append((terms, const))
        def d6_lokal_ok(zl):
            return (all(zl[nm] == w for nm, w in fest.items()) and all((zl[a] ^ zl[b2]) == kk for a, b2, kk in aliasse)
                    and all(sum(zl[a] for a in vs) % 2 == c for vs, c in xor_bez) and all(sum(c * zl[a] for a, c in t.items()) == k_ for t, k_ in lin_bez))
        A = [dict(zip(namen, w)) for w in itertools.product((0, 1), repeat=8) if d6_lokal_ok(dict(zip(namen, w)))]
        # Tabelle B: davon die, die Ch UND Stufe gemeinsam erfuellen (das gemeinsame Kaestchen)
        def kaestchen_ok(zl):
            zv = zl['f'] if zl['e'] else zl['g']; summe = zv + zl['b'] + zl['cin']
            return zl['z'] == zv and zl['s'] == (summe & 1) and zl['cout'] == (summe >> 1)
        def ch_ok(zl): return zl['z'] == (zl['f'] if zl['e'] else zl['g'])           # Ch allein
        C = [zl for zl in A if ch_ok(zl)]                                               # Tabelle C: D6 lokal + Ch allein
        B = [zl for zl in A if kaestchen_ok(zl)]                                        # Tabelle B: D6 lokal + Ch + Stufe gemeinsam
        nA, nB, nC = len(A), len(B), len(C)
        # Stufe allein (zur Vollstaendigkeit): D6 lokal + Stufengleichung als Funktion
        nS = sum(1 for zl in A if zl['s'] == ((zl['z'] + zl['b'] + zl['cin']) & 1) and zl['cout'] == ((zl['z'] + zl['b'] + zl['cin']) >> 1))
        # Neu = gilt in allen Zeilen von B, aber nicht in allen Zeilen von A (sonst war es schon in D6s lokalen Bedingungen enthalten)
        def gilt(rows, fn): return bool(rows) and all(fn(zl) for zl in rows)
        neu_fest = {nm: B[0][nm] for nm in namen if B and gilt(B, lambda zl, nm=nm: zl[nm] == B[0][nm]) and not gilt(A, lambda zl, nm=nm: zl[nm] == B[0][nm])}
        neu_paar = []
        for a, b2 in itertools.combinations(namen, 2):
            for kk in (0, 1):
                if gilt(B, lambda zl: (zl[a] ^ zl[b2]) == kk) and not gilt(A, lambda zl: (zl[a] ^ zl[b2]) == kk): neu_paar.append((a, b2, kk))
        neu_xor3 = []
        for tri in itertools.combinations(namen, 3):
            for kk in (0, 1):
                if gilt(B, lambda zl: (zl[tri[0]] ^ zl[tri[1]] ^ zl[tri[2]]) == kk) and not gilt(A, lambda zl: (zl[tri[0]] ^ zl[tri[1]] ^ zl[tri[2]]) == kk): neu_xor3.append((list(tri), kk))
        echt_zeile = {nm: echt(nd) for nm, nd in zip(namen, knoten)}
        if os.environ.get('R8L_TEST_FEHLER'): echt_zeile['e'] ^= 1      # NUR TEST des Stopps: Kontrollwert absichtlich verfaelscht
        echt_drin = any(all(zl[nm] == echt_zeile[nm] for nm in namen) for zl in B)
        if not echt_drin:
            print('FEHLER: echte Loesung in Kaestchen Ch#%d verloren – Stopp' % ci); json.dump(dict(fehler='echte Loesung verloren', ch_index=ci, echt=echt_zeile, A=nA, B=nB), open('FEHLER_R8L.json', 'w'), indent=1); raise SystemExit(3)
        zeilen = B; n0 = 256
        bericht['kaestchen'].append(dict(ch_index=ci, knoten=dict(zip(namen, knoten)), kombinationen_gesamt=256, A_d6_lokal_erlaubt=nA, C_ch_allein=nC, S_stufe_allein=nS, B_gemeinsames_kaestchen=nB, gewinn_ch_allein=nA - nC, gewinn_gemeinsam_ueber_ch_hinaus=nC - nB,
            d6_fest=fest, d6_aliasse=aliasse, d6_xor=[(vs, c) for vs, c in xor_bez], d6_linear=[(t, k_) for t, k_ in lin_bez],
            neu_feste_anschluesse=neu_fest, neu_paare=neu_paar, neu_xor3=neu_xor3, echte_loesung_erhalten=echt_drin, zeilen_rest=zeilen))
    return bericht, F

if __name__ == '__main__':
    netz = sys.argv[1] if len(sys.argv) > 1 else 'N4r09'
    dname = sys.argv[3] if len(sys.argv) > 3 else 'D6+R5+R6+R7+R1b'; t = time.perf_counter(); N = P.NETZE[netz](); D = P.DARSTELLUNGEN[dname]()
    runde = int(sys.argv[2]) if len(sys.argv) > 2 else len(N.ch_kaestchen) // 4      # Ch-Bits einer Runde (4 je Runde), Standard: letzte
    letzte4 = list(range((runde - 1) * 4, runde * 4))
    B, F = r8l(N, D, letzte4); B['runde'] = runde; B['s_gesamt'] = round(time.perf_counter() - t, 3); B['ch_kaestchen_gesamt'] = len(N.ch_kaestchen)
    B['rechner'] = 'Fable-Container Xeon 2,10 GHz 2 Kerne, Python %s' % sys.version.split()[0]
    json.dump(B, open('ERGEBNIS_R8L_%s_R%d_%s.json' % (netz, runde, dname.replace('+', '')), 'w'), indent=1, default=str)
    for k in B['kaestchen']:
        print('Ch#%d: A (D6 lokal) %d -> C (Ch allein) %d -> B (Ch+Stufe) %d [Stufe allein %d] | Gewinn Ch %d, gemeinsam darueber hinaus %d | D6 fest %s alias %s xor %d lin %d | NEU fest %s paare %s xor3 %s | echt erhalten %s' % (
            k['ch_index'], k['A_d6_lokal_erlaubt'], k['C_ch_allein'], k['B_gemeinsames_kaestchen'], k['S_stufe_allein'], k['gewinn_ch_allein'], k['gewinn_gemeinsam_ueber_ch_hinaus'], k['d6_fest'], k['d6_aliasse'], len(k['d6_xor']), len(k['d6_linear']),
            k['neu_feste_anschluesse'], k['neu_paare'], k['neu_xor3'], k['echte_loesung_erhalten']))
    print('Zeit %.3f s' % B['s_gesamt'])
