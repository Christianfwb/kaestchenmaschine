"""R10b 'Carry-Save an Bit 0' – kleiner Pruefstand (GO 2026-10-24 17:25). Nur Regel + Gegenproben an Kleinstnetzen; KEINE Anwendung im N5-Netz.
Zwei verkettete Ein-Bit-Additionen OHNE eingehende Uebertraege:  s = a^b, u = a&b ;  t = s^c, v = s&c.
Gemeinsam folgt:  (i) a + b + c = t + 2u + 2v  (ganzzahlig; Summe der beiden Stufengleichungen, s eliminiert)   (ii) u und v nie beide 1  ->  u + v + h = 1, h in {0,1}.
(Daraus u + v = Maj(a,b,c): denn a+b+c = (a^b^c) + 2*Maj(a,b,c) und t = a^b^c.)
ANWENDUNGSBEDINGUNGEN, im Code geprueft (nicht aus Bitnummern abgeleitet): Stufe 1 = (a, b, cin1, s, u), Stufe 2 = (x2, y2, cin2, t, v) mit
  - x2 oder y2 ist GENAU das Summenliteral s von Stufe 1 (derselbe Knoten, NICHT negiert – bei negiertem Link gilt der Ausschluss nicht),
  - cin1 und cin2 sind nachweislich 0: Konstante 0 oder durch Ableitung fester Wert 0 (kein Orakel),
  - u und v sind noch offen (sonst nichts zu tun).
Regel liefert: lin_gl (i), lin_gl (ii) mit frischer Hilfsgroesse, Bruecke: UND-Kaestchen ueber genau (u, v) -> 0. Alles Linearkombination/Folgerung, keine Fallwahl."""
import sys, os, itertools, json, copy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import pruefstand as P, d6, gatter as G

