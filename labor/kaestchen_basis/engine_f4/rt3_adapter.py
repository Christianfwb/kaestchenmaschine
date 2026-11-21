import time,re,types,itertools
import bitkern32 as bk
from schnitt32 import KernSchnitt

def anwenden(k, max_pairs=1200, seconds=15):
    # A fresh invocation-scoped index; never loaded from a book or shared task.
    if hasattr(k, '_rt3_scoped_gl_index'):
        raise RuntimeError('Nested RT-R3 index scope')
    k._rt3_scoped_gl_index = [set(), 0]
    try:
        return _anwenden(k, max_pairs, seconds)
    finally:
        del k._rt3_scoped_gl_index


def _anwenden(k, max_pairs=1200, seconds=15):
    import schnitt32
    schnitt32.MAXGL=getattr(k,'rt3_maxgl',5)
    if not hasattr(k,'rt3_protokoll'):
        k.maxfrei=8;k.erledigt=set();k.rt3_protokoll=[]
        k.zb.update(rt3_paare=0,rt3_ausgewertet=0,rt3_bits=0,rt3_xor2=0,rt3_xor3=0,rt3_widersprueche=0,rt3_gl_eingesetzt=0,rt3_gl_zu_gross=0,rt3_gl_ganz_frei=0,rt3_gl_erst_durch_einsetzen=0)
        for n in ('_gl_reduziert','_gl_vorhanden','schnitt'):setattr(k,n,types.MethodType(getattr(KernSchnitt,n),k))
    selected={}
    for tid,(op,names,nr) in enumerate(k.taf):
        if op not in ('Ch','Maj'):continue
        m=re.fullmatch(r'(k[12])_(ch|maj)([0-9]+)\.([0-9]+)',names[-1])
        if not m:continue
        prefix,kind,t,i=m.groups();t=int(t);i=int(i)
        if (prefix=='k1' and 3<=t<=8) or (prefix=='k2' and 55<=t<=63):selected[(prefix,kind,t,i)]=tid
    pairs=[]
    for (p,kind,t,i),tid in sorted(selected.items()):
        other=selected.get((p,kind,t+1,i))
        if other is not None:pairs.append((tid,other))
    end=min(k.deadline,time.monotonic()+seconds);rows=k._gl_reduziert()
    if not getattr(k,'rt3_einsetzen',True):rows=[r for r in rows if not r[4]]
    gl={}
    for row in rows:gl.setdefault(frozenset(row[0]),[]).append(row)
    new=0;visited=0
    for a,b in pairs:
        if time.monotonic()>end or visited>=max_pairs:raise bk.Budget('RT-R3 Paar-/Zeitgrenze')
        free=sorted({v for v in k.taf[a][1]+k.taf[b][1] if v not in k.wert})
        local=[]
        for width in range(2,min(schnitt32.MAXGL,len(free))+1):
            for vs in itertools.combinations(free,width):
                key=frozenset(vs)
                if key in gl:local.extend(gl[key])
        new+=k.schnitt(a,b,local);visited+=1
    return {'paare_besucht':visited,'neue_zeilen':new,'ausgewertet_gesamt':k.zb['rt3_ausgewertet']}

def pruefen(nr,rule,parents,art,info,known,gl,taf,contradictions):
    match=re.fullmatch(r'RT-R3 (bit|xor|widerspruch) \[([0-9]+),([0-9]+)\]',rule)
    if not match:raise ValueError('RT3-Regelform')
    mode,t1,t2=match.groups();t1=int(t1);t2=int(t2)
    if t1==t2 or t1 not in taf or t2 not in taf or list(parents[:2])!=[t1,t2]:raise ValueError('Tabelleneltern')
    if len(set(parents))!=len(parents):raise ValueError('Doppelte Eltern')
    tabs=[taf[t1],taf[t2]];names=sorted(set(tabs[0][1])|set(tabs[1][1]));fixed={};rels=[]
    bynr={n:(v,val) for v,(val,n) in known.items()}
    for p in parents[2:]:
        if p in gl:rels.append(gl[p])
        elif p in bynr:v,val=bynr[p];fixed[v]=val
        else:raise ValueError('Fremder Elternteil')
    free=[v for v in names if v not in fixed]
    if len(free)>8 or len(set(free)&set(tabs[0][1])&set(tabs[1][1]))<2:raise ValueError('Schnittumfang')
    reduced=[]
    used=set()
    for vs,p in rels:
        fv=[]
        for v in vs:
            if v in fixed:p^=fixed[v];used.add(v)
            else:fv.append(v)
        if not 2<=len(fv)<=5 or any(v not in free for v in fv):raise ValueError('Beziehungseingang nach Einsetzen')
        reduced.append((tuple(fv),p))
    if any(v not in names and v not in used for v in fixed):raise ValueError('Unbenutztes fremdes Bit')
    rels=reduced
    def fn(op,x):
        if op=='Ch':return x[1] if x[0] else x[2]
        if op=='Maj':return int(sum(x)>=2)
        raise ValueError('Nur Ch/Maj freigegeben')
    allowed=[]
    for bits in itertools.product((0,1),repeat=len(free)):
        v=dict(zip(free,bits));v.update(fixed)
        if all(fn(op,[v[n] for n in ns[:-1]])==v[ns[-1]] for op,ns in tabs) and all(sum(v[n] for n in vs)%2==p for vs,p in rels):allowed.append(v)
    if mode=='widerspruch':
        if art!='WIDERSPRUCH' or allowed:raise ValueError('Falscher Widerspruch')
        contradictions.append(nr);return
    if not allowed:raise ValueError('Leere Grundlage')
    if mode=='bit':
        v,val=info
        if art!='BIT' or v not in free or v in known or type(val)!=int or {x[v] for x in allowed}!={val}:raise ValueError('Bit nicht erzwungen')
        known[v]=(val,nr);return
    vs,p=info
    if art!='GL' or len(vs) not in (2,3) or len(set(vs))!=len(vs) or any(v not in free for v in vs) or type(p)!=int or p not in (0,1):raise ValueError('GL-Form')
    if any(sum(x[v] for v in vs)%2!=p for x in allowed):raise ValueError('GL nicht erzwungen')
    gl[nr]=(tuple(vs),p)
