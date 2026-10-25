"""Gegenproben R9 'gleiche Funktion': ohne = D6+R1b+R8c+R8m, mit = +R9 (alle Kaestchen). Alle Belegungen gegen Orakel; verloren muss 0 sein.
Zwei Kaestchen mit Ausgaengen m1, m2; Ziel-XOR mit freiem h macht den Alias an den freien Bits sichtbar; 'd' ist ein weiteres freies Bit."""
import itertools, json, sys
import pruefstand as P, d6, gatter as G
def ch(N,e,f,g):
    z=N.xor(N.und(e,f),N.und(G.inv(e),g)); N.ch_kaestchen=getattr(N,'ch_kaestchen',[])+[(e,f,g,z)]; N.ch_runde=getattr(N,'ch_runde',[])+[0]; return z
def lauf(name, nfrei, bau, erwartung):
    zeile=dict(name=name, erwartung=erwartung)
    for tag,K in (('ohne',d6.D6_R567bCM),('mit',d6.D6_R9)):
        N=P.Netz(name,nfrei); bau(N,*N.frei); D=K(); st,F,gr=D.laufen(N)
        alle=list(itertools.product((0,1),repeat=nfrei)); wahr=[b for b in alle if N.erfuellt(list(b))]; erl=[b for b in alle if D.erlaubt(N,list(b),F)]
        verloren=[w for w in wahr if w not in erl]
        zeile[tag]=dict(status=st,wahr=len(wahr),erlaubt=len(erl),verloren=len(verloren),R9=gr['regeln'].get('R9',0),protokoll=gr['r9_protokoll'])
        if verloren: print('FEHLER verloren',name,tag,verloren); sys.exit(3)
    o,m=zeile['ohne'],zeile['mit']; print('%-52s ohne %3d/%3d | mit %3d/%3d R9=%d %s | %s'%(name,o['erlaubt'],o['wahr'],m['erlaubt'],m['wahr'],m['R9'],m['protokoll'],erwartung)); return zeile
Z0=0; Z1=1
F=[
 ('a&b: Maj(a,b,0) = Maj(a,b,0)  -> gleich',          4, lambda N,a,b,h,d:(N.setze_ziel(N.xor(N.maj(a,b,Z0),h),0), N.setze_ziel(N.xor(N.maj(a,b,Z0),d),0)), 'Alias h=d (Hash-Consing macht die Knoten evtl. schon gleich)'),
 ('a&b: Ch(a,b,0) vs Maj(b,a,0)  -> gleich, vertauscht', 4, lambda N,a,b,h,d:(N.setze_ziel(N.xor(ch(N,a,b,Z0),h),0), N.setze_ziel(N.xor(N.maj(b,a,Z0),d),0)), 'Alias h=d, R9 1x'),
 ('a&b vs Maj(~a,~b,1)=~(a&b)     -> negiert gleich', 4, lambda N,a,b,h,d:(N.setze_ziel(N.xor(ch(N,a,b,Z0),h),0), N.setze_ziel(N.xor(N.maj(G.inv(a),G.inv(b),Z1),d),0)), 'Alias h=~d, R9 1x'),
 ('a&b vs a|b = Maj(a,b,1)        -> VERSCHIEDEN',    4, lambda N,a,b,h,d:(N.setze_ziel(N.xor(ch(N,a,b,Z0),h),0), N.setze_ziel(N.xor(N.maj(a,b,Z1),d),0)), 'kein Alias, R9 0x'),
 ('a&b vs ~a&b = Ch(a,0,b)        -> VERSCHIEDEN',    4, lambda N,a,b,h,d:(N.setze_ziel(N.xor(ch(N,a,b,Z0),h),0), N.setze_ziel(N.xor(ch(N,a,Z0,b),d),0)), 'kein Alias, R9 0x'),
 ('a&b vs a&c: andere Bits        -> VERSCHIEDEN',    5, lambda N,a,b,c,h,d:(N.setze_ziel(N.xor(ch(N,a,b,Z0),h),0), N.setze_ziel(N.xor(ch(N,a,c,Z0),d),0)), 'kein Alias, R9 0x'),
 ('Maj(a,b,c) vs Maj(c,a,b)       -> gleich, permutiert', 5, lambda N,a,b,c,h,d:(N.setze_ziel(N.xor(N.maj(a,b,c),h),0), N.setze_ziel(N.xor(N.maj(c,a,b),d),0)), 'Alias h=d'),
 ('Maj(a,b,c) vs Maj(~a,~b,~c)    -> negiert gleich', 5, lambda N,a,b,c,h,d:(N.setze_ziel(N.xor(N.maj(a,b,c),h),0), N.setze_ziel(N.xor(N.maj(G.inv(a),G.inv(b),G.inv(c)),d),0)), 'Alias h=~d'),
 ('Maj(a,b,c) vs Maj(~a,b,c)      -> VERSCHIEDEN',    5, lambda N,a,b,c,h,d:(N.setze_ziel(N.xor(N.maj(a,b,c),h),0), N.setze_ziel(N.xor(N.maj(G.inv(a),b,c),d),0)), 'kein Alias'),
 ('Ch(a,b,c) vs Ch(~a,c,b)        -> gleich (Auswahl gespiegelt)', 5, lambda N,a,b,c,h,d:(N.setze_ziel(N.xor(ch(N,a,b,c),h),0), N.setze_ziel(N.xor(ch(N,G.inv(a),c,b),d),0)), 'Alias h=d'),
 ('Ch(a,b,c) vs Ch(a,c,b)         -> VERSCHIEDEN',    5, lambda N,a,b,c,h,d:(N.setze_ziel(N.xor(ch(N,a,b,c),h),0), N.setze_ziel(N.xor(ch(N,a,c,b),d),0)), 'kein Alias'),
 ('Drittes Bit erst durch Ableitung fest: Maj(a,b,c), c=0 Ziel, vs Ch(a,b,0)', 5, lambda N,a,b,c,h,d:(N.setze_ziel(c,0), N.setze_ziel(N.xor(N.maj(a,b,c),h),0), N.setze_ziel(N.xor(ch(N,a,b,Z0),d),0)), 'Alias h=d, R9 1x (wie am N4r09)'),
 ('Gleiche Funktion ueber Alias-Wurzeln: b=e, Ch(a,b,0) vs Maj(a,e,0)', 5, lambda N,a,b,e,h,d:(N.setze_ziel(N.xor(b,e),0), N.setze_ziel(N.xor(ch(N,a,b,Z0),h),0), N.setze_ziel(N.xor(N.maj(a,e,Z0),d),0)), 'Alias h=d'),
]
prot=[lauf(*f) for f in F]; json.dump(prot,open('ERGEBNIS_GEGENPROBEN_R9.json','w'),indent=1,default=str); print('alle R9-Gegenproben: 0 verlorene Loesungen')
