"""Gegenproben fuer R8c (Ch exakt, alle vier Anschluesse als Literale) und den korrigierten R6-Zweig 'gegensaetzliche Uebertraege'.
Jedes Netz: alle Belegungen gegen das Orakel, jeweils OHNE und MIT der geprueften Regel. Verlorene Loesungen muessen 0 sein (sonst Abbruch)."""
import itertools, json, sys
import pruefstand as P, d6, gatter as G

def ch(N, e, f, g):
    z = N.xor(N.und(e, f), N.und(G.inv(e), g)); N.ch_kaestchen = getattr(N, 'ch_kaestchen', []) + [(e, f, g, z)]; return z

def lauf(name, nfrei, bau, ohne, mit):
    zeile = dict(name=name)
    for tag, K in (('ohne', ohne), ('mit', mit)):
        N = P.Netz(name, nfrei); bau(N, *N.frei); D = K(); st, F, gr = D.laufen(N)
        alle = list(itertools.product((0, 1), repeat=nfrei)); wahr = [b for b in alle if N.erfuellt(list(b))]; erl = [b for b in alle if D.erlaubt(N, list(b), F)]
        verloren = [w for w in wahr if w not in erl]
        zeile[tag] = dict(status=st, wahr=len(wahr), erlaubt=len(erl), verloren=len(verloren), regeln={k: v for k, v in gr['regeln'].items() if k in ('R8c', 'R6gegen')}, bez=gr['beziehungen_ueber_freie_bits'])
        if verloren: print('FEHLER: verlorene Loesungen in', name, tag, verloren); sys.exit(3)
    o, m = zeile['ohne'], zeile['mit']
    print('%-44s ohne %s %2d/%2d | mit %s %2d/%2d %s' % (name, o['status'][:4], o['erlaubt'], o['wahr'], m['status'][:4], m['erlaubt'], m['wahr'], m['regeln']))
    return zeile

