"""Tabellenfilter mit belegten lokalen XOR-Beziehungen, ohne Annahmen."""
import itertools
import bitkern32 as bk

# Truth-row masks contain no task names, values, or proof parents. Bit r denotes
# row r of the existing operator table. At most sixteen rows fit one integer.
# The independent checker below deliberately keeps its separate Boolean routine.
def _operator_masks():
    result = {}
    for op, rows in bk.TABELLEN.items():
        width = len(rows[0])
        columns = tuple(sum(row[col] << r for r, row in enumerate(rows))
                        for col in range(width))
        parity_masks = [0] * (1 << width)
        for subset in range(1, 1 << width):
            bit = subset & -subset
            parity_masks[subset] = parity_masks[subset ^ bit] ^ columns[bit.bit_length()-1]
        result[op] = ((1 << len(rows))-1, columns, tuple(parity_masks))
    return result

_OPERATOR_MASKS = _operator_masks()


def anwenden(k):
    pairindex={};known=set(k.wert)
    for vs,par,nr in k.xor:
        unknown=frozenset(set(vs)-known)
        if 2<=len(unknown)<=5:pairindex.setdefault(unknown,[]).append((vs,par,nr))
    count=0
    k.rt_neue_relationen=0
    existing={(frozenset(v),p) for v,p,_ in k.xor}
    for op,names,tn in k.taf:
        unknown=sorted(n for n in set(names) if n not in k.wert)
        if len(unknown)<2:continue
        rel=[]
        for width in range(2,len(unknown)+1):
            for subset in itertools.combinations(unknown,width):
                for vs,par,nr in pairindex.get(frozenset(subset),[]):
                    if all(n in names or n in k.wert for n in vs):rel.append((vs,par,nr))
        if not rel and not getattr(k,"tabellen_rueckgabe",False):continue
        parentbits={n for n in names if n in k.wert}
        parentbits.update(n for vs,_,_ in rel for n in vs if n in k.wert)
        parents=[tn]+[n for _,_,n in rel]+[k.her[n] for n in sorted(parentbits)]

        allowed,columns,parity_masks = _OPERATOR_MASKS[op]
        # Alias columns must agree, just as dict(zip(...)) plus the original
        # alias check required. Map to the final occurrence, matching dict().
        positions={name:i for i,name in enumerate(names)}
        for i,name in enumerate(names):
            j=positions[name]
            if i!=j:allowed &= ~(columns[i]^columns[j])
            if name in k.wert:
                allowed &= columns[i] if k.wert[name] else ~columns[i]
        for vs,par,_ in rel:
            subset=0
            for name in vs:
                if name in positions:subset ^= 1 << positions[name]
                else:par ^= k.wert[name]
            mask=parity_masks[subset]
            allowed &= mask if par else ~mask
        if not allowed:
            k.buche('RT-R1 Relationstabelle',parents,'WIDERSPRUCH',tn)
            raise bk.Widerspruch('Tabelle und Beziehungen widersprechen sich')
        for name in unknown:
            ones=allowed & columns[positions[name]]
            if (not ones or ones==allowed) and k.bit(name) is None:
                k.setze(name,int(bool(ones)),'RT-R1 Relationstabelle',parents);count+=1
        if getattr(k,'tabellen_rueckgabe',False):
            for pair in itertools.combinations(unknown,2):
                if any(n in k.wert for n in pair):continue
                ones=allowed & (columns[positions[pair[0]]]^columns[positions[pair[1]]])
                if ones and ones!=allowed:continue
                parity=int(bool(ones));key=(frozenset(pair),parity)
                if key in existing:continue
                k.xor_gl(list(pair),parity,'RT-R2 Tabellenbeziehung',parents)
                existing.add(key);k.rt_neue_relationen+=1
    return count


def pruefen(nr,rule,parents,art,info,known,gl,taf,contradictions):
    if rule not in ('RT-R1 Relationstabelle','RT-R2 Tabellenbeziehung') or not parents or len(set(parents))!=len(parents):raise ValueError('Tabellenregel')
    tn=parents[0]
    if tn not in taf:raise ValueError('Geprüfte Tabelle fehlt')
    op,names=taf[tn]
    rel=[];fixed={}
    bynr={n:(name,value) for name,(value,n) in known.items()}
    for p in parents[1:]:
        if p in gl:rel.append(gl[p])
        elif p in bynr:
            name,value=bynr[p];fixed[name]=value
        else:raise ValueError('Elternteil weder Gleichung noch Bit')
    if any(n not in names and n not in fixed for vs,_ in rel for n in vs):raise ValueError('Unbelegtes externes Bit')
    # Unabhängige Wahrheitstafel direkt aus Booleschen Formeln.
    def function(xs):
        if op=='Maj':return int(sum(xs)>=2)
        if op=='Ch':return xs[1] if xs[0] else xs[2]
        if op=='Gleich':return int(xs[0] and xs[1]==xs[2])
        if op=='Kleiner':return int(xs[0] or (xs[1] and not xs[2] and xs[3]))
        if op=='Oder':return int(any(xs))
        raise ValueError('Unbekannter Operator')
    allowed=[]
    for xs in itertools.product((0,1),repeat=len(names)-1):
        row=xs+(function(xs),);vals=dict(zip(names,row))
        if any(vals[n]!=v for n,v in zip(names,row)):continue
        if any(n in vals and vals[n]!=v for n,v in fixed.items()):continue
        vals.update(fixed)
        if all(sum(vals[n] for n in vs)%2==p for vs,p in rel):allowed.append(vals)
    if rule=='RT-R2 Tabellenbeziehung':
        if art!='GL':raise ValueError('Beziehung muss GL sein')
        vs,par=info
        if len(vs)!=2 or list(vs)!=sorted(set(vs)) or any(n not in names for n in vs):raise ValueError('Nichtkanonische oder fremde Variablen')
        if type(par)!=int or par not in (0,1) or not allowed:raise ValueError('Ungültige Parität oder leere Grundlage')
        if any((r[vs[0]]^r[vs[1]])!=par for r in allowed):raise ValueError('Beziehung nicht erzwungen')
        gl[nr]=(tuple(vs),par);return
    if art=='WIDERSPRUCH':
        if info!=tn or allowed:raise ValueError('Widerspruch nicht belegt')
        contradictions.append(nr);return
    if art!='BIT':raise ValueError('Falsche Art')
    name,value=info
    if name not in names or name in known or type(value)!=int or not allowed or {r[name] for r in allowed}!={value}:
        raise ValueError('Bit nicht erzwungen')
    known[name]=(value,nr)
