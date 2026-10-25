"""Gegenproben R9b 'nie beide 1' (p+q+h=1): ohne = D6+R9+R9a, mit = +R9b (alle Paare). Alle Belegungen gegen Orakel; verloren muss 0 sein.
Sichtbar gemacht ueber Ziele, die den Rest p+q<=1 brauchen: z.B. Summe p+q als 2-Bit-Addition mit Ziel 'Uebertrag = 1' (unerfuellbar) oder 'p=1' -> q=0."""
import itertools, json, sys
import pruefstand as P, d6, gatter as G
def ch(N,e,f,g):
    z=N.xor(N.und(e,f),N.und(G.inv(e),g)); N.ch_kaestchen=getattr(N,'ch_kaestchen',[])+[(e,f,g,z)]; N.ch_runde=getattr(N,'ch_runde',[])+[0]; return z
def lauf(name,nfrei,bau,erw):
    zeile=dict(name=name,erwartung=erw)
    for tag,K in (('ohne',d6.D6_R9a_Test),('mit',d6.D6_R9b_Test)):
        N=P.Netz(name,nfrei); bau(N,*N.frei); D=K(); st,F,gr=D.laufen(N)
        alle=list(itertools.product((0,1),repeat=nfrei)); wahr=[b for b in alle if N.erfuellt(list(b))]; erl=[b for b in alle if D.erlaubt(N,list(b),F)]
        verloren=[w for w in wahr if w not in erl]
        zeile[tag]=dict(status=st,wahr=len(wahr),erlaubt=len(erl),verloren=len(verloren),R9b=gr['regeln'].get('R9b',0),R9a=gr['regeln'].get('R9a',0),bez=gr['beziehungen_ueber_freie_bits'],mengen=gr['wertemengen'])
        if verloren: print('FEHLER verloren',name,tag,verloren); sys.exit(3)
    o,m=zeile['ohne'],zeile['mit']; print('%-58s ohne %s %3d/%3d | mit %s %3d/%3d R9a=%d R9b=%d | Bez %s Mengen %s | %s'%(name,o['status'][:4],o['erlaubt'],o['wahr'],m['status'][:4],m['erlaubt'],m['wahr'],m['R9a'],m['R9b'],m['bez'],m['mengen'],erw)); return zeile
Z0,Z1=0,1
P_=lambda N,a,b: N.maj(a,G.inv(b),Z0)   # p = a & ~b
Q_=lambda N,a,b: N.maj(G.inv(a),b,Z0)   # q = ~a & b
F=[
 ('Spiegel: p=1 als Ziel -> q=0 (h frei = q)',            3, lambda N,a,b,h:(N.setze_ziel(P_(N,a,b),1), N.setze_ziel(N.xor(Q_(N,a,b),h),0)), 'h=0 fest; ohne: schon durch R1/R8 (p=1 -> a=1,b=0 -> q=0)'),
 ('Spiegel: Addierer p+q, Ziel Uebertrag=1 -> unerfuellbar', 2, lambda N,a,b:(lambda s_,c_,co:(N.setze_ziel(co,1)))(*N.add_bits([P_(N,a,b)],[Q_(N,a,b)])), 'WIDERSPRUCH erwartet (p+q<=1)'),
 ('Spiegel: p+q als Addierer, Summe frei h: h = p^q = a^b', 3, lambda N,a,b,h:(lambda s_,c_,co:(N.setze_ziel(N.xor(s_[0],h),0)))(*N.add_bits([P_(N,a,b)],[Q_(N,a,b)])), 'Bez h^a^b=0 (R9a), R9b liefert cout=0'),
 ('Spiegel vertauscht/negiert: p=~a&b (Ch(~a,b,0)), q=a&~b (Maj(a,~b,0))', 3, lambda N,a,b,h:(lambda s_,c_,co:(N.setze_ziel(N.xor(co,h),0)))(*N.add_bits([ch(N,G.inv(a),b,Z0)],[P_(N,a,b)])), 'h=0 fest'),
 ('NICHT Spiegel: p=a&b, q=a|b koennen beide 1 sein',     3, lambda N,a,b,h:(lambda s_,c_,co:(N.setze_ziel(N.xor(co,h),0)))(*N.add_bits([ch(N,a,b,Z0)],[N.maj(a,b,Z1)])), 'R9b 0x, h bleibt offen'),
 ('NICHT Spiegel: p=a&b, q=a&c (andere Wurzeln)',         4, lambda N,a,b,c,h:(lambda s_,c_,co:(N.setze_ziel(N.xor(co,h),0)))(*N.add_bits([ch(N,a,b,Z0)],[ch(N,a,c,Z0)])), 'R9b 0x'),
 ('Beide 0 moeglich, beide 1 nie: p=a&~b, q=~a&~b (= ~a&~b) -> p+q<=1', 3, lambda N,a,b,h:(lambda s_,c_,co:(N.setze_ziel(N.xor(co,h),0)))(*N.add_bits([P_(N,a,b)],[N.maj(G.inv(a),G.inv(b),Z0)])), 'h=0 fest, R9b 1x (Differenz p^q = ~b nicht... = ~b affin)'),
]
prot=[lauf(*f) for f in F]; json.dump(prot,open('ERGEBNIS_GEGENPROBEN_R9B.json','w'),indent=1,default=str); print('alle R9b-Gegenproben: 0 verlorene Loesungen')