prot = []
# ---- R8c: h frei, Ziel z XOR h = 0 macht die Folgerung an den freien Bits sichtbar ----
A, B_ = d6.D6_R567b, d6.D6_R567bC
R8C = [
 ('f=g -> z=f',                 4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(f,g),0), N.setze_ziel(N.xor(ch(N,e,f,g),h),0))),
 ('f=~g -> z^e^f=1',            4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(f,g),1), N.setze_ziel(N.xor(ch(N,e,f,g),h),0))),
 ('e=f,g=0 -> z=e',             4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(e,f),0), N.setze_ziel(g,0), N.setze_ziel(N.xor(ch(N,e,f,g),h),0))),
 ('e=f,g=1 -> z=1',             4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(e,f),0), N.setze_ziel(g,1), N.setze_ziel(N.xor(ch(N,e,f,g),h),0))),
 ('e=~f,g=0 -> z=0',            4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(e,f),1), N.setze_ziel(g,0), N.setze_ziel(N.xor(ch(N,e,f,g),h),0))),
 ('e=~f,g=1 -> z=~e',           4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(e,f),1), N.setze_ziel(g,1), N.setze_ziel(N.xor(ch(N,e,f,g),h),0))),
 ('Ch(~e,f,~g) f=~g -> z=f',    4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(f,g),1), N.setze_ziel(N.xor(ch(N,G.inv(e),f,G.inv(g)),h),0))),
 ('Ch(e,~f,g) e=~f,g=0 -> z=e', 4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(e,f),1), N.setze_ziel(g,0), N.setze_ziel(N.xor(ch(N,e,G.inv(f),g),h),0))),
 # z als NEGATIVES Literal: Ch(e,~f,~g) = ~Ch(e,f,g) -> gate liefert negierten Knoten
 ('z negativ: Ch(e,~f,~g), f=g -> z=~f', 4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(f,g),0), N.setze_ziel(N.xor(ch(N,e,G.inv(f),G.inv(g)),h),0))),
 ('z negativ: Ch(e,~f,~g), e=f,g=0 -> z=~e', 4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(e,f),0), N.setze_ziel(g,0), N.setze_ziel(N.xor(ch(N,e,G.inv(f),G.inv(g)),h),0))),
 # z bekannt, Rueckschluss auf Eingaenge: z=1 mit e=0 -> g=1; z=0 mit f=g -> f=0
 ('z=1, e=0 -> g=1',            4, lambda N,e,f,g,h:(N.setze_ziel(e,0), N.setze_ziel(ch(N,e,f,g),1), N.setze_ziel(N.xor(g,h),0))),
 ('z=0, f=g -> f=0',            4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(f,g),0), N.setze_ziel(ch(N,e,f,g),0), N.setze_ziel(N.xor(f,h),0))),
 # z aliasiert mit einem Eingang: z=e (als Ziel) -> Ch(e,f,g)=e heisst e=1->f=1, e=0->g=0: keine lineare Folgerung, R8c darf nichts Falsches tun
 ('z=e vorgegeben (nicht linear)', 4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(ch(N,e,f,g),e),0), N.setze_ziel(N.xor(f,h),0))),
 ('z=~g vorgegeben -> e=1, f=~g',  4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(ch(N,e,f,g),g),1), N.setze_ziel(N.xor(f,h),0))),
 ('e=g -> z=e&f (nicht linear)', 4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(e,g),0), N.setze_ziel(N.xor(ch(N,e,f,g),h),0))),
 ('nichts bekannt',              4, lambda N,e,f,g,h:(N.setze_ziel(N.xor(ch(N,e,f,g),h),0),)),
 ('unerfuellbar: f=g, z=~f',     3, lambda N,e,f,g:(N.setze_ziel(N.xor(f,g),0), N.setze_ziel(N.xor(ch(N,e,f,g),f),1))),
 ('unerfuellbar: e=f,g=0, z=~e', 3, lambda N,e,f,g:(N.setze_ziel(N.xor(e,f),0), N.setze_ziel(g,0), N.setze_ziel(N.xor(ch(N,e,f,g),e),1))),
]
print('== R8c ==')
for name, n, bau in R8C: prot.append(dict(regel='R8c', **lauf(name, n, bau, A, B_)))
# ---- R6 gegensaetzliche Uebertraege: zwei gleich breite Addierer, cout_A = NOT cout_B als Ziel ----
class R6aus(d6.D6_Rueckwaertsleine): name='ohne R6'; AKTIV=('R1','R1b','R2','R3','R4','R5','R7')
R6 = [
 ('2-Bit: a+b, c+d, coutA=~coutB, Summen frei',  8, lambda N,*x:(lambda sA,cA,sB,cB:(N.setze_ziel(N.xor(cA,cB),1), N.setze_ziel(N.xor(sA[0],sB[0]),0), N.setze_ziel(N.xor(sA[1],sB[1]),0)))(*[v for i,(v) in enumerate(N.add_bits(list(x[0:2]),list(x[2:4]))) if i!=1]+[v for i,(v) in enumerate(N.add_bits(list(x[4:6]),list(x[6:8]))) if i!=1])),
 ('2-Bit: coutA=~coutB, sA=1, sB=2',           8, lambda N,*x:(lambda sA,cA,sB,cB:(N.setze_ziel(N.xor(cA,cB),1), N.setze_ziel(sA[0],1), N.setze_ziel(sA[1],0), N.setze_ziel(sB[0],0), N.setze_ziel(sB[1],1)))(*[v for i,(v) in enumerate(N.add_bits(list(x[0:2]),list(x[2:4]))) if i!=1]+[v for i,(v) in enumerate(N.add_bits(list(x[4:6]),list(x[6:8]))) if i!=1])),
 ('3-Bit geteilt x0,x1: coutA=~coutB, sA=5, sB=6', 10, lambda N,*x:(lambda sA,cA,sB,cB:(N.setze_ziel(N.xor(cA,cB),1), [N.setze_ziel(s_,v) for s_,v in ((sA[0],1),(sA[1],0),(sA[2],1),(sB[0],0),(sB[1],1),(sB[2],1))]))(*[v for i,(v) in enumerate(N.add_bits([x[0],x[1],x[2]],[x[3],x[4],x[5]])) if i!=1]+[v for i,(v) in enumerate(N.add_bits([x[0],x[1],x[6]],[x[7],x[8],x[9]])) if i!=1])),
]
print('== R6 gegensaetzliche Uebertraege (korrigiert: Summe der Reste = W) ==')
for name, n, bau in R6: prot.append(dict(regel='R6gegen', **lauf(name, n, bau, R6aus, d6.D6_R567b)))
json.dump(prot, open('ERGEBNIS_GEGENPROBEN_R8C_R6.json', 'w'), indent=1)
print('alle Gegenproben: 0 verlorene Loesungen')
