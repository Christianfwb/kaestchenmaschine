"""Gekoppeltes Zielteilwissen durch die letzte Feedforward-Addition.
Nur der allgemeine Fall H<2^192 und H5=e63+K modulo2^32.
"""
def anwenden(k):
    if k.bit('V_treffer')!=1:return 0
    nr=next(n for n,r in enumerate(k.buch) if r[0]=='START ZIEL' and r[2]=='WORT' and r[3][0]=='V_T')
    target=k.buch[nr][3][1]
    if target>=2**192:return 0
    matches=[(n,key) for n,key in k.additionen.values()
             if key[0]=='B-R5' and key[1:3]==('k2_H5','k2_e63')]
    if len(matches)!=1:raise ValueError('Feedforward nicht eindeutig')
    addnr,key=matches[0]; constant=key[3]
    possible=[]
    for upper in range((target>>176)+1):
        hlow=int.from_bytes(upper.to_bytes(2,'big'),'little')
        possible.append((hlow-constant)&65535)
    count=0
    for bit in range(16):
        values={(x>>bit)&1 for x in possible}
        name=f'k2_e63.{bit}'
        if len(values)==1 and k.bit(name) is None:
            k.setze(name,values.pop(),f'Z-R2 Teilintervall {bit}',[nr,k.her['V_treffer'],addnr]);count+=1
    return count


def pruefen(nr,rule,parents,art,info,contract,words,known,adds,cache):
    if len(parents)!=3 or art!='BIT':raise ValueError('Teilintervall-Eltern')
    bit=int(rule.split()[-1])
    if rule!=f'Z-R2 Teilintervall {bit}' or not 0<=bit<16:raise ValueError('Teilbit')
    p,q,a=parents
    # Dieselbe vollständig vertragsgebundene Vergleichskette wie Z-R1.
    # Prüfung auf einer Kopie: kein Hilfswert gelangt ins geprüfte Buch.
    from zielbits import pruefen as bound
    temporary=dict(known);temporary.pop('k2_H7.7',None)
    bound(nr,'Z-R1 Obergrenze 255',[p,q],'BIT',('k2_H7.7',0),contract,words,temporary,cache)
    target=words[p][1]
    if target>=2**192:raise ValueError('Projektionsbereich nicht erfüllt')
    matches=[entry for entry in adds.values() if entry[0]==a]
    if len(matches)!=1:raise ValueError('Keine geprüfte Addition')
    key=matches[0][1]
    if key[0]!='B-R5' or tuple(key[1:3])!=('k2_H5','k2_e63') or key not in contract['add']:
        raise ValueError('Fremde Feedforward-Addition')
    constant=key[3]
    # Zweitroutine: Projektionswerte über numerische Bytes und Modulo.
    values=set()
    limit=target//(2**176)
    for high in range(limit+1):
        lowword=256*(high%256)+high//256
        residue=(lowword-constant)%65536
        values.add((residue//(2**bit))%2)
    name,value=info
    if name!=f'k2_e63.{bit}' or type(value)!=int or values!={value}:
        raise ValueError('Teilwert nicht für alle zulässigen Werte bewiesen')
    if name in known or name in contract.get('verdeckt',()):raise ValueError('Überschreiben oder verdeckter Eingang')
    known[name]=(value,nr)
