"""Gegenproben R8m (Maj exakt): alle Belegungen gegen Orakel, ohne (D6+R1b+R8c) / mit (D6+R1b+R8c+R8m). Verloren muss 0 sein."""
import itertools, json, sys
import pruefstand as P, d6, gatter as G
def lauf(name, nfrei, bau):
    zeile = dict(name=name)
    for tag, K in (('ohne', d6.D6_R567bC), ('mit', d6.D6_R567bCM)):
        N = P.Netz(name, nfrei); bau(N, *N.frei); D = K(); st, F, gr = D.laufen(N)
        alle = list(itertools.product((0, 1), repeat=nfrei)); wahr = [b for b in alle if N.erfuellt(list(b))]; erl = [b for b in alle if D.erlaubt(N, list(b), F)]
        verloren = [w for w in wahr if w not in erl]
        zeile[tag] = dict(status=st, wahr=len(wahr), erlaubt=len(erl), verloren=len(verloren), R8m=gr['regeln'].get('R8m', 0), bez=gr['beziehungen_ueber_freie_bits'])
        if verloren: print('FEHLER verloren', name, tag, verloren); sys.exit(3)
    o, m = zeile['ohne'], zeile['mit']; print('%-44s ohne %s %3d/%3d | mit %s %3d/%3d R8m=%d' % (name, o['status'][:4], o['erlaubt'], o['wahr'], m['status'][:4], m['erlaubt'], m['wahr'], m['R8m'])); return zeile
M = lambda N, a, b, c: N.maj(a, b, c)
F = [
 ('Maj(a,a,c)=a  (h=out)',           4, lambda N,a,b,c,h:(N.setze_ziel(N.xor(a,b),0), N.setze_ziel(N.xor(M(N,a,b,c),h),0))),
 ('Maj(a,~a,c)=c',                   4, lambda N,a,b,c,h:(N.setze_ziel(N.xor(a,b),1), N.setze_ziel(N.xor(M(N,a,b,c),h),0))),
 ('Maj(a,b,~a)=b',                   4, lambda N,a,b,c,h:(N.setze_ziel(N.xor(a,c),1), N.setze_ziel(N.xor(M(N,a,b,c),h),0))),
 ('Maj(a,b,b)=b',                    4, lambda N,a,b,c,h:(N.setze_ziel(N.xor(b,c),0), N.setze_ziel(N.xor(M(N,a,b,c),h),0))),
 ('Maj(~a,a,c) negierte Eingaenge=c',4, lambda N,a,b,c,h:(N.setze_ziel(N.xor(a,b),0), N.setze_ziel(N.xor(M(N,G.inv(a),b,c),h),0))),
 ('Maj(~a,~b,~c)=~Maj -> out negativ, a=b', 4, lambda N,a,b,c,h:(N.setze_ziel(N.xor(a,b),0), N.setze_ziel(N.xor(M(N,G.inv(a),G.inv(b),G.inv(c)),h),0))),
 ('b=1: Maj=a OR c (nicht linear)',  4, lambda N,a,b,c,h:(N.setze_ziel(b,1), N.setze_ziel(N.xor(M(N,a,b,c),h),0))),
 ('b=0: Maj=a AND c (nicht linear)', 4, lambda N,a,b,c,h:(N.setze_ziel(b,0), N.setze_ziel(N.xor(M(N,a,b,c),h),0))),
 ('out=1, a=0 -> b=c=1',             4, lambda N,a,b,c,h:(N.setze_ziel(a,0), N.setze_ziel(M(N,a,b,c),1), N.setze_ziel(N.xor(b,h),0))),
 ('out=0, a=1 -> b=c=0',             4, lambda N,a,b,c,h:(N.setze_ziel(a,1), N.setze_ziel(M(N,a,b,c),0), N.setze_ziel(N.xor(c,h),0))),
 ('out=~a vorgegeben -> b=c=~a',     4, lambda N,a,b,c,h:(N.setze_ziel(N.xor(M(N,a,b,c),a),1), N.setze_ziel(N.xor(b,h),0))),
 ('out=a vorgegeben (nicht linear)', 4, lambda N,a,b,c,h:(N.setze_ziel(N.xor(M(N,a,b,c),a),0), N.setze_ziel(N.xor(b,h),0))),
 ('nichts bekannt',                  4, lambda N,a,b,c,h:(N.setze_ziel(N.xor(M(N,a,b,c),h),0),)),
 ('unerfuellbar: a=b, out=~a',       3, lambda N,a,b,c:(N.setze_ziel(N.xor(a,b),0), N.setze_ziel(N.xor(M(N,a,b,c),a),1))),
 ('unerfuellbar: a=~b, out=~c',      3, lambda N,a,b,c:(N.setze_ziel(N.xor(a,b),1), N.setze_ziel(N.xor(M(N,a,b,c),c),1))),
 ('Uebertrag im Addierer: a=b -> cout=a (2-Bit, Summe frei)', 5, lambda N,a,b,c,d,h:(N.setze_ziel(N.xor(a,b),0), N.setze_ziel(N.xor(N.add_bits([a,c],[b,d])[2],h),0))),
]
prot = [lauf(*f) for f in F]; json.dump(prot, open('ERGEBNIS_GEGENPROBEN_R8M.json', 'w'), indent=1); print('alle R8m-Gegenproben: 0 verlorene Loesungen')
