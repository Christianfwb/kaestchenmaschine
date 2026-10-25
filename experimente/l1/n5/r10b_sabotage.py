"""Pruefstandstest: eine absichtlich UNSOUND gemachte R10b-Variante (greift auch bei negiertem Link) muss am Orakel des UNVERAENDERTEN Originalnetzes
an 'verlorene Loesungen' scheitern. Zeigt, dass die Korrektur (Orakel vor der Ableitung am Original) falsche Ausschluesse sichtbar macht."""
import sys, os, itertools, copy, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import pruefstand as P, d6, gatter as G, r10b
class R10b_SABOTAGE(r10b.D6_R10b):
    name = 'R10b SABOTAGE (greift auch bei negiertem Link – absichtlich unsound)'
    def laufen(self, N):
        st, F, gr = d6.D6_Vollscan.laufen(self, N); Z = self._zustand; lit, find, wert = Z['lit'], Z['find'], Z['wert']
        def wv(node):
            v, c = lit(node)
            if v is None: return c
            r, k = find(v); return (wert[r] ^ k ^ c) if r in wert else None
        zus = []
        for i, (a, b, cin1, s, u) in enumerate(N.stufen):
            if wv(cin1) != 0: continue
            for j, (x2, y2, cin2, t, v) in enumerate(N.stufen):
                if j == i or wv(cin2) != 0: continue
                if s in (x2, y2) or -s in (x2, y2):          # FEHLER ABSICHTLICH: negierter Link zugelassen
                    c = y2 if x2 in (s, -s) else x2; zus.append((i, j, a, b, c, t, u, v))
        return self._mit_zusatz(copy.deepcopy(N), zus) if zus else (st, F, gr)
if __name__ == '__main__':
    name = 'SABOTAGE: negierter Link'; nfrei = 5; alle = list(itertools.product((0, 1), repeat=nfrei))
    N0 = P.Netz(name, nfrei); a, b, c, h, d = N0.frei
    s = N0.xor(a, b); u = N0.maj(a, b, 0); N0.stufen.append((a, b, 0, s, u)); s2 = G.inv(s); t = N0.xor(s2, c); v = N0.maj(s2, c, 0); N0.stufen.append((s2, c, 0, t, v))
    N0.setze_ziel(N0.xor(u, h), 0); N0.setze_ziel(N0.xor(v, d), 0)
    wahr = [x for x in alle if N0.erfuellt(list(x))]
    D = R10b_SABOTAGE(); st, F, gr = D.laufen(N0); erl = [x for x in alle if D.erlaubt(N0, list(x), F)]; verloren = [w for w in wahr if w not in erl]
    r = dict(wahr=len(wahr), erlaubt=len(erl), verloren=len(verloren), erkannt=bool(verloren)); json.dump(r, open(os.path.join(HERE, 'ERGEBNIS_R10B_SABOTAGE.json'), 'w'), indent=1)
    print('Sabotage-Regel: wahr %d, erlaubt %d, VERLOREN %d -> %s' % (len(wahr), len(erl), len(verloren), 'FEHLER ERKANNT (Pruefstand faengt die unsound Regel)' if verloren else 'NICHT erkannt – Pruefstand unzureichend'))
    sys.exit(0 if verloren else 3)