class D6_R10b(d6.D6_Vollscan):
    name = 'Vollscan + R10b (Carry-Save Bit 0)'; AKTIV = d6.D6_Vollscan.AKTIV + ('R10b',)
    def laufen(self, N):
        # R10b wird als Vorverarbeitung + Nachlauf umgesetzt: wir haengen uns in den Formelbestand ueber eine Unterklasse von laufen() ein,
        # indem wir die Stufenliste um 'virtuelle' Gleichungen erweitern. Da d6.laufen die Regeln in einer Schleife bis zum Fixpunkt anwendet und wir
        # d6.py nicht aendern, nutzen wir den Haken self._zustand nach einem ersten Lauf, pruefen die Bedingungen am abgeleiteten Stand (Werte 0 der cin),
        # fuegen die Gleichungen hinzu und lassen d6.laufen erneut laufen (zweiter Fixpunkt). Protokolliert wird jede Anwendung.
        self._r10b = []
        st, F, gr = super().laufen(N)
        if st == 'WIDERSPRUCH': return st, F, gr
        Z = self._zustand; lit, find, wert = Z['lit'], Z['find'], Z['wert']
        def wert_von(node):
            v, c = lit(node)
            if v is None: return c
            r, k = find(v); return (wert[r] ^ k ^ c) if r in wert else None
        def offen(node):
            v, c = lit(node)
            if v is None: return False
            r, k = find(v); return r not in wert
        zusatz = []
        for i, (a, b, cin1, s, u) in enumerate(N.stufen):
            if wert_von(cin1) != 0: continue                                  # Nachweis cin1 = 0 (Konstante oder abgeleitet)
            for j, (x2, y2, cin2, t, v) in enumerate(N.stufen):
                if j == i: continue
                if s not in (x2, y2): continue                                # GENAU dasselbe Summenliteral, nicht negiert (−s zaehlt nicht)
                if wert_von(cin2) != 0: continue                              # Nachweis cin2 = 0
                c = y2 if x2 == s else x2
                if not (offen(u) and offen(v)): continue
                zusatz.append((i, j, a, b, c, t, u, v))
        if not zusatz: gr['R10b'] = 0; return st, F, gr
        # zweiter Lauf mit den Zusatzgleichungen: wir geben sie ueber N.zusatz_lin mit (d6.laufen liest sie nicht) -> deshalb hier direkt in die Formelwelt:
        # einfachster sauberer Weg ohne d6.py zu aendern: Netz um 'Zusatzstufen' erweitern, die d6 als Stufen liest (R4 behandelt sie als lineare Gleichungen).
        # Stufe (x, y, cin, sb, cn) bedeutet x + y + cin = sb + 2 cn. (i) a + b + c = t + 2u + 2v laesst sich NICHT als eine Stufe schreiben (zwei cout-Terme),
        # darum nutzen wir statt dessen den Haken self._zusatz_lin, den diese Unterklasse selbst in einer eigenen Schleife anwendet:
        self._r10b = zusatz
        N_kopie = copy.deepcopy(N)                       # ORIGINALNETZ BLEIBT UNVERAENDERT: Zusatzgleichungen nur in der Kopie (Korrektur 2026-10-24 17:50)
        return self._mit_zusatz(N_kopie, zusatz)
    def _mit_zusatz(self, N, zusatz):
        """Wiederholt d6.laufen, nachdem die Zusatzgleichungen als Stufen/Linearformen in eine Kopie des Netzes eingetragen wurden – ohne d6.py zu aendern:
        (i)  a + b + c = t + 2u + 2v  wird als ZWEI Stufen dargestellt: a + b + c' = t + 2 m  ist nicht moeglich ... deshalb:
        wir schreiben (i) als Stufe mit cin = c und 'Doppel-cout': das geht nicht. Stattdessen: Hilfsknoten m mit Stufe (a, b, c, t, m) [a+b+c = t+2m] und
        lineare Gleichung m = u + v (als zwei Stufen? nein) -> wir nutzen die R5-Form: lin_gl-Eintraege sind in d6.laufen lokal. Daher: eigene Mini-Propagation
        hier NICHT – sondern wir erweitern N.stufen um die Stufe (a, b, c, t, m) mit frischem Knoten m und setzen die Beziehungen m = u + v und u*v = 0 ueber
        ein UND-/XOR-Paar: m = u ^ v (weil u*v = 0) und u & v = 0. Das sind gewoehnliche Gatter-Gleichungen, die d6 lesen kann."""
        g = N.g; neu = []
        for (i, j, a, b, c, t, u, v) in zusatz:
            m = g.gate('xor', u, v)                    # m = u ^ v ; mit u*v = 0 ist das u + v
            und = g.gate('and', u, v)                  # und = u & v ; muss 0 sein
            keiner = g.gate('and', G.inv(u), G.inv(v))  # keiner = ~u & ~v = 1 - u - v  (weil u*v = 0)
            N.stufen.append((a, b, c, t, m))           # Stufe (i):  a + b + c = t + 2 m        (d6 liest N.stufen -> R4/R5/R6/R7)
            N.stufen.append((u, v, keiner, 1, 0))      # Stufe (ii): u + v + keiner = 1 + 2*0   -> ganzzahlig 'nie beide 1' mit Hilfsgroesse keiner
            N.ziel[und] = 0                            # u & v = 0 als Zielwert eines inneren Knotens (Bruecke zu R1)
            neu.append(dict(stufen=(i, j), knoten=dict(a=a, b=b, c=c, t=t, u=u, v=v, m=m, und=und, keiner=keiner)))
        self._r10b_neu = neu
        st, F, gr = d6.D6_Vollscan.laufen(self, N)
        gr['R10b'] = len(neu); gr['r10b_anwendungen'] = neu
        return st, F, gr

