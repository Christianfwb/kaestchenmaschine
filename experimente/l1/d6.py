#!/usr/bin/env python3
"""D6 – RUECKWAERTSLEINE MIT ERHALTENEN HILFSGROESSEN (Spezifikation Ghost/Fable 2026-10-24).
(1) FORMELBESTAND (exakt, eine Zeile je Gatter/Stufe):
    XOR-Gleichungen   {v1,...,vk} = c  ueber GF(2)      aus XOR-Gattern (Negation = Konstante 1), aus Zielbits, und je Additionsstufe s = x^y^cin
    UND-Gleichungen   z = x*y                            aus AND-Gattern (Ch/Maj zerlegt); bleiben Produkt, werden NICHT linearisiert
    STUFEN-Gleichungen x + y + cin = s + 2*cout  (ganze Zahlen) je Additionsstufe; werden als Ganzes gehalten
    Identitaet: dieselbe Variable = derselbe Knoten (Graph); Aliasse (x = y) ueber Union-Find, ohne Aufzaehlung.
(2) REGELN (jede sound = nur Folgerungen; keine Kandidaten):
    R1 EINSETZEN bekannter Werte in alle Gleichungen; UND: z=1 -> x=y=1; x=0 oder y=0 -> z=0; x=y=1 -> z=1; z=0 & x=1 -> y=0.
    R2 XOR-ZUSAMMENFUEHREN: Gauss-Elimination ueber GF(2) (Hilfsgroessen zuerst, freie Bits zuletzt) -> Werte, Aliasse, Widerspruch,
       und die auf freie Bits projizierten linearen Beziehungen.
    R3 GLEICHSETZEN: x = y (aus XOR-Gleichung mit zwei Variablen und Konstante 0) -> Alias; x = NOT y (Konstante 1) -> Alias mit Vorzeichen.
    R4 UEBERTRAGSREGELN (gekoppelt): Stufengleichung nach Einsetzen/Aliassen als  sum(coef_v * v) = const  ueber 0/1-Variablen:
       (a) Schranken: liegt const ausserhalb [min,max] -> WIDERSPRUCH; const = max -> alle positiven Variablen 1, negativen 0; const = min analog.
       (b) Eine Variable uebrig -> Wert. (c) Zwei Variablen mit Koeffizienten (+2,-2) oder (+1,-1) -> Alias (bzw. (+1,+1)=1 -> x^y=1, (+2,+2)... ).
       (d) Paritaet: Summe der Variablen mit ungeradem Koeffizienten = const mod 2 -> XOR-Gleichung (geht in R2).
    Schleife bis Fixpunkt. Suche: keine.
(3) EINGEFRORENE FOLGERUNGEN (projiziert auf freie Bits): feste freie Bits; lineare GF(2)-Beziehungen NUR ueber freie Bits (aus der Elimination);
    Widerspruch. erlaubt(belegung) prueft genau diese. Alles andere (UND, Stufen) ist Wissen, das NICHT zur Kontrollzaehlung benutzt wird."""
import itertools, time

