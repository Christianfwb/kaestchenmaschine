"""KARTE des Endstands (nur Lesen, keine Regel, keine Weitergabe): Welche Ch-/Maj-Kaestchen sind am N4r09 nach D6+R1b+R8c+R8m noch offen,
welche lokale Relation bleibt in ihnen, welcher Teil davon ist durch Werte/Gleichheiten/XOR schon ausgedrueckt, welcher Rest geht verloren,
und welche Anschluesse teilen sich die offenen Kaestchen (insbesondere Verbindungen zu den freien Bits = wiederverwendete Woerter W0,W1,W2).
Aufruf: python3 karte.py N4r09 [Darstellung]"""
import sys, json, itertools, collections
import pruefstand as P

CH = lambda a, b, c: b if a else c
MAJ = lambda a, b, c: (a & b) | (a & c) | (b & c)

def karte(N, D):
    st, F, gr = D.laufen(N); Z = D._zustand; lit, find, wert, pivots = Z['lit'], Z['find'], Z['wert'], Z['pivots']
    frei = {k: i for i, k in enumerate(N.frei)}
    def wort(i): return 'W%d.b%d' % (i // 4, i % 4)
    def anschluss(nd):
        v, c = lit(nd)
        if v is None: return dict(art='konst', wert=c)
        r, k = find(v); k ^= c
        if r in wert: return dict(art='wert', wert=wert[r] ^ k, wurzel=r)
        return dict(art='offen', wurzel=r, neg=k, frei=(wort(frei[r]) if r in frei else None))
    boxen = []
    for typ, liste, runden, fn in (('Ch', N.ch_kaestchen, N.ch_runde, CH), ('Maj', N.maj_kaestchen, N.maj_runde, MAJ)):
        for ci, (kn, rd) in enumerate(zip(liste, runden)):
            A = [anschluss(nd) for nd in kn]
            offen = [j for j, a in enumerate(A) if a['art'] == 'offen']
            if not offen: boxen.append(dict(typ=typ, index=ci, runde=rd, status='fest')); continue
            # R: Zeilen der Wahrheitstafel, vertraeglich mit Werten und Aliassen (exakte lokale Relation)
            R = []
            for av, bv, cv in itertools.product((0, 1), repeat=3):
                vals = (av, bv, cv, fn(av, bv, cv)); bel = {}; ok = True
                for a, val in zip(A, vals):
                    if a['art'] == 'konst' or a['art'] == 'wert':
                        if val != a['wert']: ok = False; break
                    else:
                        rv = val ^ a['neg']
                        if a['wurzel'] in bel and bel[a['wurzel']] != rv: ok = False; break
                        bel[a['wurzel']] = rv
                if ok: R.append(vals)
            # L: Zeilen ueber die offenen Anschluesse, die D6s LINEARE Kenntnis (Werte, Aliasse, XOR-Pivots ueber diese Wurzeln) zulaesst – OHNE die Funktion
            wurzeln = sorted({A[j]['wurzel'] for j in offen})
            xors = [(res, cc) for pv, (res, cc) in pivots.items() if res and all(r in wurzeln for r in res)]
            L = []
            for w in itertools.product((0, 1), repeat=len(wurzeln)):
                bel = dict(zip(wurzeln, w))
                if all(sum(bel[r] for r in res) % 2 == cc for res, cc in xors): L.append(bel)
            # Projektion von R auf die Wurzelbelegungen
            Rw = set()
            for vals in R:
                bel = {}
                for j in offen: bel[A[j]['wurzel']] = vals[j] ^ A[j]['neg']
                Rw.add(tuple(bel[r] for r in wurzeln))
            Lw = {tuple(b[r] for r in wurzeln) for b in L}
            verloren = Lw - Rw               # Kombinationen, die D6 linear zulaesst, die Kaestchen aber ausschliesst
            # Wie laesst sich R beschreiben? fest/paar/xor3 ueber offene Anschluesse (das, was R8 bereits ausgedrueckt haette)
            beschreibbar = []
            for j in offen:
                d = {v[j] for v in R}
                if len(d) == 1: beschreibbar.append('%s=%d' % ('efgz'[j] if typ == 'Ch' else 'abcm'[j], d.pop()))
            for j1, j2 in itertools.combinations(offen, 2):
                d = {v[j1] ^ v[j2] for v in R}
                if len(d) == 1: beschreibbar.append('%s^%s=%d' % tuple(list(('efgz' if typ == 'Ch' else 'abcm')[j] for j in (j1, j2)) + [d.pop()]))
            for tri in itertools.combinations(offen, 3):
                d = {v[tri[0]] ^ v[tri[1]] ^ v[tri[2]] for v in R}
                if len(d) == 1: beschreibbar.append('^'.join(('efgz' if typ == 'Ch' else 'abcm')[j] for j in tri) + '=%d' % d.pop())
            namen = 'efgz' if typ == 'Ch' else 'abcm'
            boxen.append(dict(typ=typ, index=ci, runde=rd, status='offen', offene_anschluesse=[namen[j] for j in offen], wurzeln=wurzeln,
                frei_anschluesse={namen[j]: A[j]['frei'] for j in offen if A[j]['frei']},
                relation_zeilen=len(R), linear_zugelassen=len(Lw), rest_verloren=len(verloren), beschreibbar=beschreibbar,
                relation=[''.join(str(x) for x in v) for v in R], verlorene_kombinationen=[''.join(str(x) for x in t) for t in sorted(verloren)]))
    # Funktionstafeln NORMIERT (Wurzeln sortiert, Vorzeichen der Eingaenge UND des Ausgangs beruecksichtigt): gleiche Tafel = gleiche Funktion
    funktionen = collections.defaultdict(list)
    for typ, liste, runden, fn in (('Ch', N.ch_kaestchen, N.ch_runde, CH), ('Maj', N.maj_kaestchen, N.maj_runde, MAJ)):
        for ci, (kn, rd) in enumerate(zip(liste, runden)):
            A = [anschluss(nd) for nd in kn]
            if A[3]['art'] != 'offen' or any(a['art'] == 'offen' and not a['frei'] for a in A[:3]): continue
            wz = sorted({a['wurzel'] for a in A[:3] if a['art'] == 'offen'})
            if not wz: continue
            tafel = []
            for w in itertools.product((0, 1), repeat=len(wz)):
                bel = dict(zip(wz, w)); ein = [a['wert'] if a['art'] != 'offen' else bel[a['wurzel']] ^ a['neg'] for a in A[:3]]
                tafel.append(fn(*ein) ^ A[3]['neg'])
            funktionen[(tuple(wort(frei[r]) for r in wz), tuple(tafel))].append('%s#%d(R%s) Ausgangswurzel %d' % (typ, ci, rd, A[3]['wurzel']))
    gleiche_funktion = {str(k): v for k, v in funktionen.items() if len(v) > 1}
    alle_funktionen = {str(k): v for k, v in funktionen.items()}
    # TAFELN UEBER ALLEN WURZELN (innere und freie, mit Vorzeichen; R9-Normierung): Gruppen gleicher Wurzelmenge, Paare nach Beziehung gezaehlt
    alle_tafeln = {}
    for typ, liste, runden, fn in (('Ch', N.ch_kaestchen, N.ch_runde, CH), ('Maj', N.maj_kaestchen, N.maj_runde, MAJ)):
        for ci, (kn, rd) in enumerate(zip(liste, runden)):
            A = [anschluss(nd) for nd in kn]
            if A[3]['art'] != 'offen': continue
            wz = sorted({a['wurzel'] for a in A[:3] if a['art'] == 'offen'})
            if not wz: continue
            tafel = []
            for w in itertools.product((0, 1), repeat=len(wz)):
                bel = dict(zip(wz, w)); ein = [a['wert'] if a['art'] != 'offen' else bel[a['wurzel']] ^ a['neg'] for a in A[:3]]
                tafel.append(fn(*ein) ^ A[3]['neg'])
            alle_tafeln[(typ, ci)] = (tuple(wz), tuple(tafel), A[3]['wurzel'], rd)
    gruppen = collections.defaultdict(list)
    for key, (wz, tf, out, rd) in alle_tafeln.items(): gruppen[wz].append(key)
    paar_stat = collections.Counter(); paar_liste = []
    for wz, keys in gruppen.items():
        n = len(wz)
        for k1, k2 in itertools.combinations(sorted(keys), 2):
            t1, o1, r1 = alle_tafeln[k1][1], alle_tafeln[k1][2], alle_tafeln[k1][3]; t2, o2, r2 = alle_tafeln[k2][1], alle_tafeln[k2][2], alle_tafeln[k2][3]
            if o1 == o2: paar_stat['gleiche_ausgangswurzel'] += 1; continue
            diff = [x ^ y for x, y in zip(t1, t2)]; zeilen_w = list(itertools.product((0, 1), repeat=n)); c0 = diff[0]
            koeff = [diff[zeilen_w.index(tuple(1 if j == i else 0 for j in range(n)))] ^ c0 for i in range(n)]
            affin = all(d == (c0 ^ (sum(k * w for k, w in zip(koeff, zeilen_w[idx])) & 1)) for idx, d in enumerate(diff))
            art = 'gleich' if t1 == t2 else ('komplementaer' if all(x != y for x, y in zip(t1, t2)) else ('affin' if affin else 'nicht affin'))
            nie_beide = all(not (x and y) for x, y in zip(t1, t2)); paar_stat[art] += 1; paar_stat['nie_beide_1'] += nie_beide
            paar_liste.append(dict(paar=['%s#%d(R%s)' % (k1[0], k1[1], r1), '%s#%d(R%s)' % (k2[0], k2[1], r2)], wurzeln=[('x%d' % frei[r]) if r in frei else ('w%d' % r) for r in wz], art=art, nie_beide_1=nie_beide))
    tafel_stat = dict(kaestchen_mit_tafel=len(alle_tafeln), wurzelmengen=len(gruppen), wurzelmengen_mit_mehreren=sum(1 for v in gruppen.values() if len(v) > 1),
                      paare=sum(paar_stat[k] for k in ('gleich', 'komplementaer', 'affin', 'nicht affin', 'gleiche_ausgangswurzel')), nach_art=dict(paar_stat),
                      wurzelmengen_nur_freie_bits=sum(1 for wz in gruppen if all(r in frei for r in wz)), wurzelmengen_mit_inneren=sum(1 for wz in gruppen if any(r not in frei for r in wz)))
    # gemeinsame Anschluesse zwischen offenen Kaestchen
    teil = collections.defaultdict(list)
    for b in boxen:
        if b['status'] == 'offen':
            for r in b['wurzeln']: teil[r].append('%s#%d(R%s)' % (b['typ'], b['index'], b['runde']))
    gemeinsam = {str(r): v for r, v in teil.items() if len(v) > 1}
    freie_wurzeln = {str(r): dict(bit=wort(frei[r]), kaestchen=v) for r, v in teil.items() if r in frei}
    return dict(netz=N.name, darstellung=D.name, status=st, erlaubt_bez=gr['beziehungen_ueber_freie_bits'], boxen=boxen, gemeinsame_wurzeln=gemeinsam, freie_bits_an_kaestchen=freie_wurzeln, funktionen_ueber_freien_bits_normiert=alle_funktionen, gleiche_funktion_normiert=gleiche_funktion, tafeln_ueber_allen_wurzeln=tafel_stat, paare_ueber_allen_wurzeln=paar_liste)

if __name__ == '__main__':
    netz = sys.argv[1] if len(sys.argv) > 1 else 'N4r09'; dn = sys.argv[2] if len(sys.argv) > 2 else 'D6+R1b+R8c+R8m'
    N = P.NETZE[netz](); D = P.DARSTELLUNGEN[dn](); K = karte(N, D)
    json.dump(K, open('KARTE_%s.json' % netz, 'w'), indent=1, default=str)
    off = [b for b in K['boxen'] if b['status'] == 'offen']; fest = [b for b in K['boxen'] if b['status'] == 'fest']
    print('%s | %s | %s' % (K['netz'], K['darstellung'], K['status']))
    print('Kaestchen gesamt %d: fest %d, offen %d (Ch offen %d von %d, Maj offen %d von %d)' % (len(K['boxen']), len(fest), len(off),
        sum(1 for b in off if b['typ'] == 'Ch'), sum(1 for b in K['boxen'] if b['typ'] == 'Ch'), sum(1 for b in off if b['typ'] == 'Maj'), sum(1 for b in K['boxen'] if b['typ'] == 'Maj')))
    mit_rest = [b for b in off if b['rest_verloren'] > 0]
    print('Offene Kaestchen MIT verlorenem Rest (linear zugelassen > Relation): %d; ohne Rest (vollstaendig ausgedrueckt): %d' % (len(mit_rest), len(off) - len(mit_rest)))
    print('Je Runde (offen/mit Rest):', {r: (sum(1 for b in off if b['runde'] == r), sum(1 for b in mit_rest if b['runde'] == r)) for r in sorted({b['runde'] for b in off}, key=lambda r: -1 if r is None else r)})
    print('Verteilung der Relationsgroessen (Zeilen) bei Kaestchen mit Rest:', collections.Counter((b['typ'], b['relation_zeilen'], b['linear_zugelassen']) for b in mit_rest))
    print('Gemeinsame Wurzeln zwischen offenen Kaestchen: %d; davon freie Bits: %d' % (len(K['gemeinsame_wurzeln']), len(K['freie_bits_an_kaestchen'])))
    for r, v in sorted(K['freie_bits_an_kaestchen'].items(), key=lambda kv: kv[1]['bit']): print('  freies Bit %s an: %s' % (v['bit'], ' '.join(v['kaestchen'])))
    print('TAFELN UEBER ALLEN WURZELN (innere + freie, mit Vorzeichen):', K['tafeln_ueber_allen_wurzeln'])
    print('Funktionen ueber freien Bits (NORMIERT, mit Vorzeichen):'); [print('   ', k, '<-', v, '** GLEICH' if len(v) > 1 else '') for k, v in K['funktionen_ueber_freien_bits_normiert'].items()]
    print('--- Kaestchen mit Rest, die an freien Bits haengen ---')
    for b in mit_rest:
        if b['frei_anschluesse']: print('  %s#%d R%s offen %s frei %s | Relation %d Zeilen, linear %d, Rest %d | beschreibbar %s | Rel %s | verloren %s' % (
            b['typ'], b['index'], b['runde'], ''.join(b['offene_anschluesse']), b['frei_anschluesse'], b['relation_zeilen'], b['linear_zugelassen'], b['rest_verloren'], b['beschreibbar'], b['relation'], b['verlorene_kombinationen']))
