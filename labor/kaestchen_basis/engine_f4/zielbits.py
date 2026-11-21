"""Sichere obere Nullbits aus einem belegten vollständigen H<=T-Vergleich."""
def anwenden(k):
    if k.bit('V_treffer') != 1:return 0
    targets=[nr for nr,(rule,parents,art,info) in enumerate(k.buch)
             if rule=='START ZIEL' and art=='WORT' and info[0]=='V_T']
    if len(targets)!=1:raise ValueError('Zielwort nicht eindeutig')
    target_nr=targets[0]
    _,target,width=k.buch[target_nr][3]
    if width!=256:raise ValueError('Vergleichsbreite')
    parents=[target_nr,k.her['V_treffer']]
    count=0
    for i in range(target.bit_length(),256):
        # Produzent nutzt Byteabbildung der bestehenden Verdrahtung.
        from sha_verdrahtung32 import hash_zahl_bits
        name=hash_zahl_bits([f'k2_H{j}' for j in range(8)])[i]
        if k.bit(name) is None:
            k.setze(name,0,f'Z-R1 Obergrenze {i}',parents);count+=1
    return count


def pruefen(nr,rule,parents,art,info,contract,words,known,cache):
    if not rule.startswith('Z-R1 Obergrenze ') or len(parents)!=2 or art!='BIT':
        raise ValueError('Zielregel oder Eltern ungültig')
    i=int(rule.split()[-1])
    if rule!=f'Z-R1 Obergrenze {i}' or not 0<=i<256:raise ValueError('Index')
    p,q=parents
    if p not in words:raise ValueError('Kein geprüftes Zielwort')
    w,target,width=words[p]
    if w!='V_T' or width!=256 or type(target)!=int or not 0<=target<2**256:
        raise ValueError('Fremdes Zielwort')
    if contract['worte'].get('V_T')!=(target,256):raise ValueError('Ziel nicht im Vertrag')
    if known.get('V_treffer')!=(1,q):raise ValueError('Trefferbedingung nicht belegt')
    if (1<<i)<=target:raise ValueError('Bit durch Obergrenze nicht festgelegt')
    # Prüfer rekonstruiert die gesamte Kette selbst, keine Produzentenfunktion.
    binding=(p,q,target)
    if binding not in cache:
        if contract['starts'].get('V_eq.256')!=1 or contract['starts'].get('V_lt.256')!=0:
            raise ValueError('Vergleichsstart fehlt')
        tables=contract['taf']
        for j in range(256):
            bit=8*(3-((j//8)%4))+j%8
            h=f'k2_H{j//32}.{bit}'
            if ('Gleich',(f'V_eq.{j+1}',h,f'V_T.{j}',f'V_eq.{j}')) not in tables:
                raise ValueError('Gleichheitskette fehlt')
            if ('Kleiner',(f'V_lt.{j+1}',f'V_eq.{j+1}',h,f'V_T.{j}',f'V_lt.{j}')) not in tables:
                raise ValueError('Kleinerkette fehlt')
        if ('Oder',('V_lt.0','V_eq.0','V_treffer')) not in tables:
            raise ValueError('Vergleichsausgang fehlt')
        cache.add(binding)
    name,value=info
    pos=8*(3-((i//8)%4))+i%8
    if name!=f'k2_H{i//32}.{pos}' or type(value)!=int or value!=0:
        raise ValueError('Falsche Bitzuordnung oder Wert')
    if name in contract.get('verdeckt',()):raise ValueError('Verdeckter Eingang')
    if name in known:raise ValueError('Wert überschrieben')
    known[name]=(0,nr)