class D6_Rueckwaertsleine:
    name = 'D6 Rueckwaertsleine (Formeln + R1-R4)'
    AKTIV = ('R1', 'R2', 'R3', 'R4')          # Ablation: Unterklassen schalten Regeln ab
    R8C_INDICES = None                        # R8c: None = alle Ch-Kaestchen, sonst Liste von Indizes (begrenzte Anwendung)
    R9_AUSWAHL = None                         # R9: None = alle Kaestchen, sonst {'Ch': [...], 'Maj': [...]}
    R9A_PAARE = None                          # R9a: None = alle Paare innerhalb der R9-Auswahl, sonst Liste von ((typ,i),(typ,j))
    def laufen(self, N):
        t = time.perf_counter(); g = N.g; n_nodes = len(g.nodes); self._r9_protokoll = []
        # Variablen: Knoten >= 2. Konstanten 0,1. Negation: Knoten -k = k ^ 1.
        xor_gl = []; und_gl = []; stufen = []
        def lit(x):                        # (var, konst): Knoten x als (Variable oder None, Konstante)
            if x == 0: return (None, 0)
            if x == 1: return (None, 1)
            if x == -1: return (None, 0)
            return (abs(x), 1 if x < 0 else 0)
        for i in range(2, n_nodes):
            nd = g.nodes[i]
            if nd[0] == 'input': continue
            a, b = nd[1], nd[2]
            if nd[0] == 'xor':
                va, ca = lit(a); vb, cb = lit(b); vs = [v for v in (va, vb, i) if v is not None]; xor_gl.append((set(vs) if len(set(vs)) == len(vs) else self._sym(vs), (ca ^ cb) & 1))
            else: und_gl.append((i, a, b))
        for (x, y, cin, sb, cn) in N.stufen: stufen.append([x, y, cin, sb, cn])
        lin_gl = [([(x, 1), (y, 1), (cin, 1), (sb, -1), (cn, -2)], 0) for (x, y, cin, sb, cn) in stufen]   # Stufengleichung: sum = const
        r5_fertig = set(); r6_fertig = set(); r9b_fertig = set(); r9b_bruecken = []; r9_stat = dict(kaestchen_mit_tafel=0, wurzelmengen=0, paare=0, tafelzeilen=0); 
        # Addierer = Ketten von Stufen (cout einer Stufe ist cin der naechsten)
        addierer = []
        for st in stufen:
            for kette in addierer:
                if kette[-1][4] == st[2]: kette.append(st); break
            else: addierer.append([st])
        if 'R6' in self.AKTIV:
            wort_gl = []
            for kette in addierer:                    # sum_i 2^i * (x_i + y_i + cin_i - s_i - 2 cout_i) = 0 -> innere Uebertraege heben sich auf
                terms = []
                for i, (x, y, cin, sb, cn) in enumerate(kette):
                    w = 1 << i; terms += [(x, w), (y, w), (sb, -w)]
                    if i == 0: terms.append((cin, w))
                    if i == len(kette) - 1: terms.append((cn, -2 * w))
                wort_gl.append((terms, 0)); lin_gl.append((terms, 0))
            self._wort_gl = wort_gl
        wert = {}; alias = {}; frei_set = set(N.frei)            # alias[v] = (w, k): v = w ^ k; Wurzel bevorzugt ein FREIES Bit (Projektion)
        for k, w in N.ziel.items():
            v, c = lit(k); 
            if v is None:
                if c != w: return 'WIDERSPRUCH', dict(widerspruch=True, frei_fest={}, frei_xor=[]), dict(grund='Zielkonstante')
            else: wert[v] = w ^ c
        def find(v):
            k = 0
            while v in alias: w, kk = alias[v]; v, k = w, k ^ kk
            return v, k
        def setze(v, w):
            v, k = find(v); w ^= k
            if v in wert:
                if wert[v] != w: raise ValueError('WIDERSPRUCH')
                return False
            wert[v] = w; return True
        def verbinde(v1, v2, k):          # v1 = v2 ^ k
            r1, k1 = find(v1); r2, k2 = find(v2)
            if r1 == r2:
                if (k1 ^ k2) != k: raise ValueError('WIDERSPRUCH')
                return False
            if r1 in wert and r2 in wert:
                if wert[r1] != (wert[r2] ^ k ^ k1 ^ k2): raise ValueError('WIDERSPRUCH')
                return False
            if r1 in wert: wert[r2] = wert[r1] ^ k ^ k1 ^ k2; return True
            if r2 in wert: wert[r1] = wert[r2] ^ k ^ k1 ^ k2; return True
            if r1 in frei_set and r2 not in frei_set: alias[r2] = (r1, k ^ k1 ^ k2)      # Hilfsgroesse zeigt auf freies Bit
            else: alias[r1] = (r2, k ^ k1 ^ k2)
            return True
        regeln = dict(R1=0, R2=0, R3=0, R4=0, R5=0, R6=(len(addierer) if 'R6' in self.AKTIV else 0), R7=0); status = 'FIXPUNKT'
        def norm_xor(vs, c):
            """XOR-Gleichung in Normalform ueber Repraesentanten: set vars, konst."""
            res = set(); cc = c
            for v in vs:
                r, k = find(v); cc ^= k
                if r in wert: cc ^= wert[r]
                else: res ^= {r}
            return res, cc
        try:
            geaendert = True; runden = 0
            while geaendert and runden < 1000:
                geaendert = False; runden += 1
                # R1 + UND-Regeln
                for (z, a, b) in (und_gl if 'R1' in self.AKTIV else []):
                    va, ca = lit(a); vb, cb = lit(b)
                    def val(v, c):
                        if v is None: return c
                        r, k = find(v); return (wert[r] ^ k ^ c) if r in wert else None
                    A, B, Z = val(va, ca), val(vb, cb), val(z, 0)
                    if A is not None and B is not None: 
                        if setze(z, A & B): geaendert = True; regeln['R1'] += 1
                    elif Z == 1:
                        if va is not None and setze(va, 1 ^ ca): geaendert = True; regeln['R1'] += 1
                        if vb is not None and setze(vb, 1 ^ cb): geaendert = True; regeln['R1'] += 1
                    elif Z == 0 and A == 1 and vb is not None:
                        if setze(vb, 0 ^ cb): geaendert = True; regeln['R1'] += 1
                    elif Z == 0 and B == 1 and va is not None:
                        if setze(va, 0 ^ ca): geaendert = True; regeln['R1'] += 1
                    elif (A == 0 or B == 0):
                        if setze(z, 0): geaendert = True; regeln['R1'] += 1
                    elif 'R1b' in self.AKTIV and A == 1 and vb is not None:      # R1b: ein Eingang bekannt 1 -> Ausgang = anderer Eingang (Literal: z = vb ^ cb)
                        if verbinde(z, vb, cb): geaendert = True; regeln['R1b'] = regeln.get('R1b', 0) + 1
                    elif 'R1b' in self.AKTIV and B == 1 and va is not None:
                        if verbinde(z, va, ca): geaendert = True; regeln['R1b'] = regeln.get('R1b', 0) + 1
                # R8c Ch-Kaestchen exakt: Wahrheitstafel von z = Ch(e,f,g) mit bekannten WERTEN und ALIASSEN der Anschluesse schneiden;
                # daraus nur sichere Folgerungen: z fest, z = Literal eines Anschlusses, oder XOR-Beziehung z^Li^Lj = konst. Keine Fallwahl, keine Kandidaten.
                # Verallgemeinert Ghosts zwei Vereinfachungen (f=g -> z=f; e=f,g=0 -> z=e) und deren Negationsvarianten.
                # R8c (Ch) und R8m (Maj): exaktes Kaestchen ueber vier Literale, gleiche Bauart, nur andere Wahrheitstafel.
                for regel, attr, fn in (('R8c', 'ch_kaestchen', lambda a, b, c: b if a else c), ('R8m', 'maj_kaestchen', lambda a, b, c: (a & b) | (a & c) | (b & c))):
                    if regel not in self.AKTIV or not hasattr(N, attr): continue
                    liste = getattr(N, attr)
                    idx = self.R8C_INDICES if (regel == 'R8c' and self.R8C_INDICES is not None) else range(len(liste))
                    for ci in idx:                     # jede Runde erneut: Werte/Aliasse der Anschluesse koennen erst spaeter entstehen (Konvergenz: nur echte Aenderungen setzen geaendert)
                        if self._kaestchen_exakt(liste[ci], fn, lit, find, wert, setze, verbinde, xor_gl, regeln, regel): geaendert = True
                # R9 'gleiche Funktion': zwei Kaestchenausgaenge, die DIESELBE Funktion DERSELBEN Eingangswurzeln berechnen, sind gleich (bzw. negiert gleich).
                # Normierung: Eingaenge auf Wurzeln (find) mit Vorzeichen, Konstanten eingesetzt, Tafel ueber die SORTIERTEN Wurzeln ausgewertet, Ausgang auf seine Wurzel
                # mit Vorzeichen bezogen. Nur Tafeln ueber identischen Wurzelmengen werden verglichen. Begrenzt durch R9_AUSWAHL (None = alle Kaestchen).
                if any(r_ in self.AKTIV for r_ in ('R9', 'R9a', 'R9b')):
                    tafeln = {}; tafel_je_kaestchen = {}
                    for typ, attr, fn in (('Ch', 'ch_kaestchen', lambda a, b, c: b if a else c), ('Maj', 'maj_kaestchen', lambda a, b, c: (a & b) | (a & c) | (b & c))):
                        if not hasattr(N, attr): continue
                        liste = getattr(N, attr); idx = range(len(liste)) if self.R9_AUSWAHL is None else [i for i in self.R9_AUSWAHL.get(typ, ()) if i < len(liste)]
                        for ci in idx:
                            kn = liste[ci]; lits = []
                            for nd in kn:
                                v, c = lit(nd)
                                if v is None: lits.append((None, c)); continue
                                r, k = find(v); k ^= c
                                lits.append((None, wert[r] ^ k) if r in wert else (r, k))
                            ro, ko = lits[3]
                            if ro is None: continue                                   # Ausgang bekannt -> nichts zu vergleichen
                            wurzeln = sorted({r for r, k in lits[:3] if r is not None})
                            if not wurzeln: continue
                            tafel = []
                            for w in itertools.product((0, 1), repeat=len(wurzeln)):
                                bel = dict(zip(wurzeln, w)); ein = [(k if r is None else bel[r] ^ k) for r, k in lits[:3]]
                                tafel.append(fn(*ein) ^ ko)                             # Wert der AUSGANGSWURZEL
                            key = (tuple(wurzeln), tuple(tafel)); keyn = (tuple(wurzeln), tuple(1 - t for t in tafel))
                            tafel_je_kaestchen[(typ, ci)] = (tuple(wurzeln), tuple(tafel), ro)
                            if 'R9' not in self.AKTIV: continue                   # Ablation: ohne R9 keine Gleichsetzung, Tafeln bleiben fuer R9a/R9b
                            if key in tafeln:
                                r2 = tafeln[key]
                                if r2 != ro and verbinde(ro, r2, 0): geaendert = True; regeln['R9'] = regeln.get('R9', 0) + 1; self._r9_protokoll.append((typ, ci, 'gleich', wurzeln))
                            elif keyn in tafeln:
                                r2 = tafeln[keyn]
                                if r2 != ro and verbinde(ro, r2, 1): geaendert = True; regeln['R9'] = regeln.get('R9', 0) + 1; self._r9_protokoll.append((typ, ci, 'negiert gleich', wurzeln))
                            else: tafeln[key] = ro
                    # R9a 'affine Differenz': zwei normierte Tafeln ueber DENSELBEN Wurzeln XOR-verknuepfen; ist die Differenz an JEDER Zeile von der Form
                    # Konstante XOR (ausgewaehlte Wurzeln), dann gilt out1 ^ out2 ^ (diese Wurzeln) = Konstante als XOR-Gleichung. Nur fuer R9A_PAARE.
                    if 'R9a' in self.AKTIV or 'R9b' in self.AKTIV:
                        if self.R9A_PAARE is not None: paare = self.R9A_PAARE
                        else:
                            gruppen = {}
                            for kk_, (wz_, tf_, o_) in tafel_je_kaestchen.items(): gruppen.setdefault(wz_, []).append(kk_)
                            paare = [pp for g_ in gruppen.values() for pp in itertools.combinations(sorted(g_), 2)]
                            r9_stat.update(kaestchen_mit_tafel=len(tafel_je_kaestchen), wurzelmengen=len(gruppen), paare=max(r9_stat['paare'], len(paare)))
                        for p1, p2 in paare:
                            if p1 not in tafel_je_kaestchen or p2 not in tafel_je_kaestchen: continue
                            w1, t1, o1 = tafel_je_kaestchen[p1]; w2, t2, o2 = tafel_je_kaestchen[p2]
                            if w1 != w2 or o1 == o2: continue
                            n = len(w1); diff = [x ^ y for x, y in zip(t1, t2)]; r9_stat['tafelzeilen'] += len(diff)
                            if 'R9a' not in self.AKTIV:                                    # Ablation: nur R9b-Teil
                                if 'R9b' in self.AKTIV and (p1, p2) not in r9b_fertig and all(not (x and y) for x, y in zip(t1, t2)):
                                    r1_, k1_ = find(o1); r2_, k2_ = find(o2); h = n_nodes + 1000 + len(r9b_fertig); terms = [(h, 1)]; const = 1
                                    for r_, k_ in ((r1_, k1_), (r2_, k2_)): const -= k_; terms.append((r_, 1 - 2 * k_))
                                    lin_gl.append((terms, const)); r9b_fertig.add((p1, p2)); geaendert = True; regeln['R9b'] = regeln.get('R9b', 0) + 1
                                    self._r9_protokoll.append(('R9b', p1, p2, 'nie beide 1', 'p+q+h=1', h)); r9b_bruecken.append((o1, o2))
                                continue
                            zeilen_w = list(itertools.product((0, 1), repeat=n))
                            c0 = diff[0]                                                   # Zeile 0...0
                            koeff = [diff[zeilen_w.index(tuple(1 if j == i else 0 for j in range(n)))] ^ c0 for i in range(n)]   # Einheitszeilen
                            affin = all(d == (c0 ^ (sum(k * w for k, w in zip(koeff, zl)) & 1)) for d, zl in zip(diff, zeilen_w))    # JEDE Zeile pruefen
                            if 'R9b' in self.AKTIV and (p1, p2) not in r9b_fertig and all(not (x and y) for x, y in zip(t1, t2)):   # nie beide 1 (an JEDER Zeile)
                                r1_, k1_ = find(o1); r2_, k2_ = find(o2); h = n_nodes + 1000 + len(r9b_fertig)                    # frische Hilfsgroesse
                                # Literale o1 = r1 ^ k1: als Zahl k1 + (1-2k1) r1 -> p + q + h = 1
                                terms = [(h, 1)]; const = 1
                                for r_, k_ in ((r1_, k1_), (r2_, k2_)): const -= k_; terms.append((r_, 1 - 2 * k_))
                                lin_gl.append((terms, const)); r9b_fertig.add((p1, p2)); geaendert = True
                                r9b_bruecken.append((o1, o2))                     # Bruecke wird unten in JEDER Runde erneut geprueft (Aliasse koennen spaeter entstehen)
                                regeln['R9b'] = regeln.get('R9b', 0) + 1; self._r9_protokoll.append(('R9b', p1, p2, 'nie beide 1', 'p+q+h=1', h))
                            if not affin: self._r9_protokoll.append(('R9a', p1, p2, 'nicht affin')); continue
                            vs = set(); cc = c0
                            for v0 in (o1, o2):                                        # Wurzeln NEU aufloesen (R9 kann sie soeben verbunden haben)
                                r_, k_ = find(v0); vs ^= {r_}; cc ^= k_
                            for k, r in zip(koeff, w1):
                                if k: r_, k_ = find(r); vs ^= {r_}; cc ^= k_
                            if not vs:
                                if cc: raise ValueError('WIDERSPRUCH')
                                continue
                            eq = (vs, cc)
                            if eq not in xor_gl: xor_gl.append(eq); geaendert = True; regeln['R9a'] = regeln.get('R9a', 0) + 1; self._r9_protokoll.append(('R9a', p1, p2, 'affin', [r for k, r in zip(koeff, w1) if k], cc))
                # R9b-Bruecke, jede Runde bis zum Stillstand: jedes z = a UND b, dessen Eingangsliterale (nach find) genau ein 'nie beide 1'-Paar sind -> z = 0
                for (o1, o2) in (r9b_bruecken if 'R9bBr' in self.AKTIV else []):
                    r1_, k1_ = find(o1); r2_, k2_ = find(o2); ziel_lits = {(r1_, k1_), (r2_, k2_)}
                    for (zq, aq, bq) in und_gl:
                        ls = []
                        for q_ in (aq, bq):
                            vq, cq = lit(q_)
                            if vq is None: ls.append(None); continue
                            rq, kq = find(vq); ls.append((rq, kq ^ cq))
                        if ls[0] is not None and ls[1] is not None and {ls[0], ls[1]} == ziel_lits:
                            if setze(zq, 0): geaendert = True; regeln['R9b_bruecke'] = regeln.get('R9b_bruecke', 0) + 1
                # R4 Stufengleichungen als lineare Integer-Gleichungen ueber 0/1
                # R6b: Differenz zweier Addierer-Wortgleichungen, deren AUSGANGSUEBERTRAEGE nachweislich gleich sind -> Beziehung nur zwischen Eingangsbits
                if 'R6' in self.AKTIV:
                    for i1 in range(len(addierer)):
                        for i2 in range(i1 + 1, len(addierer)):
                            if (i1, i2) in r6_fertig: continue
                            v1, c1_ = lit(addierer[i1][-1][4]); v2, c2_ = lit(addierer[i2][-1][4])
                            if v1 is None or v2 is None: continue
                            r1, k1 = find(v1); r2, k2 = find(v2)
                            if r1 != r2 or r1 in wert: continue
                            kk = k1 ^ c1_ ^ k2 ^ c2_; t1, _ = self._wort_gl[i1]; t2, _ = self._wort_gl[i2]
                            W = 1 << len(addierer[i1]); W2 = 1 << len(addierer[i2])
                            ohne1 = [(n, c) for (n, c) in t1 if n != addierer[i1][-1][4]]; ohne2 = [(n, c) for (n, c) in t2 if n != addierer[i2][-1][4]]
                            if kk == 0 and W == W2: lin_gl.append((ohne1 + [(n, -c) for (n, c) in ohne2], 0))        # (A - 2^n c) - (B - 2^n c) = 0
                            elif kk == 1 and W == W2: lin_gl.append((ohne1 + ohne2, W)); regeln['R6gegen'] = regeln.get('R6gegen', 0) + 1   # c + c' = 1 -> Summe der Reste = 2^n * (c + c') = W  (korrigiert 2026-10-24, war 2W; Zweig hatte nie gefeuert)
                            else: continue
                            r6_fertig.add((i1, i2)); regeln['R6'] = regeln.get('R6', 0) + 1; geaendert = True
                # R5 gekoppelte Uebertraege: zwei Stufen, deren cout-Literale NACHWEISLICH gleich (oder negiert gleich) sind -> neue lineare Gleichung
                if 'R5' in self.AKTIV:
                    for i1 in range(len(stufen)):
                        for i2 in range(i1 + 1, len(stufen)):
                            if (i1, i2) in r5_fertig: continue
                            v1, c1_ = lit(stufen[i1][4]); v2, c2_ = lit(stufen[i2][4])
                            if v1 is None or v2 is None: continue
                            r1, k1 = find(v1); r2, k2 = find(v2)
                            if r1 != r2 or r1 in wert: continue
                            kk = k1 ^ c1_ ^ k2 ^ c2_               # cout2 = cout1 ^ kk
                            x, y, cin, sb, _ = stufen[i1]; x2, y2, cin2, sb2, _ = stufen[i2]
                            if kk == 0: lin_gl.append(([(x, 1), (y, 1), (cin, 1), (sb, -1), (x2, -1), (y2, -1), (cin2, -1), (sb2, 1)], 0))   # Differenz = 0
                            else: lin_gl.append(([(x, 1), (y, 1), (cin, 1), (sb, -1), (x2, 1), (y2, 1), (cin2, 1), (sb2, -1)], 2))          # Summe = 2
                            r5_fertig.add((i1, i2)); regeln['R5'] = regeln.get('R5', 0) + 1; geaendert = True
                for gl in (lin_gl if 'R4' in self.AKTIV else []):
                    paare_, const0 = gl; terms = {}; const = const0
                    for node, coef in paare_:
                        v, c = lit(node)
                        if v is None: const -= coef * c; continue
                        r, k = find(v); k ^= c                      # Literal-Negation (c) UND Alias-Versatz (k) zusammen
                        if r in wert: const -= coef * (wert[r] ^ k); continue
                        # node = r ^ k  ->  als Zahl: k + (1-2k) r
                        const -= coef * k; terms[r] = terms.get(r, 0) + coef * (1 - 2 * k)
                    terms = {r: c for r, c in terms.items() if c != 0}
                    if not terms:
                        if const != 0: raise ValueError('WIDERSPRUCH')
                        continue
                    mn = sum(min(0, c) for c in terms.values()); mx = sum(max(0, c) for c in terms.values())
                    if const < mn or const > mx: raise ValueError('WIDERSPRUCH')
                    if const == mx:
                        for r, c in terms.items():
                            if setze(r, 1 if c > 0 else 0): geaendert = True; regeln['R4'] += 1
                        continue
                    if const == mn:
                        for r, c in terms.items():
                            if setze(r, 1 if c < 0 else 0): geaendert = True; regeln['R4'] += 1
                        continue
                    if len(terms) == 2:
                        (r1, c1), (r2, c2) = list(terms.items())
                        if c1 == -c2 and const == 0:
                            if verbinde(r1, r2, 0): geaendert = True; regeln['R4'] += 1
                            continue
                        if c1 == c2 and const == c1:
                            if verbinde(r1, r2, 1): geaendert = True; regeln['R4'] += 1
                            continue
                    # (d) Paritaet
                    odd = {r for r, c in terms.items() if c % 2}
                    if odd:
                        eq = (odd, const & 1)
                        if eq not in xor_gl: xor_gl.append(eq); geaendert = True; regeln['R4'] += 1
                # R2 Gauss ueber GF(2) auf den XOR-Gleichungen (mit Aliassen/Werten normalisiert) – NUR wenn R2 aktiv (Ablation 'ohne Gauss' = wirklich ohne)
                frei = set(N.frei); rows = []
                if 'R2' not in self.AKTIV:
                    direkt = {}
                    for vs, c in xor_gl:
                        res, cc = norm_xor(vs, c)
                        if not res:
                            if cc: raise ValueError('WIDERSPRUCH')
                            continue
                        if len(res) == 1:
                            if setze(next(iter(res)), cc): geaendert = True; regeln['R1'] += 1     # Einsetzen-Niveau, kein Gauss
                        elif all(v in frei for v in res): direkt[(frozenset(res), cc)] = (res, cc)   # vollstaendige Gleichungsmenge (Schluessel = Gleichung)
                    self._pivots = direkt
                    continue
                for vs, c in xor_gl:
                    res, cc = norm_xor(vs, c)
                    if not res:
                        if cc: raise ValueError('WIDERSPRUCH')
                        continue
                    rows.append((res, cc))
                # Elimination: Pivot bevorzugt Hilfsgroessen (nicht-freie), damit Beziehungen ueber freie Bits uebrig bleiben
                pivots = {}
                for res, cc in rows:
                    res = set(res)
                    for pv, (prow, pc) in pivots.items():
                        if pv in res: res ^= prow; cc ^= pc
                    if not res:
                        if cc: raise ValueError('WIDERSPRUCH')
                        continue
                    hilfs = [v for v in res if v not in frei]; pv = min(hilfs) if hilfs else min(res)
                    for q, (qrow, qc) in list(pivots.items()):
                        if pv in qrow: pivots[q] = (qrow ^ res, qc ^ cc)
                    pivots[pv] = (res, cc)
                for pv, (res, cc) in list(pivots.items()):
                    if len(res) == 1 and 'R2' in self.AKTIV:
                        if setze(pv, cc): geaendert = True; regeln['R2'] += 1
                    elif len(res) == 2 and 'R3' in self.AKTIV:
                        a_, b_ = sorted(res)
                        if verbinde(a_, b_, cc): geaendert = True; regeln['R3'] += 1
                self._pivots = pivots
        except ValueError:
            status = 'WIDERSPRUCH'
        # Eingefrorene Folgerungen, projiziert auf freie Bits
        frei_idx = {k: i for i, k in enumerate(N.frei)}
        frei_fest = {}
        for k in N.frei:
            r, kk = find(k)
            if r in wert: frei_fest[frei_idx[k]] = wert[r] ^ kk
        frei_xor = []
        if status != 'WIDERSPRUCH':
            # Beziehungen nur ueber freie Bits: aus Pivot-Zeilen, deren Variablen alle frei sind; dazu Aliasse zwischen freien Bits
            for pv, (res, cc) in getattr(self, '_pivots', {}).items():
                if res and all(v in frei_idx for v in res) and len(res) >= 2: frei_xor.append((sorted(frei_idx[v] for v in res), cc))
            for k in N.frei:
                r, kk = find(k)
                if r != k and r in frei_idx and r not in wert: frei_xor.append((sorted([frei_idx[k], frei_idx[r]]), kk))
        frei_xor = sorted({(tuple(a), c) for a, c in frei_xor})
        frei_lin = set()
        if status != 'WIDERSPRUCH' and 'R6' in self.AKTIV:
            for paare_, const0 in lin_gl:
                terms = {}; const = const0; ok = True
                for node, coef in paare_:
                    v, c = lit(node)
                    if v is None: const -= coef * c; continue
                    r, k = find(v); k ^= c
                    if r in wert: const -= coef * (wert[r] ^ k); continue
                    const -= coef * k; terms[r] = terms.get(r, 0) + coef * (1 - 2 * k)
                terms = {r: c for r, c in terms.items() if c != 0}
                if terms and all(r in frei_idx for r in terms) and len(terms) >= 2:
                    frei_lin.add((tuple(sorted((frei_idx[r], c) for r, c in terms.items())), const))
        frei_lin = sorted(frei_lin)
        frei_menge = set()
        if status != 'WIDERSPRUCH' and 'R7' in self.AKTIV:
            for paare_, const0 in lin_gl:
                terms = {}; const = const0
                for node, coef in paare_:
                    v, c = lit(node)
                    if v is None: const -= coef * c; continue
                    r, k = find(v); k ^= c
                    if r in wert: const -= coef * (wert[r] ^ k); continue
                    const -= coef * k; terms[r] = terms.get(r, 0) + coef * (1 - 2 * k)
                terms = {r: c for r, c in terms.items() if c != 0}
                hilfs = [r for r in terms if r not in frei_idx]
                if len(hilfs) == 1 and len(terms) >= 2:
                    h = hilfs[0]; m = terms.pop(h)          # sum(coef*x) + m*h = const, h in {0,1}  ->  sum(coef*x) in {const, const - m}
                    frei_menge.add((tuple(sorted((frei_idx[r], c) for r, c in terms.items())), tuple(sorted({const, const - m}))))
                    regeln['R7'] = regeln.get('R7', 0) + 1
        frei_menge = sorted(frei_menge)
        self._zustand = dict(wert=wert, alias=alias, find=find, lit=lit, lin_gl=lin_gl, xor_gl=xor_gl, pivots=getattr(self, '_pivots', {}), status=status)   # fuer R8l (nur Lesen)
        F = dict(widerspruch=(status == 'WIDERSPRUCH'), frei_fest=frei_fest, frei_xor=[list(a) + [c] for a, c in frei_xor], frei_lin=[[list(map(list, t)), c] for t, c in frei_lin],
                 frei_menge=[[list(map(list, t)), list(w)] for t, w in frei_menge])
        gr = dict(r9_protokoll=list(self._r9_protokoll), r9_stat=r9_stat, xor_gleichungen=len(xor_gl), und_gleichungen=len(und_gl), stufen=len(stufen), werte=len(wert), aliasse=len(alias), regeln=regeln,
                  beziehungen_ueber_freie_bits=[('^'.join('x%d' % i for i in a) + '=%d' % c) for a, c in frei_xor], ganzzahlige_beziehungen=[(' '.join('%+d*x%d' % (c, i) for i, c in t) + ' = %d' % k) for t, k in frei_lin],
                  wertemengen=[(' '.join('%+d*x%d' % (c, i) for i, c in t) + ' in %s' % list(w)) for t, w in frei_menge],
                  feste_freie_bits=len(frei_fest), s=round(time.perf_counter() - t, 4))
        return status, F, gr
    def _kaestchen_exakt(self, knoten4, fn, lit, find, wert, setze, verbinde, xor_gl, regeln, regel):
        """Wahrheitstafel out = fn(a,b,c) (8 Zeilen) mit bekannten Werten und Aliassen aller VIER Anschluesse (als Literale) schneiden.
        Sichere Folgerungen: (a) Anschluss fest, (b) zwei Anschluesse gleich/negiert, (c) XOR dreier Anschluesse konstant (doppelte Wurzeln heben sich auf).
        Leere Tafel -> WIDERSPRUCH. Keine Fallwahl, keine Kandidaten. Liefert True, wenn etwas Neues abgeleitet wurde."""
        lits = []
        for nd in knoten4:
            v, c = lit(nd)
            if v is None: lits.append((None, c))
            else:
                r, k = find(v); k ^= c
                lits.append((None, wert[r] ^ k) if r in wert else (r, k))
        zeilen = []
        for av, bv, cv in itertools.product((0, 1), repeat=3):
            vals = (av, bv, cv, fn(av, bv, cv)); bel = {}; ok = True
            for (r, k), val in zip(lits, vals):
                if r is None:
                    if val != k: ok = False; break
                    continue
                rv = val ^ k
                if r in bel and bel[r] != rv: ok = False; break
                bel[r] = rv
            if ok: zeilen.append(vals)
        if not zeilen: raise ValueError('WIDERSPRUCH')
        offen = [j for j, (r, k) in enumerate(lits) if r is not None]; getan = False
        for j in offen:
            d = {zl[j] for zl in zeilen}
            if len(d) == 1:
                r, k = lits[j]
                if setze(r, d.pop() ^ k): regeln[regel] = regeln.get(regel, 0) + 1; getan = True
        if getan: return True
        for j1, j2 in itertools.combinations(offen, 2):
            (r1, k1), (r2, k2) = lits[j1], lits[j2]
            if r1 == r2: continue
            d = {zl[j1] ^ zl[j2] for zl in zeilen}
            if len(d) == 1:
                if verbinde(r1, r2, d.pop() ^ k1 ^ k2): regeln[regel] = regeln.get(regel, 0) + 1; getan = True
        if getan: return True
        for j1, j2, j3 in itertools.combinations(offen, 3):
            d = {zl[j1] ^ zl[j2] ^ zl[j3] for zl in zeilen}
            if len(d) == 1:
                vs = set(); cc = d.pop()
                for j in (j1, j2, j3): r, k = lits[j]; vs ^= {r}; cc ^= k
                if not vs:
                    if cc: raise ValueError('WIDERSPRUCH')
                    continue
                eq = (vs, cc)
                if eq not in xor_gl: xor_gl.append(eq); regeln[regel] = regeln.get(regel, 0) + 1; getan = True
        return getan
    def _sym(self, vs):
        """XOR mit doppelter Variable: x^x hebt sich auf."""
        s = set()
        for v in vs: s ^= {v}
        return s
    def erlaubt(self, N, belegung, F):
        if F['widerspruch']: return False
        if not all(belegung[int(i)] == w for i, w in F['frei_fest'].items()): return False
        for eq in F['frei_xor']:
            *idx, c = eq
            if sum(belegung[i] for i in idx) % 2 != c: return False
        for terms, c in F.get('frei_lin', []):
            if sum(coef * belegung[i] for i, coef in terms) != c: return False
        for terms, werte in F.get('frei_menge', []):
            if sum(coef * belegung[i] for i, coef in terms) not in werte: return False
        return True

