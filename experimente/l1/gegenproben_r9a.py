"""Gegenproben R9a 'affine Differenz': ohne = D6+R9 (alle), mit = D6+R9+R9a (alle Paare). Alle Belegungen gegen Orakel; verloren muss 0 sein."""
import itertools, json, sys
import pruefstand as P, d6, gatter as G
def ch(N,e,f,g):
    z=N.xor(N.und(e,f),N.und(G.inv(e),g)); N.ch_kaestchen=getattr(N,'ch_kaestchen',[])+[(e,f,g,z)]; N.ch_runde=getattr(N,'ch_runde',[])+[0]; return z
def lauf(name,nfrei,bau,erw):
    zeile=dict(name=name,erwartung=erw)
    for tag,K in (('ohne',d6.D6_R9),('mit',d6.D6_R9a_Test)):
        N=P.Netz(name,nfrei); bau(N,*N.frei); D=K(); st,F,gr=D.laufen(N)
        alle=list(itertools.product((0,1),repeat=nfrei)); wahr=[b for b in alle if N.erfuellt(list(b))]; erl=[b for b in alle if D.erlaubt(N,list(b),F)]
        verloren=[w for w in wahr if w not in erl]
        zeile[tag]=dict(status=st,wahr=len(wahr),erlaubt=len(erl),verloren=len(verloren),R9a=gr['regeln'].get('R9a',0),protokoll=[x for x in gr['r9_protokoll'] if x[0]=='R9a'],bez=gr['beziehungen_ueber_freie_bits'])
        if verloren: print('FEHLER verloren',name,tag,verloren); sys.exit(3)
    o,m=zeile['ohne'],zeile['mit']; print('%-50s ohne %3d/%3d | mit %3d/%3d R9a=%d %s | Bez %s | %s'%(name,o['erlaubt'],o['wahr'],m['erlaubt'],m['wahr'],m['R9a'],[x[3] for x in m['protokoll']],m['bez'],erw)); return zeile
Z0,Z1=0,1
F=[
 ('Spiegel: p=a&~b (Maj(a,~b,0)), q=~a&b (Maj(~a,b,0)) -> p^q=a^b', 4, lambda N,a,b,h,d:(N.setze_ziel(N.xor(N.maj(a,G.inv(b),Z0),h),0), N.setze_ziel(N.xor(N.maj(G.inv(a),b,Z0),d),0)), 'affin, Bez h^d^a^b=0'),
 ('Spiegel vertauschte Eingaenge: Maj(~b,a,0) vs Ch(~a,b,0)', 4, lambda N,a,b,h,d:(N.setze_ziel(N.xor(N.maj(G.inv(b),a,Z0),h),0), N.setze_ziel(N.xor(ch(N,G.inv(a),b,Z0),d),0)), 'affin'),
 ('Negierte Ausgaenge: ~(a&~b) = Maj(~a,b,1) vs ~a&b', 4, lambda N,a,b,h,d:(N.setze_ziel(N.xor(N.maj(G.inv(a),b,Z1),h),0), N.setze_ziel(N.xor(N.maj(G.inv(a),b,Z0),d),0)), 'affin: (a|~b)^(~a&b)= a^b^1 -> Bez h^d^a^b=1'),
 ('a&b vs a|b: Differenz a^b', 4, lambda N,a,b,h,d:(N.setze_ziel(N.xor(ch(N,a,b,Z0),h),0), N.setze_ziel(N.xor(N.maj(a,b,Z1),d),0)), 'affin, Bez h^d^a^b=0'),
 ('a&b vs a^b (Ch(a,~b,b)): Differenz a|b NICHT affin', 4, lambda N,a,b,h,d:(N.setze_ziel(N.xor(ch(N,a,b,Z0),h),0), N.setze_ziel(N.xor(ch(N,a,G.inv(b),b),d),0)), 'nicht affin, R9a 0x'),
 ('Maj(a,b,c) vs Ch(a,b,c): Differenz nicht affin', 5, lambda N,a,b,c,h,d:(N.setze_ziel(N.xor(N.maj(a,b,c),h),0), N.setze_ziel(N.xor(ch(N,a,b,c),d),0)), 'nicht affin, R9a 0x'),
 ('Maj(a,b,c) vs Maj(a,b,~c): Differenz = a^b^1 affin', 5, lambda N,a,b,c,h,d:(N.setze_ziel(N.xor(N.maj(a,b,c),h),0), N.setze_ziel(N.xor(N.maj(a,b,G.inv(c)),d),0)), 'affin, Bez h^d^a^b=1'),
 ('Verschiedene Wurzeln a&b vs a&c: kein Vergleich', 5, lambda N,a,b,c,h,d:(N.setze_ziel(N.xor(ch(N,a,b,Z0),h),0), N.setze_ziel(N.xor(ch(N,a,c,Z0),d),0)), 'R9a 0x'),
 ('Unerfuellbar: p^q=a^b, aber Ziel h=d und a^b=1 (p=h,q=d)', 4, lambda N,a,b,h,d:(N.setze_ziel(N.xor(N.maj(a,G.inv(b),Z0),h),0), N.setze_ziel(N.xor(N.maj(G.inv(a),b,Z0),d),0), N.setze_ziel(N.xor(h,d),0), N.setze_ziel(N.xor(a,b),1)), '0 wahr, WIDERSPRUCH erwartet'),
]
prot=[lauf(*f) for f in F]; json.dump(prot,open('ERGEBNIS_GEGENPROBEN_R9A.json','w'),indent=1,default=str); print('alle R9a-Gegenproben: 0 verlorene Loesungen')
