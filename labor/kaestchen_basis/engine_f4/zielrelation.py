"""Gültige Paarbeziehungen zwischen bisher nicht feststehenden Zielteilbits."""
from itertools import combinations

def anwenden(k):
    if k.bit('V_treffer')!=1:return 0
    p=next(n for n,r in enumerate(k.buch) if r[0]=='START ZIEL' and r[2]=='WORT' and r[3][0]=='V_T')
    t=k.buch[p][3][1]
    if t>=2**192:return 0
    a,key=next((n,key) for n,key in k.additionen.values() if key[:3]==('B-R5','k2_H5','k2_e63'))
    domain=[(int.from_bytes(u.to_bytes(2,'big'),'little')-key[3])&65535 for u in range((t>>176)+1)]
    variable=[i for i in range(16) if len({(v>>i)&1 for v in domain})==2]
    existing={(frozenset(v),par) for v,par,_ in k.xor};count=0
    for i,j in combinations(variable,2):
        parity={((v>>i)^(v>>j))&1 for v in domain}
        names=sorted([f'k2_e63.{i}',f'k2_e63.{j}'])
        if len(parity)==1:
            par=parity.pop()
            if (frozenset(names),par) not in existing:
                k.xor_gl(names,par,'Z-R3 Zielpaar',[p,k.her['V_treffer'],a]);count+=1
    return count

def pruefen(nr,rule,parents,art,info,contract,words,known,adds,cache):
    if rule!='Z-R3 Zielpaar' or art!='GL' or len(parents)!=3:raise ValueError('Zielpaar-Form')
    p,q,a=parents
    from zielbits import pruefen as bound
    temp=dict(known);temp.pop('k2_H7.7',None)
    bound(nr,'Z-R1 Obergrenze 255',[p,q],'BIT',('k2_H7.7',0),contract,words,temp,cache)
    target=words[p][1]
    if target>=2**192:raise ValueError('Projektionsbereich')
    matches=[e for e in adds.values() if e[0]==a]
    if len(matches)!=1:raise ValueError('Additionsbeleg fehlt')
    key=matches[0][1]
    if tuple(key[:3])!=('B-R5','k2_H5','k2_e63') or key not in contract['add']:raise ValueError('Fremde Addition')
    names,par=info
    if len(names)!=2 or list(names)!=sorted(set(names)) or type(par)!=int or par not in (0,1):raise ValueError('Paar nicht kanonisch')
    positions=[]
    for n in names:
        if not n.startswith('k2_e63.'):raise ValueError('Fremdes Wort')
        i=int(n.rsplit('.',1)[1])
        if not 0<=i<16 or n!=f'k2_e63.{i}':raise ValueError('Bitindex')
        positions.append(i)
    for high in range(target//2**176+1):
        low=(256*(high%256)+high//256-key[3])%65536
        if sum((low//2**i)%2 for i in positions)%2!=par:raise ValueError('Paarbeziehung nicht allgemeingültig')
    return tuple(names),par
