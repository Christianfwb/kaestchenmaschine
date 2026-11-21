"""Begrenztes Zusammenschalten bereits belegter XOR-Gleichungen.
Bekannte Bits bleiben in der Rohgleichung und damit in der Beweiskette.
Keine Welt, kein Kandidat und kein unbekanntes Bit wird eingesetzt.
"""
def verbinden(k, max_neu=2000, max_eltern=64, max_breite=128):
    import time
    import bitkern32 as bk
    vorhandene={(frozenset(v),p) for v,p,_ in k.xor}
    known=set(k.wert)
    pivots={};neu=0;begrenzungen=0
    for idx,(vs,par,nr) in enumerate(list(k.xor)):
        if idx%256==0 and time.monotonic()>k.deadline:
            raise bk.Budget('Zeitgrenze der Verbindungsanalyse')
        names=set(vs);parents={nr};unknown=names-known
        if not 2<=len(unknown)<=16:continue
        combined=False
        while unknown:
            pivot=min(unknown)
            if pivot not in pivots:
                pivots[pivot]=(set(names),par,set(parents));break
            ov,op,oe=pivots[pivot]
            nn=names^ov;pp=parents^oe
            if len(nn)>max_breite or len(pp)>max_eltern:
                begrenzungen+=1;break
            names,par,parents=nn,par^op,pp
            unknown=names-known;combined=True
        key=(frozenset(names),par)
        if combined and names and parents and key not in vorhandene:
            k.xor_gl(sorted(names),par,'RB-R1 XOR-Elimination',sorted(parents))
            vorhandene.add(key);neu+=1
            if neu>=max_neu:
                return {'neu':neu,'grenze':True,'breitengrenzen':begrenzungen}
    return {'neu':neu,'grenze':False,'breitengrenzen':begrenzungen}


def w22_anschliessen(k):
    # Originale, gerichtete GL-Definitionen; keine bereits eliminierten Zeilen.
    defs={}
    for vs,p,n in k.xor:
        if vs and not k.buch[n][0].startswith('RB-') and vs[0].startswith('k1_'):
            defs.setdefault(vs[0],n)
    allowed=('k1_W20.','k1_s120.','k1_y120.','k1_y220.',
             'k1_s122.','k1_y122.','k1_y222.')
    rows=[]
    existing={(frozenset(v),p) for v,p,_ in k.xor}
    for i in range(7):
        start=defs.get(f'k1_W22.{i}')
        if start is None:continue
        names=set(k.buch[start][3][0]);par=k.buch[start][3][1];parents={start}
        for step in range(256):
            options=sorted(n for n in names if n.startswith(allowed) and n in defs)
            if not options:break
            n=defs[options[0]];vs,p=k.buch[n][3]
            names.symmetric_difference_update(vs);par^=p;parents.symmetric_difference_update({n})
        else:raise ValueError('W22-Verbindung nicht abgeschlossen')
        if (frozenset(names),par) not in existing:
            rows.append(k.xor_gl(sorted(names),par,'RB-R1 XOR-Elimination',sorted(parents)))
    return rows


def saettigen(k, runden=8):
    log=[]
    w22=w22_anschliessen(k);k.fixpunkt()
    for turn in range(runden):
        before=len(k.wert);info=verbinden(k);k.fixpunkt()
        if getattr(k,'relationstabellen_an',False):
            from relationstabellen import anwenden as rt_anwenden
            info['tabellen_neue_bits']=rt_anwenden(k);info['tabellen_neue_relationen']=k.rt_neue_relationen;k.fixpunkt()
        info.update(runde=turn+1,zusaetzliche_bits=len(k.wert)-before);log.append(info)
        if not info['neu'] and not info.get('tabellen_neue_relationen',0) and len(k.wert)==before:break
    return {'w22_verbindungen':len(w22),'runden':log,
            'vollstaendig':bool(log and not log[-1]['neu'] and not any(x['breitengrenzen'] or x['grenze'] for x in log)),
            'hinweis':'Begrenzte Elimination, keine Behauptung mathematisch vollständiger Schlussfolgerung.'}