def gegenproben():
    prot = []; alle_ok = True
    def lauf(name, nfrei, bau, erwartung, erw_r10b, erw_mit):
        """erw_r10b: erwartete Anwendungen; erw_mit: 'kleiner' (mit < ohne), 'gleich' (mit == ohne), 'exakt' (mit == wahr). Wird GEPRUEFT, nicht nur ausgegeben."""
        nonlocal alle_ok
        alle = list(itertools.product((0, 1), repeat=nfrei))
        N0 = P.Netz(name, nfrei); bau(N0, *N0.frei)
        wahr = [x for x in alle if N0.erfuellt(list(x))]                                   # ORAKEL AM UNVERAENDERTEN ORIGINAL, VOR JEDER ABLEITUNG
        abdruck = (len(N0.g.nodes), dict(N0.ziel), list(N0.stufen))
        out = {}
        for tag, K in (('ohne', d6.D6_Vollscan), ('mit', D6_R10b)):
            D = K(); st, F, gr = D.laufen(N0)
            assert (len(N0.g.nodes), dict(N0.ziel), list(N0.stufen)) == abdruck, 'Originalnetz wurde veraendert!'   # Unveraendertheit geprueft
            erl = [x for x in alle if D.erlaubt(N0, list(x), F)]; verloren = [w for w in wahr if w not in erl]
            out[tag] = dict(status=st, wahr=len(wahr), erlaubt=len(erl), verloren=len(verloren), R10b=gr.get('R10b', 0))
            if verloren: print('FEHLER verloren', name, tag, verloren); sys.exit(3)
        o, m = out['ohne'], out['mit']
        ok = (m['R10b'] == erw_r10b) and ({'kleiner': m['erlaubt'] < o['erlaubt'], 'gleich': m['erlaubt'] == o['erlaubt'], 'exakt': m['erlaubt'] == len(wahr)}[erw_mit])
        alle_ok &= ok
        print('%-58s ohne %3d/%3d | mit %3d/%3d R10b=%d | erwartet R10b=%d, mit %s | %s' % (name, o['erlaubt'], o['wahr'], m['erlaubt'], m['wahr'], m['R10b'], erw_r10b, erw_mit, 'BESTANDEN' if ok else 'GESCHEITERT'))
        prot.append(dict(name=name, erwartung=erwartung, erwartet_r10b=erw_r10b, erwartet_mit=erw_mit, bestanden=ok, **out)); return out
    def kette(N, a, b, c, cin1=0, cin2=0, link_neg=False):
        s = N.xor(a, b, cin1) if cin1 != 0 else N.xor(a, b); u = N.maj(a, b, cin1); N.stufen.append((a, b, cin1, s, u))
        s2 = G.inv(s) if link_neg else s
        t = N.xor(s2, c, cin2) if cin2 != 0 else N.xor(s2, c); v = N.maj(s2, c, cin2); N.stufen.append((s2, c, cin2, t, v))
        return s, u, t, v
    # 1) Vollstaendige Pruefung der Behauptungen an allen 8 Belegungen (reine Wahrheitstafel, kein D6)
    tafel_ok = all((not ((a & b) and ((a ^ b) & c))) and ((a & b) + ((a ^ b) & c) == ((a & b) | (a & c) | (b & c))) for a, b, c in itertools.product((0, 1), repeat=3))
    print('Wahrheitstafel (8 Belegungen): u*v = 0 und u + v = Maj(a,b,c):', 'BESTAETIGT' if tafel_ok else 'VERLETZT'); alle_ok &= tafel_ok
    # 2) Regel sichtbar machen: freie Bits h, d an u, v; Ziel 'u = h, v = d'
    lauf('Kette ohne cin: u=h, v=d (h,d frei) -> h*d=0, h+d=Maj', 5, lambda N,a,b,c,h,d:(lambda s,u,t,v:(N.setze_ziel(N.xor(u,h),0), N.setze_ziel(N.xor(v,d),0)))(*kette(N,a,b,c)), 'Ausschluss sichtbar', 1, 'kleiner')
    lauf('dasselbe, a negiert am Eingang', 5, lambda N,a,b,c,h,d:(lambda s,u,t,v:(N.setze_ziel(N.xor(u,h),0), N.setze_ziel(N.xor(v,d),0)))(*kette(N,G.inv(a),b,c)), 'Ausschluss sichtbar', 1, 'kleiner')
    lauf('dasselbe, c negiert', 5, lambda N,a,b,c,h,d:(lambda s,u,t,v:(N.setze_ziel(N.xor(u,h),0), N.setze_ziel(N.xor(v,d),0)))(*kette(N,a,b,G.inv(c))), 'Ausschluss sichtbar', 1, 'kleiner')
    lauf('Alias a=b (Ziel) -> u=a, v=0', 5, lambda N,a,b,c,h,d:(lambda s,u,t,v:(N.setze_ziel(N.xor(a,b),0), N.setze_ziel(N.xor(u,h),0), N.setze_ziel(N.xor(v,d),0)))(*kette(N,a,b,c)), 'schon ohne exakt, u/v nicht offen', 0, 'gleich')
    lauf('Ziel h=d=1 (beide Uebertraege 1) -> unerfuellbar', 5, lambda N,a,b,c,h,d:(lambda s,u,t,v:(N.setze_ziel(N.xor(u,h),0), N.setze_ziel(N.xor(v,d),0), N.setze_ziel(h,1), N.setze_ziel(d,1)))(*kette(N,a,b,c)), '0 wahr; mit: 0 erlaubt', 0, 'gleich')
    # 3) Gegenproben: Regel darf NICHT greifen
    lauf('NEGIERTER Link (t = ~s ^ c, v = ~s & c): u, v koennen beide 1 sein', 5, lambda N,a,b,c,h,d:(lambda s,u,t,v:(N.setze_ziel(N.xor(u,h),0), N.setze_ziel(N.xor(v,d),0)))(*kette(N,a,b,c,link_neg=True)), 'negierter Link: darf nicht greifen', 0, 'gleich')
    lauf('cin1 = freies Bit e (kein Nachweis 0)', 6, lambda N,a,b,c,h,d,e:(lambda s,u,t,v:(N.setze_ziel(N.xor(u,h),0), N.setze_ziel(N.xor(v,d),0)))(*kette(N,a,b,c,cin1=e)), 'kein Nachweis', 0, 'gleich')
    lauf('cin2 = freies Bit e (kein Nachweis 0)', 6, lambda N,a,b,c,h,d,e:(lambda s,u,t,v:(N.setze_ziel(N.xor(u,h),0), N.setze_ziel(N.xor(v,d),0)))(*kette(N,a,b,c,cin2=e)), 'kein Nachweis', 0, 'gleich')
    lauf('cin1 = e mit Ziel e=1 (nachweislich 1)', 6, lambda N,a,b,c,h,d,e:(lambda s,u,t,v:(N.setze_ziel(e,1), N.setze_ziel(N.xor(u,h),0), N.setze_ziel(N.xor(v,d),0)))(*kette(N,a,b,c,cin1=e)), 'nachweislich 1', 0, 'gleich')
    lauf('cin2 = e mit Ziel e=0 (NACHWEIS 0 durch Ableitung)', 6, lambda N,a,b,c,h,d,e:(lambda s,u,t,v:(N.setze_ziel(e,0), N.setze_ziel(N.xor(u,h),0), N.setze_ziel(N.xor(v,d),0)))(*kette(N,a,b,c,cin2=e)), 'Nachweis 0 durch Ableitung', 1, 'kleiner')
    lauf('zwei UNVERKETTETE Additionen (kein gemeinsames s)', 6, lambda N,a,b,c,h,d,e:(N.stufen.append((a,b,0,N.xor(a,b),N.maj(a,b,0))), N.stufen.append((c,e,0,N.xor(c,e),N.maj(c,e,0))), N.setze_ziel(N.xor(N.maj(a,b,0),h),0), N.setze_ziel(N.xor(N.maj(c,e,0),d),0)), 'unverkettet', 0, 'gleich')
    json.dump(dict(tafel_ok=tafel_ok, proben=prot), open(os.path.join(HERE, 'ERGEBNIS_R10B_GEGENPROBEN.json'), 'w'), indent=1)
    json.dump(dict(tafel_ok=tafel_ok, alle_erwartungen_bestanden=alle_ok, proben=prot), open(os.path.join(HERE, 'ERGEBNIS_R10B_GEGENPROBEN.json'), 'w'), indent=1)
    print('alle R10b-Gegenproben: 0 verlorene Loesungen; Erwartungen', 'ALLE BESTANDEN' if alle_ok else 'GESCHEITERT')
    if not alle_ok: sys.exit(3)

if __name__ == '__main__': gegenproben()