class D6_ohne_R4(D6_Rueckwaertsleine):
    name = 'D6 ohne R4 (Uebertragsregeln aus)'; AKTIV = ('R1', 'R2', 'R3')
class D6_ohne_R3(D6_Rueckwaertsleine):
    name = 'D6 ohne R3 (keine Aliasse)'; AKTIV = ('R1', 'R2', 'R4')
class D6_nur_R4(D6_Rueckwaertsleine):
    name = 'D6 nur R1+R4 (wirklich ohne Gauss, ohne Aliasse)'; AKTIV = ('R1', 'R4')
class D6_R5(D6_Rueckwaertsleine):
    name = 'D6 + R5 (gekoppelte Uebertraege)'; AKTIV = ('R1', 'R2', 'R3', 'R4', 'R5')
class D6_R56(D6_Rueckwaertsleine):
    name = 'D6 + R5 + R6 (gewichtete Elimination, ganzzahlige Beziehungen)'; AKTIV = ('R1', 'R2', 'R3', 'R4', 'R5', 'R6')
class D6_R567(D6_Rueckwaertsleine):
    name = 'D6 + R5 + R6 + R7 (Wertemengen)'; AKTIV = ('R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7')
class D6_R567b(D6_Rueckwaertsleine):
    name = 'D6+R5+R6+R7+R1b (UND-Alias)'; AKTIV = ('R1', 'R1b', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7')
class D6_R567bC_20_22(D6_Rueckwaertsleine):
    name = 'D6+R5+R6+R7+R1b+R8c nur Ch#20,#22'; AKTIV = ('R1', 'R1b', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8c'); R8C_INDICES = (20, 22)
class D6_R567bC(D6_Rueckwaertsleine):
    name = 'D6+R5+R6+R7+R1b+R8c (alle Ch)'; AKTIV = ('R1', 'R1b', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8c')
class D6_R567bCM(D6_Rueckwaertsleine):
    name = 'D6+R5+R6+R7+R1b+R8c+R8m (Ch und Maj exakt)'; AKTIV = ('R1', 'R1b', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8c', 'R8m')
class D6_R9_Auswahl(D6_Rueckwaertsleine):
    name = 'D6+R1b+R8c+R8m+R9 nur Ch#21,Maj#197,#261,#25,#201'; AKTIV = ('R1', 'R1b', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8c', 'R8m', 'R9'); R9_AUSWAHL = {'Ch': [21], 'Maj': [197, 261, 25, 201]}
class D6_R9(D6_Rueckwaertsleine):
    name = 'D6+R1b+R8c+R8m+R9 (alle Kaestchen)'; AKTIV = ('R1', 'R1b', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8c', 'R8m', 'R9')
class D6_R9a_Spiegel(D6_Rueckwaertsleine):
    name = 'D6+R1b+R8c+R8m+R9(5)+R9a Spiegelpaare'; AKTIV = ('R1', 'R1b', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8c', 'R8m', 'R9', 'R9a')
    R9_AUSWAHL = {'Ch': [21], 'Maj': [197, 261, 25, 201]}; R9A_PAARE = [(('Maj', 197), ('Maj', 261)), (('Maj', 25), ('Maj', 201))]
class D6_R9a_Test(D6_Rueckwaertsleine):
    name = 'D6+R9+R9a (alle, nur Gegenproben)'; AKTIV = ('R1', 'R1b', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8c', 'R8m', 'R9', 'R9a')
class D6_R9b_Spiegel(D6_R9a_Spiegel):
    name = 'D6+...+R9a+R9b Spiegelpaare (nie beide 1)'; AKTIV = D6_R9a_Spiegel.AKTIV + ('R9b', 'R9bBr')
class D6_R9b_Test(D6_R9a_Test):
    name = 'D6+R9+R9a+R9b (alle, nur Gegenproben)'; AKTIV = D6_R9a_Test.AKTIV + ('R9b', 'R9bBr')
class D6_Vollscan(D6_Rueckwaertsleine):
    name = 'D6+R1b+R8c+R8m+R9+R9a+R9b VOLLSCAN (alle Paare gleicher Wurzelmenge)'; AKTIV = ('R1', 'R1b', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8c', 'R8m', 'R9', 'R9a', 'R9b', 'R9bBr')
_V = D6_Vollscan.AKTIV
class D6_Vollscan_ohne_R9(D6_Vollscan):   name = 'Vollscan ohne R9';      AKTIV = tuple(r for r in _V if r != 'R9')
class D6_Vollscan_ohne_R9a(D6_Vollscan):  name = 'Vollscan ohne R9a';     AKTIV = tuple(r for r in _V if r != 'R9a')
class D6_Vollscan_ohne_R9b(D6_Vollscan):  name = 'Vollscan ohne R9b';     AKTIV = tuple(r for r in _V if r not in ('R9b', 'R9bBr'))
class D6_Vollscan_ohne_Br(D6_Vollscan):   name = 'Vollscan ohne Bruecke'; AKTIV = tuple(r for r in _V if r != 'R9bBr')
class D6_Vollscan_nur_R9(D6_Vollscan):    name = 'Vollscan nur R9';       AKTIV = tuple(r for r in _V if r not in ('R9a', 'R9b', 'R9bBr'))
class D6_Vollscan_nur_R9a(D6_Vollscan):   name = 'Vollscan nur R9a';      AKTIV = tuple(r for r in _V if r not in ('R9', 'R9b', 'R9bBr'))
class D6_Vollscan_nur_R9b(D6_Vollscan):   name = 'Vollscan nur R9b+Br';   AKTIV = tuple(r for r in _V if r not in ('R9', 'R9a'))
class D6_Vollscan_ohne_R7(D6_Vollscan):     name = 'Vollscan ohne R7';            AKTIV = tuple(r for r in _V if r != 'R7')
class D6_Vollscan_nur_R9b_ohneBr(D6_Vollscan): name = 'Vollscan nur R9b ohne Bruecke'; AKTIV = tuple(r for r in _V if r not in ('R9', 'R9a', 'R9bBr'))
class D6_Vollscan_ohne_R9_Br(D6_Vollscan): name = 'Grundgeruest + R9a + R9b (ohne R9, ohne Bruecke)'; AKTIV = tuple(r for r in _V if r not in ('R9', 'R9bBr'))
